# Synthetic Entry Full Flow and Calculation Guide

This document explains one complete synthetic example from data entry to final credit recommendation. It is written so you can explain the project in an interview with both business logic and formulas.

## 1. Example Synthetic Counterparty

Assume an analyst creates a synthetic airline customer:

- Counterparty name: `Synthetic Airways Ltd`
- Counterparty type: `airline`
- Country: `United States`
- Requested credit limit: `10,000,000`
- Payment tenor: `45 days`
- Security: `standby letter of credit`
- Outstanding receivables: `2,000,000`
- Invoice amount: `4,000,000`
- Utilization rate: `60%`

Synthetic financial statement:

- Revenue: `120,000,000`
- EBITDA: `18,000,000`
- EBIT: `12,000,000`
- Interest expense: `4,000,000`
- Net income: `6,000,000`
- Cash: `8,000,000`
- Accounts receivable: `18,000,000`
- Inventory: `10,000,000`
- Current assets: `45,000,000`
- Current liabilities: `30,000,000`
- Total assets: `150,000,000`
- Total debt: `70,000,000`
- Total liabilities: `100,000,000`
- Shareholders equity: `50,000,000`
- Currency: `USD`

The goal is to answer: should we approve the requested `10M` credit line, and what terms/security should apply?

## 2. Step 1 - Counterparty Creation

The first persistent row is created in `counterparties_master`.

Stored values:

- `counterparty_name = Synthetic Airways Ltd`
- `counterparty_type = airline`
- `country = United States`

Why it matters:

- This gives every downstream record a stable `counterparty_id`.
- The `counterparty_type` changes risk sensitivity later. Airlines are mapped as highly exposed to jet fuel prices, USD/FX moves, and macro stress.

## 3. Step 2 - Manual Financial Entry or PDF Upload

There are two ways to create the financial input.

### 3.1 Manual entry path

If the analyst enters data manually, the code creates:

- A synthetic `uploaded_documents` row with `document_type = manual_financial_statement`
- A `financial_metrics_extracted` row with the entered financial line items

Manual entries get:

- `extraction_status = completed`
- `file_path = manual://financial-metrics/...`
- `extraction_confidence = 1.00` if critical fields are present
- `original_text_references = {"source": "manual analyst entry"}`
- `extraction_warnings = ["manual_entry_no_pdf_source"]`

### 3.2 PDF path

If a PDF is uploaded, the document row tracks:

- File name
- File path
- File size
- Upload time
- Extraction status
- Extraction error if processing fails

The extraction service then stores financial statement line items in `financial_metrics_extracted`.

## 4. Step 3 - Financial Metrics Stored

The row in `financial_metrics_extracted` is the structured financial statement. It groups data into:

- Income statement: revenue, EBITDA, EBIT, interest expense, net income
- Balance sheet assets: cash, receivables, inventory, current assets, total assets
- Balance sheet liabilities/equity: current liabilities, debt, total liabilities, equity
- Cash flow: operating cash flow, investing cash flow, financing cash flow, free cash flow
- Audit metadata: confidence, missing fields, source references, warnings

For the synthetic entry, important stored values are:

- `revenue = 120,000,000`
- `ebitda = 18,000,000`
- `ebit = 12,000,000`
- `interest_expense = 4,000,000`
- `net_income = 6,000,000`
- `cash_and_equivalents = 8,000,000`
- `accounts_receivable = 18,000,000`
- `inventory = 10,000,000`
- `current_assets = 45,000,000`
- `current_liabilities = 30,000,000`
- `total_assets = 150,000,000`
- `total_debt = 70,000,000`
- `total_liabilities = 100,000,000`
- `shareholders_equity = 50,000,000`

This table does not yet make a credit decision. It only stores the financial facts.

## 5. Step 4 - Financial Ratio Calculation

The ratio engine reads `financial_metrics_extracted` and writes to `financial_ratios`.

The code deliberately avoids fabricating values. If a denominator is zero or an input is missing, the ratio becomes `None`, and the missing input is recorded in `missing_inputs`.

### 5.1 Liquidity ratios

Current ratio:

```text
current_ratio = current_assets / current_liabilities
              = 45,000,000 / 30,000,000
              = 1.50
```

Meaning:

- Values above `1.0` suggest the firm can cover short-term liabilities with short-term assets.

Quick ratio:

```text
quick_ratio = (cash + accounts_receivable) / current_liabilities
            = (8,000,000 + 18,000,000) / 30,000,000
            = 0.8667
```

Meaning:

- More conservative than current ratio because it excludes inventory.

Cash ratio:

```text
cash_ratio = cash / current_liabilities
           = 8,000,000 / 30,000,000
           = 0.2667
```

Meaning:

- Very conservative immediate liquidity measure.

Working capital:

```text
working_capital = current_assets - current_liabilities
                = 45,000,000 - 30,000,000
                = 15,000,000
```

Meaning:

- Positive working capital supports day-to-day repayment capacity.

### 5.2 Leverage ratios

Debt to equity:

```text
debt_to_equity = total_debt / shareholders_equity
               = 70,000,000 / 50,000,000
               = 1.40
```

