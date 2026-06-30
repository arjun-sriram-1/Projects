# AGENTS.md

# AI-Augmented Trade Finance Credit Risk Agent — Coding Ruler

## 1. Project Identity

This project is not a generic ML dashboard.

It is an AI-augmented credit risk decision system for fuel suppliers, fuel resellers, commodity traders, and trade finance teams evaluating jet fuel and marine fuel counterparties on credit terms.

The system must always answer the business question:

> Can we safely extend fuel trade credit to this counterparty, and if yes, under what credit limit, tenor, collateral/security, and risk conditions?

Every feature, model, API, table, and dashboard component must support this decision.

---

## 2. Core Design Principle

AI is an accelerator, not the decision-maker.

The risk decision must be grounded in:

- Financial statement analysis
- Trade finance logic
- Commodity market risk
- Macroeconomic indicators
- Geopolitical/market stress indicators
- Quantitative credit risk models
- Scenario analysis
- Portfolio risk metrics

Do not generate code where the LLM invents final credit recommendations without using model outputs and stored data.

---

## 3. Main System Workflow

All code should fit into this workflow:

1. User uploads counterparty financial PDF.
2. System extracts financial statement data.
3. System computes financial ratios.
4. System ingests real market and macro data.
5. System builds market features and stress indicators.
6. System detects market regimes from historical data.
7. System estimates PD using Merton and ML proxy models.
8. System estimates LGD using Random Forest.
9. System calculates EAD from invoices, credit line, fuel volume, and tenor.
10. System generates data-driven scenarios from historical regimes.
11. System runs Monte Carlo portfolio simulation.
12. System computes EL, UL, VaR, and Expected Shortfall.
13. System recommends credit limit, tenor, collateral, and risk grade.
14. AI layer explains the result and generates a credit memo.

Do not build isolated features that do not connect to this workflow.

---

## 4. No Hardcoded Scenarios

Never hardcode business scenarios like:

- oil_shock = 0.20
- fx_shock = 0.10
- revenue_drop = 0.15

Scenarios must be generated from historical data using:

- historical quantiles
- market regimes
- rolling volatility
- bootstrapping
- Monte Carlo sampling
- GARCH volatility forecasts
- VAR forecasts
- PCA/GMM/HMM regime outputs

Allowed exception: sample/demo seed data may contain clearly marked synthetic examples under `data/sample/` or `database/seed_data.py`.

All synthetic assumptions must be documented.

---

## 5. Data-Driven First Rule

Prefer real/free/proxy data sources before synthetic data.

Acceptable sources:

- Yahoo Finance / yfinance
- FRED
- EIA
- World Bank
- IMF public datasets
- company annual reports
- public investor presentations
- exchange filings
- public airline/shipping operational data

If real data is unavailable, use synthetic data only as a fallback and label it explicitly as synthetic.

Never mix synthetic and real data without a `data_source` field.

---

## 6. Financial Statement Extraction Rules

PDF extraction must produce structured financial data, not just text.

Required extracted fields where available:

- revenue
- EBITDA
- EBIT
- net income
- cash
- total assets
- current assets
- total liabilities
- current liabilities
- total debt
- equity
- interest expense
- operating cash flow
- accounts receivable
- accounts payable
- inventory

All extracted values must include:

- counterparty_id
- fiscal_year
- currency
- source_document_id
- extraction_confidence
- original_text_reference if possible

Never silently accept missing critical financial fields. Flag them.

---

## 7. Financial Ratio Engine Rules

Ratios must be calculated from stored financial statement data.

Required ratios:

- current ratio
- quick ratio
- debt to equity
- debt to EBITDA
- interest coverage
- net margin
- operating margin
- ROA
- ROE
- cash ratio where possible
- working capital

Rules:

- handle divide-by-zero safely
- return null instead of fake values
- store calculation date
- store formula version
- preserve units and currency

---

## 8. Credit Risk Model Rules

The credit risk engine must clearly separate:

- PD: probability of default
- LGD: loss given default
- EAD: exposure at default

Expected Loss must be calculated as:

EL = PD × LGD × EAD

Do not confuse PD with risk score.
Do not confuse LGD with total loss.
Do not confuse EAD with credit limit.

---

## 9. Merton Model Rules

The Merton model is the structural PD model.

Inputs should include:

- asset value proxy
- debt threshold
- asset volatility
- risk-free rate
- time horizon

Outputs must include:

- distance_to_default
- structural_pd
- asset_volatility
- debt_threshold
- model_assumptions

The Merton model should be explainable in business terms:

> Higher leverage or higher asset volatility should increase default risk.

Always include sensitivity tests where possible.

---

## 10. ML PD Model Rules

The ML PD model is a cross-check, not the only source of truth.

Preferred models:

- Logistic Regression as baseline
- XGBoost only if clearly justified

Inputs may include:

- financial ratios
- commodity exposure
- macro stress index
- payment delay history
- country risk proxy
- market volatility

Outputs:

- ml_pd
- classification label
- model confidence
- feature importance or coefficients

Do not train ML models on meaningless labels.
If synthetic labels are used, clearly document the label-generation logic.

---

## 11. LGD Model Rules

The LGD model is the main ML contribution.

Preferred model:

- Random Forest Regressor

Inputs should include:

- collateral/security type
- letter of credit flag
- guarantee flag
- deposit percentage
- counterparty type
- liquidity ratios
- country risk
- seniority/security strength
- exposure size
- payment terms

Output:

- predicted_lgd between 0 and 1

Business logic must hold:

- stronger collateral → lower LGD
- LC/guarantee → lower LGD
- unsecured exposure → higher LGD

---

## 12. EAD Rules

Exposure at Default must be based on actual trade exposure logic.

Inputs:

- invoice amount
- fuel volume
- fuel price
- credit limit
- outstanding receivables
- payment tenor
- utilization percentage

EAD must not exceed logical exposure limits unless explicitly justified.

---

## 13. Market Data Rules

Market data should include, where available:

- Brent crude
- WTI crude
- jet fuel proxy
- marine fuel proxy
- natural gas
- VIX
- S&P 500
- DXY or USD proxy
- US 2Y yield
- US 10Y yield
- yield curve spread
- CPI/inflation
- Baltic Dry Index or freight proxy
- gold

For each market time series store:

- date
- ticker/source_id
- asset_name
- price/value
- return
- rolling_volatility
- data_source

---

## 14. Geopolitical / Macro Stress Index Rules

The geopolitical stress index must not be manually invented.

It should be built using market/macro proxies such as:

- VIX
- oil volatility
- S&P 500 returns
- DXY movement
- gold returns
- rates movement
- freight index movement
- inflation surprise if available

Preferred methods:

- z-score normalization
- PCA
- weighted composite index
- regime-aware scaling

Output must be 0–100 with explainable drivers.

---

## 15. Regime Detection Rules

Market regimes must be learned from historical data.

Preferred methods:

- PCA + KMeans
- Gaussian Mixture Model
- Hidden Markov Model

Regime labels should be assigned after observing model behavior.

Example labels:

- Stable Market
- Commodity Stress
- USD Stress
- Risk-Off
- Crisis

Do not predefine regimes using hardcoded thresholds unless used only for baseline comparison.

---

## 16. Commodity Forecasting Rules

Commodity forecasting should be treated as probabilistic, not deterministic.

Preferred models:

- ARIMA as simple baseline
- VAR for multi-factor relationships
- GARCH for volatility forecasting

Outputs:

- expected path
- volatility forecast
- confidence interval
- forecast horizon
- backtest error

Never present forecasts as guaranteed predictions.

---

## 17. Scenario Engine Rules

Scenarios must include:

- base case
- normal volatility case
- adverse case
- severe downside case
- tail case

But these must be generated from historical data.

Scenario outputs should show impact on:

- PD
- LGD
- EAD
- Expected Loss
- credit limit
- payment terms
- collateral requirement

Normal scenarios are the main use case.
Stress scenarios are supporting risk controls.

---

## 18. Monte Carlo Rules

Monte Carlo simulation must simulate uncertainty in:

- commodity prices
- FX
- market stress
- counterparty asset values
- defaults
- LGD if applicable
- portfolio losses

Outputs:

- expected loss
- unexpected loss
- VaR
- expected shortfall
- loss distribution
- marginal contribution by counterparty

Always expose number of simulations and random seed.

---

## 19. Copula Rules

Use copulas only for portfolio default dependence.

Allowed:

- Gaussian copula baseline
- t-copula for tail dependence

Do not use copulas for single-counterparty PD.

Outputs must explain correlation assumptions.

---

## 20. Credit Decision Engine Rules

The final recommendation must be rules-based or model-based using risk outputs.

Required outputs:

- recommended_credit_limit
- recommended_tenor_days
- recommended_security
- risk_grade
- approval_status
- key_risk_drivers
- model_version

Example recommendation logic:

- Low PD + low LGD + strong liquidity → higher limit, longer tenor
- High PD + high LGD → lower limit, shorter tenor, LC required
- High commodity sensitivity → reduce tenor or require collateral
- High market stress regime → apply risk haircut

Never allow the LLM alone to decide final limits.

---

## 21. AI/RAG Rules

The AI layer must only explain, retrieve, summarize, and assist.

It may generate:

- credit memo
- risk explanation
- scenario explanation
- Q&A answers
- model interpretation

It must not hallucinate numbers.

Every numerical claim must come from:

- SQL database
- model output
- uploaded financial document
- market data table
- scenario result table

If data is missing, the AI must say data is missing.

---

## 22. Database Design Rules

Use PostgreSQL-friendly schemas.

Important tables should include:

- counterparties_master
- uploaded_documents
- extracted_financials
- financial_ratios
- market_prices
- market_features
- macro_indicators
- geopolitical_index
- market_regimes
- model_predictions
- scenario_results
- simulation_results
- credit_recommendations
- ai_credit_memos
- audit_logs

Every model output table must include:

- model_name
- model_version
- run_id
- created_at
- input_data_reference
- assumptions_reference

---

## 23. Auditability Rules

This is a finance/risk project.

Every important output must be traceable.

For any credit recommendation, the user should be able to trace:

credit recommendation
→ scenario result
→ PD/LGD/EAD
→ financial ratios
→ extracted financials
→ source PDF
→ market data inputs

No black-box final output.

---

## 24. Model Validation Rules

Every model should have validation outputs.

Required:

- train/test split where applicable
- backtest where applicable
- sensitivity analysis
- sanity checks
- error metrics
- assumption documentation

Examples:

- Higher leverage must increase risk.
- Stronger collateral must reduce LGD.
- Higher oil volatility must increase risk for airlines.
- Longer tenor must increase exposure risk.

---

## 25. Code Organization Rules

Use this structure unless already existing files require compatibility:

```text
ingestion/
analytics/
models/
models/credit/
models/market/
models/portfolio/
decision_engine/
rag_agent/
api/
dashboard/
database/
tests/
notebooks/
reports/

Do not place unrelated logic in main.py.

Keep business logic outside API route files.

API routes should call services, not contain full modelling logic.



## 26. Naming Rules

Use finance-friendly names.

Good:

probability_of_default
loss_given_default
exposure_at_default
expected_loss
credit_var
expected_shortfall
distance_to_default
recommended_tenor_days

Bad:

score1
result
output
risknum
final_value

27. Testing Rules

Every major module should have tests.

Minimum tests:

financial ratio formula tests
Merton model sensitivity tests
LGD bounds test
EAD calculation test
scenario generator non-hardcoding test
Monte Carlo output shape test
credit recommendation sanity test
API endpoint smoke tests

Do not mark a feature complete without tests


28. Documentation Rules

Every major model file must include:

business purpose
inputs
outputs
formula/model logic
assumptions
limitations

Every feature should be explainable to a finance interviewer.

Avoid comments that only explain code mechanics.
Prefer comments that explain finance logic.

29. Student Project Realism Rule

This is a student project.

Do not over-engineer into an enterprise system.

Prefer:

clear working pipeline
realistic assumptions
explainable models
reproducible outputs
professional documentation

over complex but fragile architecture.

30. Final Deliverable Rule

The final project must produce these deliverables:

Dashboard
API
PostgreSQL database
Sample uploaded financial report
Extracted financials
Risk model outputs
Scenario results
Credit recommendation
AI-generated credit memo
Model validation report
README explaining business logic
LinkedIn/GitHub-ready project summary

If a feature does not improve one of these deliverables, question whether it belongs.

31. Safety and Dependency Rules

Before adding any new dependency:

check whether it is necessary
prefer well-known libraries
avoid obscure packages
document why it is needed

Do not install random packages for simple tasks.

32. Response Style For Codex

When generating or modifying code, always provide:

Files changed
What changed
Why it changed
How to run it
How to test it
Any assumptions made

Do not only dump code without explanation.

33. Golden Rule

Every generated line of code should support this sentence:

This system helps a fuel supplier make a better, more explainable, data-driven trade credit decision under normal and stressed commodity market conditions.