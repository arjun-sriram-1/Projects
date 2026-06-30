# Frontend Rules

Use these rules for Streamlit page code, API client calls, layout components, charts, and dashboard tests.

The frontend is a Streamlit dashboard for the fuel trade credit workflow. It displays backend/API outputs; it does not calculate core credit risk models.

Expected pages:

- Executive Overview
- Counterparty Workspace
- Financial Extraction
- Market Intelligence
- PD / LGD / EAD Models
- Scenario and Monte Carlo
- Credit Decision
- Monitoring Alerts
- AI Copilot
- Credit Memo / Reporting
- Model Validation

Required rules:

- Use `web/api_client.py` for backend calls.
- Do not import SQLAlchemy, database sessions, DB URLs, or backend model engines into `web/`.
- Use Plotly/Streamlit for charts and tables.
- Show loading, empty, and error states.
- Keep pages focused on credit decisions, scenario impact, market context, portfolio risk, alerts, copilot, and memo/report outputs.
- Keep UI display logic separate from backend calculation logic.
- Follow `.ruler/web/dashboard_design_rules.md` for detailed UI/UX, dark theme, component, page, and responsive rules.
- Run `pytest tests/test_dashboard.py -q` after dashboard structure or API-client changes.
