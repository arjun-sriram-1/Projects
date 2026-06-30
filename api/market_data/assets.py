"""Canonical market asset groups used across ingestion, models, UI, and RAG."""

from __future__ import annotations


CORE_MARKET_ASSETS = [
    "brent_oil",
    "crude_oil",
    "heating_oil_proxy",
    "jet_fuel_proxy",
    "jet_crack_spread",
    "vix",
    "sp500",
    "dxy",
    "gold",
    "us_10y_yield",
    "us_2y_yield",
    "yield_curve_spread",
    "cpi_index",
    "freight_proxy",
    "eia_crude_inventories",
    "opec_production",
    "global_pmi",
    "pmi",
    "iata_passenger_traffic",
]


MACRO_CONTEXT_ASSETS = {
    "vix",
    "sp500",
    "dxy",
    "gold",
    "us_10y_yield",
    "us_2y_yield",
    "yield_curve_spread",
    "cpi_index",
    "high_yield_spread",
    "eia_crude_inventories",
    "opec_production",
    "global_pmi",
    "pmi",
    "iata_passenger_traffic",
}


FORECAST_DEFAULT_ASSETS = [
    "brent_oil",
    "crude_oil",
    "jet_fuel_proxy",
    "jet_crack_spread",
    "dxy",
    "vix",
    "sp500",
    "us_10y_yield",
    "freight_proxy",
    "eia_crude_inventories",
    "opec_production",
    "global_pmi",
    "iata_passenger_traffic",
]


PD_MARKET_FEATURES = [
    "stress_index",
    "brent_oil",
    "crude_oil",
    "heating_oil_proxy",
    "jet_fuel_proxy",
    "jet_crack_spread",
    "vix",
    "sp500",
    "dxy",
    "us_10y_yield",
    "yield_curve_spread",
    "freight_proxy",
    "eia_crude_inventories",
    "opec_production",
    "global_pmi",
    "pmi",
    "iata_passenger_traffic",
]


def sql_asset_list(assets: list[str] | tuple[str, ...] = CORE_MARKET_ASSETS) -> str:
    """Return a SQL-safe quoted list for static asset filters."""
    return ", ".join(f"'{asset}'" for asset in assets)

