"""Schemas for RAG/copilot endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CopilotRequest(BaseModel):
    question: str
    counterparty_id: Optional[int] = None
    counterparty_name: Optional[str] = None
    page: Optional[str] = None
    visible_metrics: Optional[Dict[str, Any]] = None


class MemoRequest(BaseModel):
    company_name: str


class Counterparty(BaseModel):
    revenue: float
    debt: float
    fleet_size: int
    fuel_dependency: float
    fx_exposure: float
    profit_margin: float
    exposure: Optional[float] = 1_000_000
    security: Optional[str] = "None"
    sector: Optional[str] = "Airline"


class PortfolioRequest(BaseModel):
    counterparties: List[Counterparty]
    n_simulations: Optional[int] = 100
