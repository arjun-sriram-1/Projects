"""Financial ratio engine tests for V2."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.base import Base
from api.db.models import (
    CounterpartyMaster,
    FinancialMetricsExtracted,
    FinancialRatios,
    UploadedDocument,
)
from api.db.session import get_db
from api.financials.router import router as financials_router
from api.financials.service import calculate_and_store_ratios, create_manual_financial_metrics
from api.financials.service import get_latest_financial_metrics_for_counterparty
from api.financials.schemas import ManualFinancialMetricsCreate
from api.financials.trends import calculate_trend_risk_overlay
from api.shared.financial_ratios import FORMULA_VERSION, calculate_financial_ratios


def sample_financials(**overrides):
    data = {
        "id": 77,
        "counterparty_id": 10,
        "uploaded_document_id": 20,
        "fiscal_year": 2024,
        "fiscal_period": "FY",
        "currency": "USD",
        "revenue": 1_000_000.0,
        "ebitda": 200_000.0,
        "ebit": 150_000.0,
        "interest_expense": 30_000.0,
        "net_income": 90_000.0,
        "cash_and_equivalents": 120_000.0,
        "accounts_receivable": 180_000.0,
        "inventory": 80_000.0,
        "current_assets": 500_000.0,
        "total_assets": 2_000_000.0,
        "current_liabilities": 250_000.0,
        "short_term_debt": 100_000.0,
        "current_portion_long_term_debt": 50_000.0,
        "long_term_debt": 450_000.0,
        "total_debt": 600_000.0,
        "total_liabilities": 1_100_000.0,
        "shareholders_equity": 900_000.0,
    }
    data.update(overrides)
    return data


def make_test_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def create_sample_financial_metrics(db):
    suffix = uuid4().hex
    counterparty = CounterpartyMaster(
        counterparty_name=f"Phase 5 Test Counterparty {suffix}",
        counterparty_type="airline",
        country="USA",
    )
    db.add(counterparty)
    db.commit()
    db.refresh(counterparty)

    document = UploadedDocument(
        counterparty_id=counterparty.id,
        filename=f"phase5_test_{suffix}.pdf",
        file_path=f"data/uploads/documents/phase5_test_{suffix}.pdf",
        document_type="annual_report",
        extraction_status="completed",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    metrics = FinancialMetricsExtracted(
        uploaded_document_id=document.id,
        counterparty_id=counterparty.id,
        fiscal_year=2024,
        fiscal_period="FY",
        currency="USD",
        revenue=Decimal("1000000.00"),
        ebitda=Decimal("200000.00"),
        ebit=Decimal("150000.00"),
        interest_expense=Decimal("30000.00"),
        net_income=Decimal("90000.00"),
        cash_and_equivalents=Decimal("120000.00"),
        accounts_receivable=Decimal("180000.00"),
        inventory=Decimal("80000.00"),
        current_assets=Decimal("500000.00"),
        total_assets=Decimal("2000000.00"),
        current_liabilities=Decimal("250000.00"),
        total_debt=Decimal("600000.00"),
        total_liabilities=Decimal("1100000.00"),
        shareholders_equity=Decimal("900000.00"),
        extraction_confidence=Decimal("0.95"),
    )
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    return counterparty, document, metrics


class TestFinancialRatioCalculator:
    def test_calculates_required_ratios(self):
        ratios = calculate_financial_ratios(sample_financials())

        assert ratios.current_ratio == 2.0
        assert ratios.quick_ratio == 1.2
        assert ratios.cash_ratio == 0.48
        assert ratios.working_capital == 250_000.0
        assert ratios.debt_to_equity == pytest.approx(0.666667, rel=1e-5)
        assert ratios.debt_to_ebitda == 3.0
        assert ratios.interest_coverage == 5.0
        assert ratios.net_margin == 0.09
        assert ratios.operating_margin == 0.15
        assert ratios.return_on_assets == 0.045
        assert ratios.return_on_equity == 0.1
        assert ratios.formula_version == FORMULA_VERSION
        assert ratios.currency == "USD"
        assert ratios.input_data_reference == "financial_metrics_extracted:77"

    def test_divide_by_zero_returns_none_and_warning_input(self):
        ratios = calculate_financial_ratios(
            sample_financials(current_liabilities=0.0, revenue=0.0)
        )

        assert ratios.current_ratio is None
        assert ratios.quick_ratio is None
        assert ratios.net_margin is None
        assert "current_liabilities_zero" in ratios.missing_inputs["current_ratio"]
        assert "revenue_zero" in ratios.missing_inputs["net_margin"]

    def test_missing_data_returns_none_instead_of_fake_values(self):
        ratios = calculate_financial_ratios(
            sample_financials(ebitda=None, shareholders_equity=None)
        )

        assert ratios.debt_to_ebitda is None
        assert ratios.debt_to_equity is None
        assert ratios.return_on_equity is None
        assert ratios.missing_inputs["debt_to_ebitda"] == ["ebitda"]

    def test_total_debt_can_be_derived_from_components(self):
        ratios = calculate_financial_ratios(sample_financials(total_debt=None))

        assert ratios.debt_to_ebitda == 3.0
        assert ratios.calculation_warnings

    def test_quick_ratio_requires_receivables_or_inventory_fallback(self):
        ratios = calculate_financial_ratios(
            sample_financials(accounts_receivable=None, inventory=None)
        )

        assert ratios.quick_ratio is None
        assert ratios.cash_ratio == 0.48
        assert ratios.missing_inputs["quick_ratio"] == [
            "cash_and_equivalents_plus_accounts_receivable"
        ]

    def test_quick_ratio_can_use_current_assets_less_inventory_fallback(self):
        ratios = calculate_financial_ratios(
            sample_financials(cash_and_equivalents=None, accounts_receivable=None)
        )

        assert ratios.quick_ratio == pytest.approx((500_000.0 - 80_000.0) / 250_000.0)
        assert "quick_assets were derived" in ratios.calculation_warnings[0]


class TestFinancialRatioPersistenceAndApi:
    def test_calculate_and_store_ratios(self):
        TestingSessionLocal = make_test_session()
        with TestingSessionLocal() as db:
            counterparty, _, metrics = create_sample_financial_metrics(db)

            ratio_record = calculate_and_store_ratios(db, metrics.id)

            assert ratio_record.id is not None
            assert ratio_record.counterparty_id == counterparty.id
            assert float(ratio_record.current_ratio) == 2.0
            assert float(ratio_record.debt_to_ebitda) == 3.0
            assert ratio_record.input_data_reference == (
                f"financial_metrics_extracted:{metrics.id}"
            )
            assert ratio_record.formula_version == FORMULA_VERSION

            updated_record = calculate_and_store_ratios(db, metrics.id)
            assert updated_record.id == ratio_record.id

    def test_create_manual_financial_metrics_stores_auditable_record(self):
        TestingSessionLocal = make_test_session()
        with TestingSessionLocal() as db:
            counterparty = CounterpartyMaster(
                counterparty_name=f"Manual Capture {uuid4().hex}",
                counterparty_type="airline",
                country="USA",
            )
            db.add(counterparty)
            db.commit()
            db.refresh(counterparty)

            metrics = create_manual_financial_metrics(
                db,
                ManualFinancialMetricsCreate(
                    counterparty_id=counterparty.id,
                    fiscal_year=2025,
                    currency="usd",
                    revenue=1_000_000.0,
                    ebitda=220_000.0,
                    operating_margin_percent=12.5,
                    net_income=80_000.0,
                    total_assets=2_100_000.0,
                    total_debt=650_000.0,
                    shareholders_equity=850_000.0,
                ),
            )

            assert metrics.id is not None
            assert metrics.uploaded_document.document_type == "manual_financial_statement"
            assert metrics.currency == "USD"
            assert float(metrics.ebit) == 125000.0
            assert metrics.extraction_warnings == [
                "manual_entry_no_pdf_source",
                "ebit_derived_from_operating_margin",
            ]

    def test_financials_api_calculate_ratios_endpoint(self):
        TestingSessionLocal = make_test_session()
        with TestingSessionLocal() as setup_db:
            counterparty, _, metrics = create_sample_financial_metrics(setup_db)
            metrics_id = metrics.id
            counterparty_id = counterparty.id

        app = FastAPI()
        app.include_router(financials_router)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        response = client.post(f"/api/v1/financial-analysis/ratios/calculate/{metrics_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["message"] == "Financial ratios calculated and stored."
        assert payload["ratios"]["current_ratio"] == 2.0
        assert payload["ratios"]["formula_version"] == FORMULA_VERSION

        latest = client.get(
            f"/api/v1/financial-analysis/counterparty/{counterparty_id}/latest-ratios"
        )
        assert latest.status_code == 200
        assert latest.json()["financial_metrics_id"] == metrics_id

    def test_financials_api_manual_capture_endpoint(self):
        TestingSessionLocal = make_test_session()
        with TestingSessionLocal() as setup_db:
            counterparty = CounterpartyMaster(
                counterparty_name=f"Manual API {uuid4().hex}",
                counterparty_type="airline",
                country="USA",
            )
            setup_db.add(counterparty)
            setup_db.commit()
            setup_db.refresh(counterparty)
            counterparty_id = counterparty.id

        app = FastAPI()
        app.include_router(financials_router)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        response = client.post(
            "/api/v1/financial-analysis/metrics/manual",
            json={
                "counterparty_id": counterparty_id,
                "fiscal_year": 2025,
                "currency": "USD",
                "revenue": 1_000_000,
                "ebitda": 200_000,
                "net_income": 90_000,
                "total_assets": 2_000_000,
                "total_debt": 600_000,
                "shareholders_equity": 900_000,
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["message"] == "Manual financial metrics captured."
        assert payload["metrics"]["counterparty_id"] == counterparty_id
        assert payload["metrics"]["extraction_warnings"] == ["manual_entry_no_pdf_source"]

    def test_financials_api_manual_batch_capture_preserves_latest_snapshot(self):
        TestingSessionLocal = make_test_session()
        with TestingSessionLocal() as setup_db:
            counterparty = CounterpartyMaster(
                counterparty_name=f"Manual Batch {uuid4().hex}",
                counterparty_type="airline",
                country="USA",
            )
            setup_db.add(counterparty)
            setup_db.commit()
            setup_db.refresh(counterparty)
            counterparty_id = counterparty.id

        app = FastAPI()
        app.include_router(financials_router)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        response = client.post(
            "/api/v1/financial-analysis/metrics/manual/batch",
            json={
                "counterparty_id": counterparty_id,
                "periods": [
                    {
                        "counterparty_id": counterparty_id,
                        "fiscal_year": 2025,
                        "period_type": "annual",
                        "period_label": "FY",
                        "is_latest_snapshot": True,
                        "currency": "USD",
                        "revenue": 1_200_000,
                        "ebitda": 240_000,
                        "net_income": 100_000,
                        "current_assets": 500_000,
                        "current_liabilities": 250_000,
                        "total_assets": 2_400_000,
                        "total_debt": 700_000,
                        "shareholders_equity": 1_000_000,
                    },
                    {
                        "counterparty_id": counterparty_id,
                        "fiscal_year": 2024,
                        "period_type": "annual",
                        "period_label": "FY",
                        "is_latest_snapshot": False,
                        "currency": "USD",
                        "revenue": 1_000_000,
                        "ebitda": 210_000,
                        "net_income": 80_000,
                        "current_assets": 420_000,
                        "current_liabilities": 240_000,
                        "total_assets": 2_100_000,
                        "total_debt": 650_000,
                        "shareholders_equity": 900_000,
                    },
                ],
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["message"] == "Manual financial history captured."
        assert len(payload["metrics"]) == 2
        assert payload["latest_metrics"]["fiscal_year"] == 2025
        assert payload["latest_metrics"]["period_type"] == "annual"
        assert payload["latest_metrics"]["period_label"] == "FY"
        assert payload["latest_metrics"]["is_latest_snapshot"] is True

        latest = client.get(
            f"/api/v1/financial-analysis/counterparty/{counterparty_id}/latest-ratios"
        )
        assert latest.status_code == 200
        assert latest.json()["fiscal_year"] == 2025

        history = client.get(
            f"/api/v1/financial-analysis/counterparty/{counterparty_id}/metrics-history"
        )
        assert history.status_code == 200
        history_payload = history.json()
        assert len(history_payload["periods"]) == 2
        assert history_payload["latest_metrics"]["fiscal_year"] == 2025

        older_id = next(
            item["id"] for item in history_payload["periods"] if item["fiscal_year"] == 2024
        )
        mark = client.post(
            f"/api/v1/financial-analysis/metrics/{older_id}/mark-latest"
        )
        assert mark.status_code == 200
        assert mark.json()["latest_metrics"]["fiscal_year"] == 2024

        latest_after_mark = client.get(
            f"/api/v1/financial-analysis/counterparty/{counterparty_id}/latest-ratios"
        )
        assert latest_after_mark.status_code == 200
        assert latest_after_mark.json()["fiscal_year"] == 2024

        trends = client.get(
            f"/api/v1/financial-analysis/counterparty/{counterparty_id}/trend-features"
        )
        assert trends.status_code == 200
        trend_payload = trends.json()
        assert trend_payload["period_count"] == 2
        assert trend_payload["history_status"] == "available"
        assert trend_payload["latest_revenue_growth"] is not None
        assert trend_payload["model_overlay"]["period_count"] == 2
        assert "pd_multiplier" in trend_payload["model_overlay"]

    def test_latest_snapshot_prefers_materially_more_complete_newer_period(self):
        TestingSessionLocal = make_test_session()
        with TestingSessionLocal() as db:
            counterparty = CounterpartyMaster(
                counterparty_name=f"Complete Latest {uuid4().hex}",
                counterparty_type="airline",
                country="USA",
            )
            db.add(counterparty)
            db.commit()
            db.refresh(counterparty)

            older_incomplete = create_manual_financial_metrics(
                db,
                ManualFinancialMetricsCreate(
                    counterparty_id=counterparty.id,
                    fiscal_year=2025,
                    is_latest_snapshot=True,
                    revenue=1_000_000,
                    ebitda=200_000,
                    net_income=80_000,
                    cash_and_equivalents=120_000,
                    current_assets=500_000,
                    current_liabilities=250_000,
                    total_assets=2_000_000,
                    total_debt=600_000,
                    total_liabilities=1_100_000,
                    shareholders_equity=900_000,
                    interest_expense=30_000,
                ),
            )
            newer_complete = create_manual_financial_metrics(
                db,
                ManualFinancialMetricsCreate(
                    counterparty_id=counterparty.id,
                    fiscal_year=2026,
                    is_latest_snapshot=False,
                    revenue=1_000_000,
                    ebitda=200_000,
                    ebit=150_000,
                    interest_expense=30_000,
                    net_income=90_000,
                    cash_and_equivalents=120_000,
                    accounts_receivable=180_000,
                    inventory=80_000,
                    current_assets=500_000,
                    current_liabilities=250_000,
                    total_assets=2_000_000,
                    total_debt=600_000,
                    total_liabilities=1_100_000,
                    shareholders_equity=900_000,
                ),
            )

            latest = get_latest_financial_metrics_for_counterparty(db, counterparty.id)

            assert older_incomplete.id != newer_complete.id
            assert latest.id == newer_complete.id

    def test_financial_trend_overlay_is_neutral_until_history_exists(self):
        overlay = calculate_trend_risk_overlay(
            {
                "period_count": 1,
                "history_status": "insufficient_history",
            }
        )

        assert overlay["pd_multiplier"] == 1.0
        assert overlay["lgd_addon"] == 0.0
        assert overlay["direction"] == "neutral"

    def test_financial_trend_overlay_flags_deteriorating_history(self):
        overlay = calculate_trend_risk_overlay(
            {
                "period_count": 3,
                "history_status": "available",
                "revenue_cagr": -0.08,
                "latest_revenue_growth": -0.12,
                "ebitda_margin_trend": -0.03,
                "debt_growth": 0.22,
                "interest_coverage_trend": -1.0,
                "current_ratio_trend": -0.25,
                "cash_trend": -0.18,
                "current_ratio_latest": 0.85,
            }
        )

        assert overlay["direction"] == "deteriorating"
        assert overlay["pd_multiplier"] > 1.0
        assert overlay["lgd_addon"] > 0.0
        assert 0.0 < overlay["liquidity_score"] < 1.0

    def test_financials_api_returns_404_for_missing_financial_metrics(self):
        TestingSessionLocal = make_test_session()
        app = FastAPI()
        app.include_router(financials_router)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        response = client.post("/api/v1/financial-analysis/ratios/calculate/999999999")
        assert response.status_code == 404


def test_no_v1_imports_in_migrated_financial_files():
    files = [
        "api/shared/financial_ratios.py",
        "api/financials/service.py",
        "api/financials/router.py",
        "api/financials/schemas.py",
    ]
    forbidden = [
        "analytics.",
        "database.db_connection",
        "models.phase2_orm",
        "api.schemas_phase3",
        "CREDIT_RISK_PROJECT_V1",
    ]

    for file_path in files:
        text = open(file_path, encoding="utf-8").read()
        for pattern in forbidden:
            assert pattern not in text
