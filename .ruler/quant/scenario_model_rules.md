# Scenario And Market Model Rules

Scenarios must be data-driven.

Allowed sources:

- historical quantiles
- market regimes
- rolling volatility
- bootstrapping
- Monte Carlo sampling
- GARCH/VAR/ARIMA forecasts when implemented
- PCA/GMM/HMM regime outputs

Do not hardcode business shocks such as:

- oil_shock = 0.20
- fx_shock = 0.10
- revenue_drop = 0.15

Required scenario types:

- base case
- normal volatility case
- adverse case
- severe downside case
- tail case

Scenario outputs should show impact on PD, LGD, EAD, Expected Loss, credit limit, tenor, and security.

