# Mathematical Formulas and Model Pipeline Guide

This guide explains the main formulas, machine-learning models, and end-to-end workflow used in this credit risk project. It is written as a study/interview reference: what each formula means, why it is used here, how it is used elsewhere in finance, and how the pieces connect.

## 1. Big Picture

The project converts financial statement data, market data, trade exposure terms, and collateral information into a final credit recommendation.

Simple flow:

```text
Financial inputs + Market inputs + Credit terms
        -> Financial ratios
        -> Market stress index
        -> PD model
        -> LGD and EAD model
        -> Expected loss
        -> Scenario and Monte Carlo risk
        -> Credit policy decision
        -> Recommended limit, tenor, security, and approval status
```

In interview language:

> The project is an end-to-end trade credit risk engine. It starts with company financials and market conditions, calculates liquidity, leverage, profitability, and market stress, then estimates default probability, loss severity, exposure at default, expected loss, and downside tail risk. Finally, a policy engine converts those model outputs into credit terms.

## 2. Financial Statement Formulas

These formulas are calculated from uploaded or manually entered financial statement data. They are the foundation for PD, LGD, policy rules, and the AI copilot explanations.

### 2.1 Current Ratio

```text
current_ratio = current_assets / current_liabilities
```

Used data:

- `current_assets`
- `current_liabilities`

Why it is used:

Current ratio measures short-term liquidity. In this project, weak liquidity can increase PD pressure and can trigger tighter credit terms.

Used elsewhere:

Banks, lenders, and credit analysts use current ratio to judge whether a company has enough short-term assets to meet short-term obligations.

Connection:

```text
current_ratio -> liquidity assessment -> PD model + policy haircut
```

### 2.2 Quick Ratio

Primary formula:

```text
quick_ratio = (cash_and_equivalents + accounts_receivable) / current_liabilities
```

Fallback formula:

```text
quick_ratio = (current_assets - inventory) / current_liabilities
```

Used data:

- `cash_and_equivalents`
- `accounts_receivable`
- `current_assets`
- `inventory`
- `current_liabilities`

Why it is used:

Quick ratio is stricter than current ratio because it excludes inventory or focuses on cash plus receivables. In this project, it helps prevent a company from looking liquid just because it has inventory that may not be quickly converted to cash.

Used elsewhere:

Credit analysts use quick ratio for working-capital quality, especially when inventories are large or slow-moving.

Connection:

```text
cash + receivables + inventory -> quick_ratio -> liquidity quality -> model confidence and credit terms
```

### 2.3 Cash Ratio

```text
cash_ratio = cash_and_equivalents / current_liabilities
```

Used data:

- `cash_and_equivalents`
- `current_liabilities`

Why it is used:

Cash ratio is the most conservative liquidity measure. It checks immediate cash coverage.

Used elsewhere:

Used in credit analysis when analysts want to understand how much debt or short-term liability can be covered without selling assets or collecting receivables.

Connection:

```text
cash_ratio -> ML PD proxy -> liquidity score -> LGD and policy explanation
```

### 2.4 Working Capital

```text
working_capital = current_assets - current_liabilities
```

Used data:

- `current_assets`
- `current_liabilities`

Why it is used:

Working capital shows the absolute short-term cushion. Positive working capital suggests more room to absorb trade credit obligations.

Used elsewhere:

Used in corporate finance and lending to assess daily operating liquidity.

Connection:

```text
working_capital -> historical ML PD artifact + financial health display
```

### 2.5 Debt to Equity

```text
debt_to_equity = total_debt / shareholders_equity
```

Used data:

- `total_debt`
- `shareholders_equity`

Why it is used:

Debt/equity measures leverage relative to book capital. High leverage increases default risk.

Used elsewhere:

Common in lending, equity analysis, and covenant monitoring.

Connection:

```text
debt_to_equity -> ML PD proxy -> leverage signal -> policy risk drivers
```

### 2.6 Debt to EBITDA

```text
debt_to_ebitda = total_debt / ebitda
```

Used data:

- `total_debt`
- `ebitda`

Why it is used:

Debt/EBITDA estimates how many years of EBITDA would be needed to cover debt, ignoring capex, taxes, and working-capital leakage. In this project, high Debt/EBITDA increases PD pressure and can add a policy haircut.

Used elsewhere:

This is one of the most common credit ratios in banking, leveraged finance, corporate credit, and rating analysis.

Connection:

```text
debt_to_ebitda -> ML PD proxy + policy haircut + financial trend overlay
```

### 2.7 Liabilities to Assets

```text
liabilities_to_assets = total_liabilities / total_assets
```

Used data:

- `total_liabilities`
- `total_assets`

Why it is used:

This measures balance-sheet solvency. A very high value means the company has limited asset cushion.

Used elsewhere:

Used in solvency analysis and distress screening.

