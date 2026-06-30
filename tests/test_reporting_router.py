"""Reporting API route tests for V2 Phase 12C."""

from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from importlib import import_module

reporting_router_module = import_module("api.reporting.router")
reporting_router = reporting_router_module.router


def make_client():
    app = FastAPI()
    app.include_router(reporting_router)
    return TestClient(app)


def test_memo_export_endpoint_uses_memo_service_with_explicit_paths(tmp_path, monkeypatch):
    calls = []

    def fake_generate_memo_files(question, output_dir=None, docx_filename=None, pdf_filename=None):
        calls.append((question, output_dir, docx_filename, pdf_filename))
        docx = Path(docx_filename or tmp_path / "memo.docx")
        pdf = Path(pdf_filename or tmp_path / "memo.pdf")
        docx.parent.mkdir(parents=True, exist_ok=True)
        pdf.parent.mkdir(parents=True, exist_ok=True)
        docx.write_text("docx placeholder", encoding="utf-8")
        pdf.write_text("pdf placeholder", encoding="utf-8")
        return {
            "memo": "stored memo",
            "docx": str(docx),
            "pdf": str(pdf),
            "source": "stored V2 credit memo service",
        }

    monkeypatch.setattr(reporting_router_module, "generate_memo_files", fake_generate_memo_files)
    client = make_client()

    response = client.post(
        "/api/v1/reporting/memo/export",
        json={
            "question": "Acme Fuel",
            "docx_filename": str(tmp_path / "custom.docx"),
            "pdf_filename": str(tmp_path / "custom.pdf"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["memo"] == "stored memo"
    assert Path(body["docx"]).parent == tmp_path
    assert Path(body["pdf"]).parent == tmp_path
    assert calls == [("Acme Fuel", None, str(tmp_path / "custom.docx"), str(tmp_path / "custom.pdf"))]


def test_risk_report_export_endpoint_uses_reporting_services(tmp_path, monkeypatch):
    calls = []

    def fake_generate_report_data(company_name=None):
        calls.append(("generate", company_name))
        return {
            "total_exposure": 1_000_000.0,
            "total_expected_loss": 25_000.0,
            "avg_pd": 0.05,
            "avg_lgd": 0.50,
            "var95": 60_000.0,
            "var99": 90_000.0,
            "es95": 75_000.0,
            "es99": 110_000.0,
            "top_risk": pd.DataFrame(),
        }

    def fake_create_risk_report_pdf(report_data, output_file):
        calls.append(("pdf", report_data["total_exposure"], str(output_file)))
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        Path(output_file).write_text("pdf placeholder", encoding="utf-8")

    monkeypatch.setattr(reporting_router_module, "generate_report_data", fake_generate_report_data)
    monkeypatch.setattr(reporting_router_module, "create_risk_report_pdf", fake_create_risk_report_pdf)
    client = make_client()

    output_file = tmp_path / "risk.pdf"
    response = client.get(
        "/api/v1/reporting/risk-report/export",
        params={"company_name": "Acme Fuel", "output_file": str(output_file)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report_file"] == str(output_file)
    assert body["company_name"] == "Acme Fuel"
    assert body["total_exposure"] == 1_000_000.0
    assert body["source"] == "stored V2 reporting data"
    assert output_file.exists()
    assert calls[0] == ("generate", "Acme Fuel")
    assert calls[1] == ("pdf", 1_000_000.0, str(output_file))


def test_reporting_router_paths_and_no_generated_project_reports():
    route_paths = {route.path for route in reporting_router.routes}

    assert "/api/v1/reporting/memo/export" in route_paths
    assert "/api/v1/reporting/risk-report/export" in route_paths
    assert not Path("credit_memo.pdf").exists()
    assert not Path("credit_memo.docx").exists()
    assert not Path("daily_risk_report.pdf").exists()


def test_no_legacy_reporting_route_imports():
    files = [
        "api/reporting/router.py",
        "api/reporting/schemas.py",
    ]
    forbidden = [
        "dashboard.components.database",
        "database.db_connection",
        "from reporting.",
        "from rag.",
        "CREDIT_RISK_PROJECT_V1",
    ]

    for file_path in files:
        text = Path(file_path).read_text(encoding="utf-8-sig")
        for pattern in forbidden:
            assert pattern not in text