Meaning:

- The company has `1.4x` debt for every dollar of equity.

Debt to EBITDA:

```text
debt_to_ebitda = total_debt / EBITDA
               = 70,000,000 / 18,000,000
               = 3.8889
```

Meaning:

- Roughly 3.9 years of EBITDA would be needed to repay debt, before interest/tax/capex.

Liabilities to assets:

```text
liabilities_to_assets = total_liabilities / total_assets
                      = 100,000,000 / 150,000,000
                      = 0.6667
```

Meaning:

- Around two-thirds of assets are funded by liabilities.

### 5.3 Coverage and profitability

Interest coverage:

```text
interest_coverage = EBIT / interest_expense
                  = 12,000,000 / 4,000,000
                  = 3.00
```

Meaning:

- Operating profit covers interest expense 3 times.

Operating margin:

```text
operating_margin = EBIT / revenue
                 = 12,000,000 / 120,000,000
                 = 0.10 = 10%
```

Net margin:

```text
net_margin = net_income / revenue
           = 6,000,000 / 120,000,000
           = 0.05 = 5%
```

Return on assets:

```text
return_on_assets = net_income / total_assets
                 = 6,000,000 / 150,000,000
                 = 0.04 = 4%
```

Return on equity:

```text
return_on_equity = net_income / shareholders_equity
                 = 6,000,000 / 50,000,000
                 = 0.12 = 12%
```

## 6. Step 5 - Market Data Ingestion

Market data is stored in `market_prices` and sometimes mirrored into `macro_indicators`.

Examples of assets:

- `brent_oil`
- `crude_oil`
- `heating_oil_proxy`
- `jet_fuel_proxy`
- `vix`
- `sp500`
- `dxy`
- `gold`
- `us_10y_yield`
- `yield_curve_spread`
- `cpi_index`
- `freight_proxy`

Each row stores:

```text
date, asset, price, ticker, source_id, data_source, frequency, units, return, rolling_volatility
```

The system uses market data for:

- Stress index
- Market regime
- Scenario generation
- PD vulnerability scores
- Monte Carlo shocks

## 7. Step 6 - Market Stress Index Using PCA

The stress index converts many market signals into a single `0-100` stress score.

### 7.1 Market prices are pivoted

Raw `market_prices` rows are converted into a date-by-asset matrix:

```text
date        brent_oil   vix   sp500   dxy   us_10y_yield ...
2026-01-01  82.10       18.2  5000    104   4.2
2026-01-02  84.00       20.1  4920    105   4.3
```

Missing values are forward-filled when possible.

### 7.2 Returns and stress components are built

The system calculates economically oriented stress components.

Examples:

```text
oil_return = log(oil_price_t / oil_price_t-1)
oil_volatility = rolling_std(oil_return, 20 days)
sp500_loss = -log(sp500_t / sp500_t-1)
dxy_return = log(dxy_t / dxy_t-1)
yield_10y_change = us_10y_yield_t - us_10y_yield_t-1
yield_curve_stress = -(yield_curve_spread_t - yield_curve_spread_t-1)
freight_loss = -log(freight_t / freight_t-1)
inflation_change = pct_change(cpi_index)
```

Why the signs differ:

- Higher oil volatility means more stress.
- Higher Brent/jet fuel return means fuel cost pressure.
- Lower S&P 500 means risk-off stress, so the return is multiplied by `-1`.
- Stronger USD can pressure airlines/traders with USD liabilities or imported fuel.
- Falling freight can signal weaker global trade, so freight return is multiplied by `-1`.

### 7.3 Each component is z-scored

Each component is standardized:

```text
z = (value - mean(component)) / standard_deviation(component)
```

Example:

```text
vix_zscore = (latest_vix - average_vix) / vix_standard_deviation
```

This puts all components on the same scale, so VIX, oil, FX, freight, and rates can be compared.

### 7.4 PCA combines the components

If there are enough components and observations, the system runs PCA with one component:

```text
component_matrix = [z_oil_volatility, z_brent_return, z_vix, z_sp500_loss, z_dxy, ...]
pc1_score = PCA(component_matrix, n_components=1)
```

PCA finds the weighted combination of components that explains the largest common movement:

```text
pc1_score_t = w1*z1_t + w2*z2_t + w3*z3_t + ... + wn*zn_t
```

The weights are the PCA loadings. The code also checks the sign:

```text
if correlation(pc1_score, average_component_stress) < 0:
    pc1_score = -pc1_score
    loadings = -loadings
```

That ensures higher PC1 means higher stress.

If PCA cannot be used because there is too little data, the fallback is:

```text
pc1_score = average(z-scored stress components)
```

### 7.5 PC1 is scaled to 0-100

The raw PCA score is percentile-scaled:

```text
p1 = 1st percentile of pc1_score history
p99 = 99th percentile of pc1_score history
stress_index = ((pc1_score - p1) / (p99 - p1)) * 100
stress_index = clipped between 0 and 100
```

Stress level:

