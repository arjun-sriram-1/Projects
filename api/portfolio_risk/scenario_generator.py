"""
Data-driven scenario generator for Phase 7.

Business purpose:
Build base, normal, adverse, severe, and tail market scenarios from historical
fuel, FX, equity, rates, freight, and stress-index data. These scenarios feed
counterparty loss estimates and portfolio Monte Carlo simulation.

Inputs:
Historical market_prices data, optional stress_index_history, and optional
market_regime_history records.

Outputs:
ScenarioDefinition objects containing market shocks, driver z-scores, source
window metadata, and assumptions that can be stored with scenario_results.

Method:
Daily historical changes are converted to a scenario matrix. Quantiles are then
used to generate scenario movements. Fuel/VIX/DXY/rates/stress use upper-tail
adverse quantiles, while S&P 500 and freight use lower-tail adverse quantiles.

Assumptions:
Jet fuel is proxied by heating oil. Marine fuel is proxied by Brent/crude where
dedicated bunker-fuel history is unavailable.

Limitations:
Scenarios are empirical historical quantiles, not forecasts. They should be
recomputed as fresh market data is loaded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, Optional

import numpy as np
import pandas as pd


SCENARIO_MODEL_VERSION = "historical_quantile_scenarios_v1.0"


@dataclass
class ScenarioDefinition:
    scenario_name: str
    scenario_type: str
    scenario_quantile: float
    market_shocks: Dict[str, float]
    driver_zscores: Dict[str, float]
    source_start_date: Optional[str]
    source_end_date: Optional[str]
    source_observations: int
    market_regime: Optional[str] = None
    data_source: str = "market_prices/stress_index_history/market_regime_history"
    model_name: str = "Historical Quantile Scenario Generator"
    model_version: str = SCENARIO_MODEL_VERSION
    assumptions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


DRIVER_SPECS: Dict[str, Dict[str, Any]] = {
    "brent_change": {"assets": ["brent_oil"], "adverse_tail": "upper"},
    "wti_change": {"assets": ["crude_oil"], "adverse_tail": "upper"},
    "jet_fuel_change": {"assets": ["jet_fuel_proxy", "heating_oil_proxy"], "adverse_tail": "upper"},
    "jet_crack_spread_change": {"assets": ["jet_crack_spread"], "adverse_tail": "upper"},
    "marine_fuel_change": {"assets": ["marine_fuel_proxy", "crude_oil"], "adverse_tail": "upper"},
    "dxy_change": {"assets": ["dxy"], "adverse_tail": "upper"},
    "vix_change": {"assets": ["vix"], "adverse_tail": "upper"},
    "sp500_change": {"assets": ["sp500"], "adverse_tail": "lower"},
    "yield_change": {"assets": ["us_10y_yield", "yield_curve_spread"], "adverse_tail": "upper"},
    "baltic_dry_change": {"assets": ["freight_proxy"], "adverse_tail": "lower"},
    "crude_inventory_change": {"assets": ["eia_crude_inventories"], "adverse_tail": "upper"},
    "opec_production_change": {"assets": ["opec_production"], "adverse_tail": "lower"},
    "global_pmi_change": {"assets": ["global_pmi", "pmi"], "adverse_tail": "lower"},
    "iata_passenger_traffic_change": {"assets": ["iata_passenger_traffic"], "adverse_tail": "lower"},
    "stress_index_change": {"assets": ["stress_index"], "adverse_tail": "upper"},
}


SCENARIO_QUANTILES = {
    "base_case": {"label": "Base Case", "quantile": 0.50},
    "normal_volatility": {"label": "Normal Volatility Case", "quantile": 0.75},
    "adverse": {"label": "Adverse Case", "quantile": 0.90},
    "severe_downside": {"label": "Severe Downside Case", "quantile": 0.95},
    "tail": {"label": "Tail Case", "quantile": 0.99},
}


def _as_date_string(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, date):
        return value.isoformat()
    return pd.to_datetime(value).date().isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_scenario_matrix(
    market_prices: pd.DataFrame,
    stress_history: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Convert historical market and stress data into daily scenario drivers."""
    required = {"date", "asset", "price"}
    if not required.issubset(market_prices.columns):
        raise ValueError("market_prices must include date, asset, and price columns.")

    prices = market_prices.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.date
    prices["price"] = pd.to_numeric(prices["price"], errors="coerce")
    prices = prices.dropna(subset=["date", "asset", "price"])

    pivot = (
        prices.pivot_table(index="date", columns="asset", values="price", aggfunc="last")
        .sort_index()
        .ffill()
    )
    returns = pivot.pct_change()

    scenario_matrix = pd.DataFrame(index=returns.index)
    for driver, spec in DRIVER_SPECS.items():
        for asset in spec["assets"]:
            if asset in returns.columns and asset != "stress_index":
                scenario_matrix[driver] = returns[asset]
                break

    if stress_history is not None and not stress_history.empty:
        stress = stress_history.copy()
        stress["date"] = pd.to_datetime(stress["date"]).dt.date
        stress["stress_index"] = pd.to_numeric(stress["stress_index"], errors="coerce")
        stress = stress.dropna(subset=["date", "stress_index"]).set_index("date").sort_index()
        scenario_matrix["stress_index_change"] = stress["stress_index"].diff() / 100.0

    available = [col for col in DRIVER_SPECS if col in scenario_matrix.columns]
    scenario_matrix = scenario_matrix[available].replace([np.inf, -np.inf], np.nan).dropna(how="all")
    return scenario_matrix


