"""
Pydantic schemas for Phase 2 API validation.
"""

from datetime import datetime
from typing import Optional, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class CounterpartyBase(BaseModel):
    """Base schema for counterparty."""

    counterparty_name: str
    counterparty_type: Optional[str] = None
    country: Optional[str] = None


class CounterpartyCreate(CounterpartyBase):
    """Schema for creating a counterparty."""

    pass


class CounterpartyResponse(CounterpartyBase):
    """Schema for counterparty response."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class UploadedDocumentBase(BaseModel):
    """Base schema for uploaded document."""

    filename: str
    document_type: Optional[str] = "annual_report"
    created_by: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Response when a document is uploaded."""

    id: int
    counterparty_id: int
    filename: str
    file_path: str
    extraction_status: str
    uploaded_at: datetime
    message: str = "Document uploaded successfully. Extraction queued."
    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    """Response for document status query."""

    id: int
    counterparty_id: int
    filename: str
    extraction_status: str
    extraction_error: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class FinancialMetricsResponse(BaseModel):
    """Response for extracted financial metrics."""

    id: int
    uploaded_document_id: int
    counterparty_id: int
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None

    # Key metrics
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_debt: Optional[float] = None
    shareholders_equity: Optional[float] = None

    # Metadata
    currency: Optional[str] = "USD"
    extraction_confidence: Optional[float] = None
    missing_critical_fields: Optional[List[str]] = None
    original_text_references: Optional[Dict[str, str]] = None
    extraction_warnings: Optional[List[str]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentWithMetricsResponse(DocumentStatusResponse):
    """Complete response including extracted metrics."""

    financial_metrics: Optional[FinancialMetricsResponse] = None


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
    status_code: int


