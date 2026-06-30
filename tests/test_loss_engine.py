"""LGD, EAD, and expected loss tests for V2."""

from pathlib import Path

from api.machine_learning.loss_model import (
    HISTORICAL_LGD_MODEL_PATH,
    PROJECT_ROOT,
    TradeExposureInput,
    calculate_ead,
    calculate_expected_loss,
    calculate_lgd,
    estimate_loss,
)
from api.machine_learning.loss_router import router as loss_router


def test_lgd_decreases_with_stronger_credit_support():
    unsecured = TradeExposureInput(counterparty_id=1, collateral_type="unsecured")
    letter_of_credit = TradeExposureInput(
        counterparty_id=1,
        collateral_type="letter_of_credit",
        letter_of_credit_flag=True,
    )
    cash_deposit = TradeExposureInput(
        counterparty_id=1,
        collateral_type="cash_deposit",
        deposit_percentage=80,
    )

    unsecured_lgd, unsecured_strength, unsecured_warnings, _ = calculate_lgd(unsecured)
    lc_lgd, lc_strength, lc_warnings, _ = calculate_lgd(letter_of_credit)
    deposit_lgd, deposit_strength, deposit_warnings, _ = calculate_lgd(cash_deposit)

    assert 0 <= unsecured_lgd <= 1
    assert 0 <= lc_lgd <= 1
    assert 0 <= deposit_lgd <= 1
    assert lc_lgd < unsecured_lgd
    assert deposit_lgd < unsecured_lgd
    assert lc_strength > unsecured_strength
    assert deposit_strength > unsecured_strength
    assert unsecured_warnings
    assert lc_warnings
    assert deposit_warnings


def test_ead_uses_invoice_drawdown_and_credit_limit_cap():
    exposure = TradeExposureInput(
        counterparty_id=2,
        invoice_amount=1_000_000,
        approved_credit_limit=900_000,
        outstanding_receivables=200_000,
        payment_tenor_days=60,
        utilization_rate=0.75,
    )

    ead, expected_drawdown, invoice_exposure, cap_applied, warnings = calculate_ead(exposure)

    assert invoice_exposure == 1_000_000
    assert expected_drawdown == 1_500_000
    assert ead == 900_000
    assert cap_applied is True
    assert "EAD capped" in " ".join(warnings)


def test_ead_can_estimate_invoice_from_fuel_volume_and_price():
    exposure = TradeExposureInput(
        counterparty_id=3,
        fuel_volume=10_000,
        fuel_price=3.25,
        outstanding_receivables=5_000,
        payment_tenor_days=30,
        utilization_rate=0.50,
    )

    ead, expected_drawdown, invoice_exposure, cap_applied, warnings = calculate_ead(exposure)

    assert invoice_exposure == 32_500
    assert expected_drawdown == 16_250
    assert ead == 21_250
    assert cap_applied is False
    assert any("fuel_volume" in warning for warning in warnings)


def test_expected_loss_formula_and_estimate_output_are_traceable():
    exposure = TradeExposureInput(
        counterparty_id=4,
        invoice_amount=500_000,
        approved_credit_limit=700_000,
        outstanding_receivables=100_000,
        collateral_type="guarantee",
        guarantee_flag=True,
    )

    result = estimate_loss(0.08, exposure, pd_prediction_id=11, trade_exposure_id=22)

    assert result.probability_of_default == 0.08
    assert result.expected_loss == calculate_expected_loss(
        result.probability_of_default,
        result.predicted_lgd,
        result.exposure_at_default,
    )
    assert result.pd_prediction_id == 11
    assert result.trade_exposure_id == 22
    assert result.input_data_reference["pd_prediction_id"] == 11
    assert result.model_assumptions["expected_loss_formula"] == "EL = PD * LGD * EAD"


def test_financial_history_overlay_increases_lgd_and_expected_loss():
    exposure = TradeExposureInput(
        counterparty_id=4,
        invoice_amount=500_000,
        approved_credit_limit=700_000,
        outstanding_receivables=100_000,
        collateral_type="unsecured",
    )

    base = estimate_loss(0.08, exposure, pd_prediction_id=11, trade_exposure_id=22)
    stressed = estimate_loss(
        0.08,
        exposure,
        pd_prediction_id=11,
        trade_exposure_id=22,
        financial_trend_overlay={
            "period_count": 3,
            "direction": "deteriorating",
            "risk_score": 0.25,
            "lgd_addon": 0.025,
            "liquidity_score": 0.20,
        },
    )

    assert stressed.predicted_lgd > base.predicted_lgd
    assert stressed.expected_loss > base.expected_loss
    assert stressed.model_assumptions["financial_trend_overlay"]["direction"] == "deteriorating"
    assert "financial_trend_lgd_addon" in stressed.model_assumptions["lgd_driver_components"]


def test_lgd_artifact_path_uses_v2_data_models_without_copying_artifact():
    assert PROJECT_ROOT.name == "CREDIT_RISK_PROJECT_V2"
    assert HISTORICAL_LGD_MODEL_PATH == PROJECT_ROOT / "data" / "models" / "historical_lgd_model.pkl"
    assert "models/ml" not in HISTORICAL_LGD_MODEL_PATH.as_posix()


def test_loss_router_imports_with_v2_paths():
    assert loss_router.prefix == "/api/v1/credit-risk"
    route_paths = {route.path for route in loss_router.routes}
    assert "/api/v1/credit-risk/loss/calculate" in route_paths
    assert "/api/v1/credit-risk/counterparty/{counterparty_id}/latest-loss" in route_paths


def test_no_v1_imports_or_legacy_artifact_paths_in_phase8_files():
    files = [
        "api/machine_learning/loss_model.py",
        "api/machine_learning/loss_service.py",
        "api/machine_learning/loss_router.py",
        "api/machine_learning/loss_schemas.py",
    ]
    forbidden = [
        "database.db_connection",
        "models.credit",
        "models.phase2_orm",
        "api.schemas_phase6",
        "CREDIT_RISK_PROJECT_V1",
        '"models" / "ml"',
        "models/ml/",
    ]

    for file_path in files:
        text = Path(file_path).read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text
