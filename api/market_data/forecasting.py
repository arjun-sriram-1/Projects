"""
Commodity, FX, and volatility forecasting for V2 market intelligence.

Business purpose:
Produce probabilistic ARIMA, VAR, and GARCH market forecasts that can support
scenario widening and credit risk explanations.

Inputs:
Historical market price records with date, asset, and price columns.

Outputs:
Forecast path/value, confidence interval, backtest error, forecast volatility,
model assumptions, and warnings.

Mathematical method:
ARIMA and VAR use statsmodels. GARCH uses the arch package, matching the V1
quantitative ruler and V1 environment guidance.

Economic intuition:
Forecasts are probabilistic support signals. Higher forecast volatility should
widen adverse scenarios and should not reduce PD or portfolio risk by itself.

Assumptions:
Log returns are used. Missing/short histories produce warnings instead of
fabricated precision.

Limitations:
These models are student-project forecasting components and are not guaranteed
price predictions or institutionally calibrated trading models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

FORECAST_MODEL_VERSION = "statsmodels_arch_market_forecasting_v1.0"


@dataclass
class ForecastResult:
    model_name: str
    model_version: str
    forecast_horizon: int
    input_series: list[str]
    forecast_path: dict[str, list[float]]
    forecast_value: dict[str, float]
    confidence_interval: dict[str, dict[str, float]]
    forecast_error: Optional[float]
    backtest_error: Optional[float]
    forecast_volatility: Optional[float]
    volatility_regime: Optional[str]
    assumptions: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def _require_statsmodels():
    try:
        from statsmodels.tsa.api import VAR
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError as exc:
        raise ImportError(
            "statsmodels is required for ARIMA/VAR forecasting. Install V2 requirements first."
        ) from exc
    return ARIMA, VAR


def _require_arch_model():
    try:
        from arch import arch_model
    except ImportError as exc:
        raise ImportError(
            "arch is required for GARCH volatility forecasting. Install V2 requirements first."
        ) from exc
    return arch_model


def _prepare_price_matrix(market_prices: pd.DataFrame, assets: list[str]) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    required = {"date", "asset", "price"}
    if not required.issubset(market_prices.columns):
        missing = sorted(required - set(market_prices.columns))
        raise ValueError(f"market_prices missing required columns: {missing}")
    frame = market_prices.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    pivot = frame.pivot_table(index="date", columns="asset", values="price", aggfunc="last").sort_index()
    selected = [asset for asset in assets if asset in pivot.columns]
    missing_assets = [asset for asset in assets if asset not in pivot.columns]
    if missing_assets:
        warnings.append(f"Missing requested assets skipped: {missing_assets}")
    if not selected:
        raise ValueError("None of the requested assets are available in market_prices.")
    return pivot[selected].dropna(how="all").ffill().dropna(), warnings


def _log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return np.log(prices / prices.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()


def _vol_regime(volatility: float) -> str:
    if volatility < 0.10:
        return "low"
    if volatility < 0.25:
        return "normal"
    if volatility < 0.45:
        return "elevated"
    return "stress"


def _backtest_mae(actual: pd.Series, fitted: pd.Series) -> Optional[float]:
    aligned = pd.concat([actual, fitted], axis=1).dropna()
    if aligned.empty:
        return None
    return float(np.mean(np.abs(aligned.iloc[:, 0] - aligned.iloc[:, 1])))


def arima_baseline_forecast(market_prices: pd.DataFrame, asset: str, horizon: int = 10) -> ForecastResult:
    """Forecast one market series with statsmodels ARIMA."""
    ARIMA, _ = _require_statsmodels()
    prices, warnings = _prepare_price_matrix(market_prices, [asset])
    horizon = max(int(horizon), 1)
    series = prices[asset].dropna()
    if len(series) < 12:
        raise ValueError("At least 12 observations are required for statsmodels ARIMA forecasting.")

    model = ARIMA(series.astype(float), order=(1, 1, 1), enforce_stationarity=False, enforce_invertibility=False)
    fitted = model.fit()
    forecast = fitted.get_forecast(steps=horizon)
    mean_forecast = forecast.predicted_mean.astype(float)
    conf = forecast.conf_int(alpha=0.05)
    returns = _log_returns(prices)[asset]
    vol = float(returns.tail(min(len(returns), 60)).std() * np.sqrt(252)) if not returns.empty else None
    fitted_values = fitted.fittedvalues.reindex(series.index)
    error = _backtest_mae(series, fitted_values)
    lower = float(conf.iloc[-1, 0])
    upper = float(conf.iloc[-1, 1])
    return ForecastResult(
        model_name="statsmodels ARIMA forecast",
        model_version=FORECAST_MODEL_VERSION,
        forecast_horizon=horizon,
        input_series=[asset],
        forecast_path={asset: [float(value) for value in mean_forecast.values]},
        forecast_value={asset: float(mean_forecast.iloc[-1])},
        confidence_interval={asset: {"lower": lower, "upper": upper}},
        forecast_error=error,
        backtest_error=error,
        forecast_volatility=vol,
        volatility_regime=_vol_regime(vol) if vol is not None else None,
        assumptions={
            "method": "statsmodels ARIMA(1,1,1) baseline on price level.",
            "forecast_not_certainty": True,
            "statsmodels_required": True,
        },
        warnings=warnings,
    )


def var_forecast(market_prices: pd.DataFrame, assets: list[str], horizon: int = 10) -> ForecastResult:
    """Forecast interacting market returns with statsmodels VAR."""
    _, VAR = _require_statsmodels()
    prices, warnings = _prepare_price_matrix(market_prices, assets)
    horizon = max(int(horizon), 1)
    returns = _log_returns(prices)
    if len(returns) < 12 or len(returns.columns) < 2:
        raise ValueError("At least 12 observations and two assets are required for statsmodels VAR forecasting.")

    model = VAR(returns.astype(float))
    fitted = model.fit(maxlags=1, ic=None)
    forecast_returns = fitted.forecast(returns.values[-fitted.k_ar :], steps=horizon)
    forecast_returns_df = pd.DataFrame(forecast_returns, columns=returns.columns)
    last_prices = prices.iloc[-1].astype(float)
    paths: dict[str, list[float]] = {asset: [] for asset in returns.columns}
    current = last_prices.copy()
    for _, row in forecast_returns_df.iterrows():
        current = current * np.exp(row)
        for asset in returns.columns:
            paths[asset].append(float(current[asset]))
    values = {asset: path[-1] for asset, path in paths.items()}
    fitted_returns = pd.DataFrame(fitted.fittedvalues, index=returns.index[-len(fitted.fittedvalues):], columns=returns.columns)
    error = float(np.mean(np.abs(returns.loc[fitted_returns.index].values - fitted_returns.values)))
    vols = returns.tail(min(len(returns), 60)).std() * np.sqrt(252)
    intervals = {}
    for asset in returns.columns:
        vol = float(vols[asset])
        band = 1.96 * (vol / np.sqrt(252)) * np.sqrt(horizon)
        intervals[asset] = {"lower": float(values[asset] * np.exp(-band)), "upper": float(values[asset] * np.exp(band))}
    avg_vol = float(vols.mean())
    return ForecastResult(
        model_name="statsmodels VAR forecast",
        model_version=FORECAST_MODEL_VERSION,
        forecast_horizon=horizon,
        input_series=list(returns.columns),
        forecast_path=paths,
        forecast_value=values,
        confidence_interval=intervals,
        forecast_error=error,
        backtest_error=error,
        forecast_volatility=avg_vol,
        volatility_regime=_vol_regime(avg_vol),
        assumptions={
            "method": "statsmodels VAR(1) over log returns.",
            "relationships": "Multi-factor interactions can capture oil, FX, volatility, equity, and freight pressure.",
            "statsmodels_required": True,
        },
        warnings=warnings,
    )


def garch_volatility_forecast(market_prices: pd.DataFrame, asset: str, horizon: int = 10) -> ForecastResult:
    """Forecast volatility with arch GARCH(1,1)."""
    arch_model = _require_arch_model()
    prices, warnings = _prepare_price_matrix(market_prices, [asset])
    horizon = max(int(horizon), 1)
    returns = _log_returns(prices)[asset].dropna() * 100.0
    if len(returns) < 30:
        raise ValueError("At least 30 returns are required for GARCH volatility forecasting.")

    model = arch_model(returns.astype(float), vol="Garch", p=1, q=1, mean="Constant", dist="normal", rescale=False)
    fitted = model.fit(disp="off")
    forecast = fitted.forecast(horizon=horizon, reindex=False)
    variance_path = forecast.variance.iloc[-1].astype(float).values
    daily_vol_decimal = float(np.sqrt(variance_path[-1]) / 100.0)
    annual_vol = float(daily_vol_decimal * np.sqrt(252))
    last_price = float(prices[asset].dropna().iloc[-1])
    band = 1.96 * daily_vol_decimal * np.sqrt(horizon)
    return ForecastResult(
        model_name="arch GARCH volatility forecast",
        model_version=FORECAST_MODEL_VERSION,
        forecast_horizon=horizon,
        input_series=[asset],
        forecast_path={asset: [last_price for _ in range(horizon)]},
        forecast_value={asset: last_price},
        confidence_interval={asset: {"lower": float(last_price * np.exp(-band)), "upper": float(last_price * np.exp(band))}},
        forecast_error=None,
        backtest_error=None,
        forecast_volatility=annual_vol,
        volatility_regime=_vol_regime(annual_vol),
        assumptions={
            "method": "arch GARCH(1,1) on percentage log returns.",
            "volatility_clustering": "High volatility tends to follow high volatility; low volatility tends to follow low volatility.",
            "arch_required": True,
        },
        warnings=warnings,
    )


def run_forecast(market_prices: pd.DataFrame, model_type: str, assets: list[str], horizon: int = 10) -> ForecastResult:
    normalized = model_type.lower().replace("-", "_")
    if normalized == "arima":
        return arima_baseline_forecast(market_prices, assets[0], horizon)
    if normalized == "var":
        return var_forecast(market_prices, assets, horizon)
    if normalized == "garch":
        return garch_volatility_forecast(market_prices, assets[0], horizon)
    raise ValueError("model_type must be one of: arima, var, garch")
