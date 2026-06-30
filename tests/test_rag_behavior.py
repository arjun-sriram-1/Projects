"""RAG behavior and local fallback tests for V2 Phase 11B."""

from fastapi.testclient import TestClient

from api.rag.llm import credit_copilot
from api.rag.retriever.context_builder import MISSING_RETRIEVAL_CONTEXT, build_context
from api.rag.retriever import lazy_faiss, multi_index_retriever
from api.rag.router import router as rag_router
from fastapi import FastAPI


def test_build_context_reports_missing_retrieval_context():
    context = build_context([])

    assert "RETRIEVED CREDIT RISK CONTEXT" in context
    assert MISSING_RETRIEVAL_CONTEXT in context
    assert "Do not invent financial numbers" in context


def test_build_context_includes_only_supplied_documents():
    context = build_context(["Policy: LC required for high-risk obligors.", "", "Tenor cap: 30 days."])

    assert "Policy: LC required" in context
    assert "Tenor cap: 30 days" in context
    assert MISSING_RETRIEVAL_CONTEXT not in context


def test_retrieve_context_routes_policy_question_without_vector_artifacts(monkeypatch):
    calls = []

    def fake_policy(query, k=2):
        calls.append((query, k))
        return ["Policy source: require confirmed LC for weak counterparties."]

    monkeypatch.setattr(multi_index_retriever, "search_policy", fake_policy)

    context = multi_index_retriever.retrieve_context("What is the credit policy for tenor and security?")

    assert calls
    assert "Policy source" in context
    assert MISSING_RETRIEVAL_CONTEXT not in context


def test_retrieve_context_empty_results_tell_generation_data_is_missing(monkeypatch):
    monkeypatch.setattr(multi_index_retriever, "search_counterparty", lambda query: [])
    monkeypatch.setattr(multi_index_retriever, "search_policy", lambda query: [])

    context = multi_index_retriever.retrieve_context("Tell me about Unknown Jet Fuel LLC")

    assert MISSING_RETRIEVAL_CONTEXT in context


def test_vector_search_returns_empty_when_embedding_model_unavailable(monkeypatch):
    class DummyIndex:
        def search(self, embedding, k):
            raise AssertionError("search should not run when embedding model fails")

    lazy_faiss._embedding_model.cache_clear()
    monkeypatch.setattr(
        lazy_faiss,
        "_load_index",
        lambda index_path, metadata_path: (DummyIndex(), {"documents": ["stored doc"]}),
    )
    monkeypatch.setattr(
        lazy_faiss,
        "_embedding_model",
        lambda: (_ for _ in ()).throw(RuntimeError("offline embedding model")),
    )

    assert lazy_faiss.search_index("PD driver", "counterparty_index.faiss", "counterparty_metadata.pkl", 1) == []


def test_credit_copilot_uses_retrieved_context_before_generation(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        credit_copilot,
        "retrieve_context",
        lambda question: "Grounded source: expected loss is stored in loss_estimates.",
    )

    def fake_generate_response(prompt):
        captured["prompt"] = prompt
        return "Answered from retrieved context."

    monkeypatch.setattr(credit_copilot, "generate_response", fake_generate_response)

    answer = credit_copilot.ask_credit_copilot("Explain expected loss")

    assert answer == "Answered from retrieved context."
    assert "Grounded source" in captured["prompt"]
    assert "Explain expected loss" in captured["prompt"]


def test_rag_router_uses_v2_handlers_with_local_fallback(monkeypatch):
    app = FastAPI()
    app.include_router(rag_router)

    monkeypatch.setattr("api.rag.router.route_query", lambda question: f"routed: {question}")
    monkeypatch.setattr("api.rag.router.generate_credit_memo", lambda company: f"memo for {company}")

    client = TestClient(app)

    health = client.get("/api/health")
    copilot = client.post("/api/copilot", json={"question": "What is portfolio VaR?"})
    memo = client.post("/api/memo", json={"company_name": "Acme Fuel"})

    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert copilot.status_code == 200
    assert copilot.json()["answer"] == "routed: What is portfolio VaR?"
    assert memo.status_code == 200
    assert memo.json()["memo"] == "memo for Acme Fuel"


def test_rag_router_passes_selected_counterparty_context(monkeypatch):
    app = FastAPI()
    app.include_router(rag_router)

    captured = {}

    class DummySession:
        def __enter__(self):
            return "db-session"

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_context(db, **kwargs):
        captured["db"] = db
        captured["context_kwargs"] = kwargs
        return "grounded-context"

    def fake_route(question, grounded_context=None):
        captured["question"] = question
        captured["grounded_context"] = grounded_context
        return "counterparty-specific answer"

    monkeypatch.setattr("api.rag.router.SessionLocal", lambda: DummySession())
    monkeypatch.setattr("api.rag.router.build_grounded_copilot_context", fake_context)
    monkeypatch.setattr("api.rag.router.route_query", fake_route)

    client = TestClient(app)
    response = client.post(
        "/api/copilot",
        json={
            "question": "Why is PD high?",
            "counterparty_id": 42,
            "counterparty_name": "Indigo",
            "page": "models",
            "visible_metrics": {"pd": 0.08},
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "counterparty-specific answer"
    assert captured["db"] == "db-session"
    assert captured["question"] == "Why is PD high?"
    assert captured["grounded_context"] == "grounded-context"
    assert captured["context_kwargs"]["counterparty_id"] == 42
    assert captured["context_kwargs"]["page"] == "models"