```text
0-20   = Calm
20-40  = Normal
40-60  = Elevated
60-80  = Stressed
80-100 = Crisis
```

The output is stored in `stress_index_history` with:

- `stress_index`
- `stress_level`
- `pc1_score`
- `explained_variance_ratio`
- `pca_loadings`
- `component_values`
- `top_positive_drivers`
- `top_negative_drivers`
- missing/available components

For example:

```text
stress_index = 68.0
stress_level = Stressed
top drivers = VIX, Brent return, DXY strength, S&P 500 loss
```

## 8. Step 7 - Market Regime Detection

The regime detector uses the same stress component matrix.

It standardizes the feature matrix:

```text
scaled_features = StandardScaler(component_matrix)
```

Then it applies a clustering model:

- KMeans by default
- GMM as an option
- HMM-style smoothing as an option over GMM states

For KMeans:

```text
regime_id = cluster(component_zscores)
confidence = 1 / (1 + distance_to_nearest_cluster_center)
```

The system interprets clusters based on average stress and dominant drivers:

- `Stable Market`
- `Normal Volatility`
- `Commodity Stress`
- `USD Stress`
- `Risk-Off`
- `Crisis`

For the synthetic example:

```text
market_regime = Commodity Stress
regime_probability = 0.76
```

Stored in `market_regime_history`.

## 9. Step 8 - Probability of Default Model

The PD model uses:

- Financial metrics from `financial_metrics_extracted`
- Ratios from `financial_ratios`
- Market context from `stress_index_history` and `market_regime_history`
- Latest risk-free rate proxy from `market_prices`, usually `us_10y_yield`

It writes to `pd_model_predictions`.

## 10. Step 8A - Market Context

The PD service loads:

```text
stress_index = latest stress_index_history.stress_index
stress_level = latest stress_index_history.stress_level
market_regime = latest market_regime_history.regime_label
risk_free_rate = latest us_10y_yield / 100 if stored as percent
```

Example:

```text
stress_index = 68.0
stress_level = Stressed
market_regime = Commodity Stress
risk_free_rate = 0.042
```

It also reads stress components:

```text
oil_volatility_zscore
heating_oil_return_zscore or brent_return_zscore
dxy_return_zscore
freight_loss_zscore
```

## 11. Step 8B - Vulnerability Scores

Because the counterparty is an airline, the code maps it as high fuel and USD sensitive.

The stress component is:

```text
stress_component = stress_index / 100
                 = 68 / 100
                 = 0.68
```

Oil, FX, and freight components are clipped z-score transformations:

```text
oil_component = clip((oil_volatility_zscore + fuel_return_zscore) / 4, 0, 1)
fx_component = clip(fx_return_zscore / 3, 0, 1)
freight_component = clip(freight_loss_zscore / 3, 0, 1)
```

For airlines:

```text
commodity_sensitivity = 0.65 + 0.25 * oil_component
fx_sensitivity = 0.45 + 0.25 * fx_component
macro_sensitivity = 0.40 + 0.35 * stress_component
```

Example if:

```text
oil_component = 0.50
fx_component = 0.40
stress_component = 0.68
```

Then:

```text
commodity_sensitivity = 0.65 + 0.25*0.50 = 0.775
fx_sensitivity = 0.45 + 0.25*0.40 = 0.550
macro_sensitivity = 0.40 + 0.35*0.68 = 0.638
```

Meaning:

- The airline is materially exposed to fuel cost spikes, USD pressure, and market stress.

## 12. Step 8C - Structural Merton PD

The structural model treats default as a balance-sheet event: default risk rises when asset value is close to or below the debt threshold, especially under high asset volatility.

### 12.1 Asset value proxy

The code uses:

```text
asset_value_proxy = total_assets
```

If `total_assets` is missing, it falls back to:

```text
asset_value_proxy = 1.5 * revenue
```

For this example:

```text
asset_value_proxy = 150,000,000
```

### 12.2 Debt threshold

The code uses:

```text
debt_threshold = total_debt
```

If `total_debt` is missing, it derives debt from debt components or uses `60%` of total liabilities.

For this example:

```text
debt_threshold = 70,000,000
```

### 12.3 Asset volatility proxy

The code estimates asset volatility from leverage, liquidity, market stress, and vulnerability:

```text
asset_volatility =
    0.18
  + 0.08 * min(debt_to_equity, 5)
  + 0.12 * stress
  + 0.10 * average_vulnerability
  + 0.05 * max(0, 1 - min(current_ratio, 2) / 2)
```

Where:

```text
average_vulnerability = average(commodity_sensitivity, fx_sensitivity, macro_sensitivity)
```

Using:

```text
debt_to_equity = 1.40
current_ratio = 1.50
stress = 0.68
average_vulnerability = average(0.775, 0.550, 0.638) = 0.6543
```

Then:

```text
asset_volatility =
    0.18
  + 0.08*1.40
  + 0.12*0.68
  + 0.10*0.6543
  + 0.05*max(0, 1 - 1.50/2)

= 0.18 + 0.112 + 0.0816 + 0.0654 + 0.0125
= 0.4515
```

So:

