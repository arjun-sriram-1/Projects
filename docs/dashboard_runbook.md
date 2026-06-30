# Dashboard Runbook

Use this guide to start and smoke-check the V2 Streamlit dashboard.

## Start Backend API

From `CREDIT_RISK_PROJECT_V2`:

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

Expected result: JSON with `status` equal to `healthy`.

## Start Dashboard

Open a second terminal from `CREDIT_RISK_PROJECT_V2`:

```powershell
streamlit run web\app.py --server.address 127.0.0.1 --server.port 8501
```

The dashboard loads `CREDIT_RISK_PROJECT_V2\.env` automatically. To override
the backend URL for one terminal session, set:

```powershell
$env:V2_API_BASE_URL="http://127.0.0.1:8000"
```

Open:

```text
http://127.0.0.1:8501
```

## Default Analyst Context

The dashboard defaults to:

- Counterparty label: `Phase 16 Golden Airways`
- Counterparty ID: `180`
- Date range: `Latest available`

The label is display-only. Backend calls use the counterparty ID.

## Smoke Check Pages

Verify these pages load from the sidebar:

- 1. Counterparty Analysis
- 2. Financial Statements
- 3. Market & Stress Intel
- 4. Scenario & Forecasts
- 5. Quant & Monte Carlo
- 6. Credit Recommendation
- 7. AI Credit Analyst

Expected behavior:

- API badge shows healthy when FastAPI is running.
- Empty/missing backend records are shown as user-facing messages.
- No page directly connects to Postgres.
- Active workflow pages do not display raw database tables or raw JSON.
- No `.env` values, API keys, DB URLs, or secrets are displayed.
- The right copilot rail tracks the active workflow page and question.
- AI Credit Analyst shows clean answer grounding and data lineage.

## Test Commands

```powershell
pytest tests\test_dashboard.py -q
pytest -q
```

The dashboard smoke test verifies that all expected pages are registered and that `web/` does not use direct database access tokens.
