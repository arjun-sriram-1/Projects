"""Dashboard smoke tests for the Streamlit API-only frontend."""

from __future__ import annotations

from pathlib import Path

from web import app


EXPECTED_PAGES = {
    "1. Counterparty Analysis",
    "2. Financial Statements",
    "3. Market & Stress Intel",
    "4. Scenario & Forecasts",
    "5. Quant & Monte Carlo",
    "6. Credit Recommendation",
    "7. AI Credit Analyst",
}

ACTIVE_WORKFLOW_FILES = [
    Path("web/pages/counterparty.py"),
    Path("web/pages/financials.py"),
    Path("web/pages/market.py"),
    Path("web/pages/scenario.py"),
    Path("web/pages/models.py"),
    Path("web/pages/decision.py"),
    Path("web/pages/copilot.py"),
]


def test_dashboard_page_registry_is_complete():
    assert set(app.PAGES) == EXPECTED_PAGES
    assert set(app.PAGE_META) == EXPECTED_PAGES
    assert all(callable(renderer) for renderer in app.PAGES.values())


def test_dashboard_pages_import_without_side_effects():
    for page_name, renderer in app.PAGES.items():
        assert renderer.__module__.startswith("web.pages"), page_name


def test_dashboard_uses_terminal_workflow_context():
    source = Path("web/app.py").read_text(encoding="utf-8-sig")
    api_client = Path("web/api_client.py").read_text(encoding="utf-8-sig")
    config_source = Path("web/config.py").read_text(encoding="utf-8-sig")
    assert "RiskIntel Agent" in source
    assert "render_terminal_header" in source
    assert "render_persistent_copilot" in source
    assert "render_ingestion_dialog" in source
    assert "Ingest New Data" in source
    assert "active_page" in source
    assert "active_question" in source
    assert "PAGE_META" in source
    assert "Question answered:" in source
    assert "2. Financial Statements" in source
    assert "client.counterparties" in source
    assert "Manual backend ID fallback" in source
    assert "def counterparties" in api_client
    assert "/api/v1/documents/counterparties" in api_client
    assert "selected_segment" in source
    assert "requested_limit" in source
    assert "requested_tenor" in source
    assert "load_dotenv(ENV_PATH" in config_source
    assert "V2_API_BASE_URL" in config_source
    assert "API_BASE_URL" in config_source


def test_dashboard_config_prefers_explicit_api_base_url(monkeypatch):
    from web.config import DashboardConfig

    monkeypatch.setenv("V2_API_BASE_URL", "http://127.0.0.1:9000")
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:8001")
    assert DashboardConfig().api_base_url == "http://127.0.0.1:9000"


def test_dashboard_config_supports_legacy_api_base_url(monkeypatch):
    from web.config import DashboardConfig

    monkeypatch.delenv("V2_API_BASE_URL", raising=False)
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:8002")
    assert DashboardConfig().api_base_url == "http://127.0.0.1:8002"


def test_dashboard_uses_terminal_shell_styles():
    source = Path("web/styles.py").read_text(encoding="utf-8-sig")
    assert "terminal-header-strip" in source
    assert "terminal-counterparty-select" in source
    assert "terminal-copilot-rail" in source
    assert "terminal-copilot-context" in source
    assert "terminal-page-kicker" in source
    assert "terminal-kpi-strip" in source
    assert "terminal-decision-card" in source
    assert "terminal-compact-table" in source
    assert "terminal-ingest-context" in source
    assert "terminal-ingest-note" in source


def test_dashboard_does_not_use_direct_database_access():
    web_root = Path("web")
    forbidden = ["sqlalchemy", "psycopg", "asyncpg", "SessionLocal", "create_engine", "DATABASE_URL"]
    offenders: list[str] = []
    for path in web_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8-sig")
        for token in forbidden:
            if token in source:
                offenders.append(f"{path}:{token}")
    assert offenders == []


def test_active_workflow_pages_do_not_show_raw_tables_or_json():
    forbidden = ["st.dataframe", "st.json", "st.table"]
    offenders: list[str] = []
    for path in ACTIVE_WORKFLOW_FILES:
        source = path.read_text(encoding="utf-8-sig")
        for token in forbidden:
            if token in source:
                offenders.append(f"{path}:{token}")
    assert offenders == []

def test_executive_overview_uses_summary_panels_not_tables_or_json():
    source = Path("web/pages/executive.py").read_text(encoding="utf-8-sig")
    assert "st.dataframe" not in source
    assert "st.json" not in source
    assert "render_data_summary_grid" in source
    assert "decision_panel" in source

