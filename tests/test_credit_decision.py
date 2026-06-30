"""Credit decision engine tests for V2."""

from pathlib import Path

from api.credit_decision.credit_policy import evaluate_credit_policy
from api.credit_decision.engine import (
    CREDIT_DECISION_MODEL_VERSION,
    CreditDecisionInput,
    map_risk_grade,
    recommend_credit_terms,
)
from api.credit_decision.router import router as credit_decision_router
from api.credit_decision.service import _single_name_tail_metric


def direct_input(
    counterparty_id=1,
    pd=0.02,
    lgd=0.35,
    ead=1_000_000,
    requested_limit=1_000_000,
    current_ratio=1.8,
    debt_to_ebitda=2.0,
    collateral_type="letter_of_credit",
    tenor=30,
    scenario_expected_loss=30_000,
    credit_var_95=60_000,
    expected_shortfall_95=75_000,
):
    return CreditDecisionInput(
        counterparty_id=counterparty_id,
        counterparty_name="Direct Test",
        counterparty_type="airline",
        country="USA",
        pd_prediction_id=1,
        loss_estimate_id=1,
        trade_exposure_id=1,
        scenario_result_id=1,
        simulation_result_id=1,
        financial_ratios_id=1,
        probability_of_default=pd,
        structural_pd=pd,
        ml_pd=pd,
        predicted_lgd=lgd,
        exposure_at_default=ead,
        expected_loss=pd * lgd * ead,
        requested_credit_limit=requested_limit,
        approved_credit_limit=requested_limit,
        payment_tenor_days=tenor,
        collateral_type=collateral_type,
        letter_of_credit_flag=collateral_type == "letter_of_credit",
        guarantee_flag=collateral_type == "guarantee",
        deposit_percentage=0.0,
        current_ratio=current_ratio,
        quick_ratio=current_ratio,
        debt_to_ebitda=debt_to_ebitda,
        interest_coverage=5.0 if current_ratio > 1 else 1.2,
        operating_margin=0.10,
        market_stress_index=45 if current_ratio > 1 else 82,
        market_regime="Stable Market" if current_ratio > 1 else "Crisis",
        scenario_expected_loss=scenario_expected_loss,
        credit_var_95=credit_var_95,
        expected_shortfall_95=expected_shortfall_95,
        model_disagreement=False,
    )


def test_risk_grade_mapping_uses_pd_thresholds():
    assert map_risk_grade(0.005) == "A"
    assert map_risk_grade(0.02) == "BBB"
    assert map_risk_grade(0.05) == "BB"
    assert map_risk_grade(0.10) == "B"
    assert map_risk_grade(0.20) == "CCC"


def test_credit_recommendation_sanity_strong_vs_weak():
    strong = recommend_credit_terms(direct_input())
    weak = recommend_credit_terms(
        direct_input(
            pd=0.16,
            lgd=0.72,
            current_ratio=0.85,
            debt_to_ebitda=5.5,
            collateral_type="unsecured",
            tenor=90,
            scenario_expected_loss=300_000,
            credit_var_95=500_000,
            expected_shortfall_95=700_000,
        )
    )

    assert strong.model_version == CREDIT_DECISION_MODEL_VERSION
    assert weak.model_version == CREDIT_DECISION_MODEL_VERSION
    assert strong.recommended_credit_limit > weak.recommended_credit_limit
    assert strong.recommended_tenor_days > weak.recommended_tenor_days
    assert strong.risk_grade in {"A", "BBB"}
    assert weak.risk_grade == "CCC"
    assert weak.approval_status == "REJECT / PREPAYMENT ONLY"
    assert "LC" in weak.recommended_security or "Prepayment" in weak.recommended_security
    assert weak.key_risk_drivers


