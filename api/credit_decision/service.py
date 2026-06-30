"""Database service for canonical credit recommendations and grounded memos."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.credit_decision.engine import (
    CreditDecisionInput,
    CreditDecisionResult,
    recommend_credit_terms,
)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _json_value(db: Session, param_name: str) -> str:
    if db.get_bind().dialect.name == "postgresql":
        return f"CAST(:{param_name} AS JSONB)"
    return f":{param_name}"


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _single_name_tail_metric(
    simulation: Any,
    counterparty_id: int,
    metric_name: str,
    exposure_at_default: float,
    requested_credit_limit: Optional[float],
) -> Optional[float]:
    """Allocate portfolio VaR/ES to one counterparty using marginal contribution.

    Monte Carlo VaR and ES are portfolio totals. For a single-name credit
    recommendation, using those totals directly makes a small exposure look as
    if it can lose the whole portfolio. The stored marginal contribution is a
    share of simulated portfolio losses, so the single-name proxy is:
    portfolio tail metric * counterparty marginal contribution, capped at the
    amount that can actually be exposed for that counterparty.
    """
    if simulation is None:
        return None

    portfolio_metric = _safe_float(simulation[metric_name] if metric_name in simulation else None)
    if portfolio_metric is None:
        return None

    contributions = _json_dict(
        simulation["marginal_risk_contribution"]
        if "marginal_risk_contribution" in simulation
        else None
    )
    contribution = _safe_float(contributions.get(str(counterparty_id)))
    if contribution is None or contribution <= 0:
        return None

    allocated = portfolio_metric * contribution if contribution <= 1.0 else contribution
    exposure_cap_candidates = [
        value
        for value in (
            _safe_float(exposure_at_default),
            _safe_float(requested_credit_limit),
        )
        if value and value > 0
    ]
    exposure_cap = min(exposure_cap_candidates, default=0.0)
    if exposure_cap > 0:
        allocated = min(allocated, exposure_cap)
    return max(0.0, float(allocated))


def _latest_scenario_for_counterparty(db: Session, counterparty_id: int):
    if db.get_bind().dialect.name != "postgresql":
        return None
    key = str(counterparty_id)
    return db.execute(
        text(
            """
            SELECT *
            FROM scenario_results
            WHERE scenario_impacts ? :counterparty_key
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"counterparty_key": key},
    ).mappings().first()