def filter_matrix_by_regime(
    scenario_matrix: pd.DataFrame,
    regime_history: Optional[pd.DataFrame] = None,
    target_regime: Optional[str] = None,
    minimum_observations: int = 60,
) -> tuple[pd.DataFrame, Optional[str]]:
    """Use same-regime history when enough observations exist; otherwise use all history."""
    if regime_history is None or regime_history.empty:
        return scenario_matrix, target_regime

    regimes = regime_history.copy()
    regimes["date"] = pd.to_datetime(regimes["date"]).dt.date
    regimes = regimes.dropna(subset=["date", "regime_label"]).sort_values("date")
    if regimes.empty:
        return scenario_matrix, target_regime

    regime_label = target_regime or str(regimes.iloc[-1]["regime_label"])
    matching_dates = set(regimes.loc[regimes["regime_label"] == regime_label, "date"])
    filtered = scenario_matrix.loc[[idx for idx in scenario_matrix.index if idx in matching_dates]]

    if len(filtered) >= minimum_observations:
        return filtered, regime_label
    return scenario_matrix, regime_label


def _quantile_for_driver(values: pd.Series, scenario_quantile: float, adverse_tail: str) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    if scenario_quantile == 0.50:
        return _safe_float(clean.quantile(0.50))
    quantile = scenario_quantile if adverse_tail == "upper" else 1.0 - scenario_quantile
    return _safe_float(clean.quantile(quantile))


