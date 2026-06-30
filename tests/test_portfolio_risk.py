"""Scenario, Monte Carlo, and portfolio risk tests for V2."""

from pathlib import Path

import numpy as np
import pandas as pd

from api.portfolio_risk.expected_shortfall import calculate_expected_shortfall
from api.portfolio_risk.hedging import HedgeSensitivityInput, calculate_hedging_sensitivity
from api.portfolio_risk.monte_carlo import PortfolioExposure, simulate_portfolio_loss
from api.portfolio_risk.router import router as portfolio_router
from api.portfolio_risk.scenario_generator import generate_market_scenarios
from api.portfolio_risk.unexpected_loss import compute_unexpected_loss
from api.portfolio_risk.var import compute_var


def synthetic_market_history(n_days=180, start="2024-01-01"):
    rng = np.random.default_rng(77)
    dates = pd.date_range(start, periods=n_days, freq="D")
    starts = {
        "brent_oil": 80.0,
        "crude_oil": 76.0,
        "heating_oil_proxy": 2.8,
        "dxy": 102.0,
        "vix": 15.0,
        "sp500": 4800.0,
        "us_10y_yield": 42.0,
        "freight_proxy": 12.0,
    }
    rows = []
    for asset, initial_value in starts.items():
        values = [initial_value]
        for idx in range(1, n_days):
            shock = rng.normal(0.0002, 0.006)
            if idx > n_days - 30:
                if asset in {"brent_oil", "crude_oil", "heating_oil_proxy", "dxy", "vix", "us_10y_yield"}:
                    shock += 0.006
                if asset in {"sp500", "freight_proxy"}:
                    shock -= 0.006
            values.append(max(0.1, values[-1] * (1 + shock)))
        for dt, value in zip(dates, values):
            rows.append({"date": dt, "asset": asset, "price": value})
    return pd.DataFrame(rows)


def synthetic_stress_history(n_days=180, start="2024-01-01"):
    dates = pd.date_range(start, periods=n_days, freq="D")
    stress = np.linspace(35, 75, n_days) + np.sin(np.arange(n_days) / 8) * 5
    return pd.DataFrame({"date": dates, "stress_index": stress})


def sample_exposure(counterparty_id=1):
    return PortfolioExposure(
        counterparty_id=counterparty_id,
        loss_estimate_id=10 + counterparty_id,
        pd_prediction_id=20 + counterparty_id,
        trade_exposure_id=30 + counterparty_id,
        probability_of_default=0.05,
        loss_given_default=0.45,
        exposure_at_default=1_000_000,
        expected_loss=22_500,
        collateral_strength=0.50,
        commodity_sensitivity_score=0.80,
        fx_sensitivity_score=0.40,
        macro_sensitivity_score=0.60,
        market_stress_index=70,
    )


def test_scenario_generator_uses_historical_quantiles_not_fixed_shocks():
    market = synthetic_market_history()
    stress = synthetic_stress_history()

    scenarios = generate_market_scenarios(market, stress)
    adverse = next(s for s in scenarios if s.scenario_type == "adverse")

    brent_returns = (
        market[market["asset"] == "brent_oil"]
        .sort_values("date")["price"]
        .pct_change()
        .dropna()
    )
    expected_quantile = float(brent_returns.quantile(0.90))

    assert {scenario.scenario_type for scenario in scenarios} == {
        "base_case",
        "normal_volatility",
        "adverse",
        "severe_downside",
        "tail",
    }
    assert adverse.market_shocks["brent_change"] == expected_quantile
    assert adverse.market_shocks["brent_change"] != 0.20
    assert adverse.source_observations > 100


def test_monte_carlo_outputs_required_metrics_and_is_reproducible():
    scenario = generate_market_scenarios(synthetic_market_history(), synthetic_stress_history())[-1]
    exposures = [sample_exposure(1), sample_exposure(2)]

    first = simulate_portfolio_loss(exposures, scenario, n_simulations=300, random_seed=123)
    second = simulate_portfolio_loss(exposures, scenario, n_simulations=300, random_seed=123)

    assert first.number_of_simulations == 300
    assert first.random_seed == 123
    assert first.credit_var_99 >= first.credit_var_95
    assert first.expected_shortfall_95 >= first.credit_var_95
    assert first.loss_distribution_summary == second.loss_distribution_summary
    assert first.default_correlation == second.default_correlation
    assert "1" in first.marginal_risk_contribution
    assert first.input_data_reference["loss_estimate_ids"] == [11, 12]


