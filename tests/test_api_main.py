"""FastAPI app entrypoint tests for V2 Phase 13."""

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app, create_app


def test_create_app_health_endpoint_imports_without_database_access():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["version"] == "2.0.0"


def test_v2_app_registers_migrated_router_paths():
    route_paths = {route.path for route in app.routes}

    expected_paths = {
        "/api/v1/documents/upload",
        "/api/v1/documents/counterparties/{counterparty_id}",
        "/api/v1/financial-analysis/ratios/calculate/{financial_metrics_id}",
        "/api/v1/market-intelligence/stress/latest",
        "/api/v1/monitoring/alerts/latest",
        "/api/v1/credit-risk/pd/calculate/{financial_metrics_id}",
        "/api/v1/credit-risk/loss/calculate",
        "/api/v1/scenario-analysis/monte-carlo/run",
        "/api/v1/credit-decision/counterparty/{counterparty_id}/recommend",
        "/api/copilot",
        "/api/v1/copilot/health",
        "/api/v1/copilot/capabilities",
        "/api/v1/copilot/knowledge/status",
        "/api/v1/copilot/retrieval/status",
        "/api/v1/copilot/suggestions",
        "/api/v1/copilot/fields",
        "/api/v1/copilot/formulas",
        "/api/v1/copilot/models",
        "/api/v1/copilot/pipeline",
        "/api/v1/copilot/sources",
        "/api/v1/copilot/evaluation/questions",
        "/api/v1/copilot/evaluation/run",
        "/api/v1/copilot/route",
        "/api/v1/copilot/query",
        "/api/v1/copilot/trace",
        "/api/v1/copilot/market-impact",
        "/api/v1/reporting/memo/export",
        "/api/v1/reporting/risk-report/export",
    }

    assert expected_paths.issubset(route_paths)


def test_v2_app_has_no_duplicate_method_path_pairs():
    seen = set()
    duplicates = []
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            key = (method, route.path)
            if key in seen:
                duplicates.append(key)
            seen.add(key)

    assert duplicates == []


def test_main_entrypoint_uses_v2_router_imports_only():
    text = Path("api/main.py").read_text(encoding="utf-8-sig")
    forbidden = [
        "CREDIT_RISK_PROJECT_V1",
        "database.db_connection",
        "from api.routes",
        "from api.routes_phase",
        "from rag.",
        "from reporting.",
        "dashboard.components.database",
    ]

    for pattern in forbidden:
        assert pattern not in text