Connection:

```text
liabilities_to_assets -> distress floor checks -> final PD
```

### 2.8 Interest Coverage

```text
interest_coverage = ebit / interest_expense
```

Used data:

- `ebit`
- `interest_expense`

Why it is used:

Interest coverage measures whether operating profit can cover interest expense. If coverage is weak, debt service is already pressuring the company.

Used elsewhere:

Used in credit underwriting, debt covenants, rating agency analysis, and bond analysis.

Connection:

```text
ebit -> interest_coverage -> debt service assessment -> PD + policy haircut
```

### 2.9 Operating Margin

```text
operating_margin = ebit / revenue
```

Used data:

- `ebit`
- `revenue`

Why it is used:

Operating margin measures core profitability before interest and tax. In this project, low or negative margin can increase PD risk.

Used elsewhere:

Used in equity research, credit analysis, industry benchmarking, and company performance analysis.

Connection:

```text
operating_margin -> ML PD proxy + financial health score + trend overlay
```

### 2.10 Net Margin

```text
net_margin = net_income / revenue
```

Used data:

- `net_income`
- `revenue`

Why it is used:

Net margin measures final profitability after all expenses. Negative margins are a credit warning.

Used elsewhere:

Used in profitability analysis, peer comparison, and distress screening.

Connection:

```text
net_margin -> ML PD proxy + trend overlay
```

### 2.11 Return on Assets

```text
return_on_assets = net_income / total_assets
```

Used data:

- `net_income`
- `total_assets`

Why it is used:

ROA measures how efficiently assets generate profit.

Used elsewhere:

Used in credit and equity analysis to compare profitability across asset-heavy companies.

Connection:

```text
return_on_assets -> historical ML PD artifact
```

### 2.12 Return on Equity

```text
return_on_equity = net_income / shareholders_equity
```

Used data:

- `net_income`
- `shareholders_equity`

Why it is used:

ROE measures profitability relative to shareholder capital.

Used elsewhere:

Used in corporate finance, equity analysis, and profitability screening.

Connection:

```text
return_on_equity -> historical ML PD artifact
```

## 3. Market and Stress Formulas

Market data is used to understand external pressure on airlines and fuel buyers. The project uses free/live or latest-available market indicators such as crude oil, jet fuel proxy, USD/INR, DXY, VIX, S&P 500, US yields, freight/trade indicators, PMI, and IATA traffic.

### 3.1 Log Return

```text
log_return = ln(price_t / price_t-1)
```

Used data:

- Market price today
- Market price previous day

Why it is used:

Log returns measure percentage-like market movement in a mathematically stable way.

Used elsewhere:

Used in trading, risk management, volatility models, VaR, and time-series finance.

Connection:

```text
market prices -> log returns -> z-scores -> PCA stress index
```

### 3.2 Rolling Volatility

```text
rolling_volatility = rolling_standard_deviation(log_returns, window)
```

Why it is used:

Volatility measures how unstable market prices are. Higher volatility means more uncertainty for fuel cost and credit risk.

Used elsewhere:

Used in market risk, option pricing, VaR, and stress testing.

Connection:

```text
oil returns -> oil volatility z-score -> stress index -> PD/scenario pressure
```

### 3.3 Z-Score Standardization

```text
z_score = (value - historical_mean) / historical_standard_deviation
```

Why it is used:

Different indicators have different units. Brent is in dollars per barrel, VIX is an index, yields are percentages, PMI is a survey value. Z-scores put them on one comparable scale.

Used elsewhere:

Used in statistics, anomaly detection, factor models, and PCA.

Connection:

```text
raw market factors -> z-scores -> PCA component matrix
```

### 3.4 PCA First Principal Component

```text
Z = standardized market component matrix
pc1_score = PCA(n_components=1).fit_transform(Z)
```

Conceptually:

```text
pc1_score = w1*z1 + w2*z2 + ... + wn*zn
```

Used data:

- Commodity pressure
- Jet crack spread pressure
- VIX/volatility pressure
- Equity pressure
- FX pressure
- Rates pressure
- PMI weakness
- IATA passenger traffic loss
- Freight/trade pressure

Why it is used:

PCA compresses many market signals into one combined market stress factor. Instead of manually weighting every indicator, PCA finds the strongest common movement across the indicators.

Used elsewhere:

PCA is common in risk factor modeling, portfolio analytics, yield curve modeling, macro factor models, and dimensionality reduction.

Connection:

```text
market z-scores -> PCA PC1 -> stress index -> PD model + scenario model
```

### 3.5 Market Stress Index

```text
stress_index = percentile_scale(pc1_score)
```

The project converts PC1 into a `0-100` score.

Why it is used:

The stress index makes market stress readable for both the dashboard and models.

Interpretation:

```text
0-40   = low/calm stress
40-65  = moderate stress
65-80  = elevated stress
80-100 = crisis stress
```

Used elsewhere:

Many institutions build internal market stress indexes from market factors.

Connection:

```text
stress_index -> market context -> ML PD + scenario multipliers + policy haircut
```

### 3.6 Jet Crack Spread

```text
jet_crack_spread = jet_fuel_proxy * 42 - brent_oil
```

Why multiply by `42`:

Jet fuel proxy is often quoted per gallon. Crude is per barrel. One barrel has 42 gallons, so the project converts jet fuel to a per-barrel equivalent.

Why it is used:

The spread shows whether jet fuel is expensive relative to crude. For airlines, wider spreads can pressure margins and working capital.

Used elsewhere:

Crack spreads are used in energy trading and airline fuel cost analysis.

Connection:

```text
jet fuel + brent -> crack spread -> market stress + ML PD feature
```

## 4. Structural Credit Formulas

The project uses a Merton-style structural model as one PD anchor.

### 4.1 Asset Value Proxy

The project estimates an asset value proxy from stored financial data, usually using total assets when available.

```text
asset_value_proxy = total_assets
```

Fallbacks may use revenue-based approximations when assets are missing.

Why it is used:

The Merton model needs an asset value to compare against debt.

Used elsewhere:

Structural credit models treat equity/debt as claims on firm assets.

Connection:

```text
financial statement -> asset value proxy -> distance to default
```

### 4.2 Debt Barrier

```text
debt_barrier = total_debt
```

Fallbacks may use debt components or liabilities when total debt is missing.

Why it is used:

The debt barrier is the level assets must stay above to avoid default pressure.

Connection:

```text
total_debt -> debt barrier -> distance to default
```

### 4.3 Asset Volatility

Project-style formula:

```text
asset_volatility =
  0.18
  + 0.08 * min(leverage, 5)
  + 0.12 * market_stress
  + 0.10 * average_vulnerability
  + 0.05 * liquidity_weakness
```

Then clipped to:

```text
0.08 <= asset_volatility <= 0.95
```

Why it is used:

Higher volatility means firm asset value is more uncertain, increasing default risk.

Used elsewhere:

Asset volatility is central to structural credit models, option pricing, and default-risk modeling.

Connection:

```text
leverage + stress + liquidity + vulnerability -> asset volatility -> structural PD
```

### 4.4 Distance to Default

```text
DD =
(
  ln(asset_value / debt_barrier)
  + (risk_free_rate - 0.5 * asset_volatility^2) * time_horizon
)
/
(
  asset_volatility * sqrt(time_horizon)
)
```

Why it is used:

Distance to default measures how many volatility-adjusted steps the company is away from the debt barrier.

Interpretation:

- Higher DD = safer company
- Lower DD = closer to default

Used elsewhere:

Distance to default is used in Merton/KMV-style structural credit models.

Connection:

```text
asset value + debt + volatility + risk-free rate -> DD -> structural PD
```

### 4.5 Merton Structural PD

```text
structural_pd = N(-DD)
```

`N()` is the standard normal cumulative distribution function.

Why it is used:

If the firm is far from default, `N(-DD)` is small. If the firm is close to default, `N(-DD)` rises.

Used elsewhere:

Used in structural default models and credit risk analytics.

Connection:

```text
structural_pd -> final PD blend
```

## 5. ML / Proxy PD Formulas

The project has an ML-style PD side that acts as a cross-check against the Merton structural PD.

### 5.1 Logistic PD Score

The project calculates a logit score from financial and market contributions:

```text
logit =
  intercept
  + leverage contributions
  + liquidity weakness
  + weak interest coverage
  + negative margin pressure
  + market stress
  + commodity vulnerability
  + FX vulnerability
  + macro vulnerability
  + market feature pressures
```

Then:

```text
rule_based_ml_pd = 1 / (1 + exp(-logit))
```

Key contribution examples:

```text
intercept = -3.40
debt_to_ebitda contribution = 0.20 * min(debt_to_ebitda, 10)
debt_to_equity contribution = 0.15 * min(debt_to_equity, 8)
weak_liquidity contribution = 0.70 * max(0, 1.20 - current_ratio)
low_cash contribution = 0.35 * max(0, 0.50 - cash_ratio)
weak_interest_coverage contribution = 0.25 * max(0, 3.0 - interest_coverage)
negative_margin contribution = 2.00 * max(0, -net_margin)
market_stress contribution = 1.25 * stress_index / 100
```

Why it is used:

The Merton model can be too low for asset-rich companies. The logistic proxy catches accounting and market weakness that the structural model may understate.

Used elsewhere:

Logistic regression is widely used in credit scoring and default classification.

Connection:

```text
financial ratios + market stress -> ML PD -> final PD blend
```

### 5.2 Historical Trained PD Artifact

