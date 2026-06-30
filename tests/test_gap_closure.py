"""Focused tests for ruler gap closure features."""

from pathlib import Path

import pandas as pd

from api.credit_decision.analysis import (
    CreditProfileInput,
    calculate_credit_profile_score,
    compare_counterparties,
    optimize_payment_terms,
)
from api.market_data.commodity_factors import analyze_commodity_factors
from api.market_data.regime_detection import detect_market_regimes
from api.monitoring.router import router as monitoring_router
from api.monitoring.service import generate_alerts_from_records
from api.reporting.model_validation import build_model_validation_report


def market_frame():
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    rows = []
    for asset, start in {"brent_oil": 80.0, "wti_oil": 75.0, "heating_oil_proxy": 2.5}.items():
        for idx, dt in enumerate(dates):
            rows.append({"date": dt, "asset": asset, "price": start * (1 + 0.001 * idx)})
    return pd.DataFrame(rows)


def test_commodity_factor_engine_outputs_required_risk_factors():
    result = analyze_commodity_factors(market_frame(), ["brent_oil", "wti_oil", "heating_oil_proxy"], 20)
    assert result.model_name == "Commodity Risk Factor Engine"
    assert "brent_oil" in result.latest_log_returns
    assert "brent_oil" in result.rolling_volatility
    assert result.spread_analysis
    assert result.correlation_matrix["brent_oil"]["brent_oil"] == 1.0


def test_scorecard_comparison_and_tenor_optimizer_are_directional():
    strong = CreditProfileInput(
        counterparty_id=1,
        counterparty_name="Strong",
        current_ratio=1.8,
        debt_to_ebitda=2.0,
        interest_coverage=5.0,
        operating_margin=0.12,
        probability_of_default=0.02,
        loss_given_default=0.35,
        exposure_at_default=1_000_000,
        collateral_strength=0.8,
        payment_tenor_days=45,
    )
    weak = CreditProfileInput(
        counterparty_id=2,
        counterparty_name="Weak",
        current_ratio=0.8,
        debt_to_ebitda=6.0,
        interest_coverage=1.0,
        operating_margin=-0.02,
        probability_of_default=0.18,
        loss_given_default=0.75,
        exposure_at_default=1_000_000,
        collateral_strength=0.0,
        payment_tenor_days=90,
        market_stress_index=85,
    )
    strong_score = calculate_credit_profile_score(strong)
    weak_score = calculate_credit_profile_score(weak)
    comparison = compare_counterparties([strong, weak])
    optimizer = optimize_payment_terms(weak, [30, 45, 60, 90])

    assert strong_score.score < weak_score.score
    assert comparison.safer_counterparty_id == 1
    losses = [option.expected_loss for option in optimizer.options]
    assert losses == sorted(losses)
    assert optimizer.recommended_tenor_days in {30, 45, 60, 90}


def test_monitoring_covers_anomaly_payment_and_news_sources():
    alerts, warnings = generate_alerts_from_records(
        anomaly_outputs=[{"counterparty_id": 1, "isolation_forest_score": -0.4}],
        payment_delays=[{"counterparty_id": 1, "payment_delay_days": 31}],
        news_sentiment=[{"counterparty_id": 1, "news_sentiment_score": -0.7}],
    )
    reasons = {alert.alert_reason for alert in alerts}
    assert warnings == []
    assert "Isolation Forest anomaly score indicates unusual deterioration." in reasons
    assert "Payment delay exceeds monitoring threshold." in reasons
    assert "Negative news sentiment exceeds monitoring threshold." in reasons


def test_model_validation_report_and_notebook_artifact_exist():
    report = build_model_validation_report()
    assert report.metrics
    assert report.sanity_checks["higher_pd_bucket_defaults_more_often"] is True
    assert "V2 Model Validation Report" in report.markdown_report
    assert Path("notebooks/model_validation_report.ipynb").exists()


def test_regime_detector_supports_gmm_and_hmm_modes():
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    features = pd.DataFrame(
        {
            "vix_zscore": list([0.1] * 20) + list([2.0] * 20),
            "brent_return_zscore": list([0.0] * 20) + list([1.8] * 20),
            "dxy_return_zscore": list([0.1] * 20) + list([1.0] * 20),
        },
        index=dates,
    )
    stress = pd.DataFrame({"date": dates, "stress_index": list([25.0] * 20) + list([85.0] * 20)})
    gmm = detect_market_regimes(features, stress, n_regimes=2, model_type="gmm")
    hmm = detect_market_regimes(features, stress, n_regimes=2, model_type="hmm")
    assert not gmm.history.empty
    assert not hmm.history.empty
    assert set(gmm.history["regime_characteristics"].iloc[0]) >= {"model_type"}
def test_monitoring_analyze_route_is_registered():
    route_paths = {route.path for route in monitoring_router.routes}
    assert "/api/v1/monitoring/alerts/analyze" in route_paths

