# Current Build Status

This feature list is the target project scope. As of the current implementation,
the backend workflow is complete through the rules-based credit recommendation
and grounded memo layer:

- Completed: financial extraction, ratio engine, yfinance/FRED/EIA/Alpha Vantage market ingestion, stress index,
  regime detection, PD, LGD/EAD/Expected Loss, data-driven scenarios, Monte Carlo,
  credit recommendation, grounded memo, historical PD/LGD training storage,
  validation reporting, and tests.
- Partial: dashboard polish, PMI macro coverage, and production-grade
  LGD/PD calibration using real observed defaults/recoveries.
- Not fully implemented: ARIMA/VAR/GARCH commodity forecasting and hedging
  sensitivity.

The canonical formal decision source is now `credit_recommendations`. Memo and
decision agents must explain that stored output rather than produce independent
recommendations.

Historical model training now persists:

- `historical_training_dataset` rows with data source and proxy label logic.
- `model_training_runs` rows for Logistic PD and Random Forest LGD artifacts.
- `model_validation_results` rows with train/test metrics and sanity checks.

The current training run can use stored SQL financial history first, then a
clearly labeled processed-CSV fallback if the database has too few financial
ratio observations.

Feature Name	Intended Audience	Problem Solved	Data Required + Free Sources	Mathematical / ML Models	Acceptance Criteria	Test Strategy
1. PDF Financial Statement Extractor	Credit analyst, trade finance officer	Converts uploaded annual reports/balance sheets into usable financial data without manual entry.	PDF annual reports, income statement, balance sheet, cash flow statement. Sources: company investor relations, stock exchange filings, airline/shipping annual reports.	OCR/NLP extraction, rule-based table parsing, LLM-assisted validation.	Extracts revenue, debt, cash, assets, liabilities, EBITDA/EBIT with >85% accuracy on test PDFs.	Compare extracted values with manually checked values from 5–10 reports.
2. Financial Ratio Engine	Credit analyst, CFO, finance controller	Converts raw financials into credit health indicators.	Extracted financial statements.	Current ratio, quick ratio, debt/equity, debt/EBITDA, interest coverage, ROA, ROE, operating margin.	Ratios match Excel/manual calculations exactly.	Unit test every ratio formula using known sample statements.
3. Counterparty Credit Profile Score	Credit manager	Gives a first-pass risk score before advanced modelling.	Financial ratios, company type, fleet size, country, payment terms, collateral. Sources: annual reports, public fleet data, synthetic trade terms.	Weighted scorecard + K-Means segmentation.	Produces Low/Medium/High risk grouping with explainable drivers.	Check whether weak firms score worse than strong firms using known examples.
4. Market Data Ingestion Engine	Quant analyst, risk team	Pulls real historical market variables instead of hardcoding assumptions.	Brent, WTI, VIX, S&P 500, DXY proxy, FX, Treasury yields, inflation. Sources: FRED, EIA, Yahoo Finance/yfinance. FRED tracks macro/market series, EIA provides oil and petroleum prices, and Yahoo Finance has commodity futures pages. (FRED)	Time-series cleaning, returns, rolling volatility, correlations.	Database updates successfully and stores clean daily/monthly time series.	Validate missing values, date alignment, return calculations.
5. Commodity Risk Factor Engine	Commodity risk analyst, supplier credit team	Measures how crude oil, jet fuel proxies, marine fuel proxies affect counterparty risk.	Brent, WTI, heating oil/jet proxy, bunker/marine proxy, natural gas. Sources: EIA, Yahoo Finance.	Log returns, rolling volatility, spread analysis, correlation matrix.	Shows commodity exposure indicators and historical volatility.	Backtest computed volatility against known high-volatility periods.
6. Geopolitical / Macro Stress Indicator	Credit committee, risk manager	Converts broad geopolitical/economic pressure into a measurable index.	VIX, S&P 500, oil prices, USD index proxy, rates, inflation, Baltic Dry proxy if available, gold. Sources: FRED/Yahoo Finance/World Bank.	PCA composite index, z-score normalization, volatility-adjusted weighting.	Produces 0–100 “market stress score” with clear drivers.	Check whether score rises during known crisis periods like 2020 COVID or 2022 oil shock.
7. Regime Detection Engine	Quant analyst, risk manager	Learns normal, adverse, and stress market environments from historical data.	Historical market feature matrix: oil returns, VIX, equity returns, FX, rates, commodity spreads.	Gaussian Mixture Model, Hidden Markov Model, PCA + clustering.	Identifies realistic regimes: stable, oil-volatility, risk-off, USD-stress.	Inspect historical dates assigned to each regime and verify economic sense.
8. Data-Driven Scenario Generator	Credit analyst, supplier management	Generates normal and stress scenarios from historical distributions, not hardcoded shocks.	Regime-classified market data.	Quantile-based scenario generation, Monte Carlo sampling, bootstrapping.	Base/adverse/severe scenarios are generated automatically from historical data.	Confirm scenario values come from historical quantiles, not manual constants.
9. Commodity Forecasting Module	Quant analyst, hedging desk	Forecasts likely commodity movement and volatility for credit decisions.	Brent, WTI, fuel proxy prices, FX, VIX.	ARIMA/VAR for prices, GARCH for volatility.	Produces forecast path, confidence interval, volatility forecast.	Backtest forecast error using rolling train/test split.
10. Structural PD Model	Credit analyst, quant risk team	Estimates default probability using financial structure, not only classification.	Debt, equity proxy, asset value estimate, asset volatility, tenor.	Merton model, distance-to-default.	Produces PD and distance-to-default for each counterparty.	Sensitivity test: higher debt/volatility should increase PD.
11. ML PD Proxy Model	Model validation team, credit analyst	Cross-checks Merton PD with data-driven default classification.	Ratios, market stress score, commodity volatility, company type, payment behavior, synthetic default labels if needed.	Logistic Regression first; XGBoost optional upgrade.	Model outputs default probability and key drivers.	Train/test split, ROC-AUC, confusion matrix, calibration plot.
12. LGD Prediction Model	Credit manager, trade finance team	Estimates loss severity instead of using fixed LGD assumptions.	Collateral type, LC/guarantee/deposit, seniority, region, exposure size, counterparty type, liquidity.	Random Forest Regressor.	Predicts LGD between 0–100% with explainable feature importance.	Check MAE/RMSE; confirm secured trades produce lower LGD than unsecured trades.
13. Exposure at Default Engine	Supplier finance team	Estimates how much money is at risk if the customer defaults.	Invoice amount, fuel volume, price, payment tenor, credit line, unpaid receivables.	EAD formula, utilization modelling, exposure simulation.	Calculates outstanding exposure by counterparty and scenario.	Reconcile EAD with sample invoice/payment examples.
14. Portfolio Monte Carlo Engine	Risk manager, CFO	Shows total portfolio loss distribution, not just single-name risk.	PD, LGD, EAD, correlations, market scenarios.	Monte Carlo simulation, Gaussian/t-Copula, Credit VaR, Expected Shortfall.	Produces EL, UL, VaR, ES at portfolio and counterparty level.	Check loss distribution behaves correctly when PD/LGD/EAD rises.
15. Credit Limit Recommendation Engine	Credit officer, CFO	Converts model output into an actual business decision.	PD, LGD, EAD, ratios, scenario losses, collateral, tenor.	Rule-based decision layer + optimization constraints.	Recommends limit, tenor, collateral, risk grade, approval/reject.	Test with strong/weak counterparties and verify logical recommendations.
16. Payment Terms Optimizer	Fuel supplier, reseller finance team	Decides whether to offer 30/45/60/90-day credit.	Counterparty risk score, cash conversion cycle, PD, LGD, scenario EL.	Expected loss by tenor, marginal risk pricing.	Higher-risk counterparties get shorter terms or stronger security.	Compare EL across tenors and verify longer tenor increases risk.
17. Early Warning System	Credit monitoring team	Flags deteriorating counterparties before default.	New financials, market stress, news sentiment, payment delays, volatility.	Isolation Forest, z-score alerts, threshold rules.	Generates alerts with reason codes.	Inject abnormal data and confirm alert is triggered.
18. Explainable Risk Dashboard	Credit analyst, interviewer, LinkedIn/GitHub viewers	Makes the project understandable and visually professional.	All model outputs.	SHAP values, feature importance, scenario attribution.	User can see why PD/LGD/limit changed.	Pick one counterparty and trace every output back to inputs.
19. AI Credit Memo Generator	Credit committee, CFO, analyst	Turns quantitative output into a professional credit memo.	Ratios, PD, LGD, EAD, scenario results, collateral, RAG documents.	RAG + LLM summarization using structured templates.	Generates a memo with company profile, risk drivers, recommendation, and caveats.	Compare memo against underlying database values; no hallucinated numbers allowed.
20. AI Credit Risk Copilot	Credit analyst, finance controller, CFO	Lets users ask: “Why is this risky?”, “What if oil rises?”, “Why 45 days?”	SQL database, documents, credit policy, model outputs, market data.	Agentic RAG, SQL tool use, retrieval, structured reasoning.	Answers are grounded in stored model outputs and cite exact drivers.	Ask 20 test questions and verify answers match database/model results.
21. Counterparty Comparison Tool	Credit manager, portfolio manager	Compares two airlines/shipping firms side by side.	Financial ratios, PD, LGD, EAD, scenario results.	Ranking model, z-score normalization, relative risk scoring.	Clearly explains which counterparty is safer and why.	Compare known stronger vs weaker companies and check result.
22. Hedging Sensitivity Module	Commodity trading / hedging audience	Shows how oil/FX hedges reduce credit exposure indirectly.	Oil price, FX, exposure, counterparty fuel sensitivity.	Delta sensitivity, scenario loss reduction, simple hedge payoff model.	Shows before/after risk metrics with hedge impact.	Test oil +10%, +20%, -10% scenarios and verify hedge payoff offsets exposure.
23. Model Validation Report	Recruiters, professors, GitHub reviewers	Proves the project is not just a dashboard but a serious quant system.	Model metrics, backtests, assumptions, limitations.	Backtesting, sensitivity analysis, error metrics, calibration.	Project includes a validation notebook/report.	Re-run pipeline end-to-end and reproduce metrics.