def _driver_zscore(value: float, values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if len(clean) < 2:
        return 0.0
    std = float(clean.std(ddof=0))
    if std == 0:
        return 0.0
    return float((value - float(clean.mean())) / std)


def generate_market_scenarios(
    market_prices: pd.DataFrame,
    stress_history: Optional[pd.DataFrame] = None,
    regime_history: Optional[pd.DataFrame] = None,
    target_regime: Optional[str] = None,
) -> list[ScenarioDefinition]:
    """Generate required Phase 7 scenarios from historical quantiles."""
    scenario_matrix = build_scenario_matrix(market_prices, stress_history)
    if scenario_matrix.empty:
        raise ValueError("Not enough market history to generate scenarios.")

    source_matrix, regime_label = filter_matrix_by_regime(
        scenario_matrix,
        regime_history=regime_history,
        target_regime=target_regime,
    )
    source_matrix = source_matrix.dropna(how="all")
    if source_matrix.empty:
        raise ValueError("Scenario source matrix is empty after regime filtering.")

    source_start = _as_date_string(source_matrix.index.min())
    source_end = _as_date_string(source_matrix.index.max())
    scenarios: list[ScenarioDefinition] = []

    for scenario_type, config in SCENARIO_QUANTILES.items():
        quantile = float(config["quantile"])
        shocks: Dict[str, float] = {}
        zscores: Dict[str, float] = {}

        for driver, spec in DRIVER_SPECS.items():
            if driver not in source_matrix.columns:
                shocks[driver] = 0.0
                zscores[driver] = 0.0
                continue
            value = _quantile_for_driver(source_matrix[driver], quantile, spec["adverse_tail"])
            shocks[driver] = value
            zscores[driver] = _driver_zscore(value, source_matrix[driver])

        scenarios.append(
            ScenarioDefinition(
                scenario_name=str(config["label"]),
                scenario_type=scenario_type,
                scenario_quantile=quantile,
                market_shocks=shocks,
                driver_zscores=zscores,
                source_start_date=source_start,
                source_end_date=source_end,
                source_observations=int(len(source_matrix)),
                market_regime=regime_label,
                assumptions={
                    "scenario_method": "Historical empirical quantiles by driver.",
                    "normal_volatility_case": "Uses 75th percentile for upper-tail adverse drivers and 25th percentile for lower-tail adverse drivers.",
                    "adverse_tail_mapping": {
                        driver: spec["adverse_tail"] for driver, spec in DRIVER_SPECS.items()
                    },
                    "proxy_mapping": {
                        "jet_fuel": "jet_fuel_proxy when available, otherwise heating_oil_proxy",
                        "jet_crack_spread": "calculated as jet_fuel_proxy * 42 - brent_oil when available",
                        "marine_fuel": "marine_fuel_proxy when available, otherwise crude_oil",
                        "baltic_dry": "freight_proxy",
                        "crude_inventories": "EIA crude inventory rows when loaded",
                        "opec_production": "staged CSV production rows when loaded",
                        "global_pmi": "global_pmi when staged, otherwise PMI proxy",
                        "iata_passenger_traffic": "staged CSV passenger traffic rows when loaded",
                    },
                    "regime_filter": "Latest/specified regime used only when enough same-regime observations exist.",
                },
            )
        )

    return scenarios


def scenarios_to_dataframe(scenarios: Iterable[ScenarioDefinition]) -> pd.DataFrame:
    rows = []
    for scenario in scenarios:
        rows.append(
            {
                "scenario_name": scenario.scenario_name,
                "scenario_type": scenario.scenario_type,
                "scenario_quantile": scenario.scenario_quantile,
                "market_regime": scenario.market_regime,
                **scenario.market_shocks,
            }
        )
    return pd.DataFrame(rows)


def get_all_scenarios(
    market_prices: Optional[pd.DataFrame] = None,
    stress_history: Optional[pd.DataFrame] = None,
    regime_history: Optional[pd.DataFrame] = None,
) -> Dict[str, Dict[str, Any]]:
    """Backward-compatible scenario lookup, now requiring historical data."""
    if market_prices is None:
        raise ValueError("market_prices history is required; Phase 7 scenarios are not hardcoded.")
    scenarios = generate_market_scenarios(market_prices, stress_history, regime_history)
    return {scenario.scenario_type: scenario.to_dict() for scenario in scenarios}


def get_scenario(
    scenario_type: str,
    market_prices: pd.DataFrame,
    stress_history: Optional[pd.DataFrame] = None,
    regime_history: Optional[pd.DataFrame] = None,
) -> ScenarioDefinition:
    scenarios = generate_market_scenarios(market_prices, stress_history, regime_history)
    for scenario in scenarios:
        if scenario.scenario_type == scenario_type:
            return scenario
    raise ValueError(f"Scenario '{scenario_type}' not found.")
