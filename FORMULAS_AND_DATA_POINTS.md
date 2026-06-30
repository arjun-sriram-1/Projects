# Formulas and Data Points Reference

This file lists the main formulas used in the project, the data points each formula uses, and a short explanation.

## 1. Current Ratio

```text
current_ratio = current_assets / current_liabilities
```

Data points used:

- `financial_metrics_extracted.current_assets`
- `financial_metrics_extracted.current_liabilities`

Explanation:

Measures short-term liquidity. A value above `1.0` means current assets are greater than current liabilities.

## 2. Quick Ratio

```text
quick_ratio = (cash_and_equivalents + accounts_receivable) / current_liabilities
```

Fallback:

```text
quick_assets = current_assets - inventory
quick_ratio = quick_assets / current_liabilities
```

Data points used:

- `cash_and_equivalents`
- `accounts_receivable`
- `current_assets`
- `inventory`
- `current_liabilities`

Explanation:

Measures liquidity using assets that are easier to convert into cash. Inventory is excluded because it may not be quickly liquidated.

## 3. Cash Ratio

```text
cash_ratio = cash_and_equivalents / current_liabilities
```

Data points used:

- `cash_and_equivalents`
- `current_liabilities`

Explanation:

Most conservative liquidity ratio. It checks whether cash alone can cover short-term obligations.

## 4. Working Capital

```text
working_capital = current_assets - current_liabilities
```

Data points used:

- `current_assets`
- `current_liabilities`

Explanation:

Shows surplus short-term resources available to run the business and repay near-term obligations.

## 5. Debt to Equity

```text
debt_to_equity = total_debt / shareholders_equity
```

Data points used:

- `total_debt`
- `shareholders_equity`

Explanation:

Measures leverage relative to shareholder capital. Higher values mean more debt-funded balance sheet risk.

## 6. Debt to EBITDA

```text
debt_to_ebitda = total_debt / ebitda
```

Data points used:

- `total_debt`
- `ebitda`

Explanation:

Shows how many years of EBITDA would be needed to repay debt, before interest, tax, capex, and working-capital effects.

## 7. Liabilities to Assets

```text
liabilities_to_assets = total_liabilities / total_assets
```

Data points used:

- `total_liabilities`
- `total_assets`

Explanation:

Measures solvency pressure. A value close to or above `1.0` means liabilities are very high relative to assets.

## 8. Interest Coverage

```text
interest_coverage = ebit / interest_expense
```

Data points used:

- `ebit`
- `interest_expense`

Explanation:

Measures ability to service debt interest from operating profit.

## 9. Operating Margin

```text
operating_margin = ebit / revenue
```

Data points used:

- `ebit`
- `revenue`

Explanation:

Measures operating profitability before interest and tax.

## 10. Net Margin

```text
net_margin = net_income / revenue
```

Data points used:

- `net_income`
- `revenue`

Explanation:

Measures final profitability after all expenses.

## 11. Return on Assets

```text
return_on_assets = net_income / total_assets
```

Data points used:

- `net_income`
- `total_assets`

Explanation:

Shows how efficiently assets generate profit.

## 12. Return on Equity

```text
return_on_equity = net_income / shareholders_equity
```

Data points used:

- `net_income`
- `shareholders_equity`

Explanation:

Shows profitability relative to shareholder capital.

## 13. Market Log Return

```text
log_return = log(price_t / price_t-1)
```

Data points used:

- `market_prices.price`
- `market_prices.date`
- `market_prices.asset`

Explanation:

Measures daily market movement for assets such as Brent, jet fuel proxy, DXY, S&P 500, VIX, gold, and freight proxies.

## 14. Rolling Volatility

```text
rolling_volatility = rolling_standard_deviation(log_return, window)
```

Data points used:

- Market returns from `market_prices`
- Usually a rolling window such as `20` observations

Explanation:

Measures how unstable an asset has been recently. Higher volatility contributes to market stress.

## 15. Market Stress Component Z-Score

```text
z_score = (component_value - component_mean) / component_standard_deviation
```

Data points used:

- Market return or change components
- Historical component mean
- Historical component standard deviation

Explanation:

Standardizes different market variables onto the same scale so oil, FX, equity, rates, and freight can be combined.

