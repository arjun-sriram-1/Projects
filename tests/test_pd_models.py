"""PD and structural credit model tests for V2."""

from pathlib import Path

from api.machine_learning.pd_model import (
    HISTORICAL_PD_MODEL_PATH,
    PROJECT_ROOT,
    MarketContext,
    calculate_structural_pd,
    calculate_vulnerability_scores,
    estimate_pd,
)
from api.machine_learning.router import router as pd_router
from api.structural_credit.merton_model import calculate_merton_pd, merton_model


def test_merton_pd_sensitivity_to_debt_volatility_and_assets():
    base_pd, _ = calculate_structural_pd(2_000_000, 600_000, 0.30, 0.04, 1)
    higher_debt_pd, _ = calculate_structural_pd(2_000_000, 1_200_000, 0.30, 0.04, 1)
    higher_vol_pd, _ = calculate_structural_pd(2_000_000, 600_000, 0.55, 0.04, 1)
    higher_asset_pd, _ = calculate_structural_pd(3_000_000, 600_000, 0.30, 0.04, 1)

    assert higher_debt_pd > base_pd
    assert higher_vol_pd > base_pd
    assert higher_asset_pd < base_pd


def test_structural_credit_helper_is_pure_merton_without_artifact_load():
    pd_value = calculate_merton_pd(asset_value=2_000_000, debt=600_000, sigma=0.30)
    result = merton_model(V0=2_000_000, D=600_000, mu=0.04, sigma=0.30, T=1)

    assert 0 < pd_value < 1
    assert 0 < result["pd_structural"] < 1
    assert result["pd_ml"] is None
    assert result["pd_hybrid"] == max(0.0001, result["pd_structural"])


def test_vulnerability_mapping_respects_counterparty_type():
    context = MarketContext(
        stress_index=70,
        oil_volatility_zscore=1.5,
        fuel_return_zscore=1.0,
        fx_return_zscore=0.6,
        freight_loss_zscore=1.0,
    )

    airline = calculate_vulnerability_scores("airline", context)
    distributor = calculate_vulnerability_scores("fuel_distributor", context)

    assert airline.commodity_sensitivity_score > distributor.commodity_sensitivity_score
    assert 0 <= airline.fx_sensitivity_score <= 1
    assert airline.vulnerability_notes


def test_vulnerability_mapping_uses_expanded_market_context():
    base = calculate_vulnerability_scores("airline", MarketContext(stress_index=45))
    stressed = calculate_vulnerability_scores(
        "airline",
        MarketContext(
            stress_index=45,
            crack_spread_zscore=2.0,
            inventory_build_zscore=1.5,
            opec_production_cut_zscore=1.0,
            pmi_weakness_zscore=2.0,
            iata_traffic_loss_zscore=2.0,
        ),
    )

    assert stressed.commodity_sensitivity_score > base.commodity_sensitivity_score
    assert stressed.macro_sensitivity_score > base.macro_sensitivity_score
    assert "passenger-demand" in stressed.vulnerability_notes[0]


def test_estimate_pd_outputs_bounded_traceable_fields():
    context = MarketContext(
        stress_index=65,
        stress_level="Stressed",
        market_regime="USD Stress",
        oil_volatility_zscore=1.2,
        fuel_return_zscore=0.9,
        crack_spread_zscore=1.5,
        fx_return_zscore=0.7,
        inventory_build_zscore=1.0,
        opec_production_cut_zscore=1.0,
        pmi_weakness_zscore=1.2,
        iata_traffic_loss_zscore=1.1,
    )
    financials = {
        "id": 1,
        "total_assets": 2_000_000,
        "total_debt": 600_000,
        "revenue": 1_000_000,
    }
    ratios = {
        "id": 2,
        "current_ratio": 2.0,
        "cash_ratio": 0.48,
        "debt_to_equity": 0.67,
        "debt_to_ebitda": 3.0,
        "interest_coverage": 5.0,
        "net_margin": 0.09,
    }

    result = estimate_pd(
        counterparty_id=99,
        counterparty_type="airline",
        financials=financials,
        ratios=ratios,
        market_context=context,
        financial_metrics_id=1,
        financial_ratios_id=2,
    )

    assert 0 < result.structural_pd < 1
    assert 0 < result.ml_pd < 1
    assert 0 < result.final_pd < 1
    assert result.distance_to_default is not None
    assert result.feature_contributions
    assert "crack_spread_pressure" in result.feature_contributions
    assert "pmi_weakness" in result.feature_contributions
    if HISTORICAL_PD_MODEL_PATH.exists():
        assert result.feature_contributions["final_pd_ml_weight_quality_cap"] <= 0.25
    assert result.input_data_reference["financial_metrics_id"] == 1
    assert result.classification_label in {"A", "BBB", "BB", "B", "CCC"}


