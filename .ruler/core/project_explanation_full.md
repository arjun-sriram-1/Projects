# PROJECT_BUILD_PLAN.md

# AI-Augmented Trade Finance Credit Risk Agent
## Full Phase-by-Phase Build Manual

---

## Project Mission

Build an AI-augmented quantitative credit risk platform for fuel suppliers evaluating airlines, shipowners, fuel distributors, or fuel resellers that buy jet fuel or marine fuel on credit terms.

The system answers:

```text
Can we safely extend trade credit?

If yes:
- How much credit limit?
- What payment tenor?
- What collateral/security?
- What risk grade?
- What are the key risks?
- What happens under normal, adverse, and stress market conditions?
```

AI is only an accelerator.  
The final recommendation must come from financial data, market data, risk models, and scenario analysis.

---

## Current Implementation Checkpoint

The codebase now implements the main backend decision chain through the formal
credit recommendation layer:

```text
PDF extraction
-> financial ratios
-> market data and stress/regime analytics
-> PD
-> LGD/EAD/Expected Loss
-> historical PD/LGD training runs and validation outputs
-> data-driven scenarios
-> Monte Carlo simulation
-> credit_recommendations
-> grounded credit memo
```

Important current truth:

- The formal recommendation is stored in `credit_recommendations`.
- The AI memo reads stored recommendation/model outputs only.
- Scenario shocks are generated from historical quantiles, not hardcoded oil/FX assumptions.
- Market ingestion now supports yfinance plus FRED, EIA, and Alpha Vantage.
  Provider rows are stored with `data_source` and `source_id`, and macro rows
  are mirrored into `macro_indicators`.
- Historical PD/LGD training is implemented with auditable `historical_training_dataset`,
  `model_training_runs`, and `model_validation_results` tables.
- Current ML labels are transparent proxy labels; real default/recovery data
  should replace them if available.
- ARIMA/VAR/GARCH commodity forecasting remains a planned or optional extension, not a completed production module.
- Dashboard polish and final project packaging still need work after the backend is stable.

---

# MASTER SYSTEM WORKFLOW

```text
PDF / Financial Data
        ↓
Financial Extraction
        ↓
Financial Ratios
        ↓
Counterparty Risk Profile
        ↓
Market + Macro + Commodity Data
        ↓
Market Features
        ↓
Geopolitical / Macro Stress Index
        ↓
Market Regime Detection
        ↓
Commodity / FX Forecasting
        ↓
Merton PD + ML PD
        ↓
LGD Model
        ↓
EAD Engine
        ↓
Data-Driven Scenarios
        ↓
Monte Carlo Portfolio Simulation
        ↓
Credit Limit / Tenor / Collateral Recommendation
        ↓
AI Credit Memo + Risk Copilot
        ↓
Dashboard + Reports
```

---

# PHASE 0 — PROJECT FOUNDATION

## Goal

Create clean project structure, database foundation, environment setup, and common rules.

## Build

```text
folders
database schema
config files
logging
environment variables
utility functions
```

## Recommended Structure

```text
fuel-credit-risk-agent/

├── api/
├── dashboard/
├── database/
├── ingestion/
├── analytics/
├── models/
│   ├── credit/
│   ├── market/
│   └── portfolio/
├── decision_engine/
├── rag_agent/
├── reports/
├── tests/
├── data/
│   ├── raw/
│   ├── processed/
│   └── sample/
├── docs/
├── notebooks/
├── requirements.txt
├── docker-compose.yml
├── AGENTS.md
├── PROJECT_BUILD_PLAN.md
└── README.md
```

## Core Rules

```text
Do not put modelling logic inside API routes.

Do not hardcode scenarios.

Do not let AI invent numbers.

Every model output must be stored with:
- run_id
- model_name
- model_version
- created_at
- assumptions
- input_reference

Every synthetic dataset must be clearly marked synthetic.
```

## Main Database Tables

```text
counterparties_master
uploaded_documents
extracted_financials
financial_ratios
trade_exposures
market_prices
market_features
macro_indicators
geopolitical_stress_index
market_regimes
model_predictions
scenario_results
simulation_results
credit_recommendations
ai_credit_memos
audit_logs
```

---

# PHASE 1 — COUNTERPARTY MASTER DATA

## Feature 1: Counterparty Master Profile

### Purpose

Store basic information about the company being analyzed.

### Audience

```text
Credit analyst
Trade finance manager
Risk manager
```

### Inputs

```text
counterparty_name
counterparty_type
country
industry
currency
listed_or_private
fleet_size
business_model
```