## 16. Stress Index PCA Score

```text
pc1_score = w1*z1 + w2*z2 + ... + wn*zn
```

Data points used:

- Z-scored stress components such as:
  - `oil_volatility_zscore`
  - `brent_return_zscore`
  - `heating_oil_return_zscore`
  - `jet_fuel_return_zscore`
  - `vix_zscore`
  - `sp500_loss_zscore`
  - `dxy_return_zscore`
  - `yield_10y_change_zscore`
  - `yield_curve_stress_zscore`
  - `inflation_zscore`
  - `freight_loss_zscore`
- PCA loadings

Explanation:

PCA compresses many market stress drivers into one common stress factor. The first principal component becomes the raw stress score.

## 17. Stress Index Scaling

```text
stress_index = ((pc1_score - p1) / (p99 - p1)) * 100
```

Then:

```text
stress_index = clipped between 0 and 100
```

Data points used:

- Current `pc1_score`
- Historical 1st percentile of PC1
- Historical 99th percentile of PC1

Explanation:

Converts the PCA score into a readable `0-100` stress index.

## 18. Market Regime Clustering

```text
scaled_features = StandardScaler(stress_component_matrix)
regime_id = KMeans/GMM/HMM_cluster(scaled_features)
```

Data points used:

- Stress component matrix
- `stress_index_history.stress_index`
- Market component z-scores

Explanation:

Groups market days into regimes such as Stable Market, Commodity Stress, USD Stress, Risk-Off, or Crisis.

## 19. Commodity Sensitivity Score

For airlines:

```text
commodity_sensitivity = 0.65 + 0.25 * oil_component
```

Data points used:

- `counterparties_master.counterparty_type`
- `oil_volatility_zscore`
- `fuel_return_zscore`

Explanation:

Measures how exposed the counterparty is to fuel and commodity moves. Airlines receive higher baseline sensitivity.

## 20. FX Sensitivity Score

For airlines:

```text
fx_sensitivity = 0.45 + 0.25 * fx_component
```

Data points used:

- `counterparty_type`
- `dxy_return_zscore` or other FX z-score

Explanation:

Measures sensitivity to USD/FX pressure.

## 21. Macro Sensitivity Score

For airlines:

```text
macro_sensitivity = 0.40 + 0.35 * stress_component
```

Where:

```text
stress_component = market_stress_index / 100
```

Data points used:

- `stress_index_history.stress_index`
- `counterparty_type`

Explanation:

Measures broad sensitivity to macro and risk-off conditions.

## 22. Asset Value Proxy

```text
asset_value_proxy = total_assets
```

Fallback:

```text
asset_value_proxy = 1.5 * revenue
```

Data points used:

- `total_assets`
- `revenue`

Explanation:

Used as the asset value input for the Merton-style structural PD model.

## 23. Debt Threshold

```text
debt_threshold = total_debt
```

Fallbacks:

```text
debt_threshold = short_term_debt + current_portion_long_term_debt + long_term_debt
debt_threshold = 0.60 * total_liabilities
```

Data points used:

- `total_debt`
- `short_term_debt`
- `current_portion_long_term_debt`
- `long_term_debt`
- `total_liabilities`

Explanation:

Represents the liability level where default risk becomes meaningful in the structural model.

## 24. Asset Volatility Proxy

```text
asset_volatility =
    0.18
  + 0.08 * min(debt_to_equity, 5)
  + 0.12 * stress
  + 0.10 * average_vulnerability
  + 0.05 * max(0, 1 - min(current_ratio, 2) / 2)
```

Data points used:

- `debt_to_equity`
- `current_ratio`
- `stress_index`
- `commodity_sensitivity_score`
- `fx_sensitivity_score`
- `macro_sensitivity_score`

Explanation:

Estimates asset volatility from leverage, liquidity, market stress, and business vulnerability.

## 25. Merton Distance to Default

```text
DD =
  [ln(asset_value_proxy / debt_threshold)
   + (risk_free_rate - 0.5 * asset_volatility^2) * time_horizon_years]
  / [asset_volatility * sqrt(time_horizon_years)]
```

Data points used:

- `asset_value_proxy`
- `debt_threshold`
- `asset_volatility`
- `risk_free_rate`
- `time_horizon_years`

