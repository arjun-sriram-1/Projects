"""Schemas for reporting/export API endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoExportRequest(BaseModel):
    question: str = Field(..., min_length=1)
    output_dir: Optional[str] = None
    docx_filename: Optional[str] = None
    pdf_filename: Optional[str] = None


class MemoExportResponse(BaseModel):
    memo: str
    docx: str
    pdf: str
    source: str


class RiskReportExportResponse(BaseModel):
    report_file: str
    company_name: Optional[str] = None
    total_exposure: float
    total_expected_loss: float
    avg_pd: float
    avg_lgd: float
    source: str
class ModelValidationRequest(BaseModel):
    predicted_pd: Optional[List[float]] = None
    observed_default: Optional[List[int]] = None
    predicted_lgd: Optional[List[float]] = None
    observed_lgd: Optional[List[float]] = None
    forecast_actual: Optional[List[float]] = None
    forecast_predicted: Optional[List[float]] = None


class ValidationMetricResponse(BaseModel):
    name: str
    value: float
    interpretation: str


class ModelValidationResponse(BaseModel):
    model_name: str
    model_version: str
    validation_scope: List[str]
    metrics: List[ValidationMetricResponse]
    sanity_checks: Dict[str, bool]
    assumptions: Dict[str, Any]
    limitations: List[str]
    markdown_report: str
    created_at: str