```text
trained_pd = historical_pd_model.predict_proba(features)
```

Then quality-weighted blending:

```text
artifact_weight = clip((AUC - 0.50) * 2.0, 0.0, 0.25)
ml_pd = (1 - artifact_weight) * rule_based_ml_pd + artifact_weight * trained_pd
```

Why it is used:

It lets the model use a trained artifact when available, while not letting a weak artifact dominate the result.

Used elsewhere:

Production credit models often blend expert rules, statistical models, and calibrated model artifacts.

Connection:

```text
rule ML PD + trained PD artifact -> blended ML PD
```

### 5.3 Final PD Blend

```text
final_pd = structural_weight * structural_pd + ml_weight * ml_pd
```

If financial history exists and has a trend multiplier:

```text
final_pd = final_pd * sqrt(financial_trend_pd_multiplier)
```

Then clipped to a valid probability range.

Why it is used:

The final PD combines two views:

- Structural PD: asset/debt default distance
- ML PD: financial ratio and market stress cross-check

Used elsewhere:

Blended models are common in risk systems because no single model captures all risk dimensions.

Connection:

```text
structural PD + ML PD + financial trend overlay -> final PD
```

### 5.4 PD Distress Floors

Concept:

```text
if negative equity or liabilities exceed assets:
    final_pd cannot fall below a distress floor
```

Why it is used:

It prevents the model from producing unrealistically low PD for distressed balance sheets.

Used elsewhere:

Credit systems commonly use floors, overrides, and policy constraints to prevent model blind spots.

Connection:

```text
balance sheet distress -> minimum PD -> final PD
```

## 6. Financial History Trend Overlay

The user can enter one or many years/quarters. The model works with one period, but trends become active only with enough history.

### 6.1 Revenue CAGR

```text
revenue_cagr = (latest_revenue / oldest_revenue)^(1 / years) - 1
```

Why it is used:

Revenue decline can signal weaker demand or business deterioration.

Connection:

```text
revenue history -> trend risk score -> PD multiplier
```

### 6.2 Latest Revenue Growth

```text
latest_revenue_growth = (latest_revenue - previous_revenue) / previous_revenue
```

Why it is used:

Captures most recent momentum.

### 6.3 Margin Trend

```text
ebitda_margin = ebitda / revenue
ebitda_margin_trend = slope_or_change(ebitda_margin over time)
```

Why it is used:

Falling margins mean weaker earnings quality.

### 6.4 Leverage Trend

```text
leverage_trend = change in debt_to_ebitda over time
```

Why it is used:

Rising leverage increases credit risk.

### 6.5 Interest Coverage Trend

```text
interest_coverage_trend = change in interest_coverage over time
```

Why it is used:

Falling coverage shows worsening ability to service debt.

### 6.6 Trend Overlay Output

Conceptual formula:

```text
trend_risk_score =
  deterioration pressures
  - improvement offsets
```

Outputs:

```text
pd_multiplier
asset_volatility_addon
lgd_addon
liquidity_score
```

Why it is used:

It improves precision when the user provides multiple periods, but it does not break the single-year pipeline.

Connection:

```text
historical financials -> trend overlay -> PD, asset volatility, LGD, liquidity score
```

## 7. LGD, EAD, and Expected Loss Formulas

### 7.1 Collateral Strength

Project logic:

```text
letter_of_credit -> collateral_strength at least 0.90
guarantee -> collateral_strength at least 0.65
cash_deposit -> collateral_strength based on deposit percentage
```

Why it is used:

Stronger collateral reduces loss severity if default happens.

Used elsewhere:

Recovery and collateral analysis is core to credit risk and loan pricing.

Connection:

```text
security type -> collateral strength -> LGD reduction
```

### 7.2 Business Rule LGD

```text
business_lgd =
  0.62
  - 0.42 * collateral_strength
  - 0.08 * liquidity_score
  + 0.035 * max(country_risk - 2, 0)
  - 0.025 * max(seniority_score - 2, 0)
  + 0.06 * max(tenor_days - 30, 0) / 90
```

Then:

```text
business_lgd = clip(business_lgd, 0.01, 0.99)
```

If unsecured:

```text
business_lgd = max(business_lgd, 0.55)
```

Why it is used:

LGD estimates severity after default. Collateral lowers LGD, long tenor can raise LGD, and weak liquidity can worsen recovery.

Used elsewhere:

LGD models are used in Basel credit risk, loan pricing, expected credit loss, and capital modeling.

Connection:

```text
collateral + liquidity + tenor -> LGD -> expected loss
```

### 7.3 Trained LGD Blend

If the trained LGD artifact is available:

```text
predicted_lgd = clip(0.65 * business_lgd + 0.35 * trained_lgd, 0.01, 0.99)
```

Why it is used:

