"""
Geopolitical and Macro Stress Index

Business purpose:
Translate market, commodity, FX, rate, freight, and safe-haven proxies into a
0-100 stress index used by scenario generation, PD stress adjustments, credit
limit haircuts, and analyst explanations.

Inputs:
Historical market_prices rows with date, asset, and price. Supported proxies
include Brent/WTI crude, heating oil as a jet-fuel proxy, VIX, S&P 500, DXY,
USD/INR, EUR/USD, gold, 10Y/2Y rates, yield-curve spread, CPI/inflation, and
freight proxy data.

Outputs:
Daily stress index history, stress level, PCA loadings, explained variance, and
driver metadata. Higher values always mean higher market/geopolitical stress.

Method:
Market prices are converted into economically oriented return/volatility/loss
components, standardized with z-scores, compressed with PCA PC1 where possible,
and rescaled to 0-100 using historical percentiles.

Assumptions:
Yahoo Finance market proxies are acceptable free proxies when direct EIA/FRED
series are unavailable. Missing proxies are explicitly reported rather than
synthetically filled.

Limitations:
This is a market-proxy stress index, not an official geopolitical risk index.
It should support credit analysis, not replace analyst judgment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA


STRESS_MODEL_VERSION = "market_stress_pca_v1.0"


ASSET_ALIASES = {
    "brent_oil": ["brent_oil", "brent", "BRENT", "BZ=F"],
    "crude_oil": ["crude_oil", "wti", "WTI", "CL=F"],
    "heating_oil_proxy": ["heating_oil_proxy", "heating_oil", "HO=F"],
    "jet_fuel_proxy": ["jet_fuel_proxy", "jet_fuel", "EER_EPJK_PF4_RGC_DPG"],
    "jet_crack_spread": ["jet_crack_spread", "crack_spread", "jet_fuel_crack_spread"],
    "natural_gas": ["natural_gas", "NG=F"],
    "vix": ["vix", "VIX", "^VIX"],
    "sp500": ["sp500", "SP500", "^GSPC"],
    "dxy": ["dxy", "DXY", "DX-Y.NYB"],
    "usd_inr": ["usd_inr", "USDINR=X"],
    "eur_usd": ["eur_usd", "EURUSD=X"],
    "gold": ["gold", "GOLD", "GC=F"],
    "us_10y_yield": ["us_10y_yield", "10y", "^TNX"],
    "us_2y_yield": ["us_2y_yield", "2y", "DGS2"],
    "yield_curve_spread": ["yield_curve_spread", "T10Y2Y"],
    "cpi_index": ["cpi_index", "CPIAUCSL", "inflation"],
    "high_yield_spread": ["high_yield_spread", "BAMLH0A0HYM2"],
    "freight_proxy": ["freight_proxy", "baltic_dry", "BDRY"],
    "eia_crude_inventories": ["eia_crude_inventories", "crude_inventories", "WCESTUS1"],
    "opec_production": ["opec_production", "opec_crude_production"],
    "global_pmi": ["global_pmi", "pmi", "NAPM"],
    "iata_passenger_traffic": ["iata_passenger_traffic", "iata_rpk", "passenger_traffic"],
}


COMPONENT_DESCRIPTIONS = {
    "oil_volatility_zscore": "Oil volatility proxy from Brent/WTI/heating oil returns",
    "brent_return_zscore": "Fuel cost pressure from Brent returns",
    "heating_oil_return_zscore": "Jet fuel proxy pressure from heating oil returns",
    "jet_fuel_return_zscore": "Jet fuel spot/proxy pressure from EIA/FRED/yfinance returns",
    "jet_crack_spread_zscore": "Refining margin pressure from jet fuel crack spread",
    "vix_zscore": "Market fear from VIX level",
    "sp500_loss_zscore": "Risk-off pressure from S&P 500 losses",
    "dxy_return_zscore": "USD strength from DXY returns",
    "usd_inr_return_zscore": "USD funding/import pressure from USD/INR returns",
    "gold_return_zscore": "Safe-haven demand from gold returns",
    "yield_10y_change_zscore": "Rate shock from 10Y yield changes",
    "yield_curve_stress_zscore": "Yield-curve/rates stress from 10Y-2Y spread changes",
    "inflation_zscore": "Inflation pressure from CPI changes",
    "high_yield_spread_zscore": "Credit-market stress from high-yield spreads",
    "freight_loss_zscore": "Trade slowdown proxy from freight losses",
    "crude_inventory_build_zscore": "Oil-demand/supply pressure from crude inventory builds",
    "opec_production_cut_zscore": "Supply-tightness pressure from falling OPEC production",
    "global_pmi_weakness_zscore": "Global activity weakness from PMI below normal",
    "iata_traffic_loss_zscore": "Airline demand weakness from passenger traffic declines",
}


@dataclass
class StressIndexBuildResult:
    history: pd.DataFrame
    component_matrix: pd.DataFrame
    pca_loadings: Dict[str, float]
    explained_variance_ratio: float
    available_components: List[str]
    missing_components: List[str]
    model_version: str = STRESS_MODEL_VERSION


def classify_stress_level(stress_index: float) -> str:
    """Classify a 0-100 stress score into an analyst-friendly bucket."""
    if stress_index < 20:
        return "Calm"
    if stress_index < 40:
        return "Normal"
    if stress_index < 60:
        return "Elevated"
    if stress_index < 80:
        return "Stressed"
    return "Crisis"


def _first_available(pivot: pd.DataFrame, canonical_asset: str) -> Optional[str]:
    for alias in ASSET_ALIASES[canonical_asset]:
        if alias in pivot.columns:
            return alias
    return None


def _zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if pd.isna(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def _safe_log_return(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce").replace(0, np.nan)
    return np.log(clean / clean.shift(1))


def _percentile_scale(scores: pd.Series) -> pd.Series:
    if scores.empty:
        return scores
    p1 = np.nanpercentile(scores, 1)
    p99 = np.nanpercentile(scores, 99)
    if not np.isfinite(p1) or not np.isfinite(p99) or p99 == p1:
        return pd.Series(50.0, index=scores.index)
    return (((scores - p1) / (p99 - p1)) * 100).clip(0, 100)


def build_market_component_matrix(
    market_prices: pd.DataFrame,
    volatility_window: int = 20,
) -> tuple[pd.DataFrame, list[str]]:
    """Build economically oriented z-scored stress components from market prices."""
    required = {"date", "asset", "price"}
    if not required.issubset(market_prices.columns):
        raise ValueError("market_prices must include date, asset, and price columns")

    prices = market_prices.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.date
    prices["price"] = pd.to_numeric(prices["price"], errors="coerce")
    prices = prices.dropna(subset=["date", "asset", "price"])
    if prices.empty:
        raise ValueError("No valid market price rows available for stress index")

    pivot = (
        prices.pivot_table(index="date", columns="asset", values="price", aggfunc="last")
        .sort_index()
        .ffill()
    )

    components: dict[str, pd.Series] = {}
    missing: list[str] = []

    brent_col = _first_available(pivot, "brent_oil")
    crude_col = _first_available(pivot, "crude_oil")
    heating_col = _first_available(pivot, "heating_oil_proxy")
    jet_fuel_col = _first_available(pivot, "jet_fuel_proxy")
    oil_return_inputs = []
    for col in [brent_col, crude_col, heating_col, jet_fuel_col]:
        if col is not None:
            oil_return_inputs.append(_safe_log_return(pivot[col]))
    if oil_return_inputs:
        oil_returns = pd.concat(oil_return_inputs, axis=1).mean(axis=1)
        components["oil_volatility_zscore"] = _zscore(
            oil_returns.rolling(volatility_window, min_periods=5).std()
        )
    else:
        missing.append("oil_volatility_zscore")

    if brent_col is not None:
        components["brent_return_zscore"] = _zscore(_safe_log_return(pivot[brent_col]))
    else:
        missing.append("brent_return_zscore")

    if heating_col is not None:
        components["heating_oil_return_zscore"] = _zscore(_safe_log_return(pivot[heating_col]))
    else:
        missing.append("heating_oil_return_zscore")

    if jet_fuel_col is not None:
        components["jet_fuel_return_zscore"] = _zscore(_safe_log_return(pivot[jet_fuel_col]))
    else:
        missing.append("jet_fuel_return_zscore")

    single_asset_components = {
        "vix": ("vix_zscore", lambda s: s),
        "sp500": ("sp500_loss_zscore", lambda s: -_safe_log_return(s)),
        "dxy": ("dxy_return_zscore", _safe_log_return),
        "usd_inr": ("usd_inr_return_zscore", _safe_log_return),
        "gold": ("gold_return_zscore", _safe_log_return),
        "us_10y_yield": ("yield_10y_change_zscore", lambda s: s.diff()),
        "yield_curve_spread": ("yield_curve_stress_zscore", lambda s: -s.diff()),
        "cpi_index": ("inflation_zscore", lambda s: s.pct_change()),
        "high_yield_spread": ("high_yield_spread_zscore", lambda s: s.diff()),
        "freight_proxy": ("freight_loss_zscore", lambda s: -_safe_log_return(s)),
        "jet_crack_spread": ("jet_crack_spread_zscore", lambda s: s.diff()),
        "eia_crude_inventories": ("crude_inventory_build_zscore", lambda s: s.pct_change()),
        "opec_production": ("opec_production_cut_zscore", lambda s: -s.pct_change()),
        "global_pmi": ("global_pmi_weakness_zscore", lambda s: -s.diff()),
        "iata_passenger_traffic": ("iata_traffic_loss_zscore", lambda s: -s.pct_change()),
    }
    for asset_name, (component_name, transform) in single_asset_components.items():
        col = _first_available(pivot, asset_name)
        if col is None:
            missing.append(component_name)
            continue
        components[component_name] = _zscore(transform(pivot[col]))

    component_matrix = pd.DataFrame(components).replace([np.inf, -np.inf], np.nan)
    component_matrix = component_matrix.dropna(how="all")
    component_matrix = component_matrix.fillna(0.0)
    if component_matrix.empty:
        raise ValueError("No stress components could be built from available market data")

    return component_matrix, missing


def _driver_lists(loadings: Dict[str, float]) -> tuple[list[dict], list[dict]]:
    ordered = sorted(loadings.items(), key=lambda item: abs(item[1]), reverse=True)
    positive = [
        {
            "component": name,
            "loading": value,
            "description": COMPONENT_DESCRIPTIONS.get(name, name),
        }
        for name, value in ordered
        if value >= 0
    ][:5]
    negative = [
        {
            "component": name,
            "loading": value,
            "description": COMPONENT_DESCRIPTIONS.get(name, name),
        }
        for name, value in ordered
        if value < 0
    ][:5]
    return positive, negative


def build_stress_index(market_prices: pd.DataFrame) -> StressIndexBuildResult:
    """Build a data-driven 0-100 stress index from historical market prices."""
    components, missing = build_market_component_matrix(market_prices)
    available = list(components.columns)

    if len(available) >= 2 and len(components) >= 10:
        pca = PCA(n_components=1)
        pc1 = pd.Series(
            pca.fit_transform(components.values)[:, 0],
            index=components.index,
            name="pc1_score",
        )
        average_stress = components.mean(axis=1)
        if pc1.corr(average_stress) < 0:
            pc1 = -pc1
            loadings_array = -pca.components_[0]
        else:
            loadings_array = pca.components_[0]
        explained = float(pca.explained_variance_ratio_[0])
        loadings = {
            component: float(loading)
            for component, loading in zip(available, loadings_array)
        }
    else:
        pc1 = components.mean(axis=1).rename("pc1_score")
        explained = 1.0
        equal_weight = 1.0 / len(available)
        loadings = {component: equal_weight for component in available}

    stress_score = _percentile_scale(pc1)
    top_positive, top_negative = _driver_lists(loadings)

    history = pd.DataFrame(
        {
            "date": pd.to_datetime(components.index),
            "stress_index": stress_score.values,
            "stress_level": [classify_stress_level(float(x)) for x in stress_score],
            "pc1_score": pc1.values,
            "explained_variance_ratio": explained,
            "pca_loadings": [loadings for _ in range(len(components))],
            "top_positive_drivers": [top_positive for _ in range(len(components))],
            "top_negative_drivers": [top_negative for _ in range(len(components))],
            "component_values": components.to_dict(orient="records"),
            "available_components": [available for _ in range(len(components))],
            "missing_components": [missing for _ in range(len(components))],
            "model_version": STRESS_MODEL_VERSION,
            "data_source": "market_prices",
        }
    )

    return StressIndexBuildResult(
        history=history,
        component_matrix=components,
        pca_loadings=loadings,
        explained_variance_ratio=explained,
        available_components=available,
        missing_components=missing,
    )


def latest_stress_record(history: pd.DataFrame) -> dict:
    """Return the latest stress record as a dictionary."""
    if history.empty:
        raise ValueError("Stress history is empty")
    return history.sort_values("date").iloc[-1].to_dict()