def test_financial_history_overlay_increases_pd_when_trends_deteriorate():
    context = MarketContext(stress_index=55, market_regime="Base")
    financials = {
        "id": 1,
        "total_assets": 2_000_000,
        "total_debt": 700_000,
        "revenue": 1_000_000,
    }
    ratios = {
        "id": 2,
        "current_ratio": 1.1,
        "cash_ratio": 0.25,
        "debt_to_equity": 1.4,
        "debt_to_ebitda": 4.0,
        "interest_coverage": 2.5,
        "net_margin": 0.02,
    }
    neutral = estimate_pd(
        counterparty_id=99,
        counterparty_type="airline",
        financials=financials,
        ratios=ratios,
        market_context=context,
        financial_metrics_id=1,
        financial_ratios_id=2,
    )
    deteriorating = estimate_pd(
        counterparty_id=99,
        counterparty_type="airline",
        financials=financials,
        ratios=ratios,
        market_context=context,
        financial_metrics_id=1,
        financial_ratios_id=2,
        financial_trends={
            "period_count": 3,
            "history_status": "available",
            "revenue_cagr": -0.08,
            "latest_revenue_growth": -0.10,
            "ebitda_margin_trend": -0.02,
            "debt_growth": 0.20,
            "interest_coverage_trend": -0.8,
            "current_ratio_trend": -0.20,
            "cash_trend": -0.15,
            "current_ratio_latest": 0.90,
        },
    )

    assert deteriorating.final_pd > neutral.final_pd
    assert deteriorating.asset_volatility >= neutral.asset_volatility
    assert deteriorating.feature_contributions["financial_trend_pd_multiplier"] > 1.0
    assert deteriorating.model_assumptions["financial_trend_overlay"]["direction"] == "deteriorating"


def test_pd_artifact_path_uses_v2_data_models():
    assert PROJECT_ROOT.name == "CREDIT_RISK_PROJECT_V2"
    assert HISTORICAL_PD_MODEL_PATH == PROJECT_ROOT / "data" / "models" / "historical_pd_model.pkl"
    assert "models/ml" not in HISTORICAL_PD_MODEL_PATH.as_posix()


def test_pd_router_imports_with_v2_paths():
    assert pd_router.prefix == "/api/v1/credit-risk"
    route_paths = {route.path for route in pd_router.routes}
    assert "/api/v1/credit-risk/pd/calculate/{financial_metrics_id}" in route_paths
    assert "/api/v1/credit-risk/counterparty/{counterparty_id}/latest-pd" in route_paths


def test_no_v1_imports_or_legacy_artifact_paths_in_phase7_files():
    files = [
        "api/machine_learning/pd_model.py",
        "api/machine_learning/pd_service.py",
        "api/machine_learning/router.py",
        "api/machine_learning/schemas.py",
        "api/structural_credit/merton_model.py",
        "api/structural_credit/distance_to_default.py",
        "api/structural_credit/black_scholes.py",
        "api/structural_credit/inverse_merton.py",
    ]
    forbidden = [
        "database.db_connection",
        "models.credit",
        "models.phase2_orm",
        "models.ml",
        "api.schemas_phase5",
        "CREDIT_RISK_PROJECT_V1",
        '"models" / "ml"',
        "models/ml/",
    ]

    for file_path in files:
        text = Path(file_path).read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text