def _latest_simulation_for_run(db: Session, run_id: Optional[str]):
    if not run_id:
        return None
    return db.execute(
        text(
            """
            SELECT *
            FROM simulation_results
            WHERE run_id = :run_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"run_id": run_id},
    ).mappings().first()


def _scenario_primary_key(row) -> Optional[int]:
    if row is None:
        return None
    if "id" in row and row["id"] is not None:
        return int(row["id"])
    if "scenario_id" in row and row["scenario_id"] is not None:
        return int(row["scenario_id"])
    return None


def load_credit_decision_input(db: Session, counterparty_id: int) -> CreditDecisionInput:
    row = db.execute(
        text(
            """
            SELECT
                cp.id AS counterparty_id,
                cp.counterparty_name,
                cp.counterparty_type,
                cp.country,
                le.id AS loss_estimate_id,
                le.pd_prediction_id,
                le.trade_exposure_id,
                le.probability_of_default,
                le.predicted_lgd,
                le.exposure_at_default,
                le.expected_loss,
                le.collateral_strength,
                pd.structural_pd,
                pd.ml_pd,
                pd.model_disagreement,
                pd.market_stress_index,
                pd.market_regime,
                fr.id AS financial_ratios_id,
                fr.current_ratio,
                fr.quick_ratio,
                fr.debt_to_ebitda,
                fr.interest_coverage,
                fr.operating_margin,
                te.requested_credit_limit,
                te.approved_credit_limit,
                te.payment_tenor_days,
                te.collateral_type,
                te.letter_of_credit_flag,
                te.guarantee_flag,
                te.deposit_percentage
            FROM counterparties_master cp
            JOIN loss_estimates le
                ON le.counterparty_id = cp.id
            LEFT JOIN pd_model_predictions pd
                ON pd.id = le.pd_prediction_id
            LEFT JOIN financial_ratios fr
                ON fr.id = pd.financial_ratios_id
            LEFT JOIN trade_exposures te
                ON te.id = le.trade_exposure_id
            WHERE cp.id = :counterparty_id
            ORDER BY le.created_at DESC, le.id DESC
            LIMIT 1
            """
        ),
        {"counterparty_id": counterparty_id},
    ).mappings().first()

    if row is None:
        raise ValueError(
            f"No Phase 6 loss estimate found for counterparty {counterparty_id}. Run PD and LGD/EAD first."
        )

    scenario = _latest_scenario_for_counterparty(db, counterparty_id)
    simulation = _latest_simulation_for_run(db, scenario["run_id"] if scenario else None)
    scenario_impacts = scenario["scenario_impacts"] if scenario else {}
    impact = scenario_impacts.get(str(counterparty_id), {}) if isinstance(scenario_impacts, dict) else {}
    exposure_at_default = float(row["exposure_at_default"])
    requested_credit_limit = _safe_float(row["requested_credit_limit"])
    credit_var_95 = _single_name_tail_metric(
        simulation,
        counterparty_id,
        "var_95",
        exposure_at_default,
        requested_credit_limit,
    )
    expected_shortfall_95 = _single_name_tail_metric(
        simulation,
        counterparty_id,
        "expected_shortfall_95",
        exposure_at_default,
        requested_credit_limit,
    )

    return CreditDecisionInput(
        counterparty_id=int(row["counterparty_id"]),
        counterparty_name=row["counterparty_name"],
        counterparty_type=row["counterparty_type"],
        country=row["country"],
        pd_prediction_id=int(row["pd_prediction_id"]) if row["pd_prediction_id"] is not None else None,
        loss_estimate_id=int(row["loss_estimate_id"]),
        trade_exposure_id=int(row["trade_exposure_id"]) if row["trade_exposure_id"] is not None else None,
        scenario_result_id=_scenario_primary_key(scenario),
        simulation_result_id=int(simulation["id"]) if simulation is not None and simulation["id"] is not None else None,
        financial_ratios_id=int(row["financial_ratios_id"]) if row["financial_ratios_id"] is not None else None,
        probability_of_default=float(row["probability_of_default"]),
        structural_pd=_safe_float(row["structural_pd"]),
        ml_pd=_safe_float(row["ml_pd"]),
        predicted_lgd=float(row["predicted_lgd"]),
        exposure_at_default=exposure_at_default,
        expected_loss=float(row["expected_loss"]),
        requested_credit_limit=requested_credit_limit,
        approved_credit_limit=_safe_float(row["approved_credit_limit"]),
        payment_tenor_days=int(row["payment_tenor_days"] or 30),
        collateral_type=row["collateral_type"] or "unsecured",
        letter_of_credit_flag=bool(row["letter_of_credit_flag"] or False),
        guarantee_flag=bool(row["guarantee_flag"] or False),
        deposit_percentage=float(row["deposit_percentage"] or 0.0),
        current_ratio=_safe_float(row["current_ratio"]),
        quick_ratio=_safe_float(row["quick_ratio"]),
        debt_to_ebitda=_safe_float(row["debt_to_ebitda"]),
        interest_coverage=_safe_float(row["interest_coverage"]),
        operating_margin=_safe_float(row["operating_margin"]),
        market_stress_index=_safe_float(row["market_stress_index"]),
        market_regime=row["market_regime"],
        scenario_expected_loss=_safe_float(impact.get("scenario_expected_loss")),
        credit_var_95=credit_var_95,
        expected_shortfall_95=expected_shortfall_95,
        model_disagreement=bool(row["model_disagreement"] or False),
    )


def save_credit_recommendation(db: Session, result: CreditDecisionResult):
    row = db.execute(
        text(
            f"""
            INSERT INTO credit_recommendations (
                run_id,
                counterparty_id,
                model_name,
                model_version,
                probability_of_default,
                loss_given_default,
                exposure_at_default,
                expected_loss,
                scenario_expected_loss,
                credit_var_95,
                expected_shortfall_95,
                recommended_credit_limit,
                recommended_tenor_days,
                recommended_security,
                risk_grade,
                approval_status,
                policy_score,
                limit_haircut,
                key_risk_drivers,
                mitigating_factors,
                model_assumptions,
                input_data_reference,
                warnings
            )
            VALUES (
                :run_id,
                :counterparty_id,
                :model_name,
                :model_version,
                :probability_of_default,
                :loss_given_default,
                :exposure_at_default,
                :expected_loss,
                :scenario_expected_loss,
                :credit_var_95,
                :expected_shortfall_95,
                :recommended_credit_limit,
                :recommended_tenor_days,
                :recommended_security,
                :risk_grade,
                :approval_status,
                :policy_score,
                :limit_haircut,
                {_json_value(db, "key_risk_drivers")},
                {_json_value(db, "mitigating_factors")},
                {_json_value(db, "model_assumptions")},
                {_json_value(db, "input_data_reference")},
                {_json_value(db, "warnings")}
            )
            RETURNING *
            """
        ),
        {
            **{
                key: value
                for key, value in result.__dict__.items()
                if key
                not in {
                    "key_risk_drivers",
                    "mitigating_factors",
                    "model_assumptions",
                    "input_data_reference",
                    "warnings",
                    "created_at",
                }
            },
            "key_risk_drivers": _json_dumps(result.key_risk_drivers),
            "mitigating_factors": _json_dumps(result.mitigating_factors),
            "model_assumptions": _json_dumps(result.model_assumptions),
            "input_data_reference": _json_dumps(result.input_data_reference),
            "warnings": _json_dumps(result.warnings),
        },
    ).mappings().first()
    db.commit()
    return row


def calculate_and_store_credit_recommendation(db: Session, counterparty_id: int):
    inputs = load_credit_decision_input(db, counterparty_id)
    result = recommend_credit_terms(inputs)
    return save_credit_recommendation(db, result)


def get_latest_credit_recommendation(db: Session, counterparty_id: int):
    return db.execute(
        text(
            """
            SELECT cr.*, cp.counterparty_name, cp.counterparty_type, cp.country
            FROM credit_recommendations cr
            JOIN counterparties_master cp
                ON cp.id = cr.counterparty_id
            WHERE cr.counterparty_id = :counterparty_id
            ORDER BY cr.created_at DESC, cr.id DESC
            LIMIT 1
            """
        ),
        {"counterparty_id": counterparty_id},
    ).mappings().first()


def get_latest_credit_recommendation_by_name(db: Session, company_name: str):
    return db.execute(
        text(
            """
            SELECT cr.*, cp.counterparty_name, cp.counterparty_type, cp.country
            FROM credit_recommendations cr
            JOIN counterparties_master cp
                ON cp.id = cr.counterparty_id
            WHERE LOWER(cp.counterparty_name) = LOWER(:company_name)
            ORDER BY cr.created_at DESC, cr.id DESC
            LIMIT 1
            """
        ),
        {"company_name": company_name},
    ).mappings().first()


def build_grounded_credit_memo(db: Session, company_name: str, persist: bool = True) -> str:
    recommendation = get_latest_credit_recommendation_by_name(db, company_name)
    if recommendation is None:
        return (
            f"Credit memo unavailable for {company_name}.\n\n"
            "No stored credit recommendation was found. Run the PD, LGD/EAD, "
            "scenario/Monte Carlo, and credit recommendation steps first. "
            "No numerical credit memo has been generated because the required "
            "stored model outputs are missing."
        )

    drivers = recommendation["key_risk_drivers"] or []
    mitigants = recommendation["mitigating_factors"] or []
    warnings = recommendation["warnings"] or []
    refs = recommendation["input_data_reference"] or {}

    memo = f"""CREDIT MEMO

Counterparty: {recommendation["counterparty_name"]}
Counterparty Type: {recommendation["counterparty_type"] or "Not stored"}
Country: {recommendation["country"] or "Not stored"}

EXECUTIVE SUMMARY
Approval Status: {recommendation["approval_status"]}
Risk Grade: {recommendation["risk_grade"]}
Recommended Credit Limit: {float(recommendation["recommended_credit_limit"]):,.2f}
Recommended Tenor: {int(recommendation["recommended_tenor_days"])} days
Recommended Security: {recommendation["recommended_security"]}

CREDIT RISK OUTPUTS
Probability of Default: {float(recommendation["probability_of_default"]):.4%}
Loss Given Default: {float(recommendation["loss_given_default"]):.4%}
Exposure at Default: {float(recommendation["exposure_at_default"]):,.2f}
Expected Loss: {float(recommendation["expected_loss"]):,.2f}
Scenario Expected Loss: {float(recommendation["scenario_expected_loss"] or 0):,.2f}
Credit VaR 95: {float(recommendation["credit_var_95"] or 0):,.2f}
Expected Shortfall 95: {float(recommendation["expected_shortfall_95"] or 0):,.2f}

KEY RISK DRIVERS
{chr(10).join(f"- {item}" for item in drivers) if drivers else "- No stored risk drivers."}

MITIGATING FACTORS
{chr(10).join(f"- {item}" for item in mitigants) if mitigants else "- No stored mitigating factors."}

WARNINGS / DATA GAPS
{chr(10).join(f"- {item}" for item in warnings) if warnings else "- No stored warnings."}

AUDIT REFERENCES
PD Prediction ID: {refs.get("pd_prediction_id")}
Loss Estimate ID: {refs.get("loss_estimate_id")}
Trade Exposure ID: {refs.get("trade_exposure_id")}
Scenario Result ID: {refs.get("scenario_result_id")}
Simulation Result ID: {refs.get("simulation_result_id")}
Financial Ratios ID: {refs.get("financial_ratios_id")}
Recommendation Run ID: {recommendation["run_id"]}

NOTE
This memo is generated only from stored SQL/model outputs. Missing values are shown as missing or zero where no stored model output exists; no numerical claim is invented by the AI layer.
"""

    if persist:
        db.execute(
            text(
                f"""
                INSERT INTO ai_credit_memos (
                    run_id,
                    counterparty_id,
                    credit_recommendation_id,
                    model_name,
                    model_version,
                    memo_text,
                    input_data_reference,
                    assumptions_reference,
                    warnings
                )
                VALUES (
                    :run_id,
                    :counterparty_id,
                    :credit_recommendation_id,
                    'Grounded SQL Credit Memo Generator',
                    'grounded_memo_v1.0',
                    :memo_text,
                    {_json_value(db, "input_data_reference")},
                    {_json_value(db, "assumptions_reference")},
                    {_json_value(db, "warnings")}
                )
                """
            ),
            {
                "run_id": f"memo-{recommendation['run_id']}",
                "counterparty_id": recommendation["counterparty_id"],
                "credit_recommendation_id": recommendation["id"],
                "memo_text": memo,
                "input_data_reference": _json_dumps(
                    {
                        "credit_recommendation_id": recommendation["id"],
                        **refs,
                    }
                ),
                "assumptions_reference": _json_dumps(
                    {
                        "grounding_rule": "Memo uses only stored credit_recommendations and referenced model IDs.",
                    }
                ),
                "warnings": _json_dumps(warnings),
            },
        )
        db.commit()

    return memo


