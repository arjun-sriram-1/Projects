from pathlib import Path

from api.main import create_app


FRONTEND_DIR = Path("frontend")


def test_fastapi_serves_html_frontend_routes():
    app = create_app()
    route_paths = {route.path for route in app.routes}

    assert "/" in route_paths
    assert "/ui" in route_paths
    assert any(getattr(route, "path", None) == "/assets" for route in app.routes)


def test_frontend_has_required_credit_workflow_pages():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    script = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")

    assert "/assets/styles.css" in html
    assert "/assets/app.js" in html
    for label in [
        "Counterparty Analysis",
        "Financial Statements",
        "Market",
        "Scenario & Forecasts",
        "Quant & Monte Carlo",
        "Credit Recommendation",
    ]:
        assert label in script
    assert "AI Credit Analyst" not in script
    assert "toggle-copilot" in html
    assert "AI Co-Pilot" in html
    assert "loading-spinner" in script
    assert "is-processing" in script
    assert "@keyframes spin" in (FRONTEND_DIR / "styles.css").read_text(encoding="utf-8")


def test_frontend_uses_backend_endpoints_not_streamlit():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [FRONTEND_DIR / "index.html", FRONTEND_DIR / "app.js"]
    )

    assert "streamlit" not in combined.lower()
    for endpoint in [
        "/api/v1/documents/upload",
        "/api/v1/financial-analysis/ratios/calculate",
        "/api/v1/credit-risk/pd/calculate",
        "/api/v1/credit-risk/loss/calculate",
        "/api/v1/credit-decision/counterparty",
        "/api/v1/copilot/query",
        "/api/copilot",
    ]:
        assert endpoint in combined


def test_frontend_keeps_copilot_answers_clean_without_source_citations():
    script = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")
    styles = (FRONTEND_DIR / "styles.css").read_text(encoding="utf-8")

    assert "renderCopilotSources" not in script
    assert "copilot-source-chip" not in script
    assert "copilotTraceValues" in script
    assert "data-copilot-prompt" in script
    assert "metric-explain" in script
    assert ".copilot-sources" not in styles
    assert ".copilot-source-chip" not in styles
    assert ".metric-explain" in styles