### Counterparty Types

```text
Airline
Shipowner
Marine fuel buyer
Fuel distributor
Fuel reseller
Commodity trader
```

### Output

Stored in:

```text
counterparties_master
```

### How It Connects

Counterparty type controls:

```text
which market factors matter
which sensitivity model is used
which scenario impacts apply
which credit policy rules apply
```

Example:

```text
Airline → jet fuel sensitivity
Shipowner → marine fuel + Baltic Dry sensitivity
Fuel reseller → inventory + receivables sensitivity
```

### Build Rules

```text
Each counterparty must have a unique counterparty_id.

counterparty_type must be standardized.

Do not use free-text types everywhere.

Use enums or controlled values.
```

---

# PHASE 2 — DOCUMENT INGESTION AND FINANCIAL EXTRACTION

## Feature 2: PDF Upload

### Purpose

Allow user to upload annual reports, balance sheets, income statements, or financial PDFs.

### Inputs

```text
PDF file
counterparty_id
document_type
fiscal_year
currency
```

### Output

Stored in:

```text
uploaded_documents
```

### Required Metadata

```text
document_id
counterparty_id
file_name
file_path
document_type
upload_date
fiscal_year
currency
extraction_status
```

### Rules

```text
Never overwrite original file.

Store original document in S3 or local data/raw during development.

Every extracted number must reference document_id.
```

---

## Feature 3: Financial Statement Extractor

### Purpose

Extract structured financial values from uploaded PDF.

### Required Extracted Fields

```text
revenue
EBITDA
EBIT
net_income
cash
current_assets
total_assets
current_liabilities
total_liabilities
total_debt
equity
interest_expense
operating_cash_flow
accounts_receivable
accounts_payable
inventory
```

### Output Table

```text
extracted_financials
```

### Why Required

This is the foundation of credit analysis.

Without financial data, the system cannot calculate:

```text
liquidity
leverage
profitability
solvency
debt servicing ability
```

### Build Approach

Use layered extraction:

```text
1. PDF text extraction
2. Table extraction
3. Regex / keyword matching
4. LLM-assisted extraction if needed
5. Validation checks
```

### Rules

```text
Do not accept extracted numbers silently.

Each extracted field must include:
- value
- unit
- currency
- fiscal_year
- source_document_id
- confidence_score

If confidence is low, flag for user review.

Do not hallucinate missing values.
```

### Example

```text
Revenue: 1,200,000,000
Debt: 650,000,000
Cash: 90,000,000
EBITDA: 140,000,000
```

---

# PHASE 3 — FINANCIAL RATIO ENGINE

## Feature 4: Liquidity Ratios

### Purpose

Measure ability to meet short-term obligations.

### Inputs

```text
cash
current_assets
current_liabilities
accounts_receivable
inventory
```

### Models / Formulas

```text
current_ratio = current_assets / current_liabilities

quick_ratio = (cash + accounts_receivable) / current_liabilities

cash_ratio = cash / current_liabilities

working_capital = current_assets - current_liabilities
```

### Output

Stored in:

```text
financial_ratios
```

### Business Meaning

```text
Low liquidity → higher payment risk → higher PD
```

### Rules

```text
If denominator is zero, return null and warning.

Do not replace missing values with zero.

Store formula_version.
```

---

## Feature 5: Leverage Ratios

### Purpose

Measure debt burden and solvency risk.

### Inputs

```text
total_debt
equity
EBITDA
total_assets
total_liabilities
```

### Formulas

```text
debt_to_equity = total_debt / equity

debt_to_ebitda = total_debt / EBITDA

liabilities_to_assets = total_liabilities / total_assets
```

### Business Meaning

```text
Higher leverage → smaller solvency cushion → higher PD
```

### Correlation

```text
Debt ↑ → Distance to Default ↓ → PD ↑
Debt/EBITDA ↑ → repayment capacity ↓ → PD ↑
```

---

## Feature 6: Coverage Ratios

### Purpose

Measure ability to service debt.

### Inputs

```text
EBIT
interest_expense
```

### Formula

```text
interest_coverage = EBIT / interest_expense
```

### Business Meaning

```text
Low coverage means operating profit barely covers interest.
```

### Correlation

```text
Interest coverage ↓ → debt service stress ↑ → PD ↑
Rates ↑ → interest expense ↑ → interest coverage ↓
```

---

## Feature 7: Profitability Ratios

### Purpose

Measure operating strength and business sustainability.

### Inputs

```text
revenue
EBIT
net_income
total_assets
equity
```

