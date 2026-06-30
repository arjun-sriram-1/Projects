"""Commodity risk factor analytics for fuel trade credit decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


COMMODITY_FACTOR_MODEL_VERSION = "commodity_factor_engine_v1.0"


@dataclass
class CommodityFactorResult:
    model_name: str
    model_version: str
    assets: list[str]
    latest_log_returns: dict[str, float]
    rolling_volatility: dict[str, float]
    spread_analysis: dict[str, dict[str, float]]
    correlation_matrix: dict[str, dict[str, float]]
    high_volatility_assets: list[str]
    assumptions: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def _pivot_prices(market_prices: pd.DataFrame, assets: list[str]) -> pd.DataFrame:
    required = {"date", "asset", "price"}
    missing = required - set(market_prices.columns)
    if missing:
        raise ValueError(f"Market price data missing columns: {sorted(missing)}")
    if not assets:
        raise ValueError("At least one commodity asset is required.")

    frame = market_prices.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame = frame[frame["asset"].isin(assets)].dropna(subset=["date", "asset", "price"])
    pivot = frame.pivot_table(index="date", columns="asset", values="price", aggfunc="last").sort_index()
    pivot = pivot.replace([np.inf, -np.inf], np.nan).dropna(how="all")
    if pivot.empty:
        raise ValueError("No usable commodity prices found for requested assets.")
    return pivot


def analyze_commodity_factors(
    market_prices: pd.DataFrame,
    assets: list[str],
    rolling_window: int = 30,
) -> CommodityFactorResult:
    """Calculate log returns, rolling volatility, spreads, and correlations."""
    warnings: list[str] = []
    window = max(2, int(rolling_window or 30))
    prices = _pivot_prices(market_prices, assets)
    available_assets = list(prices.columns)
    missing_assets = [asset for asset in assets if asset not in available_assets]
    if missing_assets:
        warnings.append(f"Missing requested assets: {', '.join(missing_assets)}")
    if len(prices) < window + 1:
        warnings.append("History is shorter than rolling window; using available observations.")
        window = max(2, min(window, len(prices) - 1))
    if window < 2:
        raise ValueError("At least three dated observations are required for commodity factor analysis.")

    returns = np.log(prices / prices.shift(1)).replace([np.inf, -np.inf], np.nan).dropna(how="all")
    latest_log_returns = {
        asset: float(value)
        for asset, value in returns.iloc[-1].dropna().items()
    }
    rolling_vol = returns.rolling(window=window, min_periods=2).std().iloc[-1] * np.sqrt(252)
    rolling_volatility = {
        asset: float(value)
        for asset, value in rolling_vol.dropna().items()
    }

    spread_analysis: dict[str, dict[str, float]] = {}
    for left in available_assets:
        for right in available_assets:
            if left >= right:
                continue
            spread = prices[left] - prices[right]
            if spread.dropna().empty:
                continue
            spread_analysis[f"{left}_minus_{right}"] = {
                "latest_spread": float(spread.dropna().iloc[-1]),
                "average_spread": float(spread.mean()),
                "spread_volatility": float(spread.std(ddof=0) or 0.0),
            }

    corr = returns.corr().fillna(0.0)
    correlation_matrix = {
        row: {col: float(corr.loc[row, col]) for col in corr.columns}
        for row in corr.index
    }
    vol_values = list(rolling_volatility.values())
    vol_threshold = float(np.quantile(vol_values, 0.75)) if vol_values else 0.0
    high_volatility_assets = [
        asset for asset, value in rolling_volatility.items()
        if value >= vol_threshold and value > 0
    ]

    return CommodityFactorResult(
        model_name="Commodity Risk Factor Engine",
        model_version=COMMODITY_FACTOR_MODEL_VERSION,
        assets=available_assets,
        latest_log_returns=latest_log_returns,
        rolling_volatility=rolling_volatility,
        spread_analysis=spread_analysis,
        correlation_matrix=correlation_matrix,
        high_volatility_assets=high_volatility_assets,
        assumptions={
            "returns": "Natural log returns from supplied price history.",
            "volatility": "Rolling daily return volatility annualized with sqrt(252).",
            "spreads": "Pairwise price differences for requested available assets.",
            "correlation": "Pearson correlation matrix on aligned log returns.",
            "rolling_window": window,
        },
        warnings=warnings,
    )
