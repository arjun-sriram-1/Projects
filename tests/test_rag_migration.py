"""RAG migration safety tests for V2 Phase 11A."""

from pathlib import Path

from api.core.config import settings
from api.rag.retriever import lazy_faiss
from api.rag.retriever.policy_retriever import search_policy
from api.rag.router import router as rag_router


RAG_FILES = [path for path in Path("api/rag").rglob("*.py")]


def test_rag_router_imports_with_v2_paths():
    assert rag_router.prefix == "/api"
    route_paths = {route.path for route in rag_router.routes}
    assert "/api/health" in route_paths
    assert "/api/copilot" in route_paths
    assert "/api/memo" in route_paths
    assert "/api/portfolio" in route_paths


def test_missing_vector_artifacts_do_not_break_retriever_startup(tmp_path, monkeypatch):
    lazy_faiss._load_index.cache_clear()
    monkeypatch.setattr(lazy_faiss, "vector_store_path", lambda filename: str(tmp_path / filename))
    try:
        assert search_policy("credit tenor policy", k=1) == []
    finally:
        lazy_faiss._load_index.cache_clear()


def test_rag_vector_paths_use_v2_data_vector_store():
    assert settings.vector_store_dir == settings.data_dir / "vector_store"
    for file_path in RAG_FILES:
        text = file_path.read_text(encoding="utf-8-sig")
        assert "rag/data" not in text
        assert "rag\\data" not in text
        assert "rag/documents" not in text
        assert "rag\\documents" not in text
        if ".faiss" in text or ".pkl" in text:
            assert file_path.parent.name in {"retriever", "embeddings", "vector_store"}
    helper_text = Path("api/rag/retriever/lazy_faiss.py").read_text(encoding="utf-8-sig")
    assert "settings.vector_store_dir" in helper_text


def test_no_rag_artifacts_or_private_documents_were_copied():
    forbidden_suffixes = {".faiss", ".pkl"}
    copied_artifacts = [
        path for path in Path("api/rag").rglob("*")
        if path.is_file() and path.suffix.lower() in forbidden_suffixes
    ]
    assert copied_artifacts == []
    assert not Path("api/rag/data").exists()
    assert not Path("api/rag/documents").exists()


def test_no_legacy_imports_in_rag_code():
    forbidden = [
        "from rag.",
        "import rag.",
        "database.db_connection",
        "decision_engine.",
        "dashboard.components.database",
        "risk.credit_policy",
        "api.schemas",
        "models.phase2_orm",
        "models.credit",
        "models.ml",
        "CREDIT_RISK_PROJECT_V1",
    ]
    for file_path in RAG_FILES:
        text = file_path.read_text(encoding="utf-8-sig")
        for pattern in forbidden:
            assert pattern not in text
