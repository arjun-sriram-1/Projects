"""Pydantic schemas for Phase 6 LGD, EAD, and expected loss."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TradeExposureRequest(BaseModel):
    counterparty_id: int
    pd_prediction_id: Optional[int] = None
    invoice_amount: Optional[float] = None
    fuel_volume: Optional[float] = None
    fuel_price: Optional[float] = None
    approved_credit_limit: Optional[float] = None
    requested_credit_limit: Optional[float] = None
    outstanding_receivables: float = 0.0
    payment_tenor_days: int = 30
    utilization_rate: float = Field(default=0.50, ge=0.0, le=1.0)
    collateral_type: str = "unsecured"
    letter_of_credit_flag: bool = False
    guarantee_flag: bool = False
    deposit_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    counterparty_type: Optional[str] = None
    country_risk_score: float = 2.0
    seniority_score: float = 2.0
    notes: Optional[str] = None


class LossEstimateResponse(BaseModel):
    id: int
    run_id: str
    counterparty_id: int
    pd_prediction_id: Optional[int] = None
    trade_exposure_id: Optional[int] = None
    requested_credit_limit: Optional[float] = None
    approved_credit_limit: Optional[float] = None
    outstanding_receivables: Optional[float] = None
    payment_tenor_days: Optional[int] = None
    utilization_rate: Optional[float] = None
    collateral_type: Optional[str] = None
    letter_of_credit_flag: Optional[bool] = None
    guarantee_flag: Optional[bool] = None
    deposit_percentage: Optional[float] = None
    invoice_amount: Optional[float] = None
    fuel_volume: Optional[float] = None
    fuel_price: Optional[float] = None
    model_name: str
    model_version: str
    probability_of_default: float
    predicted_lgd: float
    exposure_at_default: float
    expected_loss: float
    collateral_strength: Optional[float] = None
    liquidity_score: Optional[float] = None
    ead_cap_applied: bool
    expected_drawdown: Optional[float] = None
    invoice_exposure: Optional[float] = None
    model_assumptions: Optional[Dict[str, Any]] = None
    input_data_reference: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    created_at: datetime


class LossEstimateCalculationResponse(BaseModel):
    message: str
    loss_estimate: Dict[str, Any]
