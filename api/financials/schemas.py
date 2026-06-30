"""Pydantic schemas for Phase 3 financial ratio analysis."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ManualFinancialMetricsCreate(BaseModel):
    """Manual financial statement capture payload from analyst UI."""

    counterparty_id: int
    fiscal_year: Optional[int] = None
    period_type: Optional[str] = "annual"
    period_label: Optional[str] = None
    is_latest_snapshot: bool = True
    fiscal_period: Optional[str] = "FY"
    currency: str = Field(default="USD", min_length=3, max_length=3)

    revenue: Optional[float] = Field(default=None, ge=0)
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    operating_margin_percent: Optional[float] = Field(default=None, ge=-100, le=100)
    interest_expense: Optional[float] = Field(default=None, ge=0)
    net_income: Optional[float] = None

    cash_and_equivalents: Optional[float] = Field(default=None, ge=0)
    accounts_receivable: Optional[float] = Field(default=None, ge=0)
    inventory: Optional[float] = Field(default=None, ge=0)
    current_assets: Optional[float] = Field(default=None, ge=0)
    total_assets: Optional[float] = Field(default=None, ge=0)
    current_liabilities: Optional[float] = Field(default=None, ge=0)
    total_debt: Optional[float] = Field(default=None, ge=0)
    total_liabilities: Optional[float] = Field(default=None, ge=0)
    shareholders_equity: Optional[float] = None

    created_by: Optional[str] = "streamlit_dashboard"

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("period_type")
    @classmethod
    def normalize_period_type(cls, value: Optional[str]) -> str:
        normalized = (value or "annual").strip().lower()
        return "quarterly" if normalized in {"quarter", "quarterly", "q"} else "annual"

    @field_validator("period_label", "fiscal_period")
    @classmethod
    def normalize_period_label(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return value.strip().upper() or None


class ManualFinancialMetricsBatchCreate(BaseModel):
    """Manual multi-period financial statement capture payload."""

    counterparty_id: int
    periods: List[ManualFinancialMetricsCreate]


class ManualFinancialMetricsResponse(BaseModel):
    """Created manual financial metrics record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    uploaded_document_id: int
    counterparty_id: int
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    period_type: Optional[str] = None
    period_label: Optional[str] = None
    is_latest_snapshot: Optional[bool] = None
    currency: Optional[str] = None
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    interest_expense: Optional[float] = None
    net_income: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    current_assets: Optional[float] = None
    total_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_debt: Optional[float] = None
    total_liabilities: Optional[float] = None
    shareholders_equity: Optional[float] = None
    extraction_confidence: Optional[float] = None
    missing_critical_fields: Optional[List[str]] = None
    extraction_warnings: Optional[List[str]] = None
    created_at: datetime


class ManualFinancialMetricsCreateResponse(BaseModel):
    message: str
    metrics: ManualFinancialMetricsResponse


class ManualFinancialMetricsBatchCreateResponse(BaseModel):
    message: str
    metrics: List[ManualFinancialMetricsResponse]
    latest_metrics: ManualFinancialMetricsResponse


class FinancialMetricsHistoryResponse(BaseModel):
    message: str
    periods: List[ManualFinancialMetricsResponse]
    latest_metrics: Optional[ManualFinancialMetricsResponse] = None


class MarkLatestFinancialMetricsResponse(BaseModel):
    message: str
    latest_metrics: ManualFinancialMetricsResponse


class FinancialTrendFeaturesResponse(BaseModel):
    counterparty_id: int
    period_count: int
    history_status: str
    history_frequency: str
    latest_period: Optional[str] = None
    oldest_period: Optional[str] = None
    revenue_cagr: Optional[float] = None
    latest_revenue_growth: Optional[float] = None
    ebitda_margin_trend: Optional[float] = None
    net_margin_trend: Optional[float] = None
    debt_growth: Optional[float] = None
    leverage_trend: Optional[float] = None
    interest_coverage_trend: Optional[float] = None
    current_ratio_trend: Optional[float] = None
    current_ratio_latest: Optional[float] = None
    interest_coverage_latest: Optional[float] = None
    leverage_latest: Optional[float] = None
    ebitda_margin_latest: Optional[float] = None
    net_margin_latest: Optional[float] = None
    cash_trend: Optional[float] = None
    fuel_cost_growth: Optional[float] = None
    fuel_cost_to_revenue_latest: Optional[float] = None
    model_overlay: Optional[Dict[str, Any]] = None
    warnings: List[str] = []


class FinancialRatiosResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    counterparty_id: int
    uploaded_document_id: Optional[int] = None
    financial_metrics_id: int
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    currency: Optional[str] = None

    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    working_capital: Optional[float] = None
    debt_to_equity: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    liabilities_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    return_on_assets: Optional[float] = None
    return_on_equity: Optional[float] = None

    formula_version: str
    calculation_date: datetime
    input_data_reference: Optional[str] = None
    missing_inputs: Optional[Dict[str, List[str]]] = None
    calculation_warnings: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

class FinancialRatioCalculationResponse(BaseModel):
    message: str
    ratios: FinancialRatiosResponse
