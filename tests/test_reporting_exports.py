"""Reporting/export utility tests for V2 Phase 12A."""

from pathlib import Path

import pandas as pd

from api.rag.exports.docx_exporter import export_docx
from api.rag.exports.pdf_exporter import export_pdf
from api.reporting import report_generator
from api.reporting.report_pdf import create_risk_report_pdf


def test_memo_exporters_create_files_in_tmp_path(tmp_path):
    memo = "Credit memo smoke test\nRecommendation: use stored model outputs only."

    docx_file = export_docx(memo, filename=tmp_path / "memo.docx")
    pdf_file = export_pdf(memo, filename=tmp_path / "memo.pdf")

    assert Path(docx_file).exists()
    assert Path(pdf_file).exists()
    assert Path(docx_file).parent == tmp_path
    assert Path(pdf_file).parent == tmp_path
    assert Path(docx_file).stat().st_size > 0
    assert Path(pdf_file).stat().st_size > 0


def test_risk_report_pdf_creates_file_in_tmp_path(tmp_path):
    report_data = {
        "total_exposure": 2_000_000.0,
        "total_expected_loss": 45_000.0,
        "avg_pd": 0.04,
        "avg_lgd": 0.50,
        "var95": 80_000.0,
        "var99": 120_000.0,
        "es95": 95_000.0,
        "es99": 150_000.0,
        "top_risk": pd.DataFrame(
            [
                {"company_name": "Acme Fuel", "expected_loss": 30_000.0},
                {"company_name": "Beta Air", "expected_loss": 15_000.0},
            ]
        ),
    }
    output_file = tmp_path / "risk_report.pdf"

    create_risk_report_pdf(report_data, output_file)

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_generate_report_data_uses_v2_data_loaders(monkeypatch):
    monkeypatch.setattr(
        report_generator,
        "load_counterparties",
        lambda: pd.DataFrame(
            [{"counterparty_id": 1, "company_name": "Acme Fuel"}]
        ),
    )
    monkeypatch.setattr(
        report_generator,
        "load_predictions",
        lambda: pd.DataFrame(
            [{"counterparty_id": 1, "pd": 0.04}]
        ),
    )
    monkeypatch.setattr(
        report_generator,
        "load_portfolio",
        lambda: pd.DataFrame(
            [{"counterparty_id": 1, "exposure": 1_000_000.0, "expected_loss": 20_000.0, "lgd": 0.50}]
        ),
    )
    monkeypatch.setattr(
        report_generator,
        "load_simulations",
        lambda: pd.DataFrame(
            [
                {
                    "var_95": 50_000.0,
                    "var_99": 75_000.0,
                    "expected_shortfall_95": 60_000.0,
                    "expected_shortfall_99": 90_000.0,
                    "created_at": "2025-01-01",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        report_generator,
        "load_scenarios",
        lambda: pd.DataFrame([{"scenario_type": "adverse"}]),
    )

    report = report_generator.generate_report_data(company_name="Acme Fuel")

    assert report["total_exposure"] == 1_000_000.0
    assert report["total_expected_loss"] == 20_000.0
    assert report["avg_pd"] == 0.04
    assert report["avg_lgd"] == 0.50
    assert report["var95"] == 50_000.0
    assert report["es99"] == 90_000.0
    assert report["company_name"] == "Acme Fuel"


def test_generate_report_data_returns_empty_shape_when_inputs_missing(monkeypatch):
    monkeypatch.setattr(report_generator, "load_counterparties", lambda: pd.DataFrame())
    monkeypatch.setattr(report_generator, "load_predictions", lambda: pd.DataFrame())
    monkeypatch.setattr(report_generator, "load_portfolio", lambda: pd.DataFrame())
    monkeypatch.setattr(report_generator, "load_simulations", lambda: pd.DataFrame())
    monkeypatch.setattr(report_generator, "load_scenarios", lambda: pd.DataFrame())

    report = report_generator.generate_report_data()

    assert report["total_exposure"] == 0.0
    assert report["total_expected_loss"] == 0.0
    assert report["top_risk"].empty


def test_no_legacy_reporting_imports_or_generated_reports_in_project_root():
    files = [
        "api/reporting/report_generator.py",
        "api/reporting/report_pdf.py",
        "api/reporting/run_daily_report.py",
        "api/rag/exports/docx_exporter.py",
        "api/rag/exports/pdf_exporter.py",
        "api/rag/exports/memo_generator.py",
        "api/rag/exports/memo_service.py",
    ]
    forbidden = [
        "dashboard.components.database",
        "from reporting.",
        "from rag.",
        "database.db_connection",
        "CREDIT_RISK_PROJECT_V1",
    ]

    for file_path in files:
        text = Path(file_path).read_text(encoding="utf-8-sig")
        for pattern in forbidden:
            assert pattern not in text

    assert not Path("credit_memo.pdf").exists()
    assert not Path("credit_memo.docx").exists()
    assert not Path("daily_risk_report.pdf").exists()
