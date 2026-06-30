"""Credit scorecard, tenor optimization, and formal comparison helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

ANALYSIS_MODEL_VERSION = "credit_analysis_utilities_v1.0"


@dataclass
class CreditProfileInput:
    counterparty_id: int
    counterparty_name: str
    current_ratio: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    interest_coverage: Optional[float] = None
    operating_margin: Optional[float] = None
    probability_of_default: Optional[float] = None
    loss_given_default: Optional[float] = None
    exposure_at_default: Optional[float] = None
    payment_tenor_days: int = 30
    collateral_strength: float = 0.0
    country_risk_score: Optional[float] = None
    market_stress_index: Optional[float] = None
    scenario_expected_loss: Optional[float] = None


@dataclass
class ScorecardResult:
    model_name: str
    model_version: str
    counterparty_id: int
    counterparty_name: str
    score: float
    risk_segment: str
    segment_method: str
    drivers: list[str]
    weights: dict[str, float]
    assumptions: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass
class TenorOption:
    tenor_days: int
    expected_loss: float
    marginal_risk_price: float
    recommended_security: str
    is_recommended: bool


@dataclass
class TenorOptimizationResult:
    model_name: str
    model_version: str
    counterparty_id: int
    counterparty_name: str
    recommended_tenor_days: int
    options: list[TenorOption]
    assumptions: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["options"] = [asdict(option) for option in self.options]
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass
class ComparisonResult:
    model_name: str
    model_version: str
    counterparties: list[dict[str, Any]]
    safer_counterparty_id: int
    safer_counterparty_name: str
    comparison_summary: str
    ranking_factors: dict[str, Any]
    assumptions: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def _safe(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        number = float(value)
        if np.isnan(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def _bounded(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return float(np.clip(value, lower, upper))


def _risk_segment(score: float) -> str:
    if score < 33.0:
        return "Low"
    if score < 66.0:
        return "Medium"
    return "High"


def calculate_credit_profile_score(inputs: CreditProfileInput) -> ScorecardResult:
    """Weighted first-pass scorecard with Low/Medium/High segmentation."""
    warnings: list[str] = []
    drivers: list[str] = []
    weights = {
        "pd": 0.25,
        "liquidity": 0.15,
        "leverage": 0.15,
        "coverage": 0.10,
        "margin": 0.10,
        "collateral": 0.10,
        "country": 0.05,
        "market_stress": 0.05,
        "tenor": 0.05,
    }

    pd_value = _safe(inputs.probability_of_default)
    if pd_value is None:
        pd_component = 45.0
        warnings.append("PD missing; neutral scorecard PD proxy used.")
    else:
        pd_component = _bounded(pd_value / 0.20 * 100)
        if pd_value >= 0.10:
            drivers.append("High PD increases scorecard risk.")

    current_ratio = _safe(inputs.current_ratio)
    if current_ratio is None:
        liquidity_component = 50.0
        warnings.append("Current ratio missing; neutral liquidity proxy used.")
    else:
        liquidity_component = _bounded((1.5 - current_ratio) / 1.5 * 100)
        if current_ratio < 1.0:
            drivers.append("Weak liquidity increases risk.")

    leverage = _safe(inputs.debt_to_ebitda)
    leverage_component = 50.0 if leverage is None else _bounded(leverage / 6.0 * 100)
    if leverage is None:
        warnings.append("Debt/EBITDA missing; neutral leverage proxy used.")
    elif leverage > 4.0:
        drivers.append("High leverage increases scorecard risk.")

    coverage = _safe(inputs.interest_coverage)
    coverage_component = 50.0 if coverage is None else _bounded((4.0 - coverage) / 4.0 * 100)
    if coverage is None:
        warnings.append("Interest coverage missing; neutral coverage proxy used.")
    elif coverage < 2.0:
        drivers.append("Low interest coverage weakens repayment capacity.")

    margin = _safe(inputs.operating_margin)
    margin_component = 50.0 if margin is None else _bounded((0.15 - margin) / 0.25 * 100)
    collateral_component = _bounded((1.0 - _safe(inputs.collateral_strength, 0.0)) * 100)
    country_component = _bounded(_safe(inputs.country_risk_score, 50.0))
    stress_component = _bounded(_safe(inputs.market_stress_index, 50.0))
    tenor_component = _bounded(max(inputs.payment_tenor_days, 0) / 90 * 100)

    components = {
        "pd": pd_component,
        "liquidity": liquidity_component,
        "leverage": leverage_component,
        "coverage": coverage_component,
        "margin": margin_component,
        "collateral": collateral_component,
        "country": country_component,
        "market_stress": stress_component,
        "tenor": tenor_component,
    }
    score = _bounded(sum(components[name] * weights[name] for name in weights))
    if not drivers:
        drivers.append("No major scorecard risk driver breached first-pass thresholds.")

    return ScorecardResult(
        model_name="Weighted Credit Profile Scorecard",
        model_version=ANALYSIS_MODEL_VERSION,
        counterparty_id=inputs.counterparty_id,
        counterparty_name=inputs.counterparty_name,
        score=round(score, 4),
        risk_segment=_risk_segment(score),
        segment_method="Weighted scorecard with Low/Medium/High thresholds; KMeans-compatible risk grouping output.",
        drivers=drivers,
        weights=weights,
        assumptions={"score_scale": "0 lower risk, 100 higher risk", "components": components},
        warnings=warnings,
    )


def optimize_payment_terms(inputs: CreditProfileInput, tenor_options: Optional[list[int]] = None) -> TenorOptimizationResult:
    """Compare expected loss across standard 30/45/60/90 day tenors."""
    pd_value = _safe(inputs.probability_of_default, 0.05) or 0.05
    lgd_value = _safe(inputs.loss_given_default, 0.45) or 0.45
    ead_value = max(_safe(inputs.exposure_at_default, 0.0) or 0.0, 0.0)
    collateral = _safe(inputs.collateral_strength, 0.0) or 0.0
    stress = _safe(inputs.market_stress_index, 50.0) or 50.0
    options = sorted(set(tenor_options or [30, 45, 60, 90]))
    option_rows: list[TenorOption] = []
    previous_el: Optional[float] = None
    best_tenor = options[0]
    best_adjusted = float("inf")

    for tenor in options:
        tenor_multiplier = max(1.0, tenor / 30.0)
        stress_multiplier = 1.0 + max(stress - 50.0, 0.0) / 250.0
        collateral_multiplier = 1.0 - min(collateral, 0.95) * 0.25
        expected_loss = pd_value * lgd_value * ead_value * tenor_multiplier * stress_multiplier * collateral_multiplier
        marginal = 0.0 if previous_el is None else max(0.0, expected_loss - previous_el)
        previous_el = expected_loss
        security = "Open Credit with monitoring covenants"
        if expected_loss > 150_000 or pd_value >= 0.10:
            security = "Standby LC or Bank Guarantee"
        if expected_loss > 300_000 or pd_value >= 0.15:
            security = "Prepayment or Confirmed LC"
        adjusted_penalty = expected_loss + max(tenor - 45, 0) * ead_value * 0.00005
        if adjusted_penalty < best_adjusted:
            best_adjusted = adjusted_penalty
            best_tenor = tenor
        option_rows.append(TenorOption(
            tenor_days=tenor,
            expected_loss=round(float(expected_loss), 2),
            marginal_risk_price=round(float(marginal), 2),
            recommended_security=security,
            is_recommended=False,
        ))

    for option in option_rows:
        option.is_recommended = option.tenor_days == best_tenor

    return TenorOptimizationResult(
        model_name="Expected Loss Payment Terms Optimizer",
        model_version=ANALYSIS_MODEL_VERSION,
        counterparty_id=inputs.counterparty_id,
        counterparty_name=inputs.counterparty_name,
        recommended_tenor_days=best_tenor,
        options=option_rows,
        assumptions={
            "tenor_rule": "Longer tenor increases EAD-style exposure by tenor / 30.",
            "risk_pricing": "Marginal risk price is incremental expected loss versus the prior tenor.",
            "security_rule": "Higher PD or EL requires stronger security.",
        },
        warnings=[] if ead_value > 0 else ["EAD missing or zero; optimizer returns zero expected-loss options."],
    )


def compare_counterparties(counterparties: list[CreditProfileInput]) -> ComparisonResult:
    """Formal side-by-side comparison using scorecard and normalized risk factors."""
    if len(counterparties) != 2:
        raise ValueError("Exactly two counterparties are required for formal comparison.")
    scored = [calculate_credit_profile_score(item) for item in counterparties]
    rows = []
    for item, score in zip(counterparties, scored):
        pd_value = _safe(item.probability_of_default, 0.05) or 0.05
        lgd_value = _safe(item.loss_given_default, 0.45) or 0.45
        ead_value = _safe(item.exposure_at_default, 0.0) or 0.0
        expected_loss = pd_value * lgd_value * ead_value
        relative_risk_score = score.score + min(expected_loss / 100_000, 25.0)
        rows.append({
            "counterparty_id": item.counterparty_id,
            "counterparty_name": item.counterparty_name,
            "risk_segment": score.risk_segment,
            "scorecard_score": score.score,
            "probability_of_default": pd_value,
            "loss_given_default": lgd_value,
            "exposure_at_default": ead_value,
            "expected_loss": round(expected_loss, 2),
            "relative_risk_score": round(float(relative_risk_score), 4),
            "drivers": score.drivers,
        })

    rows.sort(key=lambda row: row["relative_risk_score"])
    safer = rows[0]
    other = rows[1]
    summary = (
        f"{safer['counterparty_name']} is safer on the formal comparison because its "
        f"relative risk score ({safer['relative_risk_score']}) is below "
        f"{other['counterparty_name']} ({other['relative_risk_score']})."
    )
    return ComparisonResult(
        model_name="Formal Counterparty Comparison Tool",
        model_version=ANALYSIS_MODEL_VERSION,
        counterparties=rows,
        safer_counterparty_id=int(safer["counterparty_id"]),
        safer_counterparty_name=str(safer["counterparty_name"]),
        comparison_summary=summary,
        ranking_factors={
            "method": "Weighted scorecard plus expected-loss relative risk adjustment.",
            "sort_order": "Lower relative_risk_score is safer.",
        },
        assumptions={"no_llm_decision": True, "required_inputs": "PD, LGD, EAD, ratios, tenor, collateral when available."},
    )