def test_core_workflow_pages_use_panel_layouts():
    counterparty = Path("web/pages/counterparty.py").read_text(encoding="utf-8-sig")
    decision = Path("web/pages/decision.py").read_text(encoding="utf-8-sig")
    assert "st.dataframe" not in counterparty
    assert "st.json" not in counterparty
    assert "st.dataframe" not in decision
    assert "st.json" not in decision
    assert "Counterparty Credit Analysis" in counterparty
    assert "render_terminal_kpi_strip" in counterparty
    assert "Accounting Brief Summary" in counterparty
    assert "Risk Driver Index" in counterparty
    assert "Workflow Readiness" in counterparty
    assert "Credit Recommendation" in decision
    assert "Recommended Terms" in decision
    assert "Decision Explanation" in decision
    assert "Policy Driver Index" in decision
    assert "Decision Data Lineage" in decision
    assert "decision_card" in decision
    assert "render_terminal_kpi_strip" in decision



def test_financial_and_model_pages_use_phase_ui5_panels():
    financials = Path("web/pages/financials.py").read_text(encoding="utf-8-sig")
    models = Path("web/pages/models.py").read_text(encoding="utf-8-sig")
    assert "st.dataframe" not in financials
    assert "st.json" not in financials
    assert "Source Audit" in financials
    assert "Extraction Quality" in financials
    assert "Statement Values" in financials
    assert "Ratio Analysis" in financials
    assert "terminal_panel" in financials
    assert "evidence_panel" in financials
    assert "render_financial_ingestion_workflow" in financials
    assert "st.dataframe" not in models
    assert "st.json" not in models
    assert "Quant & Monte Carlo" in models
    assert "PD Model Agreement" in models
    assert "Quant Risk Drivers" in models
    assert "Loss Input Lineage" in models
    assert "terminal_panel" in models
    assert "render_terminal_kpi_strip" in models
    assert "warning-callout" in models
    assert "render_technical_json" in models


def test_market_and_scenario_pages_use_phase_ui6_presentation():
    market = Path("web/pages/market.py").read_text(encoding="utf-8-sig")
    scenario = Path("web/pages/scenario.py").read_text(encoding="utf-8-sig")
    assert "st.dataframe" not in market
    assert "st.json" not in market
    assert "st.line_chart" not in market
    assert "st.bar_chart" not in market
    assert "apply_dark_chart_layout" in market
    assert "Price Ledger" in market
    assert "Market Stress Brief" in market
    assert "Latest Price Signals" in market
    assert "No raw database table" in market
    assert "st.dataframe" not in scenario
    assert "st.json" not in scenario
    assert "render_technical_json" in scenario
    assert "t-Copula tail dependence" in scenario
    assert "Marginal Risk Contribution" in scenario
    assert "Scenario Library" in scenario
    assert "Scenario Detail" in scenario
    assert "terminal_panel" in scenario
    assert "render_terminal_kpi_strip" in scenario


def test_monitoring_and_validation_pages_use_phase_ui7_presentation():
    monitoring = Path("web/pages/monitoring.py").read_text(encoding="utf-8-sig")
    validation = Path("web/pages/validation.py").read_text(encoding="utf-8-sig")
    assert "st.json" not in monitoring
    assert "render_technical_json" in monitoring
    assert "monitoring-alert-grid" in monitoring
    assert "st.json" not in validation
    assert "render_technical_json" in validation
    assert "validation-check-grid" in validation
    assert "render_data_summary_grid" in validation


def test_copilot_and_reporting_pages_use_phase_ui8_9_presentation():
    copilot = Path("web/pages/copilot.py").read_text(encoding="utf-8-sig")
    memo = Path("web/pages/memo.py").read_text(encoding="utf-8-sig")
    assert "st.dataframe" not in copilot
    assert "st.json" not in copilot
    assert "suggestion-grid" in copilot
    assert "AI Credit Analyst" in copilot
    assert "Analyst Context" in copilot
    assert "Live Credit Analyst" in copilot
    assert "Answer Grounding" in copilot
    assert "render_terminal_kpi_strip" in copilot
    assert "terminal_panel" in copilot
    assert "st.write(\"DOCX:" not in memo
    assert "st.write(\"Report file:" not in memo
    assert "export-result-panel" in memo
    assert "render_technical_json" in memo
    assert "Report Source Summary" in memo


def test_financial_upload_allows_long_running_pdf_extraction():
    api_client = Path("web/api_client.py").read_text(encoding="utf-8-sig")
    financials = Path("web/pages/financials.py").read_text(encoding="utf-8-sig")
    ingestion = Path("web/components/ingestion.py").read_text(encoding="utf-8-sig")
    assert "upload_timeout: int = 300" in api_client
    assert "timeout=max(self.timeout, self.upload_timeout)" in api_client
    assert "render_financial_ingestion_workflow" in financials
    assert "2-5 minutes" in ingestion
    assert "Read timed out" in ingestion


def test_financial_page_uses_clean_ingestion_labels():
    financials = Path("web/pages/financials.py").read_text(encoding="utf-8-sig")
    ingestion = Path("web/components/ingestion.py").read_text(encoding="utf-8-sig")
    assert "analyst_label(item)" in financials
    assert "FIELD_LABELS" in ingestion
    assert "Total debt" in ingestion
    assert "Cash and equivalents" in ingestion