### Formulas

```text
operating_margin = EBIT / revenue

net_margin = net_income / revenue

ROA = net_income / total_assets

ROE = net_income / equity
```

### Business Meaning

```text
Lower margins → weaker internal cash generation → higher credit risk
```

---

# PHASE 4 — TRADE EXPOSURE ENGINE

## Feature 8: Trade Exposure Capture

### Purpose

Capture transaction-level credit exposure.

### Inputs

```text
invoice_amount
fuel_volume
fuel_price
requested_credit_limit
approved_credit_limit
payment_tenor_days
outstanding_receivables
collateral_type
letter_of_credit_flag
guarantee_flag
deposit_percentage
```

### Output Table

```text
trade_exposures
```

### Business Meaning

Fuel sold today but paid later creates credit exposure.

### Rules

```text
Longer tenor means more unpaid invoices accumulate.

Higher fuel price means higher invoice amount.

Collateral reduces LGD.

Credit limit caps EAD.
```

---

## Feature 9: EAD Engine

### Purpose

Calculate Exposure at Default.

### Formula

```text
EAD = unpaid_invoices + delivered_unbilled_fuel + expected_future_drawdown
```

Simplified:

```text
EAD = min(approved_credit_limit, outstanding_receivables + expected_drawdown)
```

### Inputs

```text
approved_credit_limit
outstanding_receivables
payment_tenor_days
fuel_volume
fuel_price
utilization_rate
```

### Output

```text
exposure_at_default
```

### Correlation

```text
Fuel price ↑ → invoice value ↑ → EAD ↑
Tenor ↑ → receivables ↑ → EAD ↑
Credit limit ↑ → maximum EAD ↑
```

---

# PHASE 5 — MARKET DATA INGESTION

## Feature 10: Commodity Market Data

### Purpose

Bring real commodity risk into the credit model.

### Data Required

```text
Brent crude
WTI crude
jet fuel proxy
marine fuel proxy
heating oil proxy
natural gas
```

### Free Sources

```text
Yahoo Finance / yfinance
EIA
FRED
```

### Output Table

```text
market_prices
```

### Required Columns

```text
date
asset_name
ticker
price
currency
data_source
```

### Why Important

```text
Fuel buyers are exposed to commodity prices.
```

### Correlation

```text
Brent ↑ → jet fuel ↑ → airline costs ↑ → airline PD ↑

Brent ↑ → marine fuel ↑ → shipping cost ↑ → shipping PD may ↑

Natural gas ↑ → energy system stress ↑
```

---

## Feature 11: Macro and Market Indicator Data

### Purpose

Capture broader market environment.

### Data Required

```text
S&P 500
VIX
DXY / USD proxy
US 2Y yield
US 10Y yield
yield curve spread
gold
CPI
PPI
PMI
Baltic Dry Index
freight proxy
```

### Output Tables

```text
market_prices
macro_indicators
```

### Why Important

These indicators capture:

```text
risk appetite
inflation
rates
recession risk
trade activity
geopolitical stress
```

### Correlations

```text
VIX ↑ → market fear ↑ → funding stress ↑ → PD ↑

S&P 500 ↓ → risk appetite ↓ → stress ↑

DXY ↑ → USD strengthens → commodity import cost ↑ → PD ↑

US yields ↑ → borrowing cost ↑ → interest coverage ↓ → PD ↑

Baltic Dry ↓ → shipping revenue ↓ → shipping PD ↑

Gold ↑ + VIX ↑ → risk-off/geopolitical stress ↑
```

---

# PHASE 6 — MARKET FEATURE ENGINEERING

## Feature 12: Market Feature Builder

### Purpose

Convert raw prices into useful quantitative features.

### Inputs

```text
market_prices
macro_indicators
```

### Features

For each time series:

```text
log_return = ln(price_t / price_t-1)

rolling_volatility_30d = std(log_return, 30 days)

momentum_30d = price_t / price_t-30 - 1

drawdown = price_t / rolling_max - 1

z_score = (value - historical_mean) / historical_std
```

### Output Table

```text
market_features
```

### Required Features

```text
brent_return
brent_volatility
wti_return
wti_volatility
jet_fuel_proxy_return
marine_fuel_proxy_return
vix_level
vix_change
sp500_return
dxy_return
gold_return
yield_10y_change
yield_curve_spread
baltic_dry_return
inflation_change
pmi_change
```

### Rules

```text
Do not use raw prices directly for PCA or clustering.

Always normalize features before PCA, KMeans, GMM, or HMM.

Handle missing dates by alignment and interpolation only when justified.
```