```text
asset_volatility ~= 45.15%
```

### 12.4 Distance to default

The Merton-style distance-to-default formula is:

```text
DD = [ln(asset_value / debt_threshold) + (risk_free_rate - 0.5 * asset_volatility^2) * T]
     / [asset_volatility * sqrt(T)]
```

Where:

```text
asset_value = 150,000,000
debt_threshold = 70,000,000
risk_free_rate = 0.042
asset_volatility = 0.4515
T = 1 year
```

Calculation:

```text
ln(150,000,000 / 70,000,000) = ln(2.1429) = 0.7621
0.5 * asset_volatility^2 = 0.5 * 0.4515^2 = 0.1019
risk_free_rate - 0.5*sigma^2 = 0.042 - 0.1019 = -0.0599
numerator = 0.7621 - 0.0599 = 0.7022
denominator = 0.4515 * sqrt(1) = 0.4515
DD = 0.7022 / 0.4515 = 1.555
```

Meaning:

- The company is about `1.56` volatility units away from the default threshold.

### 12.5 Structural PD

The structural PD is:

```text
structural_pd = NormalCDF(-DD)
```

For:

```text
DD = 1.555
```

Approximate:

```text
structural_pd = NormalCDF(-1.555) ~= 0.060
```

So the structural model says:

```text
structural_pd ~= 6.0%
```

## 13. Step 8D - ML/Logistic Proxy PD

The ML proxy is an interpretable logistic model over ratios and market stress.

The formula is:

```text
ml_pd = 1 / (1 + exp(-logit))
```

Where the logit is the sum of feature contributions:

```text
logit =
  intercept
  + debt_to_ebitda contribution
  + debt_to_equity contribution
  + weak_liquidity contribution
  + low_cash contribution
  + weak_interest_coverage contribution
  + negative_margin contribution
  + market_stress contribution
  + commodity_vulnerability contribution
  + fx_vulnerability contribution
  + macro_vulnerability contribution
```

Code-level contributions:

```text
intercept = -3.40
debt_to_ebitda = 0.20 * min(debt_to_ebitda, 10)
debt_to_equity = 0.15 * min(debt_to_equity, 8)
weak_liquidity = 0.70 * max(0, 1.20 - current_ratio)
low_cash = 0.35 * max(0, 0.50 - cash_ratio)
weak_interest_coverage = 0.25 * max(0, 3.0 - interest_coverage)
negative_margin = 2.00 * max(0, -net_margin)
market_stress = 1.25 * stress_index/100
commodity_vulnerability = 0.55 * commodity_sensitivity
fx_vulnerability = 0.35 * fx_sensitivity
macro_vulnerability = 0.45 * macro_sensitivity
```

Using:

```text
debt_to_ebitda = 3.8889
debt_to_equity = 1.40
current_ratio = 1.50
cash_ratio = 0.2667
interest_coverage = 3.00
net_margin = 0.05
stress = 0.68
commodity_sensitivity = 0.775
fx_sensitivity = 0.550
macro_sensitivity = 0.638
```

Contributions:

```text
intercept = -3.4000
debt_to_ebitda = 0.20*3.8889 = 0.7778
debt_to_equity = 0.15*1.40 = 0.2100
weak_liquidity = 0.70*max(0, 1.20-1.50) = 0
low_cash = 0.35*(0.50-0.2667) = 0.0817
weak_interest_coverage = 0.25*max(0, 3.0-3.0) = 0
negative_margin = 0
market_stress = 1.25*0.68 = 0.8500
commodity_vulnerability = 0.55*0.775 = 0.4263
fx_vulnerability = 0.35*0.550 = 0.1925
macro_vulnerability = 0.45*0.638 = 0.2871
```

Total:

```text
logit = -3.4000 + 0.7778 + 0.2100 + 0.0817 + 0.8500 + 0.4263 + 0.1925 + 0.2871
      = -0.5746
```

Then:

```text
ml_pd = 1 / (1 + exp(0.5746))
      ~= 0.360
```

So the ML proxy says:

```text
ml_pd ~= 36.0%
```

Important interview explanation:

- This proxy is intentionally conservative under market stress.
- It is a cross-check, not the sole final model.
- If a trained historical PD artifact exists, the code blends the rule-based logistic PD with that trained model.

## 14. Step 8E - Final PD Blend and Distress Floors

The final PD is anchored to the structural model:

```text
final_pd = 0.65 * structural_pd + 0.35 * ml_pd
```

Using:

```text
structural_pd = 0.060
ml_pd = 0.360
```

Then:

```text
final_pd = 0.65*0.060 + 0.35*0.360
         = 0.039 + 0.126
         = 0.165
```

So:

```text
final_pd ~= 16.5%
```

The code also checks distress floors:

```text
if shareholders_equity <= 0:
    final_pd >= 16%

if liabilities_to_assets >= 1.0:
    final_pd >= 18%

if liabilities_to_assets >= 0.90:
    final_pd >= 8%
```

For this example:

```text
shareholders_equity = 50,000,000 > 0
liabilities_to_assets = 0.6667
```

No distress floor applies.

