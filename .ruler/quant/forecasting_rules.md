# Commodity Forecasting Rules

Use these rules only for commodity, FX, volatility, and multi-factor market forecast work.

Purpose:

- Forecasts support credit risk decisions; they do not replace stored PD, LGD, EAD, or policy review.
- Forecasts must be probabilistic and must never be presented as guaranteed predictions.

Allowed model roles:

- ARIMA: single-variable baseline price or return forecast.
- VAR: multi-factor relationships across oil, FX, volatility, rates, spreads, and macro variables.
- GARCH: volatility forecast for market risk and scenario widening.

Required outputs:

- model_name
- model_version
- forecast_horizon
- input_series
- forecast_path or forecast_value
- confidence_interval when available
- forecast_error or backtest_error when available
- forecast_volatility for volatility models
- assumptions
- warnings

Credit risk usage:

- Higher forecast volatility should widen adverse scenarios.
- Higher forecast volatility should not reduce PD or portfolio risk without a documented hedge or offset.
- Forecast outputs may feed scenarios, stress tests, and credit decision explanations.
- Forecasts must remain traceable to market data, not hardcoded shocks.

Validation:

- Include rolling train/test or backtest checks when practical.
- Compare ARIMA/VAR/GARCH outputs against simple historical baselines.
- Document insufficient data, convergence failures, and unstable model fits.
