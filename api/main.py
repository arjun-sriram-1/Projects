"""FastAPI application entrypoint for CREDIT_RISK_PROJECT_V2."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.calibration.router import router as calibration_router
from api.copilot.router import router as copilot_knowledge_router
from api.core.config import settings
from api.credit_decision.router import router as credit_decision_router
from api.documents.router import router as documents_router
from api.financials.router import router as financials_router
from api.machine_learning.loss_router import router as loss_router
from api.machine_learning.router import router as pd_router
from api.market_data.router import router as market_data_router
from api.monitoring.router import router as monitoring_router
from api.portfolio_risk.router import router as portfolio_risk_router
from api.rag.router import router as rag_router
from api.reporting.router import router as reporting_router

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app() -> FastAPI:
    """Create the V2 FastAPI app without requiring live database access."""
    app = FastAPI(
        title="Fuel Credit Risk Platform V2",
        version="2.0.0",
        description="Migrated V2 backend for fuel trade credit risk workflows.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health():
        return {
            "status": "healthy",
            "app_env": settings.app_env,
            "version": "2.0.0",
        }

    app.include_router(documents_router)
    app.include_router(financials_router)
    app.include_router(market_data_router)
    app.include_router(monitoring_router)
    app.include_router(pd_router)
    app.include_router(loss_router)
    app.include_router(portfolio_risk_router)
    app.include_router(credit_decision_router)
    app.include_router(rag_router)
    app.include_router(reporting_router)
    app.include_router(calibration_router)
    app.include_router(copilot_knowledge_router)

    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIR),
        name="frontend-assets",
    )

    @app.get("/", include_in_schema=False)
    def frontend_home():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/ui", include_in_schema=False)
    def frontend_ui():
        return FileResponse(FRONTEND_DIR / "index.html")

    return app


app = create_app()


__all__ = ["app", "create_app"]

