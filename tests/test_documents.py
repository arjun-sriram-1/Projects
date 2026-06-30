"""Document extraction tests for V2.

These tests validate the migrated parser, schemas, ORM mapping, and router
imports without requiring a live PostgreSQL database.
"""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.base import Base
from api.db.models import (
    CounterpartyMaster,
    FinancialMetricsExtracted,
    UploadedDocument,
)
from api.db.session import get_db
from api.documents.pdf_parser import ExtractedFinancialData, PDFFinancialParser
from api.documents.router import router as documents_router
from api.documents.schemas import CounterpartyCreate, FinancialMetricsResponse
from api.documents.service import list_counterparties


def make_test_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class TestPDFParser:
    """Test deterministic PDF/text financial extraction."""

    def setup_method(self):
        self.parser = PDFFinancialParser()

    def test_parser_initialization(self):
        assert self.parser is not None
        assert "revenue" in self.parser.patterns
        assert "net_income" in self.parser.patterns
        assert "total_assets" in self.parser.patterns

    def test_parse_number_simple_and_scaled_values(self):
        assert self.parser._parse_number("1,000") == 1000.0
        assert self.parser._parse_number("1.5M") == 1_500_000.0
        assert self.parser._parse_number("2B") == 2_000_000_000.0
        assert self.parser._parse_number("500K") == 500_000.0
        assert self.parser._parse_number("abc") is None
        assert self.parser._parse_number(None) is None

    def test_extract_text_metrics_records_values_and_references(self):
        sample_text = """
        CONSOLIDATED STATEMENTS OF OPERATIONS
        Year ended December 31, 2022

        Total Revenue: $1,234,567,890
        Cost of Goods Sold: $890,000,000
        EBITDA: $194,567,890
        EBIT: $180,000,000
        Interest Expense: $45,000,000
        Net Income: $120,000,000

        CONSOLIDATED BALANCE SHEET
        Cash and Equivalents: $500,000,000
        Current Assets: $1,100,000,000
        Accounts Receivable: $250,000,000
        Inventory: $125,000,000
        Total Assets: $3,456,789,012
        Current Liabilities: $700,000,000
        Long Term Debt: $900,000,000
        Total Debt: $950,000,000
        Total Liabilities: $2,000,000,000
        Shareholders Equity: $1,456,789,012
        Cash from Operations: $160,000,000
        Accounts Payable: $280,000,000
        """

        data = self.parser.extract_text_metrics(sample_text)

        assert data.revenue == 1_234_567_890.0
        assert data.ebitda == 194_567_890.0
        assert data.total_assets == 3_456_789_012.0
        assert data.total_debt == 950_000_000.0
        assert data.original_text_references["revenue"]

    def test_quality_flags_make_missing_fields_explicit(self):
        data = ExtractedFinancialData(revenue=1_000_000.0, total_assets=2_000_000.0)
        data.finalize_quality_flags()

        assert data.extraction_confidence == round(2 / len(data.CRITICAL_FIELDS), 2)
        assert "total_debt" in data.missing_critical_fields
        assert data.extraction_warnings

    def test_parse_pdf_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.parser.parse_pdf("non_existent.pdf")

    def test_parse_generated_digital_pdf(self, tmp_path):
        pdf_path = tmp_path / "synthetic_airline_annual_report.pdf"
        pdf = canvas.Canvas(str(pdf_path))
        pdf.drawString(72, 760, "Synthetic Airline Annual Report")
        pdf.drawString(72, 740, "For the year ended December 31, 2024")
        pdf.drawString(72, 700, "Total Revenue: $1,250,000,000")
        pdf.drawString(72, 680, "EBITDA: $220,000,000")
        pdf.drawString(72, 660, "EBIT: $180,000,000")
        pdf.drawString(72, 640, "Interest Expense: $40,000,000")
        pdf.drawString(72, 620, "Net Income: $95,000,000")
        pdf.drawString(72, 600, "Cash and Equivalents: $300,000,000")
        pdf.drawString(72, 580, "Current Assets: $700,000,000")
        pdf.drawString(72, 560, "Accounts Receivable: $210,000,000")
        pdf.drawString(72, 540, "Inventory: $80,000,000")
        pdf.drawString(72, 520, "Total Assets: $2,600,000,000")
        pdf.drawString(72, 500, "Current Liabilities: $450,000,000")
        pdf.drawString(72, 480, "Long Term Debt: $850,000,000")
        pdf.drawString(72, 460, "Total Debt: $900,000,000")
        pdf.drawString(72, 440, "Total Liabilities: $1,500,000,000")
        pdf.drawString(72, 420, "Shareholders Equity: $1,100,000,000")
        pdf.drawString(72, 400, "Cash from Operations: $160,000,000")
        pdf.drawString(72, 380, "Accounts Payable: $190,000,000")
        pdf.save()

        data = self.parser.parse_pdf(str(pdf_path))

        assert data.fiscal_year == 2024
        assert data.revenue == 1_250_000_000.0
        assert data.total_debt == 900_000_000.0
        assert data.extraction_confidence >= 0.70
        assert "revenue" in data.original_text_references