---

# PHASE 7 — GEOPOLITICAL / MACRO STRESS INDEX

## Feature 13: Stress Index Builder

### Purpose

Create one interpretable index that summarizes broad market/geopolitical stress.

### Inputs

```text
VIX z-score
oil volatility z-score
S&P 500 return z-score
DXY return z-score
gold return z-score
yield change z-score
yield curve z-score
Baltic Dry return z-score
inflation z-score
PMI z-score
```

### Model

```text
PCA
```

### What PCA Does

PCA finds the common hidden factor driving many correlated indicators.

In this project:

```text
Many stress indicators
        ↓
PCA
        ↓
PC1 = systemic stress factor
        ↓
Scaled to 0–100 stress index
```

### Output Table

```text
geopolitical_stress_index
```

### Required Outputs

```text
date
stress_index
pc1_score
explained_variance_ratio
top_positive_drivers
top_negative_drivers
```

### Rules

```text
Higher stress_index must mean higher market/geopolitical stress.

If PC1 has opposite sign, multiply PC1 by -1.

Always store PCA loadings.

Do not manually invent stress scores.
```

### Interpretation

```text
0-20   Calm
20-40  Normal
40-60  Elevated
60-80  Stressed
80-100 Crisis
```

### Correlation Logic

```text
VIX ↑ → stress index ↑
S&P 500 ↓ → stress index ↑
DXY ↑ → stress index ↑
Oil volatility ↑ → stress index ↑
Gold ↑ → stress index ↑
Baltic Dry ↓ → stress index ↑
```

---

# PHASE 8 — MARKET REGIME DETECTION

## Feature 14: Regime Detection Engine

### Purpose

Detect what type of market environment currently exists.

### Inputs

```text
brent_return
brent_volatility
vix_level
sp500_return
dxy_return
yield_curve_spread
baltic_dry_return
stress_index
```

### Models

Use one or more:

```text
KMeans
Gaussian Mixture Model
Hidden Markov Model
```

### Output Table

```text
market_regimes
```

### Possible Labels

Labels are assigned after model analysis:

```text
Stable Market
Normal Volatility
Commodity Stress
USD Stress
Risk-Off
Crisis
```

### Rules

```text
Do not hardcode labels before training.

Cluster first, then interpret the cluster.

Regime detection must use historical data.

Store regime_id, regime_label, and confidence.
```

### How It Connects

Regime drives:

```text
scenario generation
risk haircuts
market forecast assumptions
credit decision strictness
```

Example:

```text
Stable regime → normal terms possible
Risk-off regime → shorter tenor or collateral
Commodity stress regime → fuel-sensitive counterparties penalized
```

---

# PHASE 9 — COMMODITY FORECASTING ENGINE

## Feature 15: ARIMA Forecast

### Purpose

Simple baseline forecast for one market variable.

### Inputs

```text
Brent price history
WTI price history
jet fuel proxy history
```

### Output

```text
forecast_price
forecast_error
confidence_interval
```

### Rule

```text
Forecast is probabilistic, not guaranteed.
```

---

## Feature 16: VAR Forecast

### Purpose

Model relationships between multiple market variables.

### Inputs

```text
Brent
DXY
VIX
S&P 500
Baltic Dry
US 10Y
```

### Why VAR

Commodity markets do not move alone.

Example:

```text
DXY ↑ can pressure commodity demand
VIX ↑ can increase volatility
Oil ↑ can increase inflation expectations
Baltic Dry ↓ can indicate trade slowdown
```

### Output

```text
multi_factor_forecast
```

---

## Feature 17: GARCH Volatility Model

### Purpose

Forecast volatility.

### Why Needed

Commodity markets have volatility clustering:

```text
high volatility tends to follow high volatility
low volatility tends to follow low volatility
```

### Inputs

```text
Brent returns
WTI returns
FX returns
```

### Output

```text
forecast_volatility
volatility_regime
```

### How It Connects

```text
forecast_volatility ↑ → asset volatility ↑ → Merton PD ↑
forecast_volatility ↑ → scenario range wider
forecast_volatility ↑ → credit terms tighter
```

---

# PHASE 10 — COUNTERPARTY VULNERABILITY ENGINE

## Feature 18: Commodity Sensitivity Score

### Purpose

Measure how exposed the counterparty is to fuel/commodity movements.

### Inputs

```text
counterparty_type
fuel_cost_ratio
commodity_price_changes
financial ratios
industry proxy assumptions
```

### Output

```text
commodity_sensitivity_score
```

