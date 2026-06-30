"""Foundation checks for the V2 package, config, DB base, and schema."""

from pathlib import Path


def test_core_config_paths_are_v2_local():
    from api.core.config import PROJECT_ROOT, settings

    assert PROJECT_ROOT.name == "CREDIT_RISK_PROJECT_V2"
    assert settings.data_dir == PROJECT_ROOT / "data"
    assert settings.model_artifact_dir == PROJECT_ROOT / "data" / "models"
    assert settings.vector_store_dir == PROJECT_ROOT / "data" / "vector_store"
    assert "CREDIT_RISK_PROJECT_V1" not in str(settings.data_dir)


def test_database_session_exports_import_without_connecting():
    from api.db import SessionLocal, engine, get_db

    assert engine is not None
    assert SessionLocal is not None
    assert callable(get_db)


def test_orm_models_use_unified_base():
    from api.db.base import Base
    from api.db.models import (
        CounterpartyMaster,
        FinancialMetricsExtracted,
        FinancialRatios,
        UploadedDocument,
    )

    assert CounterpartyMaster.metadata is Base.metadata
    assert UploadedDocument.metadata is Base.metadata
    assert FinancialMetricsExtracted.metadata is Base.metadata
    assert FinancialRatios.metadata is Base.metadata
    assert CounterpartyMaster.__tablename__ == "counterparties_master"
    assert FinancialRatios.__tablename__ == "financial_ratios"


def test_schema_file_exists_and_contains_core_tables():
    schema_path = Path("database/schema.sql")

    assert schema_path.exists()
    schema_text = schema_path.read_text(encoding="utf-8")
    for table_name in [
        "counterparties_master",
        "uploaded_documents",
        "financial_metrics_extracted",
        "financial_ratios",
        "credit_recommendations",
    ]:
        assert table_name in schema_text


def test_no_v1_paths_in_phase3_core_files():
    phase3_files = [
        Path("api/core/config.py"),
        Path("api/db/base.py"),
        Path("api/db/session.py"),
        Path("api/db/models.py"),
        Path("api/scripts/verify_schema.py"),
    ]

    for file_path in phase3_files:
        assert file_path.exists()
        assert "CREDIT_RISK_PROJECT_V1" not in file_path.read_text(encoding="utf-8")

