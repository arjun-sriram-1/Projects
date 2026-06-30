"""Scenario stress-testing wrapper built on Phase 7 data-driven scenarios."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from api.portfolio_risk.monte_carlo import simulate_portfolio_loss_from_dataframe
from api.portfolio_risk.scenario_generator import generate_market_scenarios


def _metrics_from_distribution(summary: dict) -> dict:
    return {
        "Expected Loss": float(summary["mean"]),
        "VaR (95%)": float(summary["p95"]),
        "VaR (99%)": float(summary["p99"]),
        "Expected Shortfall (95%)": float(summary.get("expected_shortfall_95", summary["p95"])),
        "Expected Shortfall (99%)": float(summary.get("expected_shortfall_99", summary["p99"])),
        "Unexpected Loss": float(summary["std"]),
        "Max Loss": float(summary["max"]),
    }


def run_stress_test(
    df: pd.DataFrame,
    n_simulations: int = 1000,
    market_prices: Optional[pd.DataFrame] = None,
    stress_history: Optional[pd.DataFrame] = None,
    regime_history: Optional[pd.DataFrame] = None,
):
    """Run all Phase 7 scenarios against a dataframe portfolio.

    Historical market data is required so this wrapper remains compliant with
    the project rule that scenarios must not be hardcoded.
    """
    if market_prices is None:
        raise ValueError("market_prices history is required for data-driven stress testing.")

    scenarios = generate_market_scenarios(
        market_prices=market_prices,
        stress_history=stress_history,
        regime_history=regime_history,
    )
    results = {}
    for scenario in scenarios:
        output = simulate_portfolio_loss_from_dataframe(
            df,
            n_simulations=n_simulations,
            scenario=scenario,
        )
        diagnostics = output["diagnostics"]
        summary = diagnostics["loss_distribution_summary"]
        metrics = _metrics_from_distribution(
            {
                **summary,
                "expected_shortfall_95": diagnostics["expected_shortfall_95"],
                "expected_shortfall_99": diagnostics["expected_shortfall_99"],
            }
        )
        results[scenario.scenario_type] = {
            **metrics,
            "Diagnostics": diagnostics,
        }
    return results


def stress_test_to_dataframe(clean_results):
    rows = []
    for scenario, vals in clean_results.items():
        rows.append(
            {
                "Scenario": scenario,
                "Expected Loss": vals["Expected Loss"],
                "VaR (95%)": vals["VaR (95%)"],
                "VaR (99%)": vals["VaR (99%)"],
                "Unexpected Loss": vals["Unexpected Loss"],
                "Max Loss": vals["Max Loss"],
            }
        )
    return pd.DataFrame(rows)


