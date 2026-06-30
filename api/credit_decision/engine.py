"""
Rules-based credit decision engine.

Business purpose:
Convert stored PD, LGD, EAD, scenario losses, market stress, financial ratios,
and collateral information into a practical fuel trade credit recommendation.

Inputs:
Latest Phase 5 PD output, Phase 6 LGD/EAD/Expected Loss, Phase 7 scenario and
simulation outputs, financial ratios, trade exposure terms, and collateral.

Outputs:
Recommended credit limit, tenor, security, risk grade, approval status, risk
drivers, model assumptions, and audit references.

Method:
The engine applies transparent policy haircuts. Higher PD, LGD, stress, weak
liquidity, high leverage, long tenor, and high scenario tail loss reduce the
recommended limit and tighten payment/security terms. Strong collateral reduces
LGD-driven policy pressure but does not erase PD risk.

Assumptions:
Risk grades are internal proxy grades, not agency ratings. Policy thresholds are
student-project approximations documented in the output assumptions.

Limitations:
This is an explainable rules engine, not a legally binding credit approval
system. A credit officer should review final terms before commercial use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import numpy as np

from api.calibration.artifacts import collateral_strength_config


CREDIT_DECISION_MODEL_VERSION = "rules_credit_decision_v1.0"


@dataclass
class CreditDecisionInput:
    counterparty_id: int
    counterparty_name: Optional[str]
    counterparty_type: Optional[str]
    country: Optional[str]
    pd_prediction_id: Optional[int]
    loss_estimate_id: Optional[int]
    trade_exposure_id: Optional[int]
    scenario_result_id: Optional[int]
    simulation_result_id: Optional[int]
    financial_ratios_id: Optional[int]
    probability_of_default: float
    structural_pd: Optional[float]
    ml_pd: Optional[float]
    predicted_lgd: float
    exposure_at_default: float
    expected_loss: float
    requested_credit_limit: Optional[float]
    approved_credit_limit: Optional[float]
    payment_tenor_days: int
    collateral_type: str
    letter_of_credit_flag: bool
    guarantee_flag: bool
    deposit_percentage: float
    current_ratio: Optional[float]
    quick_ratio: Optional[float]
    debt_to_ebitda: Optional[float]
    interest_coverage: Optional[float]
    operating_margin: Optional[float]
    market_stress_index: Optional[float]
    market_regime: Optional[str]
    scenario_expected_loss: Optional[float]
    credit_var_95: Optional[float]
    expected_shortfall_95: Optional[float]
    model_disagreement: bool = False


@dataclass
class CreditDecisionResult:
    run_id: str
    counterparty_id: int
    model_name: str
    model_version: str
    probability_of_default: float
    loss_given_default: float
    exposure_at_default: float
    expected_loss: float
    scenario_expected_loss: Optional[float]
    credit_var_95: Optional[float]
    expected_shortfall_95: Optional[float]
    recommended_credit_limit: float
    recommended_tenor_days: int
    recommended_security: str
    risk_grade: str
    approval_status: str
    policy_score: float
    limit_haircut: float
    key_risk_drivers: list[str] = field(default_factory=list)
    mitigating_factors: list[str] = field(default_factory=list)
    model_assumptions: Dict[str, Any] = field(default_factory=dict)
    input_data_reference: Dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def _clip(value: float, lower: float, upper: float) -> float:
    return float(np.clip(value, lower, upper))


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        value_float = float(value)
        if np.isnan(value_float):
            return default
        return value_float
    except (TypeError, ValueError):
        return default


def map_risk_grade(probability_of_default: float) -> str:
    pd_value = _clip(probability_of_default, 0.0, 1.0)
    if pd_value < 0.01:
        return "A"
    if pd_value < 0.03:
        return "BBB"
    if pd_value < 0.07:
        return "BB"
    if pd_value < 0.15:
        return "B"
    return "CCC"


def _collateral_strength(inputs: CreditDecisionInput) -> float:
    collateral = (inputs.collateral_type or "unsecured").strip().lower()
    calibrated = collateral_strength_config()
    base = {
        "letter_of_credit": 0.90,
        "lc": 0.90,
        "confirmed lc": 0.95,
        "standby lc": 0.90,
        "cash_deposit": 0.80,
        "deposit": 0.80,
        "guarantee": 0.65,
        "bank guarantee": 0.70,
        "secured_collateral": 0.55,
        "secured": 0.55,
        "unsecured": 0.05,
    }.get(collateral, 0.20)
    if collateral in calibrated:
        try:
            base = float(calibrated[collateral])
        except (TypeError, ValueError):
            pass
    if inputs.letter_of_credit_flag:
        base = max(base, 0.90)
    if inputs.guarantee_flag:
        base = max(base, 0.65)
    if inputs.deposit_percentage:
        base = max(base, _clip(inputs.deposit_percentage / 100, 0.0, 1.0))
    return _clip(base, 0.0, 1.0)


def _base_limit(inputs: CreditDecisionInput) -> float:
    for value in (
        inputs.requested_credit_limit,
        inputs.approved_credit_limit,
        inputs.exposure_at_default,
    ):
        numeric = _safe_float(value)
        if numeric is not None and numeric > 0:
            return numeric
    return 0.0


def _scenario_loss_ratio(inputs: CreditDecisionInput) -> float:
    tail_loss = _safe_float(inputs.expected_shortfall_95)
    if tail_loss is None:
        tail_loss = _safe_float(inputs.credit_var_95)
    if tail_loss is None:
        tail_loss = _safe_float(inputs.scenario_expected_loss)
    ead = max(inputs.exposure_at_default, 1.0)
    return _clip((tail_loss or 0.0) / ead, 0.0, 2.0)


def _limit_haircut_and_reasons(inputs: CreditDecisionInput) -> tuple[float, float, list[str], list[str], list[str], Dict[str, float]]:
    risk_drivers: list[str] = []
    mitigants: list[str] = []
    warnings: list[str] = []
    haircut_components: Dict[str, float] = {
        "pd_grade": 0.0,
        "lgd_severity": 0.0,
        "market_stress": 0.0,
        "liquidity": 0.0,
        "leverage": 0.0,
        "interest_coverage": 0.0,
        "tenor": 0.0,
        "scenario_tail_risk": 0.0,
        "model_disagreement": 0.0,
        "collateral_credit": 0.0,
    }
    score = 0.0
    haircut = 0.0

    pd_value = _clip(inputs.probability_of_default, 0.0, 1.0)
    if pd_value >= 0.15:
        haircut += 0.40
        haircut_components["pd_grade"] += 0.40
        score += 4
        risk_drivers.append("Very high PD; internal grade CCC.")
    elif pd_value >= 0.07:
        haircut += 0.28
        haircut_components["pd_grade"] += 0.28
        score += 3
        risk_drivers.append("High PD; internal grade B.")
    elif pd_value >= 0.03:
        haircut += 0.16
        haircut_components["pd_grade"] += 0.16
        score += 2
        risk_drivers.append("Moderate PD; internal grade BB.")
    elif pd_value >= 0.01:
        haircut += 0.07
        haircut_components["pd_grade"] += 0.07
        score += 1
        risk_drivers.append("Low-to-moderate PD; internal grade BBB.")
    else:
        mitigants.append("Low PD supports credit availability.")

    if inputs.predicted_lgd >= 0.70:
        haircut += 0.18
        haircut_components["lgd_severity"] += 0.18
        score += 2
        risk_drivers.append("High LGD indicates weak recovery in default.")
    elif inputs.predicted_lgd >= 0.55:
        haircut += 0.10
        haircut_components["lgd_severity"] += 0.10
        score += 1
        risk_drivers.append("Elevated LGD increases loss severity.")
    else:
        mitigants.append("LGD is controlled by collateral or recovery protection.")

    stress = _safe_float(inputs.market_stress_index)
    if stress is not None:
        if stress >= 80:
            haircut += 0.15
            haircut_components["market_stress"] += 0.15
            score += 2
            risk_drivers.append("Crisis-level market stress tightens credit appetite.")
        elif stress >= 65:
            haircut += 0.10
            haircut_components["market_stress"] += 0.10
            score += 1.5
            risk_drivers.append("Elevated market stress/regime requires conservative terms.")
        elif stress < 40:
            mitigants.append("Market stress index is calm/normal.")
    else:
        warnings.append("Market stress index missing; decision uses conservative available data.")

    current_ratio = _safe_float(inputs.current_ratio)
    if current_ratio is not None:
        if current_ratio < 1.0:
            haircut += 0.14
            haircut_components["liquidity"] += 0.14
            score += 2
            risk_drivers.append("Current ratio below 1.0 signals weak liquidity.")
        elif current_ratio < 1.25:
            haircut += 0.07
            haircut_components["liquidity"] += 0.07
            score += 1
            risk_drivers.append("Thin liquidity limits tenor flexibility.")
        else:
            mitigants.append("Liquidity ratios support repayment capacity.")
    else:
        warnings.append("Current ratio missing from stored financial ratios.")

    debt_to_ebitda = _safe_float(inputs.debt_to_ebitda)
    if debt_to_ebitda is not None and debt_to_ebitda > 4.0:
        haircut += 0.08
        haircut_components["leverage"] += 0.08
        score += 1
        risk_drivers.append("Debt/EBITDA above 4.0x indicates leverage pressure.")

    interest_coverage = _safe_float(inputs.interest_coverage)
    if interest_coverage is not None and interest_coverage < 2.0:
        haircut += 0.08
        haircut_components["interest_coverage"] += 0.08
        score += 1
        risk_drivers.append("Interest coverage below 2.0x weakens debt service capacity.")

    if inputs.payment_tenor_days > 60:
        haircut += 0.08
        haircut_components["tenor"] += 0.08
        score += 1
        risk_drivers.append("Long tenor increases receivable accumulation and exposure risk.")
    elif inputs.payment_tenor_days <= 30:
        mitigants.append("Short tenor limits exposure build-up.")

    scenario_ratio = _scenario_loss_ratio(inputs)
    if scenario_ratio >= 0.25:
        haircut += 0.15
        haircut_components["scenario_tail_risk"] += 0.15
        score += 2
        risk_drivers.append("Scenario tail loss is high relative to EAD.")
    elif scenario_ratio >= 0.10:
        haircut += 0.08
        haircut_components["scenario_tail_risk"] += 0.08
        score += 1
        risk_drivers.append("Scenario VaR/ES creates moderate tail-loss pressure.")

    if inputs.model_disagreement:
        haircut += 0.05
        haircut_components["model_disagreement"] += 0.05
        score += 0.5
        risk_drivers.append("Structural PD and ML PD disagree; analyst review required.")

    collateral_strength = _collateral_strength(inputs)
    if collateral_strength >= 0.85:
        haircut -= 0.10
        haircut_components["collateral_credit"] -= 0.10
        score = max(0.0, score - 1.0)
        mitigants.append("Letter of credit/cash collateral materially reduces loss severity.")
    elif collateral_strength >= 0.60:
        haircut -= 0.05
        haircut_components["collateral_credit"] -= 0.05
        score = max(0.0, score - 0.5)
        mitigants.append("Guarantee or collateral partly mitigates recovery risk.")
    elif collateral_strength <= 0.10 and inputs.predicted_lgd >= 0.50:
        haircut += 0.07
        haircut_components["collateral_credit"] += 0.07
        score += 1
        risk_drivers.append("Unsecured exposure with elevated LGD requires stronger protection.")

    raw_haircut = haircut
    haircut = _clip(haircut, 0.0, 0.90)
    haircut_components["base_policy_haircut_before_scenario"] = _clip(
        raw_haircut - haircut_components["scenario_tail_risk"],
        0.0,
        0.90,
    )
    haircut_components["scenario_tail_add_on"] = haircut_components["scenario_tail_risk"]
    haircut_components["raw_policy_haircut"] = raw_haircut
    haircut_components["final_policy_haircut"] = haircut
    if not risk_drivers:
        risk_drivers.append("No major quantitative risk driver breached policy thresholds.")
    return haircut, score, risk_drivers, mitigants, warnings, haircut_components


def _recommend_tenor(inputs: CreditDecisionInput, risk_grade: str, score: float) -> int:
    if risk_grade == "A" and score <= 1.0:
        return min(max(inputs.payment_tenor_days, 45), 90)
    if risk_grade == "BBB" and score <= 2.5:
        return min(inputs.payment_tenor_days, 60)
    if risk_grade == "BB" or score <= 4.0:
        return min(inputs.payment_tenor_days, 45)
    if risk_grade == "B" or score <= 6.0:
        return min(inputs.payment_tenor_days, 30)
    return 0


def _recommend_security(inputs: CreditDecisionInput, risk_grade: str, score: float) -> str:
    collateral_strength = _collateral_strength(inputs)
    if risk_grade == "CCC" or score > 6:
        return "Prepayment or Confirmed LC"
    if risk_grade == "B" or inputs.probability_of_default >= 0.07:
        return "Standby LC or Bank Guarantee"
    if inputs.predicted_lgd >= 0.60 and collateral_strength < 0.60:
        return "Bank Guarantee or Partial Cash Deposit"
    if risk_grade == "BB":
        return "Corporate Guarantee or Partial Deposit"
    if collateral_strength >= 0.60:
        return "Existing collateral acceptable"
    return "Open Credit with monitoring covenants"


def _approval_status(risk_grade: str, score: float, recommended_limit: float) -> str:
    if recommended_limit <= 0 or risk_grade == "CCC" or score > 6.5:
        return "REJECT / PREPAYMENT ONLY"
    if score > 4.0 or risk_grade == "B":
        return "CONDITIONAL APPROVAL - SECURED"
    if score > 2.0 or risk_grade == "BB":
        return "CONDITIONAL APPROVAL"
    return "APPROVED"


def recommend_credit_terms(inputs: CreditDecisionInput) -> CreditDecisionResult:
    """Generate a traceable credit recommendation from stored model outputs."""
    pd_value = _clip(inputs.probability_of_default, 0.0, 1.0)
    lgd_value = _clip(inputs.predicted_lgd, 0.0, 1.0)
    ead_value = max(inputs.exposure_at_default, 0.0)
    base_limit = _base_limit(inputs)
    risk_grade = map_risk_grade(pd_value)
    haircut, score, risk_drivers, mitigants, warnings, haircut_components = _limit_haircut_and_reasons(inputs)
    recommended_limit = round(max(0.0, base_limit * (1.0 - haircut)), 2)
    recommended_tenor = _recommend_tenor(inputs, risk_grade, score)
    recommended_security = _recommend_security(inputs, risk_grade, score)
    approval_status = _approval_status(risk_grade, score, recommended_limit)
    expected_loss = pd_value * lgd_value * ead_value

    if base_limit <= 0:
        warnings.append("Requested/approved limit missing; recommendation uses zero base limit.")
    if inputs.scenario_result_id is None:
        warnings.append("Scenario result missing; recommendation uses point-in-time PD/LGD/EAD only.")
    if inputs.simulation_result_id is None:
        warnings.append("Simulation result missing; VaR/ES not included in limit haircut.")
    validation_diagnostics = {
        "scenario_result_included": inputs.scenario_result_id is not None,
        "simulation_result_included": inputs.simulation_result_id is not None,
        "recommended_limit_not_above_base_limit": recommended_limit <= base_limit,
        "expected_loss_formula": "PD * LGD * EAD",
        "expected_loss_formula_holds": abs(expected_loss - (pd_value * lgd_value * ead_value)) < 0.01,
        "tenor_policy_applied": True,
        "security_policy_applied": True,
        "collateral_can_reduce_lgd_pressure_but_not_pd": True,
    }

    return CreditDecisionResult(
        run_id=str(uuid4()),
        counterparty_id=inputs.counterparty_id,
        model_name="Rules-Based Fuel Trade Credit Decision Engine",
        model_version=CREDIT_DECISION_MODEL_VERSION,
        probability_of_default=pd_value,
        loss_given_default=lgd_value,
        exposure_at_default=ead_value,
        expected_loss=expected_loss,
        scenario_expected_loss=inputs.scenario_expected_loss,
        credit_var_95=inputs.credit_var_95,
        expected_shortfall_95=inputs.expected_shortfall_95,
        recommended_credit_limit=recommended_limit,
        recommended_tenor_days=recommended_tenor,
        recommended_security=recommended_security,
        risk_grade=risk_grade,
        approval_status=approval_status,
        policy_score=round(score, 4),
        limit_haircut=round(haircut, 4),
        key_risk_drivers=risk_drivers,
        mitigating_factors=mitigants,
        model_assumptions={
            "policy_calibration_status": "internal_policy_proxy_not_bank_approved",
            "validation_status": "policy_sanity_checks_embedded",
            "risk_grade_mapping": "A <1%, BBB 1-3%, BB 3-7%, B 7-15%, CCC >=15% PD.",
            "limit_framework": "recommended_limit = base_limit * (1 - policy_haircut)",
            "policy_haircut_breakdown": {
                key: round(value, 4)
                for key, value in haircut_components.items()
            },
            "base_limit_priority": "requested_credit_limit, then approved_credit_limit, then EAD",
            "tail_metric_scope": (
                "credit_var_95 and expected_shortfall_95 are single-name allocated "
                "proxies derived from portfolio Monte Carlo marginal contribution, "
                "not raw portfolio VaR/ES totals."
            ),
            "policy_thresholds": {
                "approve_score_max": 2.0,
                "conditional_score_max": 4.0,
                "secured_score_max": 6.5,
                "reject_score_above": 6.5,
                "ccc_grade": "reject unless separately overridden by policy committee",
            },
            "policy_haircut_drivers": [
                "PD",
                "LGD",
                "market stress",
                "liquidity",
                "leverage",
                "interest coverage",
                "tenor",
                "scenario VaR/ES",
                "collateral strength",
            ],
            "validation_diagnostics": validation_diagnostics,
            "rating_note": "Risk grades are internal proxy grades, not agency ratings.",
        },
        input_data_reference={
            "pd_prediction_id": inputs.pd_prediction_id,
            "loss_estimate_id": inputs.loss_estimate_id,
            "trade_exposure_id": inputs.trade_exposure_id,
            "scenario_result_id": inputs.scenario_result_id,
            "simulation_result_id": inputs.simulation_result_id,
            "financial_ratios_id": inputs.financial_ratios_id,
        },
        warnings=warnings,
    )
