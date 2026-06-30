"""Project-aware copilot knowledge and formula trace tests."""

from fastapi.testclient import TestClient

from api.copilot.formula_trace import trace_formula
from api.copilot.knowledge import (
    describe_field,
    get_catalog_status,
    get_formula,
    search_knowledge,
)
from api.copilot.grounded_llm import answer_project_question
from api.copilot.local_retriever import retrieval_status, retrieve_project_context
from api.copilot.market_trace import explain_market_factor
from api.copilot.evaluation import run_copilot_evaluation
from api.copilot.question_router import classify_project_question
from api.copilot.router import router
from api.rag.agents.master_router import route_query
from api.rag.grounded_context import GroundedCopilotContext


def test_knowledge_catalogs_load_with_expected_counts():
    status = get_catalog_status()

    assert status["status"] == "ready"
    assert status["counts"]["fields"] >= 25
    assert status["counts"]["formulas"] >= 20
    assert status["counts"]["models"] >= 8
    assert status["counts"]["pipeline_stages"] >= 10


def test_field_lookup_links_formula_and_sources():
    result = describe_field("final_pd")

    assert result is not None
    assert result["field"]["field"] == "final_pd"
    assert result["formula"]["formula_id"] == "final_pd_blend"
    assert any(model["model_id"] == "pd_blend" for model in result["models"])


def test_formula_lookup_resolves_by_field_name():
    formula = get_formula("expected_loss")

    assert formula is not None
    assert formula["formula_id"] == "expected_loss"
    assert "probability_of_default" in formula["inputs"]


def test_search_knowledge_finds_pca_and_market_stress():
    results = search_knowledge("how does pca market stress work", limit=5)

    kinds = {row["kind"] for row in results}
    assert "formula" in kinds or "field" in kinds or "model" in kinds
    assert any("pca" in str(row["item"]).lower() for row in results)


def test_search_knowledge_finds_expanded_market_indicators():
    results = search_knowledge("how do opec production iata passenger traffic crack spread and inventories affect pca", limit=8)
    joined = " ".join(str(row["item"]).lower() for row in results)

    assert "opec" in joined
    assert "iata" in joined
    assert "crack spread" in joined
    assert "inventor" in joined


def test_local_retriever_indexes_project_docs_and_catalogs():
    status = retrieval_status()

    assert status["status"] == "ready"
    assert status["retriever"] == "local_tfidf"
    assert status["uses_paid_resources"] is False
    assert status["chunk_count"] > 20


def test_local_retriever_finds_expected_loss_context():
    results = retrieve_project_context("How is expected loss calculated?", limit=5)

    assert results
    joined = " ".join(result["text"].lower() for result in results)
    assert "expected loss" in joined
    assert "pd" in joined or "probability_of_default" in joined


def test_question_router_classifies_project_intents():
    assert classify_project_question("How is expected loss calculated?").intent == "formula_trace"
    assert classify_project_question("How does PCA affect market stress?").intent == "market_pca_explanation"
    assert classify_project_question("Where does final PD come from?").intent == "data_lineage"
    assert classify_project_question("Explain this project to an interviewer").intent == "interview_explanation"


def test_market_factor_trace_explains_pca_chain():
    result = explain_market_factor(
        factor="Brent oil",
        stress_record={
            "stress_index": 60,
            "pc1_score": 1.2,
            "explained_variance_ratio": 0.44,
            "pca_loadings": {"brent_return_zscore": 0.5, "vix_zscore": 0.3},
            "component_values": {"brent_return_zscore": 1.4, "vix_zscore": 0.2},
        },
    )

    assert result["stress_index"] == 60
    assert result["selected_components"][0]["component"] == "brent_return_zscore"
    assert result["selected_components"][0]["pc1_contribution"] == 0.7
    assert "stress_index = percentile_scale(pc1_score)" in result["formulas"]


def test_market_factor_trace_covers_new_supply_and_demand_components():
    result = explain_market_factor(
        factor="OPEC production and IATA traffic",
        stress_record={
            "stress_index": 68,
            "pca_loadings": {
                "opec_production_cut_zscore": 0.4,
                "iata_traffic_loss_zscore": 0.3,
                "vix_zscore": 0.2,
            },
            "component_values": {
                "opec_production_cut_zscore": 1.5,
                "iata_traffic_loss_zscore": 2.0,
                "vix_zscore": 0.5,
            },
        },
    )

    components = {row["component"] for row in result["selected_components"]}
    assert "opec_production_cut_zscore" in components
    assert "iata_traffic_loss_zscore" in components