Explanation:

Measures how many volatility units the company is away from the default threshold.

## 26. Structural PD

```text
structural_pd = NormalCDF(-distance_to_default)
```

Data points used:

- `distance_to_default`

Explanation:

Converts distance-to-default into probability of default.

## 27. Logistic / ML Proxy PD

```text
ml_pd = 1 / (1 + exp(-logit))
```

Where:

```text
logit =
  intercept
  + 0.20 * min(debt_to_ebitda, 10)
  + 0.15 * min(debt_to_equity, 8)
  + 0.70 * max(0, 1.20 - current_ratio)
  + 0.35 * max(0, 0.50 - cash_ratio)
  + 0.25 * max(0, 3.0 - interest_coverage)
  + 2.00 * max(0, -net_margin)
  + 1.25 * stress
  + 0.55 * commodity_sensitivity_score
  + 0.35 * fx_sensitivity_score
  + 0.45 * macro_sensitivity_score
```

Data points used:

- `debt_to_ebitda`
- `debt_to_equity`
- `current_ratio`
- `cash_ratio`
- `interest_coverage`
- `net_margin`
- `stress_index`
- `commodity_sensitivity_score`
- `fx_sensitivity_score`
- `macro_sensitivity_score`

Explanation:

Provides an interpretable ML-style PD cross-check using financial weakness and market vulnerability.

## 28. Final PD

```text
final_pd = 0.65 * structural_pd + 0.35 * ml_pd
```

Data points used:

- `structural_pd`
- `ml_pd`

Explanation:

Blends the structural model and ML/proxy model. The structural model is the anchor, while ML is the cross-check.

## 29. PD Distress Floors

```text
if shareholders_equity <= 0:
    final_pd >= 0.16

if liabilities_to_assets >= 1.0:
    final_pd >= 0.18

if liabilities_to_assets >= 0.90:
    final_pd >= 0.08
```

Data points used:

- `shareholders_equity`
- `liabilities_to_assets`
- `total_assets`
- `total_liabilities`

Explanation:

Prevents the model from assigning unrealistically low PD to companies with clear balance-sheet distress.

## 30. PD Grade Mapping

```text
PD < 1%      -> A
1% to 3%    -> BBB
3% to 7%    -> BB
7% to 15%   -> B
>= 15%      -> CCC
```

Data points used:

- `final_pd`

Explanation:

Maps PD into an internal risk grade. These are internal proxy grades, not agency ratings.

## 31. Collateral Strength

```text
letter_of_credit = 0.90
cash_deposit = 0.80
guarantee = 0.65
secured_collateral = 0.55
unsecured = 0.05
```

Data points used:

- `collateral_type`
- `letter_of_credit_flag`
- `guarantee_flag`
- `deposit_percentage`

Explanation:

Converts collateral/security into a normalized recovery protection score.

## 32. LGD

```text
lgd =
    0.62
  - 0.42 * collateral_strength
  - 0.08 * liquidity_score
  + 0.035 * max(country_risk_score - 2, 0)
  - 0.025 * max(seniority_score - 2, 0)
  + 0.06 * max(payment_tenor_days - 30, 0) / 90
```

Then:

```text
lgd = clipped between 0.01 and 0.99
```

Data points used:

- `collateral_strength`
- `liquidity_score`
- `country_risk_score`
- `seniority_score`
- `payment_tenor_days`

Explanation:

Estimates loss severity if default occurs. Strong collateral lowers LGD; long tenor and country risk increase LGD.

## 33. Invoice Exposure

```text
invoice_exposure = invoice_amount
```

Fallback:

```text
invoice_exposure = fuel_volume * fuel_price
```

Data points used:

- `invoice_amount`
- `fuel_volume`
- `fuel_price`

Explanation:

Measures the invoice value at risk from the trade.

## 34. Expected Drawdown

```text
expected_drawdown = invoice_exposure * utilization_rate * max(1, payment_tenor_days / 30)
```

Data points used:

- `invoice_exposure`
- `utilization_rate`
- `payment_tenor_days`

Explanation:

Estimates how much additional exposure may build up before payment is received.

## 35. EAD

```text
uncapped_ead = outstanding_receivables + expected_drawdown
ead = min(approved_credit_limit_or_requested_limit, uncapped_ead)
```