PD grade mapping:

```text
PD < 1%      -> A
1% to 3%    -> BBB
3% to 7%    -> BB
7% to 15%   -> B
>= 15%      -> CCC
```

Since:

```text
final_pd = 16.5%
```

The internal grade is:

```text
classification_label = CCC
```

Stored in `pd_model_predictions`:

- `structural_pd`
- `ml_pd`
- `final_pd`
- `classification_label`
- `distance_to_default`
- `asset_value_proxy`
- `debt_threshold`
- `asset_volatility`
- `risk_free_rate`
- `commodity_sensitivity_score`
- `fx_sensitivity_score`
- `macro_sensitivity_score`
- `market_stress_index`
- `market_regime`
- `feature_contributions`
- `model_assumptions`
- `warnings`

## 15. Step 9 - Trade Exposure Entry

The analyst enters or the UI sends trade terms:

```text
invoice_amount = 4,000,000
requested_credit_limit = 10,000,000
approved_credit_limit = 10,000,000
outstanding_receivables = 2,000,000
payment_tenor_days = 45
utilization_rate = 0.60
collateral_type = letter_of_credit
letter_of_credit_flag = true
deposit_percentage = 0
```

This creates a row in `trade_exposures`.

## 16. Step 10 - LGD Calculation

LGD means loss given default: if the counterparty defaults, what fraction of exposure is not recovered?

### 16.1 Collateral strength

Collateral mapping:

```text
letter_of_credit = 0.90
cash_deposit = 0.80
guarantee = 0.65
secured_collateral = 0.55
unsecured = 0.05
```

Since this example has an LC:

```text
collateral_strength = 0.90
```

### 16.2 LGD formula

The business-rule LGD formula is:

```text
lgd =
    0.62
  - 0.42 * collateral_strength
  - 0.08 * liquidity
  + 0.035 * max(country_risk_score - 2, 0)
  - 0.025 * max(seniority_score - 2, 0)
  + 0.06 * max(payment_tenor_days - 30, 0) / 90
```

The code clips LGD between `1%` and `99%`.

Assume:

```text
collateral_strength = 0.90
liquidity = 0.50 default if not passed
country_risk_score = 2.0
seniority_score = 2.0
payment_tenor_days = 45
```

Then:

```text
lgd =
    0.62
  - 0.42*0.90
  - 0.08*0.50
  + 0
  - 0
  + 0.06*(45-30)/90

= 0.62 - 0.378 - 0.040 + 0.010
= 0.212
```

So:

```text
predicted_lgd = 21.2%
```

Interview interpretation:

- The LC materially reduces severity, but it does not reduce default probability itself.
- PD measures likelihood of default; LGD measures severity after default.

## 17. Step 11 - EAD Calculation

EAD means exposure at default: how much money is at risk if default occurs?

### 17.1 Invoice exposure

If invoice amount exists:

```text
invoice_exposure = invoice_amount
```

If invoice amount is missing:

```text
invoice_exposure = fuel_volume * fuel_price
```

For this example:

```text
invoice_exposure = 4,000,000
```

### 17.2 Expected drawdown

```text
expected_drawdown = invoice_exposure * utilization_rate * max(1, payment_tenor_days / 30)
```

Using:

```text
invoice_exposure = 4,000,000
utilization_rate = 0.60
payment_tenor_days = 45
```

Then:

```text
expected_drawdown = 4,000,000 * 0.60 * max(1, 45/30)
                  = 4,000,000 * 0.60 * 1.5
                  = 3,600,000
```

### 17.3 Uncapped EAD

```text
uncapped_ead = outstanding_receivables + expected_drawdown
             = 2,000,000 + 3,600,000
             = 5,600,000
```

### 17.4 Credit limit cap

The system caps EAD if it exceeds the approved/requested limit:

```text
ead = min(logical_limit, uncapped_ead)
```

Where:

```text
logical_limit = approved_credit_limit if present else requested_credit_limit
```

Here:

```text
logical_limit = 10,000,000
uncapped_ead = 5,600,000
```

So:

```text
exposure_at_default = 5,600,000
ead_cap_applied = false
```

## 18. Step 12 - Expected Loss

Expected loss is the core credit risk formula:

```text
expected_loss = PD * LGD * EAD
```

Using:

```text
PD = 0.165
LGD = 0.212
EAD = 5,600,000
```

Then:

```text
expected_loss = 0.165 * 0.212 * 5,600,000
              = 195,888
```

So the point-in-time expected loss is about:

```text
195,888
```

Stored in `loss_estimates`:

- `probability_of_default`
- `predicted_lgd`
- `exposure_at_default`
- `expected_loss`
- `collateral_strength`
- `expected_drawdown`
- `invoice_exposure`
- `ead_cap_applied`
- assumptions and warnings

## 19. Step 13 - Scenario Generation

The scenario generator builds historical quantile scenarios from market data.

It starts with the market scenario matrix:

```text
brent_change = pct_change(brent_oil)
jet_fuel_change = pct_change(jet_fuel_proxy or heating_oil_proxy)
marine_fuel_change = pct_change(marine_fuel_proxy or crude_oil)
dxy_change = pct_change(dxy)
vix_change = pct_change(vix)
sp500_change = pct_change(sp500)
yield_change = pct_change(us_10y_yield or yield_curve_spread)
baltic_dry_change = pct_change(freight_proxy)
stress_index_change = diff(stress_index) / 100
```

Scenarios use quantiles:

```text
base_case = 50th percentile
normal_volatility = 75th percentile for adverse upper-tail drivers
adverse = 90th percentile
severe_downside = 95th percentile
tail = 99th percentile
```

Tail direction depends on the driver:

- Upper-tail adverse: fuel, DXY, VIX, yields, stress index
- Lower-tail adverse: S&P 500 and freight

Example adverse scenario:

```text
brent_change = 90th percentile of Brent returns
jet_fuel_change = 90th percentile of jet fuel/heating oil returns
dxy_change = 90th percentile of DXY returns
vix_change = 90th percentile of VIX changes
sp500_change = 10th percentile of S&P 500 returns
stress_index_change = 90th percentile of stress changes
```

Each shock also gets a z-score:

```text
driver_zscore = (scenario_shock - historical_mean) / historical_std
```

Stored in scenario objects as:

- `market_shocks`
- `driver_zscores`
- `source_start_date`
- `source_end_date`
- `source_observations`
- `market_regime`
- assumptions

## 20. Step 14 - Scenario Adjustment of PD/LGD/EAD

Before Monte Carlo, each exposure is adjusted under the selected scenario.

### 20.1 Scenario pressure

Commodity pressure:

```text
commodity_pressure_z = average(
    positive(brent_change_z),
    positive(jet_fuel_change_z),
    positive(marine_fuel_change_z)
)
```

FX pressure:

```text
fx_pressure_z = positive(dxy_change_z)
```

Macro pressure:

```text
macro_pressure_z = average(
    positive(vix_change_z),
    positive(yield_change_z),
    positive(stress_index_change_z),
    positive(-sp500_change_z),
    positive(-baltic_dry_change_z)
)
```

Combined pressure:

```text
combined_pressure_z =
    (commodity_sensitivity * commodity_pressure_z
   + fx_sensitivity * fx_pressure_z
   + macro_sensitivity * macro_pressure_z) / 3
```

### 20.2 Scenario-adjusted PD

```text
adjusted_pd = base_pd * exp(0.18 * max(combined_pressure_z, -2))
```

Clipped between:

```text
0.0001 and 0.95
```

### 20.3 Scenario-adjusted LGD

```text
lgd_add_on = 0.035 * max(combined_pressure_z, 0) * (1 - collateral_strength)
adjusted_lgd = base_lgd + lgd_add_on
```

Strong collateral reduces the LGD add-on.

### 20.4 Scenario-adjusted EAD

```text
ead_multiplier = 1 + min(0.035 * max(commodity_pressure_z, 0), 0.30)
adjusted_ead = base_ead * ead_multiplier
```

Reason:

- Fuel price stress can increase invoice size and working-capital usage.

### 20.5 Scenario expected loss

```text
scenario_expected_loss = adjusted_pd * adjusted_lgd * adjusted_ead
```

For example, if the adverse scenario produces:

```text
combined_pressure_z = 1.50
commodity_pressure_z = 2.00
base_pd = 0.165
base_lgd = 0.212
base_ead = 5,600,000
collateral_strength = 0.90
```

Then:

```text
adjusted_pd = 0.165 * exp(0.18*1.50)
            = 0.165 * 1.310
            = 0.216

lgd_add_on = 0.035 * 1.50 * (1-0.90)
           = 0.00525

adjusted_lgd = 0.212 + 0.00525
             = 0.21725

ead_multiplier = 1 + min(0.035*2.00, 0.30)
               = 1.07

adjusted_ead = 5,600,000 * 1.07
             = 5,992,000

scenario_expected_loss = 0.216 * 0.21725 * 5,992,000
                       ~= 281,200
```

## 21. Step 15 - Monte Carlo Simulation

Monte Carlo simulates many possible portfolio loss outcomes under the scenario.

Inputs:

- Scenario-adjusted PD
- Scenario-adjusted LGD
- Scenario-adjusted EAD
- Default correlation
- Number of simulations
- Random seed

### 21.1 Default correlation

Default correlation is estimated from stress:

```text
correlation =
    0.06
  + 0.18 * average_market_stress / 100
  + 0.025 * min(stress_level_z + vix_level_z, 6)
```

Clipped:

```text
0.03 <= correlation <= 0.55
```

### 21.2 Gaussian copula default simulation

For each simulation:

```text
systematic_factor ~ Normal(0, 1)
idiosyncratic_factor_i ~ Normal(0, 1)
latent_score_i =
    sqrt(correlation) * systematic_factor
  + sqrt(1 - correlation) * idiosyncratic_factor_i
```

Default threshold:

```text
threshold_i = NormalInverseCDF(adjusted_pd_i)
```

Default event:

```text
default_i = latent_score_i < threshold_i
```