def test_expected_loss_trace_calculates_numeric_result():
    result = trace_formula(
        "expected_loss",
        {
            "probability_of_default": 0.048,
            "loss_given_default": 0.20,
            "exposure_at_default": 3_500_000,
        },
    )

    assert result["matched"] is True
    assert result["result"] == 33_600
    assert result["missing_inputs"] == []


def test_final_pd_trace_uses_default_calibrated_weights():
    result = trace_formula("final_pd", {"structural_pd": 0.02, "ml_pd": 0.10})

    assert result["formula_id"] == "final_pd_blend"
    assert round(result["result"], 6) == 0.068
    assert "0.4000" in result["calculation"]


def test_risk_grade_trace_maps_pd_band():
    result = trace_formula("risk_grade", {"final_pd": 0.048})

    assert result["result"] == "BB"
    assert result["missing_inputs"] == []


def test_grounded_query_uses_local_retrieval_without_llm():
    result = answer_project_question(
        "How is expected loss calculated?",
        use_llm=False,
        values={
            "probability_of_default": 0.05,
            "loss_given_default": 0.40,
            "exposure_at_default": 1000000,
        },
    )

    assert result["mode"] == "local_retrieval_no_llm"
    assert result["route"]["intent"] == "formula_trace"
    assert result["uses_paid_resources"] is False
    assert round(result["trace"]["result"], 2) == 20000
    assert "expected loss" in result["answer"].lower()


def test_field_question_answers_exact_ratio_and_credit_terms_impact():
    result = answer_project_question(
        "what does current ratio mean and how does it affect credit terms",
        use_llm=False,
    )

    answer = result["answer"].lower()
    assert result["route"]["intent"] == "field_definition"
    assert result["field_context"]["field"]["field"] == "current_ratio"
    assert "current ratio means" in answer
    assert "credit terms" in answer
    assert "cash ratio shows" not in answer
    assert "closest project source" not in answer
    assert "current_assets / current_liabilities" not in result["answer"]


def test_field_impact_questions_route_to_named_field_not_neighbor_ratio():
    result = answer_project_question(
        "how does Debt/EBITDA affect credit terms",
        use_llm=False,
    )

    answer = result["answer"].lower()
    assert result["route"]["intent"] == "field_definition"
    assert result["field_context"]["field"]["field"] == "debt_to_ebitda"
    assert "debt to ebitda means" in answer
    assert "credit terms" in answer
    assert "cash ratio shows" not in answer
    assert "source_files" not in answer


def test_copilot_answer_cleans_source_and_catalog_artifacts():
    result = answer_project_question(
        "what does current ratio mean and how does it affect credit terms",
        use_llm=False,
    )

    answer = result["answer"].lower()
    blocked = ["sources used", "closest project source", "source_files", "source_tables", "api/rag/"]
    assert all(token not in answer for token in blocked)


def test_default_market_question_reads_like_conversation_not_trace_dump():
    result = answer_project_question(
        "how does the fuel price affect the credit recommendation?",
        use_llm=False,
        values={"stress_index": 55, "final_pd": 0.048, "recommended_limit": 8_100_000},
    )

    answer = result["answer"].lower()
    assert result["answer_mode"] == "simple_explanation"
    assert "fuel prices matter" in answer
    assert "credit recommendation" in answer
    assert "pca" not in answer
    assert "pc1" not in answer
    assert "z-score" not in answer
    assert "source_files" not in answer
    assert len([line for line in result["answer"].splitlines() if line.strip()]) <= 9


def test_legacy_grounded_copilot_does_not_append_sources():
    context = GroundedCopilotContext(
        counterparty={"id": 1, "counterparty_name": "Demo Airline"},
        ratios={"current_ratio": 1.6, "quick_ratio": 1.2},
        source_notes=["unit-test source note"],
    )

    answer = route_query("what does current ratio mean", grounded_context=context)

    assert "Sources used" not in answer
    assert "unit-test source note" not in answer