Data points used:

- `outstanding_receivables`
- `expected_drawdown`
- `approved_credit_limit`
- `requested_credit_limit`

Explanation:

Exposure at default estimates how much money is at risk if the counterparty defaults.

## 36. Expected Loss

```text
expected_loss = probability_of_default * loss_given_default * exposure_at_default
```

Data points used:

- `final_pd`
- `predicted_lgd`
- `exposure_at_default`

Explanation:

Core credit risk formula. It combines likelihood of default, severity of loss, and exposure size.

## 37. Scenario Market Shocks

```text
scenario_shock = historical_quantile(driver_changes)
```

Examples:

```text
base_case = 50th percentile
normal_volatility = 75th percentile
adverse = 90th percentile
severe_downside = 95th percentile
tail = 99th percentile
```

Data points used:

- Historical `market_prices`
- Historical `stress_index_history`
- Optional `market_regime_history`

Explanation:

Builds data-driven market scenarios from historical quantiles instead of hardcoded shocks.

## 38. Scenario Driver Z-Score

```text
driver_zscore = (scenario_shock - historical_mean) / historical_standard_deviation
```

Data points used:

- Scenario shock
- Historical driver mean
- Historical driver standard deviation

Explanation:

Converts scenario shocks into standardized stress units used by the Monte Carlo model.

## 39. Scenario Combined Pressure

```text
combined_pressure_z =
    (commodity_sensitivity * commodity_pressure_z
   + fx_sensitivity * fx_pressure_z
   + macro_sensitivity * macro_pressure_z) / 3
```

Data points used:

- `commodity_sensitivity_score`
- `fx_sensitivity_score`
- `macro_sensitivity_score`
- Scenario driver z-scores

Explanation:

Combines scenario shocks with counterparty-specific vulnerabilities.

## 40. Scenario-Adjusted PD

```text
adjusted_pd = base_pd * exp(0.18 * max(combined_pressure_z, -2))
```

Data points used:

- `base_pd`
- `combined_pressure_z`

Explanation:

Raises or lowers PD under a scenario depending on stress pressure.

## 41. Scenario-Adjusted LGD

```text
lgd_add_on = 0.035 * max(combined_pressure_z, 0) * (1 - collateral_strength)
adjusted_lgd = base_lgd + lgd_add_on
```

Data points used:

- `base_lgd`
- `combined_pressure_z`
- `collateral_strength`

Explanation:

Stress increases LGD, but strong collateral reduces the increase.

## 42. Scenario-Adjusted EAD

```text
ead_multiplier = 1 + min(0.035 * max(commodity_pressure_z, 0), 0.30)
adjusted_ead = base_ead * ead_multiplier
```

Data points used:

- `base_ead`
- `commodity_pressure_z`

Explanation:

Fuel price stress can increase invoice value and working-capital exposure.

## 43. Scenario Expected Loss

```text
scenario_expected_loss = adjusted_pd * adjusted_lgd * adjusted_ead
```

Data points used:

- `adjusted_pd`
- `adjusted_lgd`
- `adjusted_ead`

Explanation:

Expected loss after applying scenario stress.

## 44. Default Correlation

```text
default_correlation =
    0.06
  + 0.18 * average_market_stress / 100
  + 0.025 * min(stress_level_z + vix_level_z, 6)
```

Then:

```text
default_correlation = clipped between 0.03 and 0.55
```

Data points used:

- `market_stress_index`
- Scenario stress z-score
- Scenario VIX z-score

Explanation:

Estimates how much defaults move together under market stress.

## 45. Gaussian Copula Default Score

```text
latent_score =
    sqrt(default_correlation) * systematic_factor
  + sqrt(1 - default_correlation) * idiosyncratic_factor
```

Data points used:

- `default_correlation`
- Random systematic factor
- Random idiosyncratic factor

Explanation:

Simulates correlated default behavior across counterparties.

## 46. Default Threshold

```text
threshold = NormalInverseCDF(adjusted_pd)
default_event = latent_score < threshold
```

Data points used:

- `adjusted_pd`
- Simulated `latent_score`

Explanation:

Converts PD into a simulation default event.

## 47. Simulated Loss

