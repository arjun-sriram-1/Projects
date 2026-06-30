"""Pydantic schemas for Phase 5 probability of default models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class PDCalculationResponse(BaseModel):
    message: str
    prediction: Dict[str, Any]


class PDPredictionResponse(BaseModel):
    id: int
    run_id: str
    counterparty_id: int
    financial_metrics_id: Optional[int] = None
    financial_ratios_id: Optional[int] = None
    model_name: str
    model_version: str
    structural_pd: float
    ml_pd: float
    final_pd: float
    classification_label: str
    model_confidence: Optional[float] = None
    model_disagreement: bool
    pd_divergence: Optional[float] = None
    distance_to_default: Optional[float] = None
    asset_value_proxy: Optional[float] = None
    debt_threshold: Optional[float] = None
    asset_volatility: Optional[float] = None
    risk_free_rate: Optional[float] = None
    time_horizon_years: Optional[float] = None
    commodity_sensitivity_score: Optional[float] = None
    fx_sensitivity_score: Optional[float] = None
    macro_sensitivity_score: Optional[float] = None
    market_stress_index: Optional[float] = None
    market_regime: Optional[str] = None
    feature_contributions: Optional[Dict[str, float]] = None
    model_assumptions: Optional[Dict[str, Any]] = None
    input_data_reference: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    created_at: datetime


class PDCalculateRequest(BaseModel):
    time_horizon_years: float = 1.0