### Rules

```text
Airlines should be highly sensitive to jet fuel.

Shipping firms should be sensitive to marine fuel and freight rates.

Fuel resellers should be sensitive to fuel price volatility, receivables, and inventory risk.
```

### Correlations

Airline:

```text
Jet fuel ↑ → cost ↑ → margin ↓ → PD ↑
```

Shipping:

```text
Marine fuel ↑ → voyage cost ↑
Baltic Dry ↓ → revenue ↓
Both together → PD ↑
```

Fuel reseller:

```text
Fuel volatility ↑ → margin/inventory risk ↑ → PD ↑
```

---

## Feature 19: FX Sensitivity Score

### Purpose

Measure sensitivity to USD strength.

### Inputs

```text
local_currency
USD debt
USD fuel purchases
DXY changes
FX pair changes
```

### Output

```text
fx_sensitivity_score
```

### Correlation

```text
USD ↑ → USD-priced fuel cost ↑ for non-USD counterparty → liquidity pressure ↑ → PD ↑
```

---

## Feature 20: Macro Sensitivity Score

### Purpose

Measure sensitivity to macro conditions.

### Inputs

```text
interest rates
GDP proxy
PMI
inflation
yield curve
```

### Output

```text
macro_sensitivity_score
```

### Correlation

```text
Rates ↑ → debt service cost ↑ → interest coverage ↓ → PD ↑

PMI ↓ → demand ↓ → revenue pressure ↑ → PD ↑
```

---

# PHASE 11 — STRUCTURAL CREDIT MODEL

## Feature 21: Merton PD Model

### Purpose

Estimate structural probability of default.

### Core Idea

A firm defaults if:

```text
Asset Value < Debt Threshold
```

### Inputs

```text
asset_value_proxy
debt_threshold
asset_volatility
risk_free_rate
time_horizon
```

### Outputs

```text
distance_to_default
structural_pd
```

### Business Meaning

```text
Distance to Default measures how far the firm is from insolvency.
```

### Rules

```text
Debt ↑ → PD ↑

Asset value ↑ → PD ↓

Asset volatility ↑ → PD ↑

Time horizon ↑ → uncertainty ↑
```

### How Market Data Connects

```text
Brent ↑ for airline → margins ↓ → asset value proxy ↓ → PD ↑

VIX ↑ → volatility ↑ → asset volatility ↑ → PD ↑

Rates ↑ → debt servicing pressure ↑ → PD ↑
```

### Output Table

```text
model_predictions
```

---

# PHASE 12 — ML PD MODEL

## Feature 22: Logistic Regression PD Model

### Purpose

Create a data-driven PD cross-check.

### Inputs

```text
current_ratio
quick_ratio
debt_to_equity
debt_to_ebitda
interest_coverage
operating_margin
cash_ratio
market_stress_index
commodity_sensitivity_score
fx_sensitivity_score
macro_sensitivity_score
country_risk_score
payment_delay_history
```

### Output

```text
ml_pd
default_label
model_confidence
feature_importance
```

### Rules

```text
ML PD is not the only source of truth.

Compare ML PD with Merton PD.

If difference is large, flag model_disagreement.
```

### Example

```text
Merton PD = 4%
ML PD = 12%

Flag: model disagreement
```

---

# PHASE 13 — LGD MODEL

## Feature 23: Random Forest LGD Model

### Purpose

Predict loss severity if default occurs.

### Inputs

```text
letter_of_credit_flag
guarantee_flag
deposit_percentage
collateral_strength
country_risk_score
counterparty_type
liquidity_score
exposure_size
seniority_score
payment_tenor_days
```

### Output

```text
predicted_lgd
```

### Rules

```text
0 <= LGD <= 1

LC present → LGD ↓

Guarantee present → LGD ↓

Deposit higher → LGD ↓

Unsecured exposure → LGD ↑

Weak legal/country environment → LGD ↑
```

### Why Random Forest

```text
Handles nonlinear relationships.
Works well with mixed features.
Easy to explain using feature importance.
```

---

# PHASE 14 — EXPECTED LOSS ENGINE

## Feature 24: Expected Loss Calculator

### Purpose

Calculate average expected credit loss.

### Formula

```text
EL = PD × LGD × EAD
```

### Inputs

```text
PD
LGD
EAD
```

### Output

```text
expected_loss
```

### Rules

```text
PD and LGD must be decimals between 0 and 1.

EAD must be currency amount.

Do not confuse EL with worst-case loss.
```

### Example