def test_t_copula_tail_dependence_outputs_metadata_and_tail_loss():
    scenario = generate_market_scenarios(synthetic_market_history(), synthetic_stress_history())[-1]
    exposures = [sample_exposure(1), sample_exposure(2), sample_exposure(3)]

    gaussian = simulate_portfolio_loss(
        exposures,
        scenario,
        n_simulations=800,
        random_seed=321,
        copula_type="gaussian",
    )
    t_copula = simulate_portfolio_loss(
        exposures,
        scenario,
        n_simulations=800,
        random_seed=321,
        copula_type="t_copula",
        degrees_of_freedom=4,
    )
    repeat = simulate_portfolio_loss(
        exposures,
        scenario,
        n_simulations=800,
        random_seed=321,
        copula_type="t_copula",
        degrees_of_freedom=4,
    )

    assert t_copula.copula_type == "t_copula"
    assert t_copula.degrees_of_freedom == 4
    assert "tail" in t_copula.tail_dependence_note.lower()
    assert t_copula.assumptions_reference["degrees_of_freedom"] == 4
    assert t_copula.expected_shortfall_95 >= t_copula.credit_var_95
    assert t_copula.loss_distribution_summary == repeat.loss_distribution_summary
    assert t_copula.credit_var_99 >= gaussian.credit_var_99


def test_var_expected_shortfall_and_unexpected_loss_are_consistent():
    losses = np.array([0, 10, 25, 40, 100, 250, 400], dtype=float)

    var_95 = compute_var(losses, confidence=0.95)
    es_95 = calculate_expected_shortfall(losses, confidence=0.95)
    ul = compute_unexpected_loss(losses)

    assert var_95 >= 0
    assert es_95 >= var_95
    assert ul > 0


def test_hedging_sensitivity_before_after_metrics_follow_rules():
    base = HedgeSensitivityInput(
        counterparty_id=7,
        exposure=1_000_000,
        probability_of_default=0.08,
        loss_given_default=0.50,
        hedge_type="oil_swap",
        hedge_notional=800_000,
        hedge_ratio=0.0,
        scenario_market_move=0.20,
        commodity_sensitivity_score=0.75,
    )
    no_hedge = calculate_hedging_sensitivity(base)
    partial = calculate_hedging_sensitivity(
        HedgeSensitivityInput(**{**base.__dict__, "hedge_ratio": 0.50})
    )
    larger = calculate_hedging_sensitivity(
        HedgeSensitivityInput(**{**base.__dict__, "hedge_ratio": 0.90})
    )

    assert no_hedge.hedge_benefit == 0
    assert no_hedge.hedged_exposure == no_hedge.unhedged_exposure
    assert partial.hedged_exposure < partial.unhedged_exposure
    assert larger.hedged_exposure <= partial.hedged_exposure
    assert partial.hedged_expected_loss < partial.unhedged_expected_loss
    assert partial.assumptions["pd_treatment"] == "PD is not reduced directly by hedge existence."
    assert partial.before_after_metrics["hedged"]["expected_loss"] == partial.hedged_expected_loss


def test_hedging_sensitivity_negative_payoff_does_not_invent_benefit():
    result = calculate_hedging_sensitivity(
        HedgeSensitivityInput(
            exposure=500_000,
            probability_of_default=0.10,
            loss_given_default=0.60,
            hedge_type="oil_swap",
            hedge_notional=300_000,
            hedge_ratio=1.0,
            scenario_market_move=-0.10,
            commodity_sensitivity_score=0.80,
        )
    )

    assert result.hedge_payoff < 0
    assert result.hedge_benefit == 0
    assert result.hedged_exposure == result.unhedged_exposure
    assert any("negative" in warning.lower() for warning in result.warnings)


def test_portfolio_router_imports_with_v2_paths():
    assert portfolio_router.prefix == "/api/v1/scenario-analysis"
    route_paths = {route.path for route in portfolio_router.routes}
    assert "/api/v1/scenario-analysis/scenarios" in route_paths
    assert "/api/v1/scenario-analysis/monte-carlo/run" in route_paths
    assert "/api/v1/scenario-analysis/monte-carlo/latest" in route_paths
    assert "/api/v1/scenario-analysis/hedging/sensitivity" in route_paths


def test_no_v1_imports_or_artifact_paths_in_phase9_files():
    files = [
        "api/portfolio_risk/scenario_generator.py",
        "api/portfolio_risk/monte_carlo.py",
        "api/portfolio_risk/service.py",
        "api/portfolio_risk/stress_testing.py",
        "api/portfolio_risk/var.py",
        "api/portfolio_risk/expected_shortfall.py",
        "api/portfolio_risk/unexpected_loss.py",
        "api/portfolio_risk/risk_contributions.py",
        "api/portfolio_risk/hedging.py",
        "api/portfolio_risk/router.py",
        "api/portfolio_risk/schemas.py",
    ]
    forbidden = [
        "database.db_connection",
        "models.phase2_orm",
        "models.credit",
        "models.ml",
        "api.schemas_phase7",
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

