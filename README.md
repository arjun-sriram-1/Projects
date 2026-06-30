# Fuel Trade Credit Risk Engine

AI-augmented trade finance credit risk system for fuel suppliers evaluating
jet fuel and marine fuel counterparties on credit terms.

The core business question is:

```text
Can we safely extend fuel trade credit to this counterparty, and if yes,
under what credit limit, tenor, collateral/security, and risk conditions?
```

AI explains and summarizes. It does not create final credit numbers. Formal
recommendations come from stored financial, market, model, scenario, and
simulation outputs.

## GitHub Safety

Before pushing this project, keep secrets and private artifacts out of Git:

- Do not commit `.env`, API keys, passwords, private annual reports, private CSVs, local databases, or large generated model files.
- Use `.env.example` as the public template and keep real credentials only in your local `.env`.
- Keep raw/private datasets under ignored folders such as `data/raw/` or `data/private/`.

## Current Implementation Status

Implemented:

- PostgreSQL schema and initialization pipeline.
- Counterparty, uploaded document, extracted financials, and financial ratio tables.
- PDF financial extraction service and API.
- Financial ratio engine with divide-by-zero and missing-data handling.
- Real/proxy market data ingestion using yfinance, FRED, EIA, and Alpha Vantage.
- Market stress index and regime detection from historical data.
- Merton-style structural PD and ML/proxy PD cross-check.
- LGD, EAD, and Expected Loss engine.
- Historical PD/LGD training pipeline with auditable proxy labels, stored training rows, model artifacts, validation metrics, and sanity checks.
- Data-driven scenario generator using historical quantiles.
- Monte Carlo portfolio simulation with VaR, Expected Shortfall, default correlation, and marginal contribution.
- Rules-based credit recommendation engine.
- Grounded credit memo generator reading stored recommendation/model outputs only.
- FastAPI routes for Phases 2-8.
- Test coverage for ratios, PD, LGD/EAD/EL, scenarios, Monte Carlo, recommendations, API smoke paths, RAG/memo wiring, and dashboard page registration/API-only rules.
- Professional Streamlit RiskIntel dashboard connected to FastAPI for the seven-step workflow: counterparty analysis, financial statements, market and stress intel, scenario forecasts, quant models, credit recommendation, and AI credit analyst.

Not yet complete or intentionally lightweight:

- CPI, rates, yield-spread, and high-yield spread ingestion is available through FRED; PMI is not yet implemented.
- PD/LGD training currently uses transparent proxy labels and counterfactual collateral augmentation when real default/recovery history is unavailable.

## Workflow

```text
PDF / financials
  -> extracted_financials
  -> financial_ratios
  -> market_prices / market_features
  -> stress_index_history / market_regime_history
  -> pd_model_predictions
  -> trade_exposures / loss_estimates
  -> historical_training_dataset / model_training_runs / model_validation_results
  -> scenario_results / simulation_results
  -> credit_recommendations
  -> grounded AI credit memo
```

## Key API Groups

```text
/api/v1/documents
/api/v1/financial-analysis
/api/v1/market-intelligence
/api/v1/credit-risk
/api/v1/scenario-analysis
/api/v1/credit-decision
/api/memo
/api/copilot
```

## Run

Create a `.env` with `DB_URL`, then initialize the schema:

```powershell
python pipelines\init_database.py
```

Start the API:

```powershell
uvicorn api.main:app --reload
```

Start the Streamlit dashboard in a second terminal:

```powershell
streamlit run web\app.py
```

The dashboard reads `CREDIT_RISK_PROJECT_V2\.env` automatically. Set
`V2_API_BASE_URL` only when you need to override the backend URL for the current
terminal session.

Dashboard runbook: [docs/dashboard_runbook.md](docs/dashboard_runbook.md)

Run tests:

```powershell
pytest -q
```

## Market Data Ingestion

Yahoo/yfinance market history:

```powershell
python pipelines\fetch_market_data.py --start_date 2018-01-01
```

FRED/EIA/Alpha Vantage provider ingestion:

```powershell
python pipelines\fetch_external_market_data.py --providers fred eia alphavantage --start_date 2018-01-01
```

Rebuild stress index and regimes after provider ingestion:

```powershell
python pipelines\fetch_external_market_data.py --providers fred eia --start_date 2018-01-01 --rebuild_stress_regimes
```

Provider rows are stored in `market_prices` with `data_source`, `source_id`,
`asset_name`, `return`, and `rolling_volatility`. Macro series are also mirrored
to `macro_indicators`.

Notes:

- FRED supplies VIX, S&P 500, Treasury yields, yield curve spread, CPI, high-yield spread, and heating-oil series.
- EIA supplies Brent, WTI/crude, heating oil, and jet fuel spot/proxy series through the API v2 petroleum route.
- Alpha Vantage free tier is used for compact daily stock/equity proxies such as oil, airline, and shipping equity proxies. Some ETF/full-history endpoints are premium and may return provider warnings.

## Historical Model Training

Train and store the historical PD/LGD models:

```powershell
python pipelines\run_historical_training.py
```

The training pipeline:

- Builds `data/processed/historical_training_dataset.csv`.
- Stores exact training rows in `historical_training_dataset`.
- Stores PD/LGD model runs in `model_training_runs`.
- Stores metrics and sanity checks in `model_validation_results`.
- Saves artifacts to `models/ml/historical_pd_model.pkl` and `models/ml/historical_lgd_model.pkl`.
- Updates `docs/historical_model_training_report.md`.

If PostgreSQL does not yet have enough uploaded financial-ratio history, the
pipeline uses `data/processed/final_dataset.csv` as a labeled fallback. Any
counterfactual collateral rows are marked in `data_source`; they are not real
observed recoveries.

## Credit Recommendation

The recommendation engine uses:

- PD from `pd_model_predictions`
- LGD/EAD/Expected Loss from `loss_estimates`
- trade terms and collateral from `trade_exposures`
- financial ratios from `financial_ratios`
- market stress/regime from Phase 4 outputs
- scenario and Monte Carlo outputs from `scenario_results` and `simulation_results`

Outputs are stored in `credit_recommendations`:

- `recommended_credit_limit`
- `recommended_tenor_days`
- `recommended_security`
- `risk_grade`
- `approval_status`
- `key_risk_drivers`
- audit references back to PD/LGD/EAD/scenario/ratio records

## Grounded Memo Rule

The credit memo generator reads from `credit_recommendations` and linked model
references only. If the stored data is missing, it says the data is missing.
It does not invent numerical claims.

## Validation

See [docs/model_validation_report.md](docs/model_validation_report.md) for the
current assumptions, sanity checks, test coverage, and limitations.

See [docs/historical_model_training_report.md](docs/historical_model_training_report.md)
for latest stored PD/LGD training metrics.