The business rule gives transparent logic, while the trained artifact provides a data-driven cross-check.

Connection:

```text
business LGD + trained LGD -> final predicted LGD
```

### 7.4 Invoice Exposure

Primary:

```text
invoice_exposure = invoice_amount
```

Fallback:

```text
invoice_exposure = fuel_volume * fuel_price
```

Why it is used:

If invoice amount is missing, fuel volume and fuel price can estimate the transaction size.

Connection:

```text
invoice/fuel terms -> expected drawdown -> EAD
```

### 7.5 Expected Drawdown

```text
expected_drawdown =
  invoice_exposure
  * utilization_rate
  * max(1, payment_tenor_days / 30)
```

Why it is used:

Longer tenor and higher utilization mean more exposure can build up before payment.

Used elsewhere:

EAD models commonly estimate future drawn exposure at default.

Connection:

```text
invoice exposure + utilization + tenor -> expected drawdown -> EAD
```

### 7.6 Business EAD

```text
uncapped_ead = outstanding_receivables + expected_drawdown
business_ead = min(logical_limit, uncapped_ead)
```

Where:

```text
logical_limit = approved_credit_limit or requested_credit_limit
```

Why it is used:

EAD estimates how much money is exposed if default occurs.

Used elsewhere:

EAD is one of the three core credit risk parameters in expected loss and regulatory capital.

Connection:

```text
receivables + drawdown + limit -> EAD
```

### 7.7 Trained EAD Blend

If calibrated EAD is available:

```text
exposure_at_default = 0.70 * business_ead + 0.30 * trained_ead
```

Then capped by logical limit when applicable.

Why it is used:

It combines transparent exposure math with the calibrated model artifact.

Connection:

```text
business EAD + trained EAD -> final EAD
```

### 7.8 Expected Loss

```text
expected_loss = probability_of_default * loss_given_default * exposure_at_default
```

Usually written as:

```text
EL = PD * LGD * EAD
```

Why it is used:

Expected loss is the average modelled credit loss in currency terms.

Used elsewhere:

This is the standard formula used in credit risk, IFRS 9 expected credit loss, Basel models, and loan pricing.

Connection:

```text
final PD + predicted LGD + EAD -> expected loss -> recommendation and dashboards
```

## 8. Scenario and Monte Carlo Formulas

Scenario and Monte Carlo models estimate downside risk beyond average expected loss.

### 8.1 Scenario Pressure

The project combines commodity, FX, and macro pressure into a scenario pressure score.

Conceptual formula:

```text
combined_pressure_z =
  commodity_pressure_z
  + fx_pressure_z
  + macro_pressure_z
```

Why it is used:

Market stress does not affect all companies the same way. Airlines are especially sensitive to fuel, FX, passenger demand, and macro pressure.

Connection:

```text
market scenario -> pressure z-score -> stressed PD/LGD/EAD
```

### 8.2 Scenario Adjusted PD

```text
pd_multiplier = exp(pd_stress_coefficient * max(combined_pressure_z, -2.0))
adjusted_pd = clip(base_pd * pd_multiplier, 0.0001, 0.95)
```

Why it is used:

Under stress, PD should rise nonlinearly rather than linearly.

Used elsewhere:

Stress testing often applies nonlinear multipliers to default probabilities.

### 8.3 Scenario Adjusted LGD

```text
lgd_add_on =
  lgd_stress_coefficient
  * max(combined_pressure_z, 0)
  * (1 - collateral_strength)

adjusted_lgd = clip(base_lgd + lgd_add_on, 0.01, 0.99)
```

Why it is used:

Loss severity can worsen in stress, especially when collateral is weak.

### 8.4 Scenario Adjusted EAD

```text
ead_multiplier =
  1 + min(ead_commodity_coefficient * max(commodity_pressure_z, 0), ead_commodity_cap)

adjusted_ead = base_ead * ead_multiplier
```

Why it is used:

Fuel cost pressure can increase working capital and exposure needs.

### 8.5 Scenario Expected Loss

```text
scenario_expected_loss = adjusted_pd * adjusted_lgd * adjusted_ead
```

Why it is used:

It shows expected loss under the selected stress scenario.

Connection:

```text
base EL -> scenario EL -> policy tail-risk add-on
```

### 8.6 Default Correlation

```text
default_correlation =
  base_correlation
  + stress_coefficient * stress_component
  + vix_stress_coefficient * min(stress_level + vix_level, 6.0)
```

Then clipped between configured minimum and maximum values.

Why it is used:

In stress, companies are more likely to default together.

Used elsewhere:

Default correlation is central to portfolio credit risk and copula models.

Connection:

```text
stress + VIX + portfolio context -> default correlation -> Monte Carlo losses
```

### 8.7 Gaussian Copula Default Simulation

For each simulation:

```text
latent_score =
  sqrt(default_correlation) * systematic_factor
  + sqrt(1 - default_correlation) * idiosyncratic_factor
```

Default occurs if:

```text
latent_score < default_threshold
```

Where:

```text
default_threshold = inverse_normal_cdf(adjusted_pd)
```

Why it is used:

It models correlated default events across counterparties.

Used elsewhere:

Gaussian copulas are used in portfolio credit risk modeling.

Connection:

```text
adjusted PD + correlation -> default simulation -> portfolio loss distribution
```

### 8.8 t-Copula Tail Variant

For t-copula:

```text
latent_score = gaussian_score * sqrt(degrees_of_freedom / chi_square_draw)
```

Why it is used:

t-copula creates heavier tails than Gaussian copula. It is useful for extreme tail scenarios.

Used elsewhere:

Used in risk management when tail dependence matters.

### 8.9 Simulated Loss

For each counterparty in each simulation:

```text
loss = default_flag * lgd_draw * ead_draw
```

Portfolio loss:

```text
portfolio_loss = sum(counterparty_losses)
```

Why it is used:

It creates a distribution of possible losses rather than only one average loss.

### 8.10 Monte Carlo Expected Loss

```text
monte_carlo_expected_loss = mean(simulated_losses)
```

Why it is used:

This is the average loss across simulated scenarios.

### 8.11 Unexpected Loss

```text
unexpected_loss = standard_deviation(simulated_losses)
```

Why it is used:

Unexpected loss measures volatility around expected loss.

Used elsewhere:

Used in economic capital and portfolio credit risk.

### 8.12 Credit VaR

```text
credit_var_95 = percentile(simulated_losses, 95)
credit_var_99 = percentile(simulated_losses, 99)
```

Why it is used:

VaR estimates a high-percentile loss threshold.

Interpretation:

`VaR 95 = 500K` means 95% of simulated losses are below or equal to 500K.

Used elsewhere:

VaR is widely used in market risk, credit risk, and portfolio risk.

### 8.13 Expected Shortfall

```text
expected_shortfall_95 = mean(losses >= credit_var_95)
expected_shortfall_99 = mean(losses >= credit_var_99)
```

Why it is used:

Expected shortfall measures average loss in the tail beyond VaR. It is usually more informative than VaR because it tells how bad losses are after the VaR threshold is breached.

Used elsewhere:

Expected shortfall is used in modern risk management and regulatory market risk.

Connection:

```text
Monte Carlo loss distribution -> VaR/ES -> policy tail-risk haircut
```

## 9. Credit Decision and Policy Formulas

The decision engine turns quantitative risk into practical credit terms.

### 9.1 Risk Grade Mapping

```text
A    = PD < 1%
BBB  = 1% <= PD < 3%
BB   = 3% <= PD < 7%
B    = 7% <= PD < 15%
CCC  = PD >= 15%
```

Why it is used:

It converts PD into an easy-to-understand internal risk grade.

Used elsewhere:

Banks use internal grades, rating masterscales, and PD bands.

Connection:

```text
final PD -> internal grade -> tenor, security, approval status
```

### 9.2 Scenario Loss Ratio

```text
scenario_loss_ratio = tail_loss / exposure_at_default
```

Where tail loss is chosen in this order:

```text
expected_shortfall_95
credit_var_95
scenario_expected_loss
```

Why it is used:

It measures tail risk relative to the actual exposure size.

Connection:

```text
VaR/ES -> scenario loss ratio -> policy haircut
```

### 9.3 Policy Haircut

The project builds the haircut additively:

```text
limit_haircut =
  PD grade haircut
  + LGD severity haircut
  + market stress haircut
  + liquidity haircut
  + leverage haircut
  + interest coverage haircut
  + tenor haircut
  + scenario tail-risk haircut
  + model disagreement haircut
  - collateral credit
```

Examples:

```text
BB PD grade -> +16%
moderate scenario tail risk -> +8%
model disagreement -> +5%
strong LC/collateral -> -10%
```

Why it is used:

The haircut converts risk into a lower approved/recommended limit.

Used elsewhere:

Credit policy frameworks often use scorecards, caps, overrides, and limit haircuts.

Connection:

```text
PD + LGD + liquidity + scenario VaR/ES + collateral -> limit haircut
```

### 9.4 Recommended Credit Limit

```text
recommended_credit_limit = base_limit * (1 - limit_haircut)
```

Base limit priority:

```text
requested_credit_limit
then approved_credit_limit
then EAD
```

Why it is used:

The model starts from the requested exposure and reduces it based on risk.

Example:

```text
requested_limit = 22.0M
base_policy_haircut = 11%
scenario_tail_add_on = 8%
final_haircut = 19%

recommended_limit = 22.0M * (1 - 0.19)
recommended_limit = 17.82M
```

Connection:

