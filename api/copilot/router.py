"""API routes for the project-aware copilot knowledge layer."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.core.config import settings
from api.copilot.evaluation import load_eval_questions, run_copilot_evaluation
from api.copilot.grounded_llm import answer_project_question
from api.copilot.formula_trace import trace_formula
from api.copilot.knowledge import (
    describe_field,
    get_catalog_status,
    get_field,
    get_formula,
    get_model,
    get_pipeline_stage,
    get_source,
    list_fields,
    list_formulas,
    list_models,
    list_pipeline_stages,
    list_sources,
    reload_knowledge_catalogs,
    search_knowledge,
)
from api.copilot.local_retriever import (
    reload_local_retrieval_index,
    retrieval_status,
    retrieve_project_context,
)
from api.copilot.market_trace import explain_market_factor
from api.copilot.question_router import classify_project_question, route_to_dict
from api.copilot.schemas import (
    FormulaTraceRequest,
    KnowledgeSearchRequest,
    CopilotEvaluationRequest,
    MarketImpactRequest,
    ProjectCopilotQueryRequest,
)
from api.copilot.suggestions import get_suggestions


router = APIRouter(prefix="/api/v1/copilot", tags=["copilot-knowledge"])


@router.get("/health")
def copilot_health() -> dict:
    """Return readiness for the finalized project-aware copilot API."""
    knowledge = get_catalog_status()
    retrieval = retrieval_status()
    return {
        "status": "healthy"
        if knowledge["status"] == "ready" and retrieval["status"] == "ready"
        else "degraded",
        "api_version": "project_copilot_v1",
        "answer_modes": [
            "local_retrieval_no_llm",
            "ollama_grounded_project_context",
            "local_retrieval_fallback_after_llm_error",
        ],
        "llm": {
            "provider": "ollama_local",
            "enabled_by_default": settings.copilot_use_llm,
            "configured_model": settings.ollama_model,
            "url": settings.ollama_url,
            "requires_paid_api": False,
        },
        "knowledge": knowledge,
        "retrieval": {
            "retriever": retrieval["retriever"],
            "chunk_count": retrieval["chunk_count"],
            "source_count": retrieval["source_count"],
            "requires_network": retrieval["requires_network"],
        },
        "capabilities": [
            "field_lookup",
            "formula_trace",
            "market_pca_trace",
            "local_project_retrieval",
            "question_routing",
            "source_citations",
            "informal_answer_style",
        ],
        "uses_paid_resources": False,
    }


@router.get("/capabilities")
def copilot_capabilities() -> dict:
    """Return a compact map of the final copilot API surface."""
    return {
        "query": "POST /api/v1/copilot/query",
        "route": "POST /api/v1/copilot/route",
        "trace": "POST /api/v1/copilot/trace",
        "market_impact": "POST /api/v1/copilot/market-impact",
        "evaluation": "POST /api/v1/copilot/evaluation/run",
        "field_lookup": "GET /api/v1/copilot/fields/{field_name}",
        "formula_lookup": "GET /api/v1/copilot/formulas/{formula_id}",
        "retrieval_search": "POST /api/v1/copilot/retrieval/search",
        "knowledge_search": "POST /api/v1/copilot/knowledge/search",
        "suggestions": "GET /api/v1/copilot/suggestions?page=models",
        "free_resource_policy": "Local catalogs, local project files, free-source calibration artifacts, and optional local Ollama only.",
    }


@router.get("/knowledge/status")
def knowledge_status() -> dict:
    """Return catalog readiness and counts."""
    return get_catalog_status()


@router.post("/knowledge/reload")
def knowledge_reload() -> dict:
    """Reload catalog JSON from disk."""
    reload_knowledge_catalogs()
    return get_catalog_status()


@router.get("/retrieval/status")
def local_retrieval_status() -> dict:
    """Return local retrieval readiness and indexed source count."""
    return retrieval_status()


@router.post("/retrieval/reload")
def local_retrieval_reload() -> dict:
    """Rebuild the local retrieval index from project files."""
    reload_local_retrieval_index()
    return retrieval_status()


@router.post("/knowledge/search")
def knowledge_search(req: KnowledgeSearchRequest) -> dict:
    """Search across fields, formulas, models, sources, and pipeline stages."""
    return {"query": req.query, "results": search_knowledge(req.query, limit=req.limit)}


@router.get("/suggestions")
def copilot_suggestions(page: str | None = None) -> dict:
    """Return copilot prompt suggestions for a page or default workflow."""
    return get_suggestions(page)


@router.get("/evaluation/questions")
def copilot_evaluation_questions() -> dict:
    """Return the regression question set used for copilot evaluation."""
    return load_eval_questions()


@router.post("/evaluation/run")
def copilot_evaluation_run(req: CopilotEvaluationRequest) -> dict:
    """Run project-aware copilot evaluation questions through the backend."""
    return run_copilot_evaluation(
        use_llm=req.use_llm,
        case_ids=req.case_ids,
        retrieval_limit=req.retrieval_limit,
    )


@router.get("/fields")
def field_list() -> dict:
    """Return all field catalog entries."""
    fields = list_fields()
    return {"fields": fields, "count": len(fields)}


@router.get("/formulas")
def formula_list() -> dict:
    """Return all formula catalog entries."""
    formulas = list_formulas()
    return {"formulas": formulas, "count": len(formulas)}


@router.get("/models")
def model_list() -> dict:
    """Return all model catalog entries."""
    models = list_models()
    return {"models": models, "count": len(models)}


@router.get("/pipeline")
def pipeline_list() -> dict:
    """Return all pipeline stages."""
    stages = list_pipeline_stages()
    return {"stages": stages, "count": len(stages)}


@router.get("/sources")
def source_list() -> dict:
    """Return all source catalog entries."""
    sources = list_sources()
    return {"sources": sources, "count": len(sources)}


@router.post("/retrieval/search")
def local_retrieval_search(req: KnowledgeSearchRequest) -> dict:
    """Search local project docs/catalogs/code with free TF-IDF retrieval."""
    return {
        "query": req.query,
        "results": retrieve_project_context(req.query, limit=req.limit),
    }


@router.post("/route")
def project_question_route(req: KnowledgeSearchRequest) -> dict:
    """Classify a question before answer generation."""
    return {"query": req.query, "route": route_to_dict(classify_project_question(req.query))}


@router.get("/fields/{field_name}")
def field_lookup(field_name: str) -> dict:
    """Return field metadata with linked formula/model/source context."""
    result = describe_field(field_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Unknown copilot field: {field_name}")
    return result


@router.get("/formulas/{formula_id}")
def formula_lookup(formula_id: str) -> dict:
    """Return a formula catalog entry."""
    result = get_formula(formula_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Unknown formula: {formula_id}")
    return result


@router.get("/models/{model_id}")
def model_lookup(model_id: str) -> dict:
    """Return a model catalog entry."""
    result = get_model(model_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    return result


@router.get("/pipeline/{stage_id}")
def pipeline_lookup(stage_id: str) -> dict:
    """Return a pipeline stage entry."""
    result = get_pipeline_stage(stage_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Unknown pipeline stage: {stage_id}")
    return result


@router.get("/sources/{source_id}")
def source_lookup(source_id: str) -> dict:
    """Return a source catalog entry."""
    result = get_source(source_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source_id}")
    return result


@router.post("/trace")
def formula_trace(req: FormulaTraceRequest) -> dict:
    """Trace a formula or field with optional input values."""
    return trace_formula(req.target, req.values or {})


@router.post("/market-impact")
def market_impact(req: MarketImpactRequest) -> dict:
    """Explain how a market/PCA factor flows into project credit outputs."""
    return explain_market_factor(factor=req.factor, stress_record=req.stress_record or {})


@router.post("/query")
def project_copilot_query(req: ProjectCopilotQueryRequest) -> dict:
    """Answer using local project retrieval plus optional grounded Ollama/Qwen."""
    return answer_project_question(
        req.question,
        style=req.style,
        use_llm=req.use_llm,
        values=req.values or {},
        retrieval_limit=req.retrieval_limit,
    )