```text
PD = 0.05
LGD = 0.60
EAD = 10,000,000

EL = 300,000
```

---

# PHASE 15 — DATA-DRIVEN SCENARIO ENGINE

## Feature 25: Scenario Generator

### Purpose

Generate normal, adverse, severe, and tail scenarios from historical data.

### Inputs

```text
market_features
market_regimes
commodity_forecasts
volatility_forecasts
```

### Scenario Types

```text
Base Case
Normal Volatility Case
Adverse Case
Severe Downside Case
Tail Case
```

### Generation Logic

For each regime:

```text
Base Case = median historical movement
Normal Volatility = 25th to 75th percentile
Adverse Case = 10th percentile
Severe Downside = 5th percentile
Tail Case = 1st percentile
```

### Required Scenario Variables

```text
brent_change
jet_fuel_change
marine_fuel_change
dxy_change
vix_change
sp500_change
yield_change
baltic_dry_change
stress_index_change
```

### Rules

```text
Never hardcode oil +20% or FX +10%.

All scenario numbers must come from historical distributions, regimes, or forecasts.

Store scenario_source and quantile_used.
```

### How It Connects

Each scenario recalculates:

```text
PD
LGD
EAD
Expected Loss
Credit Limit
Tenor
Collateral
```

---

# PHASE 16 — SCENARIO IMPACT ENGINE

## Feature 26: Scenario Impact on Counterparty

### Purpose

Translate market scenario into counterparty financial stress.

### Inputs

```text
scenario variables
counterparty_type
commodity_sensitivity_score
fx_sensitivity_score
macro_sensitivity_score
financial ratios
```

### Output

```text
stressed_financials
stressed_pd
stressed_lgd
stressed_ead
stressed_expected_loss
```

### Example for Airline

```text
Brent +15%
Jet fuel +18%
DXY +5%
VIX +30%

Effect:
fuel cost ↑
margin ↓
cash flow ↓
asset value proxy ↓
asset volatility ↑
PD ↑
```

### Example for Shipping

```text
BDI -20%
Marine fuel +12%

Effect:
revenue ↓
voyage cost ↑
cash flow ↓
PD ↑
```

---

# PHASE 17 — MONTE CARLO SIMULATION ENGINE

## Feature 27: Monte Carlo Loss Simulation

### Purpose

Simulate thousands of possible future credit outcomes.

### Inputs

```text
PD
LGD
EAD
correlations
market scenario
asset volatility
number_of_simulations
```

### Simulated Variables

```text
commodity prices
FX
stress index
asset value
default event
LGD
EAD
loss
```

### Outputs

```text
loss_distribution
expected_loss
unexpected_loss
credit_var_95
credit_var_99
expected_shortfall_95
expected_shortfall_99
```

### Rules

```text
Store simulation count.

Store random seed.

VaR should generally be >= Expected Loss.

Expected Shortfall should generally be >= VaR.

Simulation must be reproducible.
```

---

# PHASE 18 — COPULA PORTFOLIO DEFAULT MODEL

## Feature 28: Default Correlation Engine

### Purpose

Model correlated defaults across counterparties.

### Why Needed

Counterparties do not default independently.

Example:

```text
Oil spike → multiple airlines weaken together

Trade slowdown → multiple shipping firms weaken together
```

### Models

```text
Gaussian Copula
t-Copula
```

### Inputs

```text
individual PDs
correlation matrix
systematic factor
idiosyncratic factor
```

### Output

```text
joint_default_scenarios
portfolio_loss_distribution
```

### Rules

```text
Use copula only for portfolio dependence.

Do not use copula for single-name PD.

t-Copula is better for tail dependence.
```

---

# PHASE 19 — PORTFOLIO RISK ENGINE

## Feature 29: Portfolio Risk Metrics

### Purpose

Measure total portfolio credit risk.

### Inputs

```text
counterparty PD
LGD
EAD
default correlation
Monte Carlo losses
```

### Outputs

```text
portfolio_expected_loss
unexpected_loss
credit_var
expected_shortfall
marginal_risk_contribution
concentration_risk
```

### Business Meaning

```text
Expected Loss = average loss

VaR = bad but plausible loss threshold

Expected Shortfall = average loss beyond VaR

Marginal Risk Contribution = which counterparty contributes most to portfolio risk
```

---

# PHASE 20 — CREDIT DECISION ENGINE

## Feature 30: Credit Limit Recommendation

### Purpose

Recommend safe credit limit.

### Inputs

```text
requested_credit_limit
PD
LGD
EAD
Expected Loss
stress_index
market_regime
scenario_results
financial_ratios
collateral
```