If t-copula is used, the latent score is scaled by a Student-t tail factor.

### 21.3 Loss simulation

For each defaulted counterparty:

```text
lgd_draw_i ~ Normal(adjusted_lgd_i, max(0.03, 0.10 * adjusted_lgd_i))
ead_draw_i ~ Normal(adjusted_ead_i, max(1.0, 0.05 * adjusted_ead_i))
loss_i = default_i * clipped_lgd_draw_i * max(ead_draw_i, 0)
```

Portfolio loss:

```text
portfolio_loss = sum(loss_i)
```

Across simulations, the system calculates:

```text
expected_loss = mean(portfolio_losses)
unexpected_loss = standard_deviation(portfolio_losses)
var_95 = percentile(portfolio_losses, 95)
var_99 = percentile(portfolio_losses, 99)
expected_shortfall_95 = mean(losses >= var_95)
expected_shortfall_99 = mean(losses >= var_99)
avg_defaults = mean(default_counts)
max_defaults = max(default_counts)
max_loss = max(portfolio_losses)
```

Stored in:

- `scenario_results`
- `simulation_results`

## 22. Step 16 - Credit Recommendation

The decision engine loads:

- Latest `loss_estimates`
- Linked `pd_model_predictions`
- Linked `financial_ratios`
- Linked `trade_exposures`
- Latest relevant `scenario_results`
- Linked `simulation_results`

It writes to `credit_recommendations`.

## 23. Step 16A - Risk Grade

Risk grade is mapped from PD:

```text
PD < 1%      -> A
1% to 3%    -> BBB
3% to 7%    -> BB
7% to 15%   -> B
>= 15%      -> CCC
```

For:

```text
final_pd = 16.5%
```

The grade is:

```text
risk_grade = CCC
```

## 24. Step 16B - Policy Haircut

The credit engine builds a policy score and a limit haircut.

Examples of haircut rules:

### PD haircut

```text
PD >= 15%       -> +40% haircut, +4 score
7% <= PD < 15%  -> +28% haircut, +3 score
3% <= PD < 7%   -> +16% haircut, +2 score
1% <= PD < 3%   -> +7% haircut, +1 score
PD < 1%         -> mitigant
```

For this example:

```text
PD = 16.5% -> haircut += 0.40, score += 4
```

### LGD haircut

```text
LGD >= 70%       -> +18% haircut, +2 score
55% <= LGD < 70% -> +10% haircut, +1 score
LGD < 55%        -> mitigant
```

For:

```text
LGD = 21.2%
```

No LGD haircut; it is a mitigant because LC protects recovery.

### Market stress haircut

```text
stress >= 80 -> +15% haircut, +2 score
stress >= 65 -> +10% haircut, +1.5 score
stress < 40  -> mitigant
```

For:

```text
stress = 68
```

Then:

```text
haircut += 0.10
score += 1.5
```

### Liquidity haircut

```text
current_ratio < 1.0  -> +14% haircut, +2 score
current_ratio < 1.25 -> +7% haircut, +1 score
otherwise            -> mitigant
```

For:

```text
current_ratio = 1.50
```

Liquidity is a mitigant.

### Leverage and coverage haircut

```text
debt_to_ebitda > 4.0       -> +8% haircut, +1 score
interest_coverage < 2.0    -> +8% haircut, +1 score
```

For:

```text
debt_to_ebitda = 3.89
interest_coverage = 3.00
```

No haircut.

### Tenor haircut

```text
payment_tenor_days > 60 -> +8% haircut, +1 score
payment_tenor_days <= 30 -> mitigant
```

For:

```text
tenor = 45
```

No haircut.

### Scenario tail loss haircut

The engine calculates:

```text
scenario_loss_ratio = tail_loss / EAD
```

Where tail loss uses:

```text
expected_shortfall_95 if present,
else var_95,
else scenario_expected_loss
```

Rules:

```text
scenario_loss_ratio >= 25% -> +15% haircut, +2 score
scenario_loss_ratio >= 10% -> +8% haircut, +1 score
```

If:

```text
expected_shortfall_95 = 1,000,000
EAD = 5,600,000
scenario_loss_ratio = 17.9%
```

Then:

```text
haircut += 0.08
score += 1
```

### Model disagreement haircut

If structural PD and ML PD disagree materially:

```text
haircut += 0.05
score += 0.5
```

The model disagreement flag becomes true if:

```text
abs(structural_pd - ml_pd) >= 0.07
```

or the relative difference is large.

In this example:

```text
abs(0.060 - 0.360) = 0.300
```

So:

```text
model_disagreement = true
haircut += 0.05
score += 0.5
```

### Collateral adjustment

Strong collateral reduces policy pressure:

```text
collateral_strength >= 0.85 -> haircut -= 0.10, score -= 1
collateral_strength >= 0.60 -> haircut -= 0.05, score -= 0.5
weak unsecured + elevated LGD -> haircut += 0.07, score += 1
```

For:

```text
collateral_strength = 0.90
```

Then:

```text
haircut -= 0.10
score -= 1
```

### Example total haircut

Approximate example:

```text
PD haircut = +0.40
market stress haircut = +0.10
scenario loss haircut = +0.08
model disagreement haircut = +0.05
collateral benefit = -0.10
total haircut = 0.53
```

The code clips total haircut:

```text
0 <= haircut <= 0.90
```

So:

```text
limit_haircut = 53%
```

## 25. Step 16C - Recommended Credit Limit

Base limit priority:

```text
base_limit =
    requested_credit_limit
    else approved_credit_limit
    else EAD
```

For this example:

```text
base_limit = 10,000,000
```

Recommended limit:

```text
recommended_credit_limit = base_limit * (1 - limit_haircut)
                          = 10,000,000 * (1 - 0.53)
                          = 4,700,000
```

## 26. Step 16D - Recommended Tenor

Tenor policy:

```text
A and score <= 1.0      -> up to 90 days
BBB and score <= 2.5    -> up to 60 days
BB or score <= 4.0      -> up to 45 days
B or score <= 6.0       -> up to 30 days
otherwise               -> 0 days
```

Because:

```text
risk_grade = CCC
```

The engine is likely to recommend:

```text
recommended_tenor_days = 0
```

Meaning:

- Prepayment or fully secured structure is required.

## 27. Step 16E - Recommended Security

Security policy:

```text
CCC or score > 6 -> Prepayment or Confirmed LC
B or PD >= 7% -> Standby LC or Bank Guarantee
LGD >= 60% and weak collateral -> Bank Guarantee or Partial Cash Deposit
BB -> Corporate Guarantee or Partial Deposit
strong collateral -> Existing collateral acceptable
otherwise -> Open Credit with monitoring covenants
```

For:

```text
risk_grade = CCC
```

Recommendation:

```text
recommended_security = Prepayment or Confirmed LC
```

## 28. Step 16F - Approval Status

Approval status rules:

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

For:

```text
risk_grade = CCC
```

Final status:

```text
approval_status = REJECT / PREPAYMENT ONLY
```

Important nuance:

- The recommended limit calculation may still produce a nonzero mathematical amount, but the approval status can still be reject/prepayment-only because the grade is too weak.

## 29. Step 17 - AI Credit Memo

The AI memo layer reads the stored recommendation and model references.

It does not calculate PD, LGD, EAD, VaR, or limits itself.

The memo includes:

- Counterparty
- Approval status
- Risk grade
- Recommended limit
- Recommended tenor
- Recommended security
- PD, LGD, EAD, expected loss
- Scenario expected loss
- VaR and expected shortfall if available
- Risk drivers
- Mitigating factors
- Warnings and data gaps
- Audit references to source model rows

The memo is stored in `ai_credit_memos`.

Grounding rule:

```text
If stored data is missing, the memo says it is missing.
It does not invent numerical claims.
```

## 30. Final Synthetic Output Summary

For the synthetic example, the system might produce:

```text
Counterparty: Synthetic Airways Ltd
Type: Airline
Requested limit: 10,000,000
Tenor requested: 45 days
Security offered: Standby LC

Current ratio: 1.50
Debt/EBITDA: 3.89x
Interest coverage: 3.00x
Liabilities/assets: 66.67%

Market stress: 68.0 / Stressed
Regime: Commodity Stress

Structural PD: 6.0%
ML proxy PD: 36.0%
Final PD: 16.5%
Internal grade: CCC

LGD: 21.2%
EAD: 5,600,000
Expected loss: 195,888

Adverse scenario expected loss: about 281,200
Expected Shortfall 95: from Monte Carlo simulation

Recommended limit: about 4,700,000 by haircut math
Recommended tenor: 0 days
Recommended security: Prepayment or Confirmed LC
Approval status: REJECT / PREPAYMENT ONLY
```

## 31. How to Explain the Whole Flow in an Interview

Use this answer:

"I built the system as an auditable credit risk pipeline. A counterparty starts with either a PDF upload or manual financial entry. The financial statement line items are stored first, then deterministic ratios are calculated. Separately, market prices such as Brent, jet fuel proxy, VIX, S&P 500, DXY, rates, CPI, and freight are transformed into z-scored stress components. PCA compresses those components into a single 0-100 stress index, and clustering assigns a market regime. The PD model then combines company financials with this market context. The structural Merton side estimates distance-to-default from asset value, debt threshold, asset volatility, risk-free rate, and time horizon. The ML/logistic proxy uses leverage, liquidity, margins, stress, and vulnerability scores as a cross-check. The final PD is a weighted blend, with distress floors for insolvency signals.

After PD, the trade exposure module calculates LGD from collateral, tenor, country risk, seniority, and liquidity. EAD is based on outstanding receivables plus expected drawdown, capped by credit limit. Expected loss is PD times LGD times EAD. The scenario engine creates historical quantile shocks from market data, and Monte Carlo simulates default events using a copula, producing VaR and expected shortfall. Finally, the credit decision engine applies transparent policy haircuts to recommend limit, tenor, security, risk grade, and approval status. AI only summarizes the stored outputs and references the source model IDs, so the project remains explainable and auditable."