def test_documents_router_imports_with_v2_paths():
    from api.documents.router import UPLOAD_DIR, router

    assert router.prefix == "/api/v1/documents"
    route_paths = {route.path for route in router.routes}
    assert "/api/v1/documents/upload" in route_paths
    assert "CREDIT_RISK_PROJECT_V1" not in str(UPLOAD_DIR)


def test_list_counterparties_service_filters_and_orders_by_name():
    TestingSessionLocal = make_test_session()
    with TestingSessionLocal() as db:
        db.add_all(
            [
                CounterpartyMaster(counterparty_name="Zulu Fuel Buyer", counterparty_type="airline", country="US"),
                CounterpartyMaster(counterparty_name="Alpha Airways", counterparty_type="airline", country="UK"),
                CounterpartyMaster(counterparty_name="Oceanic Logistics", counterparty_type="shipowner", country="GR"),
            ]
        )
        db.commit()

        all_rows = list_counterparties(db)
        filtered_rows = list_counterparties(db, search="air")

    assert [row.counterparty_name for row in all_rows] == [
        "Alpha Airways",
        "Oceanic Logistics",
        "Zulu Fuel Buyer",
    ]
    assert [row.counterparty_name for row in filtered_rows] == ["Alpha Airways"]


def test_counterparty_list_endpoint_supports_selector_search():
    TestingSessionLocal = make_test_session()
    with TestingSessionLocal() as db:
        db.add_all(
            [
                CounterpartyMaster(counterparty_name="Phase 16 Golden Airways", counterparty_type="airline", country="US"),
                CounterpartyMaster(counterparty_name="Marine Bunker Co", counterparty_type="shipowner", country="SG"),
            ]
        )
        db.commit()

    app = FastAPI()
    app.include_router(documents_router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/api/v1/documents/counterparties", params={"search": "Golden"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["counterparty_name"] == "Phase 16 Golden Airways"
    assert payload[0]["counterparty_type"] == "airline"


def test_document_schemas_validate_from_attributes():
    counterparty = CounterpartyCreate(
        counterparty_name="Demo Airline",
        counterparty_type="airline",
        country="US",
    )

    assert counterparty.counterparty_name == "Demo Airline"

    metrics = FinancialMetricsExtracted(
        id=1,
        uploaded_document_id=1,
        counterparty_id=1,
        fiscal_year=2024,
        revenue=Decimal("1250000000.00"),
        ebitda=Decimal("220000000.00"),
        net_income=Decimal("95000000.00"),
        total_assets=Decimal("2600000000.00"),
        total_liabilities=Decimal("1500000000.00"),
        total_debt=Decimal("900000000.00"),
        shareholders_equity=Decimal("1100000000.00"),
        currency="USD",
        extraction_confidence=Decimal("0.88"),
        missing_critical_fields=[],
        original_text_references={"revenue": "Total Revenue: $1,250,000,000"},
        extraction_warnings=[],
        created_at=datetime.now(UTC),
    )

    response = FinancialMetricsResponse.model_validate(metrics)

    assert response.revenue == 1_250_000_000.0
    assert response.total_debt == 900_000_000.0
    assert response.original_text_references["revenue"]


def test_document_orm_models_use_unified_base():
    assert CounterpartyMaster.metadata is Base.metadata
    assert UploadedDocument.metadata is Base.metadata
    assert FinancialMetricsExtracted.metadata is Base.metadata


def test_no_v1_paths_in_migrated_document_files():
    for file_path in [
        Path("api/documents/pdf_parser.py"),
        Path("api/documents/router.py"),
        Path("api/documents/schemas.py"),
    ]:
        assert "CREDIT_RISK_PROJECT_V1" not in file_path.read_text(encoding="utf-8")