### Output

```text
recommended_credit_limit
```

### Logic

```text
base_limit = requested_credit_limit

risk_haircut = function(
    PD,
    LGD,
    stress_index,
    weak_liquidity,
    high_leverage,
    no_collateral,
    severe_scenario_loss
)

recommended_limit = base_limit × (1 - risk_haircut)
```

### Rules

```text
Higher PD → lower limit

Higher LGD → lower limit

Higher stress index → lower limit

Weak liquidity → lower limit

Strong collateral → less haircut
```

---

## Feature 31: Payment Tenor Recommendation

### Purpose

Recommend payment period.

### Possible Outputs

```text
Prepayment
7 days
15 days
30 days
45 days
60 days
90 days
```

### Logic

```text
Strong counterparty + stable regime → longer tenor

Medium risk → 30-45 days

High risk → 7-30 days or secured

Very high risk → prepayment or LC only
```

### Rules

```text
Longer tenor increases EAD.

Longer tenor increases probability conditions change before payment.

High stress regime should shorten tenor.
```

---

## Feature 32: Collateral Recommendation

### Purpose

Recommend security.

### Possible Outputs

```text
Open Credit
Partial Deposit
Corporate Guarantee
Bank Guarantee
Standby LC
Confirmed LC
Prepayment
```

### Logic

```text
Low PD + low LGD → open credit possible

Medium PD or LGD → guarantee/deposit

High PD or high LGD → LC required

Very high risk → prepayment
```

### Rules

```text
Security reduces LGD.

Deposit reduces EAD and LGD.

LC should materially reduce predicted LGD.
```

---

## Feature 33: Risk Grade Mapping

### Purpose

Assign internal risk grade.

### Example Mapping

```text
PD < 1%          → A
1% <= PD < 3%    → BBB
3% <= PD < 7%    → BB
7% <= PD < 15%   → B
PD >= 15%        → CCC / Secured Only
```

### Rules

```text
This is internal proxy grade only.

Do not claim official agency rating.

Store rating methodology.
```

---

# PHASE 21 — EARLY WARNING SYSTEM

## Feature 34: Early Warning Indicators

### Purpose

Detect deterioration before default.

### Inputs

```text
financial ratios over time
payment delays
stress index
market regime
commodity sensitivity
news/event risk
```

### Models

```text
threshold rules
z-score alerts
Isolation Forest
```

### Outputs

```text
alert_level
alert_reason
recommended_action
```

### Example Alerts

```text
Interest coverage below 1.5x

Current ratio below 1

Stress index above 70

Payment delay increasing

PD increased by more than 30%
```

### Rules

```text
Alerts must include reason.

Do not create unexplained alerts.
```

---

# PHASE 22 — AI CREDIT ANALYST

## Feature 35: Credit Memo Generator

### Purpose

Generate professional credit memo.

### Inputs

```text
counterparty profile
financial ratios
PD
LGD
EAD
scenario results
credit recommendation
risk drivers
source documents
```

### Output

```text
credit memo
```

### Memo Sections

```text
1. Executive Summary
2. Counterparty Overview
3. Financial Analysis
4. Market and Commodity Exposure
5. Credit Risk Assessment
6. Scenario Analysis
7. Recommendation
8. Key Risks
9. Monitoring Triggers
```

### Rules

```text
AI must not invent numbers.

All numerical claims must come from database/model outputs.

If data is missing, say missing.
```

---

## Feature 36: Risk Copilot

### Purpose

Allow user to ask questions.

### Example Questions

```text
Why is PD high?

Why was tenor reduced?

What happens if Brent rises?

Why is LC required?

Which factor contributes most to expected loss?
```

### Required Tools

```text
SQL retrieval
document retrieval
model output retrieval
scenario retrieval
```

### Rules

```text
AI explains, does not decide.

Every answer must be grounded in stored data.

If answer requires unavailable data, say so.
```

---

# PHASE 23 — DASHBOARD UI

## Page 1: Home / Portfolio Overview

### Purpose

Show overall risk position.

### Components

```text
Total EAD
Portfolio Expected Loss
Credit VaR
Expected Shortfall
Number of Counterparties
High Risk Counterparties
Current Market Regime
Stress Index
```

### Charts

```text
Portfolio loss distribution
Top 10 counterparties by EAD
Top 10 by Expected Loss
Risk grade distribution
```

---

## Page 2: Counterparty Overview

### Components

```text
Company name
Counterparty type
Country
Industry
Risk grade
PD
LGD
EAD
Expected Loss
Recommended limit
Recommended tenor
Recommended security
```

