"""Schemas for project-aware copilot knowledge and trace endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)


class FormulaTraceRequest(BaseModel):
    target: str
    values: Optional[Dict[str, Any]] = None


class ProjectCopilotQueryRequest(BaseModel):
    question: str
    style: str = "casual_precise"
    use_llm: Optional[bool] = None
    values: Optional[Dict[str, Any]] = None
    retrieval_limit: int = Field(default=6, ge=1, le=15)


class MarketImpactRequest(BaseModel):
    factor: Optional[str] = None
    stress_record: Optional[Dict[str, Any]] = None


class CopilotEvaluationRequest(BaseModel):
    use_llm: Optional[bool] = False
    case_ids: Optional[list[str]] = None
    retrieval_limit: int = Field(default=7, ge=1, le=15)