def test_credit_recommendation_preserves_expected_loss_formula_and_traceability():
    inputs = direct_input(pd=0.08, lgd=0.50, ead=2_000_000, requested_limit=2_500_000)
    result = recommend_credit_terms(inputs)

    assert result.expected_loss == inputs.probability_of_default * inputs.predicted_lgd * inputs.exposure_at_default
    assert result.input_data_reference["pd_prediction_id"] == inputs.pd_prediction_id
    assert result.input_data_reference["loss_estimate_id"] == inputs.loss_estimate_id
    assert result.input_data_reference["simulation_result_id"] == inputs.simulation_result_id
    assert result.model_assumptions["limit_framework"] == "recommended_limit = base_limit * (1 - policy_haircut)"
    assert "single-name allocated" in result.model_assumptions["tail_metric_scope"]
    assert result.recommended_credit_limit <= inputs.requested_credit_limit


def test_portfolio_tail_metrics_are_allocated_before_single_name_credit_decision():
    simulation = {
        "var_95": 23_184_318.10,
        "expected_shortfall_95": 26_174_095.20,
        "marginal_risk_contribution": {"259": 0.004487750644102689},
    }

    allocated_var = _single_name_tail_metric(
        simulation,
        counterparty_id=259,
        metric_name="var_95",
        exposure_at_default=2_273_117,
        requested_credit_limit=4_000_000,
    )
    allocated_es = _single_name_tail_metric(
        simulation,
        counterparty_id=259,
        metric_name="expected_shortfall_95",
        exposure_at_default=2_273_117,
        requested_credit_limit=4_000_000,
    )

    assert round(allocated_var, 2) == round(
        simulation["var_95"] * simulation["marginal_risk_contribution"]["259"], 2
    )
    assert round(allocated_es, 2) == round(
        simulation["expected_shortfall_95"] * simulation["marginal_risk_contribution"]["259"], 2
    )
    assert allocated_var < simulation["var_95"]
    assert allocated_es < simulation["expected_shortfall_95"]


def test_allocated_tail_metric_is_capped_at_single_name_exposure():
    simulation = {
        "var_95": 40_000_000,
        "marginal_risk_contribution": {"9": 0.80},
    }

    assert (
        _single_name_tail_metric(
            simulation,
            counterparty_id=9,
            metric_name="var_95",
            exposure_at_default=3_000_000,
            requested_credit_limit=4_000_000,
        )
        == 3_000_000
    )


def test_credit_policy_helper_is_directionally_consistent():
    strong = evaluate_credit_policy(
        {"company_name": "Strong", "pd": 0.02, "lgd": 0.35, "exposure": 1_000_000, "security": "LC"},
        requested_exposure=1_000_000,
        tenor_days=30,
    )
    weak = evaluate_credit_policy(
        {"company_name": "Weak", "pd": 0.18, "lgd": 0.75, "exposure": 1_000_000, "security": "None"},
        requested_exposure=1_000_000,
        tenor_days=120,
    )

    assert strong["decision"] == "APPROVE"
    assert weak["decision"] == "REJECT"
    assert weak["score"] > strong["score"]
    assert weak["expected_loss"] > strong["expected_loss"]


def test_credit_decision_router_imports_with_v2_paths():
    assert credit_decision_router.prefix == "/api/v1/credit-decision"
    route_paths = {route.path for route in credit_decision_router.routes}
    assert "/api/v1/credit-decision/counterparty/{counterparty_id}/recommend" in route_paths
    assert "/api/v1/credit-decision/counterparty/{counterparty_id}/latest" in route_paths
    assert "/api/v1/credit-decision/memo/{company_name}" in route_paths


def test_no_v1_imports_or_artifact_paths_in_phase10_files():
    files = [
        "api/credit_decision/engine.py",
        "api/credit_decision/service.py",
        "api/credit_decision/credit_policy.py",
        "api/credit_decision/router.py",
        "api/credit_decision/schemas.py",
    ]
    forbidden = [
        "database.db_connection",
        "decision_engine.",
        "api.schemas_phase8",
        "models.phase2_orm",
        "models.credit",
        "models.ml",
        "from simulation.",
        "from risk.",
        "CREDIT_RISK_PROJECT_V1",
        ".pkl",
        ".faiss",
    ]

    for file_path in files:
        text = Path(file_path).read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text