def test_grounded_market_answer_mentions_expanded_market_indicators():
    context = GroundedCopilotContext(
        counterparty={"id": 1, "counterparty_name": "Demo Airline"},
        pd={"final_pd": 0.05, "market_stress_index": 62},
        loss={"predicted_lgd": 0.4, "exposure_at_default": 1_000_000, "expected_loss": 20_000},
        recommendation={"approval_status": "Approve with conditions", "risk_grade": "BB"},
        stress={"stress_index": 62},
        regime={"regime_label": "Commodity Stress"},
        market_prices=[
            {"asset": "jet_crack_spread", "asset_name": "Jet Crack Spread", "price": 28.0, "units": "usd_per_barrel", "date": "2024-01-31"},
            {"asset": "opec_production", "asset_name": "OPEC Production", "price": 26000.0, "units": "kbd", "date": "2024-01-31"},
            {"asset": "iata_passenger_traffic", "asset_name": "IATA Passenger Traffic", "price": 95.0, "units": "index", "date": "2024-01-31"},
        ],
    )

    answer = route_query("How do OPEC, IATA traffic, inventories, and crack spread affect credit terms?", grounded_context=context)
    lower = answer.lower()

    assert "crack spread" in lower
    assert "opec" in lower
    assert "iata" in lower
    assert "sources used" not in lower


def test_copilot_evaluation_suite_passes_without_llm():
    result = run_copilot_evaluation(use_llm=False)

    assert result["status"] == "passed"
    assert result["total"] >= 8
    assert result["failed"] == 0
    assert result["uses_paid_resources"] is False


def test_copilot_knowledge_router_endpoints():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    status = client.get("/api/v1/copilot/knowledge/status")
    assert status.status_code == 200
    assert status.json()["status"] == "ready"

    health = client.get("/api/v1/copilot/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert health.json()["uses_paid_resources"] is False

    capabilities = client.get("/api/v1/copilot/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()["query"] == "POST /api/v1/copilot/query"

    suggestions = client.get("/api/v1/copilot/suggestions", params={"page": "models"})
    assert suggestions.status_code == 200
    assert suggestions.json()["page"] == "models"
    assert suggestions.json()["page_specific"]

    eval_questions = client.get("/api/v1/copilot/evaluation/questions")
    assert eval_questions.status_code == 200
    assert eval_questions.json()["cases"]

    eval_run = client.post("/api/v1/copilot/evaluation/run", json={"use_llm": False})
    assert eval_run.status_code == 200
    assert eval_run.json()["status"] == "passed"

    fields = client.get("/api/v1/copilot/fields")
    assert fields.status_code == 200
    assert fields.json()["count"] >= 25

    formulas = client.get("/api/v1/copilot/formulas")
    assert formulas.status_code == 200
    assert formulas.json()["count"] >= 20

    models = client.get("/api/v1/copilot/models")
    assert models.status_code == 200
    assert models.json()["count"] >= 8

    pipeline = client.get("/api/v1/copilot/pipeline")
    assert pipeline.status_code == 200
    assert pipeline.json()["count"] >= 10

    field = client.get("/api/v1/copilot/fields/final_pd")
    assert field.status_code == 200
    assert field.json()["formula"]["formula_id"] == "final_pd_blend"

    trace = client.post(
        "/api/v1/copilot/trace",
        json={
            "target": "expected_loss",
            "values": {
                "probability_of_default": 0.05,
                "loss_given_default": 0.40,
                "exposure_at_default": 1000000,
            },
        },
    )
    assert trace.status_code == 200
    assert round(trace.json()["result"], 2) == 20000

    retrieval = client.get("/api/v1/copilot/retrieval/status")
    assert retrieval.status_code == 200
    assert retrieval.json()["retriever"] == "local_tfidf"

    route = client.post("/api/v1/copilot/route", json={"query": "How does PCA affect PD?"})
    assert route.status_code == 200
    assert route.json()["route"]["intent"] == "market_pca_explanation"

    market = client.post(
        "/api/v1/copilot/market-impact",
        json={
            "factor": "DXY",
            "stress_record": {
                "pca_loadings": {"dxy_return_zscore": 0.4},
                "component_values": {"dxy_return_zscore": 2.0},
            },
        },
    )
    assert market.status_code == 200
    assert market.json()["selected_components"][0]["pc1_contribution"] == 0.8

    query = client.post(
        "/api/v1/copilot/query",
        json={
            "question": "How is final PD calculated?",
            "use_llm": False,
            "values": {"structural_pd": 0.02, "ml_pd": 0.10},
        },
    )
    assert query.status_code == 200
    assert query.json()["mode"] == "local_retrieval_no_llm"
    assert round(query.json()["trace"]["result"], 6) == 0.068