### Purpose

One-page credit snapshot.

---

## Page 3: Financial Analysis

### Components

```text
Revenue
EBITDA
Debt
Cash
Current Ratio
Debt/EBITDA
Interest Coverage
Margins
```

### Charts

```text
Financial trend chart
Ratio comparison
Liquidity and leverage dashboard
```

---

## Page 4: Market Intelligence

### Components

```text
Brent chart
VIX chart
DXY chart
S&P 500 chart
Baltic Dry chart
Yield curve chart
```

### Purpose

Show current external environment.

---

## Page 5: Geopolitical Stress Dashboard

### Components

```text
Stress index gauge
Top stress drivers
PCA loadings
Current regime
Historical stress trend
```

### Purpose

Explain why environment is calm/stressed.

---

## Page 6: Scenario Analysis

### Table Columns

```text
Scenario
Brent Change
DXY Change
VIX Change
BDI Change
PD
LGD
EAD
Expected Loss
Recommended Limit
Recommended Tenor
```

### Purpose

Compare base, normal, adverse, severe, and tail outcomes.

---

## Page 7: Monte Carlo Risk

### Components

```text
Loss distribution histogram
VaR marker
Expected Shortfall marker
Simulation summary
Percentile table
```

---

## Page 8: Credit Recommendation

### Components

```text
Approval status
Recommended limit
Recommended tenor
Recommended security
Risk grade
Top risk drivers
Decision explanation
```

---

## Page 9: AI Credit Analyst

### Components

```text
Chat window
Generated credit memo
Source citations
Scenario Q&A
```

---

# PHASE 24 — API DESIGN

## Required API Groups

```text
/counterparties
/documents
/financials
/ratios
/market-data
/stress-index
/regimes
/models/pd
/models/lgd
/models/ead
/scenarios
/simulations
/recommendations
/ai/memo
/ai/chat
```

### API Rules

```text
API routes should not contain model logic.

Routes call service functions.

Return clean JSON.

Include errors and warnings.
```

---

# PHASE 25 — TESTING RULES

## Required Tests

```text
test_financial_ratios.py
test_market_features.py
test_pca_stress_index.py
test_regime_detection.py
test_merton_model.py
test_lgd_model.py
test_ead_engine.py
test_expected_loss.py
test_scenario_generator.py
test_monte_carlo.py
test_credit_recommendation.py
test_ai_grounding.py
```

---

## Sanity Tests

```text
Debt ↑ → PD ↑

Asset volatility ↑ → PD ↑

Asset value ↑ → PD ↓

Collateral ↑ → LGD ↓

Tenor ↑ → EAD ↑

VIX ↑ → stress index ↑

S&P ↓ → stress index ↑

BDI ↓ → shipping risk ↑

Jet fuel ↑ → airline risk ↑

Expected Shortfall >= VaR

VaR >= Expected Loss generally
```

---

# PHASE 26 — DOCUMENTATION DELIVERABLES

## Required Docs

```text
README.md
PROJECT_BUILD_PLAN.md
QUANT_MODEL_RULES.md
BUSINESS_KNOWLEDGE.md
DATA_DICTIONARY.md
MODEL_ASSUMPTIONS.md
MODEL_VALIDATION_REPORT.md
CREDIT_POLICY.md
```

---

# FINAL BUILD ORDER

## Sprint 1

```text
Project structure
Database schema
Counterparty master
Trade exposure table
Financial ratio engine
```

## Sprint 2

```text
PDF upload
Financial extraction
Financial validation
Financial dashboard
```

## Sprint 3

```text
Market data ingestion
Market feature builder
Commodity dashboard
```

## Sprint 4

```text
PCA stress index
Regime detection
Market regime dashboard
```

## Sprint 5

```text
Merton PD
ML PD
LGD model
EAD engine
Expected Loss
```

## Sprint 6

```text
Scenario generator
Scenario impact engine
Monte Carlo simulation
Portfolio risk metrics
```

## Sprint 7

```text
Credit limit engine
Tenor engine
Collateral engine
Risk grade mapping
Recommendation dashboard
```

## Sprint 8

```text
AI credit memo
Risk copilot
Model validation report
Final dashboard polish
GitHub README
LinkedIn case study
```

---

# FINAL PROJECT RULE

Every feature must support this sentence:

```text
This system helps a fuel supplier make a better, explainable, data-driven trade credit decision under normal and stressed commodity market conditions.
```

If a feature does not support that sentence, do not build it.
