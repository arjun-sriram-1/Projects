"""
Probability of Default Model Layer

Business purpose:
Estimate counterparty probability of default for fuel trade credit decisions by
combining a structural Merton-style PD anchor with an ML/logistic proxy
cross-check and explicit market vulnerability mapping.

Inputs:
Phase 2 extracted financials, Phase 3 financial ratios, and Phase 4 market
stress/regime outputs.

Outputs:
Structural PD, ML proxy PD, final blended PD, distance-to-default, model
divergence flag, vulnerability scores, feature contributions, assumptions, and
warnings.

Method:
Structural PD uses the Merton distance-to-default formula. Asset value and debt
threshold are estimated from stored financial statements. Asset volatility is a
transparent proxy from leverage, market stress, and commodity/FX vulnerability.
The ML cross-check is a documented logistic proxy over financial ratios and
stress drivers. It is not the sole decision-maker.

Assumptions:
Private-company asset values use accounting total assets. Time horizon defaults
to one year. Risk-free rate defaults to the latest 10Y yield proxy when present,
otherwise a documented 4 percent fallback.

Limitations:
The logistic proxy is a student-project validation layer, not an agency rating
model. It should be replaced or retrained if real default labels become
available.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from math import exp, log, sqrt
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from scipy.stats import norm

from api.calibration.artifacts import pd_blend_config
from api.financials.trends import calculate_trend_risk_overlay


PD_MODEL_VERSION = "pd_merton_logistic_proxy_v1.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_PD_MODEL_PATH = PROJECT_ROOT / "data" / "models" / "historical_pd_model.pkl"


@dataclass
class MarketContext:
    stress_index: float = 50.0
    stress_level: str = "Unknown"
    market_regime: str = "Unknown"
    risk_free_rate: float = 0.04
    oil_volatility_zscore: float = 0.0
    fuel_return_zscore: float = 0.0
    crack_spread_zscore: float = 0.0
    fx_return_zscore: float = 0.0
    freight_loss_zscore: float = 0.0
    inventory_build_zscore: float = 0.0
    opec_production_cut_zscore: float = 0.0
    pmi_weakness_zscore: float = 0.0
    iata_traffic_loss_zscore: float = 0.0
    data_reference: str = "stress_index_history/latest;market_regime_history/latest"


@dataclass
class VulnerabilityScores:
    commodity_sensitivity_score: float
    fx_sensitivity_score: float
    macro_sensitivity_score: float
    vulnerability_notes: list[str]


@dataclass
class PDPredictionResult:
    run_id: str
    counterparty_id: int
    financial_metrics_id: Optional[int]
    financial_ratios_id: Optional[int]
    model_name: str = "Merton structural PD + logistic proxy cross-check"
    model_version: str = PD_MODEL_VERSION
    structural_pd: float = 0.0
    ml_pd: float = 0.0
    final_pd: float = 0.0
    classification_label: str = "Unknown"
    model_confidence: float = 0.0
    model_disagreement: bool = False
    pd_divergence: float = 0.0
    distance_to_default: Optional[float] = None
    asset_value_proxy: Optional[float] = None
    debt_threshold: Optional[float] = None
    asset_volatility: Optional[float] = None
    risk_free_rate: Optional[float] = None
    time_horizon_years: float = 1.0
    commodity_sensitivity_score: Optional[float] = None
    fx_sensitivity_score: Optional[float] = None
    macro_sensitivity_score: Optional[float] = None
    market_stress_index: Optional[float] = None
    market_regime: Optional[str] = None
    feature_contributions: Dict[str, float] = field(default_factory=dict)
    model_assumptions: Dict[str, Any] = field(default_factory=dict)
    input_data_reference: Dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get(source: Any, field_name: str, default: Optional[float] = None) -> Optional[float]:
    if source is None:
        return default
    if isinstance(source, dict):
        return _to_float(source.get(field_name, default))
    return _to_float(getattr(source, field_name, default))


def _clip_probability(value: float) -> float:
    return float(np.clip(value, 0.000001, 0.999))


def _safe_ratio(value: Optional[float], fallback: float) -> float:
    if value is None or not np.isfinite(value):
        return fallback
    return value


def _leverage_ratio_for_pd(value: Optional[float], fallback: float = 1.5) -> float:
    """Normalize leverage ratios so negative equity is treated as distress."""
    ratio = _safe_ratio(value, fallback)
    if ratio <= 0:
        return 8.0
    return ratio


def classify_pd(pd_value: float) -> str:
    """Map PD to internal proxy grade labels, not agency ratings."""
    if pd_value < 0.01:
        return "A"
    if pd_value < 0.03:
        return "BBB"
    if pd_value < 0.07:
        return "BB"
    if pd_value < 0.15:
        return "B"
    return "CCC"


def calculate_distance_to_default(
    asset_value_proxy: float,
    debt_threshold: float,
    asset_volatility: float,
    risk_free_rate: float,
    time_horizon_years: float,
) -> float:
    """Merton distance-to-default."""
    asset_value_proxy = max(asset_value_proxy, 1.0)
    debt_threshold = max(debt_threshold, 1.0)
    asset_volatility = max(asset_volatility, 0.01)
    time_horizon_years = max(time_horizon_years, 1 / 365)
    numerator = log(asset_value_proxy / debt_threshold) + (
        risk_free_rate - 0.5 * asset_volatility**2
    ) * time_horizon_years
    denominator = asset_volatility * sqrt(time_horizon_years)
    return float(numerator / denominator)


def calculate_structural_pd(
    asset_value_proxy: float,
    debt_threshold: float,
    asset_volatility: float,
    risk_free_rate: float = 0.04,
    time_horizon_years: float = 1.0,
) -> tuple[float, float]:
    """Return structural PD and distance-to-default."""
    dd = calculate_distance_to_default(
        asset_value_proxy,
        debt_threshold,
        asset_volatility,
        risk_free_rate,
        time_horizon_years,
    )
    return _clip_probability(float(norm.cdf(-dd))), dd


def calculate_vulnerability_scores(
    counterparty_type: Optional[str],
    market_context: MarketContext,
) -> VulnerabilityScores:
    """Map counterparty type to commodity, FX, and macro vulnerability."""
    cp_type = (counterparty_type or "fuel_trader").lower()
    stress_component = np.clip((market_context.stress_index - 50.0) / 50.0, 0, 1)
    oil_component = np.clip(
        (
            market_context.oil_volatility_zscore
            + market_context.fuel_return_zscore
            + market_context.crack_spread_zscore
            + market_context.inventory_build_zscore
            + market_context.opec_production_cut_zscore
        )
        / 7,
        0,
        1,
    )
    fx_component = np.clip(market_context.fx_return_zscore / 3, 0, 1)
    demand_component = np.clip(
        (
            market_context.freight_loss_zscore
            + market_context.pmi_weakness_zscore
            + market_context.iata_traffic_loss_zscore
        )
        / 5,
        0,
        1,
    )

    notes = []
    if "airline" in cp_type:
        commodity = 0.65 + 0.25 * oil_component
        fx = 0.45 + 0.25 * fx_component
        macro = 0.40 + 0.35 * max(stress_component, demand_component)
        notes.append("Airline mapped as high jet fuel, crack-spread, USD, and passenger-demand sensitive counterparty.")
    elif "ship" in cp_type or "marine" in cp_type:
        commodity = 0.55 + 0.20 * oil_component
        fx = 0.40 + 0.20 * fx_component
        macro = 0.45 + 0.30 * max(stress_component, demand_component)
        notes.append("Shipping/marine mapped to marine fuel, freight demand, PMI, and supply-cycle sensitivity.")
    else:
        commodity = 0.40 + 0.25 * oil_component
        fx = 0.35 + 0.20 * fx_component
        macro = 0.35 + 0.30 * max(stress_component, demand_component)
        notes.append("Fuel trader/distributor mapped to inventory, receivables, fuel volatility, OPEC supply, and PMI risk.")

    return VulnerabilityScores(
        commodity_sensitivity_score=float(np.clip(commodity, 0, 1)),
        fx_sensitivity_score=float(np.clip(fx, 0, 1)),
        macro_sensitivity_score=float(np.clip(macro, 0, 1)),
        vulnerability_notes=notes,
    )


def estimate_asset_value_proxy(financials: Any, ratios: Any, warnings: list[str]) -> float:
    total_assets = _get(financials, "total_assets")
    if total_assets and total_assets > 0:
        return total_assets
    revenue = _get(financials, "revenue")
    if revenue and revenue > 0:
        warnings.append("total_assets missing; asset value proxy estimated as 1.5x revenue.")
        return revenue * 1.5
    warnings.append("total_assets and revenue missing; asset value proxy defaulted to 1.0.")
    return 1.0


def estimate_debt_threshold(financials: Any, warnings: list[str]) -> float:
    total_debt = _get(financials, "total_debt")
    if total_debt and total_debt > 0:
        return total_debt
    debt_parts = [
        _get(financials, "short_term_debt"),
        _get(financials, "current_portion_long_term_debt"),
        _get(financials, "long_term_debt"),
    ]
    if any(value is not None for value in debt_parts):
        warnings.append("total_debt missing; debt threshold derived from debt components.")
        return sum(value or 0.0 for value in debt_parts)
    total_liabilities = _get(financials, "total_liabilities")
    if total_liabilities and total_liabilities > 0:
        warnings.append("total_debt missing; debt threshold proxied as 60 percent of total liabilities.")
        return total_liabilities * 0.60
    warnings.append("debt inputs missing; debt threshold defaulted to 1.0.")
    return 1.0


def balance_sheet_distress_pd_floor(financials: Any, ratios: Any, warnings: list[str]) -> float:
    """Apply a transparent PD floor for accounting insolvency signals."""
    floor = 0.0
    equity = _get(financials, "shareholders_equity")
    liabilities_to_assets = _get(ratios, "liabilities_to_assets")
    total_assets = _get(financials, "total_assets")
    total_liabilities = _get(financials, "total_liabilities")

    if liabilities_to_assets is None and total_assets and total_assets > 0 and total_liabilities is not None:
        liabilities_to_assets = total_liabilities / total_assets

    if equity is not None and equity <= 0:
        floor = max(floor, 0.16)
        warnings.append("Negative shareholders equity triggered a balance-sheet distress PD floor.")
    if liabilities_to_assets is not None and liabilities_to_assets >= 1.0:
        floor = max(floor, 0.18)
        warnings.append("Liabilities exceed assets; accounting insolvency PD floor applied.")
    elif liabilities_to_assets is not None and liabilities_to_assets >= 0.90:
        floor = max(floor, 0.08)
        warnings.append("Very high liabilities/assets triggered an elevated leverage PD floor.")

    return floor


def estimate_asset_volatility(
    ratios: Any,
    market_context: MarketContext,
    vulnerability: VulnerabilityScores,
) -> float:
    leverage = _leverage_ratio_for_pd(_get(ratios, "debt_to_equity"), 1.0)
    liquidity = _safe_ratio(_get(ratios, "current_ratio"), 1.0)
    stress = np.clip((market_context.stress_index - 50.0) / 50.0, 0, 1)
    vulnerability_avg = np.mean(
        [
            vulnerability.commodity_sensitivity_score,
            vulnerability.fx_sensitivity_score,
            vulnerability.macro_sensitivity_score,
        ]
    )
    volatility = (
        0.18
        + 0.08 * min(leverage, 5)
        + 0.12 * stress
        + 0.10 * vulnerability_avg
        + 0.05 * max(0, 1 - min(liquidity, 2) / 2)
    )
    return float(np.clip(volatility, 0.08, 0.95))


def calculate_ml_proxy_pd(
    ratios: Any,
    market_context: MarketContext,
    vulnerability: VulnerabilityScores,
) -> tuple[float, Dict[str, float]]:
    """Logistic cross-check using interpretable financial and market drivers."""
    debt_to_ebitda = _safe_ratio(_get(ratios, "debt_to_ebitda"), 4.0)
    debt_to_equity = _leverage_ratio_for_pd(_get(ratios, "debt_to_equity"), 1.5)
    current_ratio = _safe_ratio(_get(ratios, "current_ratio"), 1.0)
    cash_ratio = _safe_ratio(_get(ratios, "cash_ratio"), 0.4)
    interest_coverage = _safe_ratio(_get(ratios, "interest_coverage"), 3.0)
    net_margin = _safe_ratio(_get(ratios, "net_margin"), 0.03)
    stress = np.clip(market_context.stress_index / 100, 0, 1)

    contributions = {
        "intercept": -3.40,
        "debt_to_ebitda": 0.20 * min(debt_to_ebitda, 10),
        "debt_to_equity": 0.15 * min(debt_to_equity, 8),
        "weak_liquidity": 0.70 * max(0, 1.20 - current_ratio),
        "low_cash": 0.35 * max(0, 0.50 - cash_ratio),
        "weak_interest_coverage": 0.25 * max(0, 3.0 - interest_coverage),
        "negative_margin": 2.00 * max(0, -net_margin),
        "market_stress": 1.25 * stress,
        "commodity_vulnerability": 0.55 * vulnerability.commodity_sensitivity_score,
        "fx_vulnerability": 0.35 * vulnerability.fx_sensitivity_score,
        "macro_vulnerability": 0.45 * vulnerability.macro_sensitivity_score,
        "crack_spread_pressure": 0.12 * max(0, market_context.crack_spread_zscore),
        "inventory_pressure": 0.08 * max(0, market_context.inventory_build_zscore),
        "opec_supply_pressure": 0.08 * max(0, market_context.opec_production_cut_zscore),
        "pmi_weakness": 0.10 * max(0, market_context.pmi_weakness_zscore),
        "iata_demand_weakness": 0.10 * max(0, market_context.iata_traffic_loss_zscore),
    }
    logit = sum(contributions.values())
    return _clip_probability(1 / (1 + exp(-logit))), contributions


def calculate_trained_historical_pd(
    ratios: Any,
    market_context: MarketContext,
) -> tuple[Optional[float], Dict[str, float], Optional[str]]:
    """Use the stored historical PD model as an optional ML cross-check."""

    if not HISTORICAL_PD_MODEL_PATH.exists():
        return None, {}, None

    try:
        artifact = joblib.load(HISTORICAL_PD_MODEL_PATH)
        model = artifact["model"] if isinstance(artifact, dict) else artifact
        feature_columns = artifact.get("feature_columns", []) if isinstance(artifact, dict) else []
        metrics = artifact.get("metrics", {}) if isinstance(artifact, dict) else {}
        row = {
            "current_ratio": _safe_ratio(_get(ratios, "current_ratio"), 1.2),
            "quick_ratio": _safe_ratio(_get(ratios, "quick_ratio"), 0.9),
            "cash_ratio": _safe_ratio(_get(ratios, "cash_ratio"), 0.35),
            "working_capital": _safe_ratio(_get(ratios, "working_capital"), 0.0),
            "debt_to_equity": _safe_ratio(_get(ratios, "debt_to_equity"), 1.5),
            "debt_to_ebitda": _safe_ratio(_get(ratios, "debt_to_ebitda"), 3.5),
            "liabilities_to_assets": _safe_ratio(_get(ratios, "liabilities_to_assets"), 0.65),
            "interest_coverage": _safe_ratio(_get(ratios, "interest_coverage"), 3.0),
            "operating_margin": _safe_ratio(_get(ratios, "operating_margin"), 0.06),
            "net_margin": _safe_ratio(_get(ratios, "net_margin"), 0.03),
            "return_on_assets": _safe_ratio(_get(ratios, "return_on_assets"), 0.03),
            "return_on_equity": _safe_ratio(_get(ratios, "return_on_equity"), 0.08),
            "market_stress_index": market_context.stress_index,
            "oil_volatility": abs(market_context.oil_volatility_zscore),
            "fuel_return": market_context.fuel_return_zscore,
            "jet_crack_spread": market_context.crack_spread_zscore,
            "dxy_return": market_context.fx_return_zscore,
            "freight_loss": market_context.freight_loss_zscore,
            "eia_crude_inventories": market_context.inventory_build_zscore,
            "opec_production": market_context.opec_production_cut_zscore,
            "global_pmi": market_context.pmi_weakness_zscore,
            "iata_passenger_traffic": market_context.iata_traffic_loss_zscore,
            "vix_level": market_context.stress_index / 2,
            "sp500_return": 0.0,
            "country_risk_score": 2.0,
            "payment_tenor_days": 45,
            "deposit_percentage": 0.0,
            "exposure_size": 0.0,
            "letter_of_credit_flag": 0,
            "guarantee_flag": 0,
        }
        if not feature_columns:
            feature_columns = list(row.keys())
        frame = pd.DataFrame([row])
        for column in feature_columns:
            if column not in frame.columns:
                frame[column] = 0.0
        frame = frame[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        pd_value = float(model.predict_proba(frame)[:, 1][0])
        auc = _to_float(metrics.get("auc"))
        artifact_weight = float(np.clip(((auc or 0.50) - 0.50) * 2.0, 0.0, 0.25))
        return _clip_probability(pd_value), {
            "historical_trained_ml_pd": pd_value,
            "historical_pd_artifact_auc": auc or 0.50,
            "historical_pd_artifact_weight": artifact_weight,
        }, None
    except Exception as exc:
        return None, {}, f"Historical PD model artifact could not be used: {exc}"


def estimate_pd(
    counterparty_id: int,
    counterparty_type: Optional[str],
    financials: Any,
    ratios: Any,
    market_context: MarketContext,
    financial_metrics_id: Optional[int] = None,
    financial_ratios_id: Optional[int] = None,
    time_horizon_years: float = 1.0,
    financial_trends: Optional[dict[str, Any]] = None,
) -> PDPredictionResult:
    """Estimate final PD from structural and ML proxy models."""
    warnings: list[str] = []
    vulnerability = calculate_vulnerability_scores(counterparty_type, market_context)
    warnings.extend(vulnerability.vulnerability_notes)
    trend_overlay = calculate_trend_risk_overlay(financial_trends)
    if trend_overlay["period_count"] >= 2:
        warnings.extend(trend_overlay["notes"])

    asset_value_proxy = estimate_asset_value_proxy(financials, ratios, warnings)
    debt_threshold = estimate_debt_threshold(financials, warnings)
    base_asset_volatility = estimate_asset_volatility(ratios, market_context, vulnerability)
    asset_volatility = float(
        np.clip(
            base_asset_volatility + float(trend_overlay.get("asset_volatility_addon") or 0.0),
            0.08,
            0.95,
        )
    )
    structural_pd, dd = calculate_structural_pd(
        asset_value_proxy=asset_value_proxy,
        debt_threshold=debt_threshold,
        asset_volatility=asset_volatility,
        risk_free_rate=market_context.risk_free_rate,
        time_horizon_years=time_horizon_years,
    )
    rule_ml_pd, contributions = calculate_ml_proxy_pd(ratios, market_context, vulnerability)
    trend_pd_multiplier = float(trend_overlay.get("pd_multiplier") or 1.0)
    if trend_overlay["period_count"] >= 2 and trend_pd_multiplier != 1.0:
        contributions["rule_based_logistic_pd_before_trend_overlay"] = rule_ml_pd
        contributions["financial_trend_pd_multiplier"] = trend_pd_multiplier
        contributions["financial_trend_risk_score"] = float(trend_overlay.get("risk_score") or 0.0)
        rule_ml_pd = _clip_probability(rule_ml_pd * trend_pd_multiplier)
        contributions["rule_based_logistic_pd_after_trend_overlay"] = rule_ml_pd
    trained_ml_pd, trained_contributions, trained_warning = calculate_trained_historical_pd(
        ratios,
        market_context,
    )
    if trained_warning:
        warnings.append(trained_warning)
    if trained_ml_pd is not None:
        artifact_weight = float(np.clip(trained_contributions.get("historical_pd_artifact_weight", 0.0), 0.0, 0.50))
        ml_pd = _clip_probability((1.0 - artifact_weight) * rule_ml_pd + artifact_weight * trained_ml_pd)
        contributions.update(trained_contributions)
        contributions["rule_based_logistic_pd"] = rule_ml_pd
        contributions["blended_ml_pd"] = ml_pd
        warnings.append("Historical trained PD model artifact used as quality-weighted ML cross-check.")
    else:
        ml_pd = rule_ml_pd
        warnings.append("No observed-default PD calibration artifact available; proxy calibration remains active.")

    divergence = abs(structural_pd - ml_pd)
    disagreement = divergence >= 0.07 or max(structural_pd, ml_pd) / max(min(structural_pd, ml_pd), 0.0001) >= 3
    if disagreement:
        warnings.append("Structural PD and ML proxy PD diverge materially; analyst review required.")

    distress_floor = balance_sheet_distress_pd_floor(financials, ratios, warnings)

    blend_config = pd_blend_config()
    structural_weight = float(blend_config.get("structural_weight", 0.65))
    ml_weight = float(blend_config.get("ml_weight", 0.35))
    artifact_auc = contributions.get("historical_pd_artifact_auc")
    if artifact_auc is not None and artifact_auc < 0.60:
        ml_weight = min(ml_weight, 0.25)
        structural_weight = max(structural_weight, 1.0 - ml_weight)
        contributions["final_pd_ml_weight_quality_cap"] = ml_weight
    total_weight = structural_weight + ml_weight
    if total_weight <= 0:
        structural_weight, ml_weight = 0.65, 0.35
    else:
        structural_weight, ml_weight = structural_weight / total_weight, ml_weight / total_weight

    # Structural model remains the anchor unless calibrated blend weights exist.
    final_pd = _clip_probability(structural_weight * structural_pd + ml_weight * ml_pd)
    if trend_overlay["period_count"] >= 2 and trend_pd_multiplier != 1.0:
        final_trend_multiplier = float(np.sqrt(trend_pd_multiplier))
        contributions["final_pd_before_financial_trend_overlay"] = final_pd
        contributions["final_pd_financial_trend_multiplier"] = final_trend_multiplier
        final_pd = _clip_probability(final_pd * final_trend_multiplier)
    if distress_floor > final_pd:
        contributions["balance_sheet_distress_floor"] = distress_floor
        final_pd = _clip_probability(distress_floor)
    confidence = float(np.clip(1 - divergence, 0.05, 0.99))
    if distress_floor > 0:
        confidence = min(confidence, 0.70)
    artifact_available = HISTORICAL_PD_MODEL_PATH.exists()
    validation_diagnostics = {
        "structural_anchor_used": True,
        "ml_used_as_cross_check": True,
        "observed_default_calibration_available": artifact_available,
        "balance_sheet_distress_floor_applied": distress_floor > 0,
        "model_disagreement": disagreement,
        "final_pd_not_below_distress_floor": final_pd >= distress_floor,
        "leverage_signal": "high"
        if _safe_ratio(_get(ratios, "debt_to_ebitda"), 0.0) >= 4.0
        or _leverage_ratio_for_pd(_get(ratios, "debt_to_equity")) >= 3.0
        else "moderate_or_low",
        "liquidity_signal": "weak"
        if _safe_ratio(_get(ratios, "current_ratio"), 1.2) < 1.0
        else "adequate_or_strong",
        "solvency_signal": "stressed"
        if _safe_ratio(_get(ratios, "liabilities_to_assets"), 0.65) >= 0.90
        or _safe_ratio(_get(financials, "shareholders_equity"), 1.0) < 0
        else "not_stressed",
    }

    return PDPredictionResult(
        run_id=str(uuid4()),
        counterparty_id=counterparty_id,
        financial_metrics_id=financial_metrics_id,
        financial_ratios_id=financial_ratios_id,
        structural_pd=structural_pd,
        ml_pd=ml_pd,
        final_pd=final_pd,
        classification_label=classify_pd(final_pd),
        model_confidence=confidence,
        model_disagreement=disagreement,
        pd_divergence=divergence,
        distance_to_default=dd,
        asset_value_proxy=asset_value_proxy,
        debt_threshold=debt_threshold,
        asset_volatility=asset_volatility,
        risk_free_rate=market_context.risk_free_rate,
        time_horizon_years=time_horizon_years,
        commodity_sensitivity_score=vulnerability.commodity_sensitivity_score,
        fx_sensitivity_score=vulnerability.fx_sensitivity_score,
        macro_sensitivity_score=vulnerability.macro_sensitivity_score,
        market_stress_index=market_context.stress_index,
        market_regime=market_context.market_regime,
        feature_contributions=contributions,
        model_assumptions={
            "structural_anchor_weight": structural_weight,
            "ml_proxy_weight": ml_weight,
            "blend_calibration_method": blend_config.get("calibration_method", "hardcoded_default_fallback"),
            "calibration_status": (
                "observed_default_artifact_cross_check_available"
                if artifact_available
                else "proxy_calibrated_no_observed_default_history"
            ),
            "validation_status": "directional_sanity_checks_embedded",
            "default_definition": "Transparent proxy for 1-year counterparty default risk.",
            "asset_value_proxy": "Uses stored total_assets; falls back to 1.5x revenue if missing.",
            "debt_threshold": "Uses total_debt; falls back to debt components or 60% total liabilities.",
            "ml_proxy": "Interpretable logistic proxy, not trained on hidden or fabricated labels.",
            "distress_floor_rules": {
                "negative_equity": "minimum PD 16%",
                "liabilities_exceed_assets": "minimum PD 18%",
                "liabilities_to_assets_above_90pct": "minimum PD 8%",
            },
            "historical_ml_artifact": str(HISTORICAL_PD_MODEL_PATH.relative_to(PROJECT_ROOT))
            if HISTORICAL_PD_MODEL_PATH.exists()
            else "not_available",
            "financial_trend_overlay": trend_overlay,
            "base_asset_volatility_before_trend_overlay": base_asset_volatility,
            "validation_diagnostics": validation_diagnostics,
            "internal_grade_note": "Classification labels are internal proxy grades, not agency ratings.",
        },
        input_data_reference={
            "financial_metrics_id": financial_metrics_id,
            "financial_ratios_id": financial_ratios_id,
            "market_context": market_context.data_reference,
            "financial_trend_features": "financial_metrics_extracted history + financial_ratios by period",
        },
        warnings=warnings,
    )


