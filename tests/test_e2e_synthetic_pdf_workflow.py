"""End-to-end backend workflow test with a generated annual-report PDF."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.base import Base
from api.db.session import get_db
from api.main import app


RAW_TABLE_DDL = [
    "CREATE TABLE stress_index_history (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, stress_index REAL, stress_level TEXT, component_values TEXT)",
    "CREATE TABLE market_regime_history (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, regime_label TEXT)",
    "CREATE TABLE market_prices (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, asset TEXT, price REAL)",
    """
    CREATE TABLE pd_model_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, counterparty_id INTEGER,
        financial_metrics_id INTEGER, financial_ratios_id INTEGER, model_name TEXT, model_version TEXT,
        structural_pd REAL, ml_pd REAL, final_pd REAL, classification_label TEXT, model_confidence REAL,
        model_disagreement BOOLEAN, pd_divergence REAL, distance_to_default REAL, asset_value_proxy REAL,
        debt_threshold REAL, asset_volatility REAL, risk_free_rate REAL, time_horizon_years REAL,
        commodity_sensitivity_score REAL, fx_sensitivity_score REAL, macro_sensitivity_score REAL,
        market_stress_index REAL, market_regime TEXT, feature_contributions TEXT, model_assumptions TEXT,
        input_data_reference TEXT, warnings TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE trade_exposures (
        id INTEGER PRIMARY KEY AUTOINCREMENT, counterparty_id INTEGER, invoice_amount REAL, fuel_volume REAL,
        fuel_price REAL, approved_credit_limit REAL, requested_credit_limit REAL, outstanding_receivables REAL,
        payment_tenor_days INTEGER, utilization_rate REAL, collateral_type TEXT, letter_of_credit_flag BOOLEAN,
        guarantee_flag BOOLEAN, deposit_percentage REAL, counterparty_type TEXT, country_risk_score REAL,
        seniority_score REAL, notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE loss_estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, counterparty_id INTEGER, pd_prediction_id INTEGER,
        trade_exposure_id INTEGER, model_name TEXT, model_version TEXT, probability_of_default REAL,
        predicted_lgd REAL, exposure_at_default REAL, expected_loss REAL, collateral_strength REAL,
        liquidity_score REAL, ead_cap_applied BOOLEAN, expected_drawdown REAL, invoice_exposure REAL,
        model_assumptions TEXT, input_data_reference TEXT, warnings TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE credit_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, counterparty_id INTEGER, model_name TEXT,
        model_version TEXT, probability_of_default REAL, loss_given_default REAL, exposure_at_default REAL,
        expected_loss REAL, scenario_expected_loss REAL, credit_var_95 REAL, expected_shortfall_95 REAL,
        recommended_credit_limit REAL, recommended_tenor_days INTEGER, recommended_security TEXT,
        risk_grade TEXT, approval_status TEXT, policy_score REAL, limit_haircut REAL, key_risk_drivers TEXT,
        mitigating_factors TEXT, model_assumptions TEXT, input_data_reference TEXT, warnings TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for ddl in RAW_TABLE_DDL:
            conn.execute(text(ddl))
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def _write_synthetic_annual_report(pdf_path: Path) -> None:
    lines = [
        "Synthetic Skyways Global Annual Report 2025",
        "For the fiscal year ended December 31, 2025",
        "USD",
        "Consolidated Statement of Profit and Loss",
        "Revenue from operations 1,250,000,000",
        "Depreciation and amortisation expense 70,000,000",
        "Finance costs 34,000,000",
        "Profit before tax 126,000,000",
        "Profit for the year 88,000,000",
        "Consolidated Balance Sheet",
        "Non-current assets",
        "Property, plant and equipment 980,000,000",
        "Current assets",
        "Inventories 75,000,000",
        "Trade receivables 210,000,000",
        "Cash and cash equivalents 160,000,000",
        "Total current assets 520,000,000",
        "Total assets 1,850,000,000",
        "Equity and liabilities",
        "Total equity 620,000,000",
        "Non-current liabilities",
        "Lease liabilities 310,000,000",
        "Total non-current liabilities 780,000,000",
        "Current liabilities",
        "Borrowings 180,000,000",
        "Lease liabilities 40,000,000",
        "Total outstanding dues of micro enterprises 20,000,000",
        "Total outstanding dues of creditors other than micro enterprises 135,000,000",
        "Total current liabilities 450,000,000",
        "Consolidated Statement of Cash Flows",
        "Cash flows from operating activities",
        "Net cash generated from operating activities 170,000,000",
        "Cash flows from investing activities",
        "Net cash used in investing activities (85,000,000)",
        "Cash flows from financing activities",
        "Net cash used in financing activities (60,000,000)",
    ]
    pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
    _, height = letter
    y = height - 54
    for index, line in enumerate(lines):
        if y < 54:
            pdf.showPage()
            y = height - 54
        pdf.setFont("Helvetica-Bold" if index == 0 or line.startswith("Consolidated") else "Helvetica", 10)
        pdf.drawString(54, y, line)
        y -= 16
    pdf.save()


def _ok(response, label: str):
    assert response.status_code in {200, 201}, f"{label}: {response.status_code} {response.text}"
    return response.json()


def test_generated_pdf_upload_to_recommendation_e2e(tmp_path):
    TestingSessionLocal = _make_session()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    pdf_path = tmp_path / "synthetic_skyways_annual_report.pdf"
    _write_synthetic_annual_report(pdf_path)

    try:
        counterparty = _ok(
            client.post(
                "/api/v1/documents/counterparties",
                json={
                    "counterparty_name": "Synthetic Skyways E2E",
                    "counterparty_type": "Airline (Jet Fuel)",
                    "country": "United States",
                },
            ),
            "create counterparty",
        )
        counterparty_id = counterparty["id"]

        with pdf_path.open("rb") as handle:
            upload = _ok(
                client.post(
                    "/api/v1/documents/upload",
                    params={
                        "counterparty_id": counterparty_id,
                        "document_type": "annual_report",
                        "created_by": "pytest_e2e",
                    },
                    files={"file": (pdf_path.name, handle, "application/pdf")},
                ),
                "upload PDF",
            )
        assert upload["extraction_status"] == "completed"

        document_status = _ok(
            client.get(f"/api/v1/documents/status/{upload['id']}"),
            "document status",
        )
        metrics = document_status["financial_metrics"]
        assert metrics["extraction_confidence"] == 1.0
        assert metrics["missing_critical_fields"] == []
        assert metrics["revenue"] == 1_250_000_000.0
        assert metrics["total_debt"] == 530_000_000.0

        ratios = _ok(
            client.post(f"/api/v1/financial-analysis/ratios/calculate/{metrics['id']}"),
            "calculate ratios",
        )["ratios"]
        assert ratios["current_ratio"] > 1.0
        assert ratios["debt_to_ebitda"] > 0

        pd_prediction = _ok(
            client.post(
                f"/api/v1/credit-risk/pd/calculate/{metrics['id']}",
                json={"time_horizon_years": 1.0},
            ),
            "calculate PD",
        )["prediction"]
        assert pd_prediction["id"]
        assert 0 < pd_prediction["final_pd"] < 1

        loss = _ok(
            client.post(
                "/api/v1/credit-risk/loss/calculate",
                json={
                    "counterparty_id": counterparty_id,
                    "pd_prediction_id": pd_prediction["id"],
                    "invoice_amount": 1_250_000.0,
                    "fuel_volume": 420_000.0,
                    "fuel_price": 2.85,
                    "approved_credit_limit": 8_000_000.0,
                    "requested_credit_limit": 10_000_000.0,
                    "outstanding_receivables": 1_800_000.0,
                    "payment_tenor_days": 30,
                    "utilization_rate": 0.62,
                    "collateral_type": "letter_of_credit",
                    "letter_of_credit_flag": True,
                    "counterparty_type": "Airline (Jet Fuel)",
                },
            ),
            "calculate loss",
        )["loss_estimate"]
        assert loss["expected_loss"] > 0

        recommendation = _ok(
            client.post(f"/api/v1/credit-decision/counterparty/{counterparty_id}/recommend"),
            "calculate recommendation",
        )["recommendation"]
        assert recommendation["approval_status"]
        assert recommendation["recommended_credit_limit"] > 0
        assert recommendation["recommended_security"]

        latest_paths = [
            f"/api/v1/documents/counterparty/{counterparty_id}",
            f"/api/v1/financial-analysis/counterparty/{counterparty_id}/latest-ratios",
            f"/api/v1/credit-risk/counterparty/{counterparty_id}/latest-pd",
            f"/api/v1/credit-risk/counterparty/{counterparty_id}/latest-loss",
            f"/api/v1/credit-decision/counterparty/{counterparty_id}/latest",
        ]
        for path in latest_paths:
            assert client.get(path).status_code == 200, path
    finally:
        app.dependency_overrides.pop(get_db, None)