```text
base limit + policy haircut -> recommended limit
```

### 9.5 Recommended Tenor

```text
recommended_tenor_days = policy_rule(risk_grade, policy_score)
```

Examples:

- Better grade and low score can allow longer tenor.
- BB or moderate policy score usually keeps tenor controlled.
- Weak grade can reduce tenor to 30 days or require prepayment.

Why it is used:

Shorter tenor limits receivable build-up.

Connection:

```text
risk grade + policy score -> tenor
```

### 9.6 Recommended Security

```text
recommended_security = policy_rule(risk_grade, policy_score, PD, LGD, collateral_strength)
```

Examples:

- Strong collateral already present: existing collateral may be acceptable.
- BB risk: corporate guarantee or partial deposit.
- B/CCC risk: LC, bank guarantee, prepayment, or manual review.

Why it is used:

Security reduces recovery risk.

Connection:

```text
PD + LGD + grade + collateral -> security requirement
```

### 9.7 Approval Status

```text
approval_status = policy_rule(risk_grade, policy_score, recommended_credit_limit)
```

Possible statuses:

- Approved
- Conditional approval
- Conditional approval secured
- Reject / prepayment only

Why it is used:

This is the final committee-style decision label.

Connection:

```text
recommended limit + grade + score -> approval status
```

## 10. ML Models in Simple Terms

### 10.1 Market Stress PCA

Type:

```text
PCA + percentile scaling
```

What it does:

It compresses many market factors into one stress index.

Simple explanation:

> Instead of manually deciding how much weight to give Brent, VIX, USD, PMI, and other market factors, PCA finds the strongest common stress pattern across them. The project then rescales that pattern into a 0-100 market stress score.

Where it affects the project:

- ML PD
- Scenario stress
- Monte Carlo assumptions
- Market dashboard
- Copilot explanations

### 10.2 Merton Structural PD

Type:

```text
Structural credit model
```

What it does:

It compares firm assets against debt obligations.

Simple explanation:

> If assets are far above debt and volatility is low, structural PD is low. If assets are close to debt or volatility is high, structural PD rises.

Where it affects the project:

- Structural PD
- Distance to default
- Final PD blend

### 10.3 Logistic / ML Proxy PD

Type:

```text
Interpretable logistic model + optional trained historical PD artifact
```

What it does:

It converts ratios and market conditions into default probability.

Simple explanation:

> The ML side checks whether the company looks risky based on leverage, liquidity, margins, market stress, fuel sensitivity, FX sensitivity, and macro conditions.

Where it affects the project:

- ML PD
- Final PD
- Model disagreement warning

### 10.4 Final PD Blend

Type:

```text
Weighted blend
```

What it does:

Combines structural PD and ML PD.

Simple explanation:

> Structural PD is the balance-sheet/default-barrier view. ML PD is the financial-ratio and market-stress view. The final PD blends both so the project does not rely on only one model.

### 10.5 Historical Financial Trend Overlay

Type:

```text
Capped adjustment layer
```

What it does:

Uses multi-year or quarterly history to adjust risk.

Simple explanation:

> If only one year is available, the overlay stays neutral. If multiple periods are available, improving trends can reduce pressure and deteriorating trends can raise PD/LGD slightly.

### 10.6 Historical LGD Model

Type:

```text
Trained LGD artifact + business-rule blend
```

What it does:

Blends transparent LGD logic with a trained model artifact.

Simple explanation:

> The business rule gives an explainable recovery estimate. The trained LGD model provides a data-driven cross-check. The project blends them instead of letting either one fully dominate.

### 10.7 Calibrated EAD Model

Type:

```text
Trained EAD artifact + deterministic EAD blend
```

What it does:

Blends trade exposure logic with calibrated exposure behavior.

Simple explanation:

> The deterministic EAD formula estimates outstanding exposure from receivables, invoice size, utilization, and tenor. The calibrated EAD model adjusts that estimate based on learned exposure behavior.

### 10.8 Monte Carlo Portfolio Model

Type:

```text
Gaussian copula or t-copula Monte Carlo
```

What it does:

Simulates many possible default/loss outcomes.

Simple explanation:

> Expected loss tells the average loss. Monte Carlo tells the downside distribution: what happens in worse cases, including VaR and expected shortfall.

## 11. Full Pipeline Walkthrough

### Step 1: User Ingests Data

The user uploads a PDF or manually enters financials.

Important fields:

- Revenue
- EBITDA
- EBIT
- Net income
- Cash
- Accounts receivable
- Inventory
- Current assets
- Current liabilities
- Total assets
- Total debt
- Total liabilities
- Shareholders equity
- Interest expense

Output table:

```text
financial_metrics_extracted
```

### Step 2: Financial Ratios Are Calculated

The app calculates liquidity, leverage, profitability, and coverage ratios.

Output table:

```text
financial_ratios
```

These ratios feed:

- PD model
- Financial dashboard
- Trend features
- Policy engine
- Copilot context

### Step 3: Market Data Is Loaded

Market data is collected for fuel, FX, volatility, rates, equity, freight, PMI, and aviation demand indicators.

Output tables include:

```text
market_prices
stress_index_history
market_regime_history
```

### Step 4: PCA Stress Index Is Built

Market indicators are transformed into z-scores and compressed through PCA.

Output:

```text
stress_index = 0-100 market stress score
```

This feeds:

- ML PD
- Scenario stress
- Monte Carlo
- Market page

### Step 5: PD Is Estimated

Two PD views are calculated:

```text
structural_pd = Merton model PD
ml_pd = logistic/proxy/trained model PD
final_pd = blended PD
```

Output table:

```text
pd_model_predictions
```

### Step 6: LGD, EAD, and EL Are Calculated

The project estimates:

```text
LGD = severity if default happens
EAD = exposure at default
EL = PD * LGD * EAD
```

Output table:

```text
loss_estimates
```

### Step 7: Scenario and Monte Carlo Run

The app applies stress scenarios and simulates losses.

Outputs:

- Scenario expected loss
- VaR 95
- VaR 99
- Expected shortfall 95
- Expected shortfall 99
- Loss distribution

Output tables:

```text
scenario_results
simulation_results
```

### Step 8: Credit Decision Is Generated

The policy engine uses:

- Final PD
- LGD
- EAD
- Expected loss
- VaR / expected shortfall
- Liquidity
- Leverage
- Coverage
- Tenor
- Collateral

Then it produces:

- Recommended credit limit
- Recommended tenor
- Required security
- Risk grade
- Approval status
- Policy haircut
- Policy rationale

Output table:

```text
credit_recommendations
```

### Step 9: Dashboard and Copilot Explain the Outputs

The frontend displays:

- Counterparty analysis
- Financial statements
- Market page
- Scenario and forecasts
- Quant and Monte Carlo outputs
- Credit recommendation
- AI copilot explanations

The copilot uses:

- Field catalog
- Formula catalog
- Model catalog
- Pipeline graph
- Stored counterparty context

## 12. How the Formulas Are Interconnected

The simplest dependency chain is:

```text
Financial statement values
    -> ratios
    -> PD and policy rules

Market prices
    -> returns and z-scores
    -> PCA stress index
    -> PD and scenario pressure

Trade terms
    -> EAD
    -> expected loss

Collateral
    -> LGD
    -> expected loss
    -> security recommendation

PD + LGD + EAD
    -> expected loss
    -> scenario loss
    -> Monte Carlo VaR/ES
    -> policy haircut
    -> recommended limit
```

More detailed:

```text
current_ratio, quick_ratio, cash_ratio
    -> liquidity quality
    -> ML PD, LGD liquidity score, policy rules

debt_to_ebitda, debt_to_equity, liabilities_to_assets
    -> leverage and solvency
    -> ML PD, distress floor, policy rules

interest_coverage, operating_margin, net_margin
    -> earnings and debt service capacity
    -> ML PD, trend overlay, policy rules

market stress index
    -> market pressure
    -> ML PD, scenario PD multiplier, default correlation

final PD
    -> risk grade
    -> expected loss
    -> policy score

LGD
    -> expected loss
    -> recovery/security analysis

EAD
    -> expected loss
    -> VaR/ES exposure scale

VaR/ES
    -> tail-risk add-on
    -> final policy haircut
```

## 13. Final Mathematical Workflow Summary

The project's mathematical workflow can be summarized like this:

```text
1. Calculate financial ratios.
2. Convert market prices into returns, z-scores, PCA stress, and market regime.
3. Estimate structural PD using Merton distance to default.
4. Estimate ML PD using financial ratios and market stress.
5. Blend structural PD and ML PD into final PD.
6. Use collateral, liquidity, tenor, and trained LGD model to estimate LGD.
7. Use receivables, invoice exposure, utilization, tenor, and trained EAD model to estimate EAD.
8. Calculate expected loss = PD * LGD * EAD.
9. Apply market scenarios to stress PD, LGD, and EAD.
10. Run Monte Carlo to get loss distribution, VaR, and expected shortfall.
11. Apply credit policy haircuts.
12. Generate recommended limit, tenor, security, risk grade, and approval status.
```

Interview-ready summary:

> My project combines traditional credit ratios, a structural Merton PD model, an ML-style PD cross-check, collateral-aware LGD, exposure-at-default logic, market PCA stress, scenario testing, Monte Carlo VaR/expected shortfall, and a rules-based credit policy engine. The key formula is expected loss: PD times LGD times EAD. Everything before that estimates one of those three components or explains market stress; everything after that converts the risk into usable credit terms.

