"""
Early warning and alert generation for V2.

Business purpose:
Flag deteriorating counterparties and portfolio risk conditions before default.

Inputs:
Stored PD/LGD/EAD/loss estimates, scenario results, simulation results, stress
index history, and portfolio concentration records when available.

Outputs:
Explainable alerts with severity, reason, triggering metric/value, threshold,
data source, rule version, and timestamp.

Method:
Deterministic threshold and baseline rules. No alert is created from missing or
invented data.

Assumptions:
Default thresholds are student-project risk appetite settings and can be moved
to policy/database configuration later.

Limitations:
This is a rules-based early warning engine, not a production surveillance
system or legally approved credit monitoring policy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Iterable, Optional
from uuid import uuid5, NAMESPACE_URL

import numpy as np
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

ALERT_MODEL_VERSION = "early_warning_rules_v1.0"

DEFAULT_THRESHOLDS = {
    "high_pd": 0.15,
    "watch_pd": 0.10,
    "high_lgd": 0.70,
    "high_expected_loss_quantile": 0.90,
    "largest_counterparty_share_pct": 15.0,
    "stress_loss": 1_000_000.0,
    "var_95": 500_000.0,
    "stress_index": 80.0,
    "zscore": 2.0,
    "isolation_forest_score": -0.20,
    "payment_delay_days": 15.0,
    "news_sentiment": -0.35,
}


@dataclass
class RiskAlert:
    severity: str
    category: str
    alert_reason: str
    triggering_metric: str
    triggering_value: float
    data_source: str
    counterparty_id: Optional[int] = None
    threshold: Optional[float] = None
    comparison_baseline: Optional[float] = None
    model_version: str = ALERT_MODEL_VERSION
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    alert_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.alert_id is None:
            key = "|".join([
                str(self.counterparty_id or "portfolio"),
                self.category,
                self.triggering_metric,
                f"{self.triggering_value:.8f}",
                self.model_version,
            ])
            self.alert_id = str(uuid5(NAMESPACE_URL, key))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        number = float(value)
        if np.isnan(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _records(values: Optional[Iterable[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [dict(row) for row in values or []]


def _quantile(values: list[float], q: float) -> Optional[float]:
    if not values:
        return None
    return float(np.quantile(np.array(values, dtype=float), q))


def generate_alerts_from_records(
    predictions: Optional[Iterable[dict[str, Any]]] = None,
    loss_estimates: Optional[Iterable[dict[str, Any]]] = None,
    portfolio: Optional[Iterable[dict[str, Any]]] = None,
    scenario_results: Optional[Iterable[dict[str, Any]]] = None,
    simulations: Optional[Iterable[dict[str, Any]]] = None,
    stress_history: Optional[Iterable[dict[str, Any]]] = None,
    anomaly_outputs: Optional[Iterable[dict[str, Any]]] = None,
    payment_delays: Optional[Iterable[dict[str, Any]]] = None,
    news_sentiment: Optional[Iterable[dict[str, Any]]] = None,
    thresholds: Optional[dict[str, float]] = None,
) -> tuple[list[RiskAlert], list[str]]:
    """Create deterministic alerts from already-loaded records."""
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    warnings: list[str] = []
    alerts: list[RiskAlert] = []

    prediction_rows = _records(predictions)
    loss_rows = _records(loss_estimates)
    portfolio_rows = _records(portfolio)
    scenario_rows = _records(scenario_results)
    simulation_rows = _records(simulations)
    stress_rows = _records(stress_history)
    anomaly_rows = _records(anomaly_outputs)
    payment_delay_rows = _records(payment_delays)
    sentiment_rows = _records(news_sentiment)

    if not any([prediction_rows, loss_rows, portfolio_rows, scenario_rows, simulation_rows, stress_rows, anomaly_rows, payment_delay_rows, sentiment_rows]):
        warnings.append("No monitoring source records supplied; no alerts generated.")
        return [], warnings

    for row in prediction_rows:
        pd_value = _safe_float(row.get("probability_of_default", row.get("pd")))
        if pd_value is None:
            continue
        counterparty_id = _safe_int(row.get("counterparty_id"))
        if pd_value > limits["high_pd"]:
            alerts.append(RiskAlert(
                severity="HIGH",
                category="Credit Risk",
                alert_reason="Probability of default exceeds high-risk threshold.",
                triggering_metric="probability_of_default",
                triggering_value=pd_value,
                threshold=limits["high_pd"],
                counterparty_id=counterparty_id,
                data_source="pd_model_predictions",
            ))
        elif pd_value > limits["watch_pd"]:
            alerts.append(RiskAlert(
                severity="MEDIUM",
                category="Credit Watch",
                alert_reason="Probability of default exceeds watch threshold.",
                triggering_metric="probability_of_default",
                triggering_value=pd_value,
                threshold=limits["watch_pd"],
                counterparty_id=counterparty_id,
                data_source="pd_model_predictions",
            ))

        stress_value = _safe_float(row.get("market_stress_index"))
        if stress_value is not None and stress_value > limits["stress_index"]:
            alerts.append(RiskAlert(
                severity="MEDIUM",
                category="Market Stress",
                alert_reason="Counterparty market stress index exceeds stress threshold.",
                triggering_metric="market_stress_index",
                triggering_value=stress_value,
                threshold=limits["stress_index"],
                counterparty_id=counterparty_id,
                data_source="pd_model_predictions",
            ))

    expected_losses = [
        value for value in (_safe_float(row.get("expected_loss")) for row in loss_rows)
        if value is not None
    ]
    el_baseline = _quantile(expected_losses, limits["high_expected_loss_quantile"])
    for row in loss_rows:
        counterparty_id = _safe_int(row.get("counterparty_id"))
        lgd = _safe_float(row.get("predicted_lgd", row.get("loss_given_default")))
        if lgd is not None and lgd > limits["high_lgd"]:
            alerts.append(RiskAlert(
                severity="HIGH",
                category="Loss Severity",
                alert_reason="LGD exceeds high loss-severity threshold.",
                triggering_metric="predicted_lgd",
                triggering_value=lgd,
                threshold=limits["high_lgd"],
                counterparty_id=counterparty_id,
                data_source="loss_estimates",
            ))
        expected_loss = _safe_float(row.get("expected_loss"))
        if expected_loss is not None and el_baseline is not None and expected_loss > el_baseline:
            alerts.append(RiskAlert(
                severity="HIGH",
                category="Expected Loss",
                alert_reason="Expected loss is above portfolio quantile baseline.",
                triggering_metric="expected_loss",
                triggering_value=expected_loss,
                comparison_baseline=el_baseline,
                counterparty_id=counterparty_id,
                data_source="loss_estimates",
            ))

    exposure_rows = portfolio_rows or loss_rows
    exposures = [
        _safe_float(row.get("exposure", row.get("exposure_at_default")), 0.0) or 0.0
        for row in exposure_rows
    ]
    total_exposure = sum(exposures)
    if total_exposure > 0 and exposures:
        largest = max(exposures)
        share = 100.0 * largest / total_exposure
        if share > limits["largest_counterparty_share_pct"]:
            largest_idx = exposures.index(largest)
            largest_row = exposure_rows[largest_idx]
            alerts.append(RiskAlert(
                severity="MEDIUM",
                category="Concentration",
                alert_reason="Largest counterparty exceeds portfolio concentration threshold.",
                triggering_metric="largest_counterparty_share_pct",
                triggering_value=share,
                threshold=limits["largest_counterparty_share_pct"],
                counterparty_id=_safe_int(largest_row.get("counterparty_id")),
                data_source="portfolio_exposure",
            ))

    for row in scenario_rows:
        stress_loss = _safe_float(row.get("expected_loss"))
        if stress_loss is not None and stress_loss > limits["stress_loss"]:
            alerts.append(RiskAlert(
                severity="HIGH",
                category="Stress Testing",
                alert_reason="Scenario expected loss exceeds stress loss threshold.",
                triggering_metric="scenario_expected_loss",
                triggering_value=stress_loss,
                threshold=limits["stress_loss"],
                data_source="scenario_results",
                metadata={"scenario_type": row.get("scenario_type"), "run_id": row.get("run_id")},
            ))

    latest_sim = simulation_rows[0] if simulation_rows else None
    if latest_sim:
        var_95 = _safe_float(latest_sim.get("var_95", latest_sim.get("credit_var_95")))
        if var_95 is not None and var_95 > limits["var_95"]:
            alerts.append(RiskAlert(
                severity="MEDIUM",
                category="Portfolio VaR",
                alert_reason="Portfolio VaR exceeds configured threshold.",
                triggering_metric="var_95",
                triggering_value=var_95,
                threshold=limits["var_95"],
                data_source="simulation_results",
                metadata={"run_id": latest_sim.get("run_id")},
            ))

    latest_stress = stress_rows[0] if stress_rows else None
    if latest_stress:
        stress_index = _safe_float(latest_stress.get("stress_index"))
        if stress_index is not None and stress_index > limits["stress_index"]:
            alerts.append(RiskAlert(
                severity="MEDIUM",
                category="Market Stress",
                alert_reason="Latest market stress index exceeds stress threshold.",
                triggering_metric="stress_index",
                triggering_value=stress_index,
                threshold=limits["stress_index"],
                data_source="stress_index_history",
            ))

    for row in prediction_rows + loss_rows:
        zscore = _safe_float(row.get("metric_zscore", row.get("z_score")))
        if zscore is not None and abs(zscore) > limits["zscore"]:
            alerts.append(RiskAlert(
                severity="MEDIUM",
                category="Anomaly",
                alert_reason="Metric z-score exceeds anomaly threshold.",
                triggering_metric="z_score",
                triggering_value=zscore,
                threshold=limits["zscore"],
                counterparty_id=_safe_int(row.get("counterparty_id")),
                data_source=str(row.get("data_source", "monitoring_records")),
            ))


    for row in anomaly_rows:
        score = _safe_float(row.get("anomaly_score", row.get("isolation_forest_score")))
        if score is not None and score < limits["isolation_forest_score"]:
            alerts.append(RiskAlert(
                severity="MEDIUM",
                category="Anomaly",
                alert_reason="Isolation Forest anomaly score indicates unusual deterioration.",
                triggering_metric="isolation_forest_score",
                triggering_value=score,
                threshold=limits["isolation_forest_score"],
                counterparty_id=_safe_int(row.get("counterparty_id")),
                data_source=str(row.get("data_source", "anomaly_model_outputs")),
                metadata={"model_type": row.get("model_type", "IsolationForest")},
            ))

    for row in payment_delay_rows:
        delay_days = _safe_float(row.get("delay_days", row.get("payment_delay_days")))
        if delay_days is not None and delay_days > limits["payment_delay_days"]:
            alerts.append(RiskAlert(
                severity="MEDIUM" if delay_days < 30 else "HIGH",
                category="Payment Behavior",
                alert_reason="Payment delay exceeds monitoring threshold.",
                triggering_metric="payment_delay_days",
                triggering_value=delay_days,
                threshold=limits["payment_delay_days"],
                counterparty_id=_safe_int(row.get("counterparty_id")),
                data_source=str(row.get("data_source", "payment_delay_history")),
                metadata={"invoice_id": row.get("invoice_id")},
            ))

    for row in sentiment_rows:
        sentiment = _safe_float(row.get("sentiment_score", row.get("news_sentiment_score")))
        if sentiment is not None and sentiment < limits["news_sentiment"]:
            alerts.append(RiskAlert(
                severity="LOW" if sentiment > -0.6 else "MEDIUM",
                category="News Sentiment",
                alert_reason="Negative news sentiment exceeds monitoring threshold.",
                triggering_metric="news_sentiment_score",
                triggering_value=sentiment,
                threshold=limits["news_sentiment"],
                counterparty_id=_safe_int(row.get("counterparty_id")),
                data_source=str(row.get("data_source", "news_sentiment_feed")),
                metadata={"headline": row.get("headline")},
            ))
    alerts.sort(key=lambda alert: (alert.severity != "HIGH", alert.category, alert.counterparty_id or 0))
    return alerts, warnings


def _fetch_mappings(db: Session, query: str) -> list[dict[str, Any]]:
    try:
        return [dict(row) for row in db.execute(text(query)).mappings().all()]
    except SQLAlchemyError:
        return []


def generate_alerts_from_database(db: Session) -> tuple[list[RiskAlert], list[str]]:
    """Load latest backend records and generate alerts without dashboard dependencies."""
    predictions = _fetch_mappings(db, """
        SELECT counterparty_id, probability_of_default, market_stress_index
        FROM pd_model_predictions
        ORDER BY created_at DESC
        LIMIT 200
    """)
    loss_estimates = _fetch_mappings(db, """
        SELECT counterparty_id, predicted_lgd, exposure_at_default, expected_loss
        FROM loss_estimates
        ORDER BY created_at DESC
        LIMIT 200
    """)
    scenarios = _fetch_mappings(db, """
        SELECT run_id, scenario_type, expected_loss
        FROM scenario_results
        ORDER BY created_at DESC
        LIMIT 50
    """)
    simulations = _fetch_mappings(db, """
        SELECT run_id, var_95, expected_shortfall_95
        FROM simulation_results
        ORDER BY created_at DESC
        LIMIT 1
    """)
    stress = _fetch_mappings(db, """
        SELECT stress_index
        FROM stress_index_history
        ORDER BY date DESC
        LIMIT 1
    """)
    return generate_alerts_from_records(
        predictions=predictions,
        loss_estimates=loss_estimates,
        scenario_results=scenarios,
        simulations=simulations,
        stress_history=stress,
    )


def summarize_alerts(alerts: list[RiskAlert]) -> dict[str, int]:
    severities = [alert.severity for alert in alerts]
    return {
        "alert_count": len(alerts),
        "high_count": severities.count("HIGH"),
        "medium_count": severities.count("MEDIUM"),
        "low_count": severities.count("LOW"),
    }





