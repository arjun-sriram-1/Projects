from fastapi import APIRouter

from api.core.config import settings
from api.db.session import SessionLocal, test_connection
from api.rag.agents.credit_memo_agent import generate_credit_memo
from api.rag.agents.master_router import route_query
from api.rag.data_access import (
    load_counterparties,
    load_portfolio,
    load_predictions,
    load_scenarios,
)
from api.rag.grounded_context import build_grounded_copilot_context
from api.rag.schemas import CopilotRequest, MemoRequest


router = APIRouter(prefix="/api", tags=["RAG"])


# ============================================
# HEALTH
# ============================================

@router.get("/health")
def health():
    return {"status": "healthy"}


@router.get("/copilot/health")
def copilot_health():
    vector_files = []
    for name in ["counterparty", "policy", "stress", "montecarlo"]:
        vector_files.append(f"{name}_index" + "." + "faiss")
        vector_files.append(f"{name}_metadata" + "." + "pkl")
    available_vectors = [
        filename
        for filename in vector_files
        if (settings.vector_store_dir / filename).exists()
    ]

    models: list[str] = []
    ollama_status = "unavailable"
    try:
        import requests

        response = requests.get(f"{settings.ollama_url.rstrip('/')}/api/tags", timeout=3)
        response.raise_for_status()
        payload = response.json()
        models = [item.get("name") for item in payload.get("models", []) if item.get("name")]
        ollama_status = "available"
    except Exception as exc:
        ollama_status = f"unavailable: {exc}"

    database_available = test_connection()
    return {
        "status": "healthy" if database_available else "degraded",
        "database": "available" if database_available else "unavailable",
        "ollama": ollama_status,
        "configured_model": settings.ollama_model,
        "model_available": settings.ollama_model in models,
        "selected_counterparty_answer_mode": "ollama_rag" if settings.copilot_use_llm else "grounded_sql_fast",
        "embeddings_model": settings.embeddings_model_name,
        "vector_store_dir": str(settings.vector_store_dir),
        "available_vector_files": available_vectors,
        "missing_vector_files": [
            filename for filename in vector_files if filename not in available_vectors
        ],
    }


# ============================================
# COPILOT
# ============================================

@router.post("/copilot")
def copilot(req: CopilotRequest):
    has_app_context = any(
        [
            req.counterparty_id,
            req.counterparty_name,
            req.page,
            req.visible_metrics,
        ]
    )
    if has_app_context:
        with SessionLocal() as db:
            grounded_context = build_grounded_copilot_context(
                db,
                counterparty_id=req.counterparty_id,
                counterparty_name=req.counterparty_name,
                page=req.page,
                visible_metrics=req.visible_metrics,
            )
        answer = route_query(req.question, grounded_context=grounded_context)
    else:
        answer = route_query(req.question)

    return {
        "question": req.question,
        "answer": answer,
        "counterparty_id": req.counterparty_id,
        "counterparty_name": req.counterparty_name,
        "page": req.page,
    }


# ============================================
# CREDIT MEMO
# ============================================

@router.post("/memo")
def memo(req: MemoRequest):
    memo_text = generate_credit_memo(req.company_name)
    return {"company": req.company_name, "memo": memo_text}


# ============================================
# PORTFOLIO
# ============================================

@router.get("/portfolio")
def portfolio():
    df = load_portfolio()
    return df.to_dict(orient="records")


# ============================================
# COUNTERPARTY
# ============================================

@router.get("/counterparty/{counterparty_id}")
def counterparty(counterparty_id: int):
    cp = load_counterparties()
    pred = load_predictions()
    df = cp.merge(pred, on="counterparty_id", how="left")
    row = df[df["counterparty_id"] == counterparty_id]
    if row.empty:
        return {"error": "counterparty not found"}
    return row.iloc[0].to_dict()


# ============================================
# STRESS
# ============================================

@router.get("/stress")
def stress():
    df = load_scenarios()
    return df.to_dict(orient="records")
