# QUANT_MODEL_RULES.md

# Quantitative Model Ruler  
## AI-Augmented Trade Finance Credit Risk Agent for Jet Fuel / Marine Fuel Counterparties

---

## 1. Project Quantitative Objective

This project is a quantitative trade credit risk system for fuel suppliers, fuel resellers, commodity traders, and trade finance teams.

The core business question is:

> Can we safely extend fuel trade credit to this counterparty, and if yes, what credit limit, tenor, collateral/security, and risk grade should be recommended?

The quantitative model must convert:

```text
Counterparty financial health
+ Trade exposure
+ Commodity market risk
+ FX risk
+ Macro risk
+ Geopolitical/market stress
+ Scenario analysis
+ Portfolio dependence

PD  = Probability of Default
LGD = Loss Given Default
EAD = Exposure at Default
EL  = Expected Loss
UL  = Unexpected Loss
VaR = Credit Value-at-Risk
ES  = Expected Shortfall
Credit Limit
Payment Tenor
Collateral Recommendation
Risk Grade

2. Golden Quant Rule

Every quantitative result must be traceable.

Final Recommendation
    ↓
Credit Decision Engine
    ↓
Scenario Results
    ↓
PD / LGD / EAD
    ↓
Financial Ratios + Market Features
    ↓
Financial Statements + Market Data
    ↓
Source PDF / Public Data Source

No black-box output is allowed.

3. End-to-End Quant Workflow

The full quantitative workflow is:

1. Extract counterparty financials from PDF
2. Calculate financial ratios
3. Ingest market, commodity, FX, macro, and geopolitical proxy data
4. Engineer market features
5. Build macro/geopolitical stress index
6. Detect market regimes
7. Forecast commodity / FX volatility
8. Estimate counterparty vulnerability to market factors
9. Estimate structural PD using Merton model
10. Estimate ML PD as a cross-check
11. Estimate LGD using Random Forest
12. Calculate EAD from trade exposure
13. Generate data-driven scenarios
14. Run Monte Carlo simulation
15. Model portfolio default dependence using copulas
16. Calculate EL, UL, VaR, Expected Shortfall
17. Recommend credit limit, tenor, collateral, and risk grade
18. Generate explainable credit memo
4. Key Data Categories
4.1 Counterparty Financial Data

Extracted from annual reports, financial statements, uploaded PDFs, or manually entered forms.

Required fields:

revenue
EBITDA
EBIT
net_income
cash
total_assets
current_assets
total_liabilities
current_liabilities
total_debt
equity
interest_expense
operating_cash_flow
accounts_receivable
accounts_payable
inventory
fiscal_year
currency

Purpose:

Measures repayment ability, solvency, leverage, liquidity, and profitability.
4.2 Trade Exposure Data

Required fields:

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
counterparty_type

Purpose:

Measures exposure at default and potential loss size.
4.3 Commodity Market Data

Required indicators:

Brent crude
WTI crude
jet fuel proxy
marine fuel proxy
heating oil proxy
natural gas
fuel crack spread

Purpose:

Measures fuel cost pressure and commodity market stress.
4.4 Macro / Market Data

Required indicators where available:

S&P 500
VIX
DXY or USD proxy
US 2Y yield
US 10Y yield
yield curve spread
CPI
PPI
PMI
gold
Baltic Dry Index
freight index proxy

Purpose:

Measures risk appetite, inflation, funding conditions, trade activity, and geopolitical/market stress.
5. Financial Ratio Engine

Financial ratios must be calculated from extracted financials.

5.1 Liquidity Ratios
current_ratio = current_assets / current_liabilities

quick_ratio = (cash + accounts_receivable) / current_liabilities

cash_ratio = cash / current_liabilities

working_capital = current_assets - current_liabilities

Interpretation:

Lower liquidity → higher short-term payment risk → higher PD.
5.2 Leverage Ratios
debt_to_equity = total_debt / equity

debt_to_ebitda = total_debt / EBITDA

liabilities_to_assets = total_liabilities / total_assets

Interpretation:

Higher leverage → lower solvency cushion → higher PD.
5.3 Coverage Ratios
interest_coverage = EBIT / interest_expense

Interpretation:

Lower interest coverage → weaker debt servicing ability → higher PD.
5.4 Profitability Ratios
operating_margin = EBIT / revenue

net_margin = net_income / revenue

ROA = net_income / total_assets

ROE = net_income / equity

Interpretation:

Weak profitability → lower internal cash generation → higher PD.
6. Market Feature Engineering

Raw market prices must not be used directly without transformation.

For every market series:

price_t
return_t = ln(price_t / price_t-1)
rolling_volatility = std(return_t over rolling window)
momentum = price_t / price_t-n - 1
drawdown = price_t / rolling_max_price - 1
z_score = (value - historical_mean) / historical_std

Required engineered features:

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
7. Economic Correlation Rules

The model must respect economic intuition.

7.1 Oil / Fuel Risk
Brent ↑ → Jet Fuel ↑
Brent ↑ → Marine Fuel ↑
Jet Fuel ↑ → Airline fuel cost ↑
Marine Fuel ↑ → Shipping fuel cost ↑
Fuel cost ↑ → Margins ↓
Margins ↓ → Cash flow ↓
Cash flow ↓ → PD ↑

Use this relationship for:

commodity exposure engine
scenario engine
PD stress adjustment
credit terms recommendation
7.2 USD / FX Risk
DXY ↑ → USD strengthens
USD strengthens → USD-priced commodities become more expensive for non-USD buyers
Commodity import cost ↑ → liquidity pressure ↑
Liquidity pressure ↑ → PD ↑

Use this relationship for:

FX stress factor
market stress index
scenario impact on counterparty
7.3 Interest Rate Risk
Inflation ↑ → Central banks may raise rates
Rates ↑ → Borrowing cost ↑
Borrowing cost ↑ → Interest coverage ↓
Interest coverage ↓ → PD ↑

Use this relationship for:

macro stress engine
financial ratio stress
PD adjustment
7.4 Equity / Risk Appetite
S&P 500 ↓ → risk appetite ↓
Risk appetite ↓ → funding conditions tighten
Funding conditions tighten → refinancing risk ↑
Refinancing risk ↑ → PD ↑

Use this relationship for:

geopolitical stress index
market regime detection
scenario classification
7.5 VIX / Market Fear
VIX ↑ → market uncertainty ↑
Uncertainty ↑ → funding/liquidity risk ↑
Funding risk ↑ → PD ↑

Use this relationship for:

stress index
scenario generator
market regime detection
7.6 Baltic Dry / Freight Risk

For shipping counterparties:

Baltic Dry Index ↓ → freight demand/revenue ↓
Freight revenue ↓ → cash flow ↓
Cash flow ↓ → PD ↑

For broader macro:

Baltic Dry Index ↓ → global trade weakens
Global trade weakens → shipping credit risk ↑

Use this relationship for:

shipping counterparty vulnerability
macro stress index
scenario analysis
7.7 Gold / Safe Haven
Gold ↑ + VIX ↑ + S&P 500 ↓ → risk-off / geopolitical stress ↑
Risk-off ↑ → credit standards tighten

Use this relationship for:

geopolitical stress index
regime detection
8. Counterparty Vulnerability Mapping

Different counterparty types react differently to the same market shock.

8.1 Airline Counterparty

Primary risk drivers:

jet_fuel_price
brent_crude
USD strength
interest rates
passenger demand proxy
market stress index

Expected relationships:

jet_fuel_price ↑ → airline operating cost ↑ → margin ↓ → PD ↑
USD ↑ → fuel import cost ↑ → liquidity stress ↑ → PD ↑
rates ↑ → financing cost ↑ → PD ↑
8.2 Shipping / Shipowner Counterparty

Primary risk drivers:

marine_fuel_price
brent_crude
Baltic Dry Index
freight index
USD strength
global trade indicators

Expected relationships:

marine_fuel_price ↑ → voyage cost ↑ → margin ↓ → PD ↑
Baltic Dry Index ↓ → freight revenue ↓ → PD ↑
global trade ↓ → shipping demand ↓ → PD ↑

Important nuance:

If marine fuel rises but freight rates rise more, shipping profitability may not deteriorate.

So the model should consider both cost-side and revenue-side indicators.

8.3 Fuel Distributor / Reseller

Primary risk drivers:

fuel price volatility
inventory value
customer receivables
working capital
credit terms
FX

Expected relationships:

fuel volatility ↑ → inventory and margin risk ↑
receivables ↑ → liquidity risk ↑
working capital ↓ → PD ↑
9. Geopolitical / Macro Stress Index

The geopolitical stress index must be data-driven.

It should not be manually assigned.

9.1 Inputs

Use normalized indicators:

VIX z-score
oil volatility z-score
S&P 500 return z-score
DXY return z-score
gold return z-score
US 10Y yield change z-score
yield curve z-score
Baltic Dry return z-score
inflation z-score
PMI z-score
9.2 PCA Method

PCA converts many correlated indicators into a smaller number of factors.

Purpose:

Many indicators → one systemic stress factor

Steps:

1. Build feature matrix X
2. Standardize all columns
3. Run PCA
4. Extract PC1
5. Interpret PC1 as broad market/geopolitical stress factor
6. Rescale PC1 to 0–100

Final score:

0–20   calm
20–40  normal
40–60  elevated
60–80  stressed
80–100 crisis
9.3 PCA Interpretation Rules

PC1 should rise when:

VIX ↑
Oil volatility ↑
DXY ↑
Gold ↑
S&P 500 ↓
Baltic Dry ↓
Yield curve stress ↑

If PC1 behaves opposite, multiply by -1 so higher score means higher stress.

Always store PCA loadings.

Required outputs:

stress_index
pc1_score
pc1_loadings
explained_variance_ratio
top_positive_drivers
top_negative_drivers
10. Market Regime Detection

Market regimes must be learned from historical data.

10.1 Allowed Models
K-Means
Gaussian Mixture Model
Hidden Markov Model
10.2 Input Features
brent_return
brent_volatility
vix_level
sp500_return
dxy_return
yield_curve_spread
baltic_dry_return
stress_index
10.3 Possible Regime Labels

Labels must be assigned after analyzing cluster behavior.

Examples:

Stable Market
Normal Volatility
Commodity Stress
USD Stress
Risk-Off
Crisis
10.4 Regime Interpretation
Stable Market:
    low VIX, low oil volatility, positive/neutral equity returns

Commodity Stress:
    high oil volatility, large oil returns, fuel price pressure

USD Stress:
    rising DXY, commodity pressure, emerging-market stress

Risk-Off:
    VIX high, S&P down, gold up, DXY up

Crisis:
    extreme volatility, broad market stress, high tail risk
11. Scenario Generation Rules

Scenarios must be generated from historical data.

No hardcoded shocks.

11.1 Scenario Types
Base Case
Normal Volatility Case
Adverse Case
Severe Downside Case
Tail Case
11.2 Scenario Construction

For each market regime, calculate historical quantiles:

Base Case = median outcome
Normal Volatility = 25th to 75th percentile
Adverse Case = 10th percentile adverse movement
Severe Downside = 5th percentile adverse movement
Tail Case = 1st percentile adverse movement
11.3 Scenario Outputs

Each scenario must include:

brent_change
jet_fuel_change
marine_fuel_change
dxy_change
vix_change
sp500_change
yield_change
baltic_dry_change
stress_index_change
11.4 Scenario Impact

Each scenario must recompute:

counterparty financial stress
PD
LGD if relevant
EAD if tenor/exposure changes
Expected Loss
credit limit recommendation
payment tenor recommendation
collateral recommendation
12. Commodity Forecasting Rules

Forecasting must be probabilistic.

Do not present forecasts as certain.

12.1 ARIMA

Use for single-variable baseline forecasting.

Example:

Forecast Brent using Brent history.
12.2 VAR

Use when multiple variables interact.

Example:

Brent, DXY, VIX, S&P 500, Baltic Dry

VAR should capture relationships such as:

DXY movement affects commodity pressure
VIX affects risk appetite
Oil affects inflation expectations
Freight affects shipping health
12.3 GARCH

Use for volatility forecasting.

Commodity markets exhibit volatility clustering:

High volatility tends to follow high volatility.
Low volatility tends to follow low volatility.

Required GARCH outputs:

forecast_volatility
volatility_confidence
volatility_regime

Higher forecast volatility should increase risk adjustment.

13. Structural PD: Merton Model

The Merton model is the main structural credit risk model.

13.1 Core Idea

A company defaults if:

Asset Value < Debt Threshold

At maturity.

13.2 Inputs
asset_value_proxy
debt_threshold
asset_volatility
risk_free_rate
time_horizon
13.3 Outputs
distance_to_default
structural_pd
asset_volatility
model_assumptions
13.4 Intuition Rules
Asset value ↑ → PD ↓
Debt ↑ → PD ↑
Asset volatility ↑ → PD ↑
Time horizon ↑ → uncertainty ↑
13.5 Market Stress Adjustment

Market scenarios may affect:

asset_value_proxy
asset_volatility
cash_flow_proxy
debt_service_capacity

Example:

Brent ↑ for airline → fuel cost ↑ → margins ↓ → asset value ↓ → PD ↑
VIX ↑ → asset volatility ↑ → PD ↑
Rates ↑ → debt servicing pressure ↑ → PD ↑
14. ML PD Model

The ML PD model is a validation layer, not the main decision-maker.

14.1 Preferred Model
Logistic Regression

Optional upgrade:

XGBoost
14.2 Inputs
current_ratio
quick_ratio
debt_to_equity
debt_to_ebitda
interest_coverage
operating_margin
cash_ratio
market_stress_index
commodity_sensitivity_score
country_risk_score
payment_delay_history
counterparty_type
14.3 Output
ml_pd
default_label
model_confidence
feature_importance
14.4 Rules
Merton PD and ML PD should be compared.
If they diverge significantly, flag model_disagreement = true.

Example:

Merton PD = 3%
ML PD = 14%

Then:

Flag for analyst review.
15. LGD Model

LGD estimates loss severity if default occurs.

15.1 Preferred Model
Random Forest Regressor
15.2 Inputs
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
15.3 Output
predicted_lgd

Bound:

0 <= LGD <= 1
15.4 Business Logic Rules
Letter of credit present → LGD ↓
Bank guarantee present → LGD ↓
Deposit higher → LGD ↓
Collateral stronger → LGD ↓
Country/legal risk higher → LGD ↑
Unsecured exposure → LGD ↑
Longer tenor → LGD may ↑
16. EAD Model

EAD measures exposure at default.

16.1 Trade Finance Logic

For fuel credit:

EAD = unpaid invoices + delivered_unbilled_fuel + committed_future_delivery_exposure

Simplified:

EAD = min(approved_credit_limit, outstanding_receivables + expected_drawdown)
16.2 Inputs
invoice_amount
fuel_volume
fuel_price
outstanding_receivables
approved_credit_limit
payment_tenor_days
utilization_rate
16.3 Rules
Longer tenor → more invoices outstanding → EAD ↑
Higher fuel price → invoice size ↑ → EAD ↑
Higher utilization → EAD ↑
Credit limit caps EAD
17. Expected Loss

Expected Loss must always be:

EL = PD × LGD × EAD

Where:

PD is decimal between 0 and 1
LGD is decimal between 0 and 1
EAD is currency amount

Example:

PD = 0.05
LGD = 0.60
EAD = 10,000,000

EL = 300,000

Do not confuse expected loss with worst-case loss.

18. Monte Carlo Simulation

Monte Carlo is used to simulate many possible future outcomes.

18.1 Simulated Variables
commodity prices
FX
VIX / stress index
counterparty asset values
PD
LGD if stochastic
EAD if exposure changes
default events
portfolio losses
18.2 Required Outputs
loss_distribution
expected_loss
unexpected_loss
credit_var_95
credit_var_99
expected_shortfall_95
expected_shortfall_99
marginal_risk_contribution
18.3 Rules
Store number_of_simulations
Store random_seed
Store model_version
Store scenario_id
19. Copula Model

Copulas are used only for portfolio default dependence.

19.1 Purpose

Defaults are correlated.

Example:

Oil shock may weaken multiple airlines simultaneously.
Trade collapse may weaken multiple shipping firms simultaneously.
19.2 Allowed Copulas
Gaussian Copula
t-Copula
19.3 Rules
Use Gaussian Copula as baseline.
Use t-Copula for tail dependence.
Do not use copulas for single-name PD.
Store correlation assumptions.
20. Credit Decision Engine

The credit decision engine converts quantitative outputs into business action.

20.1 Inputs
structural_pd
ml_pd
predicted_lgd
ead
expected_loss
credit_var
expected_shortfall
stress_index
market_regime
financial_ratios
collateral_info
counterparty_type
scenario_results
20.2 Outputs
recommended_credit_limit
recommended_tenor_days
recommended_security
risk_grade
approval_status
key_risk_drivers
20.3 Decision Logic Examples
Low PD + low LGD + stable regime → approve higher limit and longer tenor

High PD + high LGD → reduce limit, shorten tenor, require LC

High stress index → apply credit limit haircut

High fuel sensitivity → shorten tenor or require security

Weak liquidity → reduce limit

No collateral + high LGD → require LC or guarantee
21. Risk Grade Mapping

Example mapping:

PD < 1%          → A
1% <= PD < 3%    → BBB
3% <= PD < 7%    → BB
7% <= PD < 15%   → B
PD >= 15%        → CCC / Reject or secured only

This is a student-project approximation.

Always document that rating grades are internal proxy grades, not official agency ratings.

22. Credit Limit Logic

Credit limit should be linked to expected loss and risk appetite.

Possible framework:

base_limit = requested_limit

risk_haircut = function(PD, LGD, stress_index, weak_ratios, regime)

recommended_limit = base_limit × (1 - risk_haircut)

Possible haircut drivers:

PD high → haircut ↑
LGD high → haircut ↑
Stress index high → haircut ↑
Weak liquidity → haircut ↑
No collateral → haircut ↑
Long tenor → haircut ↑
23. Payment Tenor Logic

Payment tenor must reflect risk.

Strong counterparty + low stress → 60–90 days possible
Medium risk → 30–45 days
High risk → 7–30 days or secured only
Very high risk → prepayment / LC only

Longer tenor increases risk because:

More unpaid invoices accumulate
Market conditions may change before payment
Counterparty liquidity may deteriorate
24. Collateral / Security Logic

Recommended security should depend on LGD and PD.

Low PD + low LGD → open credit possible
Medium PD or LGD → partial deposit / guarantee
High PD or high LGD → LC required
Very high risk → prepayment only

Security impact:

LC → LGD decreases
Guarantee → LGD decreases
Deposit → EAD/LGD decreases
Collateral → LGD decreases
25. Model Interconnection Map
Financial Statements
    ↓
Financial Ratios
    ↓
Merton PD + ML PD
    ↓
Expected Loss

Market Data
    ↓
Market Features
    ↓
Stress Index + Regime Detection
    ↓
Scenario Generator
    ↓
Stressed PD / LGD / EAD

Trade Exposure
    ↓
EAD

Collateral / Security
    ↓
LGD

PD + LGD + EAD
    ↓
Expected Loss
    ↓
Monte Carlo Portfolio Loss
    ↓
VaR + Expected Shortfall
    ↓
Credit Recommendation
26. Full Economic Chain Example

For an airline counterparty:

Middle East tension ↑
    ↓
Brent crude ↑
    ↓
Jet fuel ↑
    ↓
Airline fuel cost ↑
    ↓
Operating margin ↓
    ↓
Cash flow ↓
    ↓
Asset value proxy ↓
    ↓
Merton distance-to-default ↓
    ↓
PD ↑
    ↓
Expected Loss ↑
    ↓
Recommended credit limit ↓
    ↓
Payment tenor shortened
    ↓
LC required

For a shipping counterparty:

Global trade slowdown ↑
    ↓
Baltic Dry Index ↓
    ↓
Freight revenue ↓
    ↓
Cash flow ↓
    ↓
PD ↑
    ↓
Credit terms tightened
27. Sanity Checks

Codex must ensure the model passes these economic sanity checks.

27.1 Credit Risk
Higher leverage should not reduce PD.
Lower liquidity should not reduce PD.
Lower interest coverage should not reduce PD.
Higher collateral should not increase LGD.
Higher EAD should not reduce expected loss, all else equal.
27.2 Commodity Risk
Higher jet fuel price should increase airline risk.
Higher marine fuel price should increase shipping cost pressure.
Lower Baltic Dry Index should increase shipping counterparty risk.
Higher VIX should increase stress index.
Lower S&P 500 should increase stress index.
Higher DXY should increase FX stress.
27.3 Scenario Risk
Adverse scenario should not produce lower risk than base scenario unless justified.
Severe scenario should usually produce higher risk than adverse scenario.
Tail scenario should represent worse tail loss than severe scenario.
28. Output Requirements

Every quantitative model output must include:

run_id
counterparty_id
model_name
model_version
input_data_reference
created_at
assumptions
outputs
warnings

For credit recommendations, include:

recommended_limit
recommended_tenor
recommended_security
risk_grade
approval_status
pd_used
lgd_used
ead_used
expected_loss
scenario_summary
top_risk_drivers
29. Missing Data Rules

Never silently fill critical missing data.

If missing:

debt
cash
EBITDA
interest expense
current liabilities
market data
collateral information

then:

flag missing_data_warning = true

Allowed fallback:

use proxy only if documented

Example:

If jet fuel price unavailable, use heating oil or refined product proxy.
30. Assumption Rules

Every assumption must be explicit.

Examples:

Default defined as >90 days overdue
LGD proxy based on collateral strength
Jet fuel proxy based on heating oil / refined fuel index
Private company asset value estimated using financial statement proxy
Synthetic labels used only for student demonstration

No hidden assumptions.

31. Validation Rules

Each model should include validation.

31.1 Ratio Validation
Manual formula test
Divide-by-zero test
Missing data test
31.2 Merton Validation
Debt ↑ → PD ↑
Volatility ↑ → PD ↑
Asset value ↑ → PD ↓
31.3 LGD Validation
LC flag true → LGD lower
Deposit higher → LGD lower
No collateral → LGD higher
31.4 Scenario Validation
Scenarios generated from historical data
Quantiles correctly calculated
No hardcoded scenario shocks
31.5 Monte Carlo Validation
Loss distribution created
VaR >= Expected Loss generally
Expected Shortfall >= VaR
Random seed reproducible
32. Documentation Rules For Quant Files

Every quantitative model file must include a docstring with:

Business purpose
Inputs
Outputs
Mathematical method
Economic intuition
Assumptions
Limitations
Example usage

Example:

This model estimates structural probability of default using the Merton framework.
It treats equity as a call option on firm assets and default occurs when asset value falls below debt threshold.
33. What Not To Do

Do not:

Hardcode scenario shocks
Let AI invent financial numbers
Mix synthetic and real data without labeling
Use random risk scores without economic meaning
Use ML outputs without explaining features
Use copulas for single-name PD
Use VaR as expected loss
Treat forecasts as certainty
Ignore missing data
Hide assumptions
34. Final Quant Deliverables

The quantitative engine must produce:

1. Extracted financial data
2. Financial ratios
3. Market features
4. Geopolitical / macro stress index
5. Market regime classification
6. Commodity volatility forecast
7. Structural PD
8. ML PD
9. LGD
10. EAD
11. Expected Loss
12. Scenario results
13. Monte Carlo loss distribution
14. Credit VaR
15. Expected Shortfall
16. Credit recommendation
17. Quant explanation of top risk drivers
35. Final Guiding Sentence

Every quantitative model must support this sentence:

The system translates financial weakness, commodity exposure, macro/geopolitical stress, and trade exposure into measurable credit risk and practical trade credit decisions.