```text
loss = default_event * lgd_draw * ead_draw
```

Data points used:

- Simulated default event
- Simulated LGD draw
- Simulated EAD draw

Explanation:

Calculates simulated credit loss for one counterparty in one Monte Carlo trial.

## 48. Portfolio Loss

```text
portfolio_loss = sum(counterparty_losses)
```

Data points used:

- All simulated counterparty losses

Explanation:

Aggregates individual losses into total portfolio loss.

## 49. Credit VaR

```text
var_95 = 95th percentile(portfolio_losses)
var_99 = 99th percentile(portfolio_losses)
```

Data points used:

- Monte Carlo portfolio loss distribution

Explanation:

Measures tail loss at a selected confidence level.

## 50. Expected Shortfall

```text
expected_shortfall_95 = mean(portfolio_losses >= var_95)
expected_shortfall_99 = mean(portfolio_losses >= var_99)
```

Data points used:

- Monte Carlo portfolio loss distribution
- `var_95`
- `var_99`

Explanation:

Measures average loss beyond the VaR threshold.

## 51. Unexpected Loss

```text
unexpected_loss = standard_deviation(portfolio_losses)
```

Data points used:

- Monte Carlo portfolio loss distribution

Explanation:

Measures volatility of simulated portfolio losses.

## 52. Scenario Loss Ratio

```text
scenario_loss_ratio = tail_loss / exposure_at_default
```

Where:

```text
tail_loss = expected_shortfall_95, else var_95, else scenario_expected_loss
```

Data points used:

- `expected_shortfall_95`
- `var_95`
- `scenario_expected_loss`
- `exposure_at_default`

Explanation:

Measures how large scenario/tail losses are relative to exposure.

## 53. Policy Haircut

```text
limit_haircut = sum(policy_haircut_additions) - collateral_benefits
```

Then:

```text
limit_haircut = clipped between 0 and 0.90
```

Data points used:

- `probability_of_default`
- `predicted_lgd`
- `market_stress_index`
- `current_ratio`
- `debt_to_ebitda`
- `interest_coverage`
- `payment_tenor_days`
- `scenario_loss_ratio`
- `model_disagreement`
- `collateral_strength`

Explanation:

Converts risk signals into a percentage reduction of the requested or approved credit limit.

## 54. Recommended Credit Limit

```text
recommended_credit_limit = base_limit * (1 - limit_haircut)
```

Where:

```text
base_limit = requested_credit_limit, else approved_credit_limit, else exposure_at_default
```

Data points used:

- `requested_credit_limit`
- `approved_credit_limit`
- `exposure_at_default`
- `limit_haircut`

Explanation:

Proposes the credit limit after risk-based reduction.

## 55. Recommended Tenor

```text
if grade = A and score <= 1.0: tenor <= 90
if grade = BBB and score <= 2.5: tenor <= 60
if grade = BB or score <= 4.0: tenor <= 45
if grade = B or score <= 6.0: tenor <= 30
else: tenor = 0
```

Data points used:

- `risk_grade`
- `policy_score`
- Requested `payment_tenor_days`

Explanation:

Shortens payment terms as risk increases.

## 56. Recommended Security

```text
CCC or score > 6 -> Prepayment or Confirmed LC
B or PD >= 7% -> Standby LC or Bank Guarantee
LGD >= 60% and weak collateral -> Bank Guarantee or Partial Cash Deposit
BB -> Corporate Guarantee or Partial Deposit
strong existing collateral -> Existing collateral acceptable
otherwise -> Open Credit with monitoring covenants
```

Data points used:

- `risk_grade`
- `policy_score`
- `probability_of_default`
- `predicted_lgd`
- `collateral_strength`

Explanation:

Recommends security requirements based on default risk and loss severity.

## 57. Approval Status

```text
if recommended_limit <= 0 or grade = CCC or score > 6.5:
    REJECT / PREPAYMENT ONLY
elif score > 4.0 or grade = B:
    CONDITIONAL APPROVAL - SECURED
elif score > 2.0 or grade = BB:
    CONDITIONAL APPROVAL
else:
    APPROVED
```

Data points used:

- `recommended_credit_limit`
- `risk_grade`
- `policy_score`

Explanation:

Converts model output into a practical credit decision status.

