"""Pydantic schemas for Phase 8 credit recommendations and grounded memos."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CreditRecommendationCalculationResponse(BaseModel):
    message: str
    recommendation: Dict[str, Any]


class CreditRecommendationResponse(BaseModel):
    id: int
    run_id: str
    counterparty_id: int
    counterparty_name: Optional[str] = None
    counterparty_type: Optional[str] = None
    country: Optional[str] = None
    model_name: str
    model_version: str
    probability_of_default: float
    loss_given_default: float
    exposure_at_default: float
    expected_loss: float
    scenario_expected_loss: Optional[float] = None
    credit_var_95: Optional[float] = None
    expected_shortfall_95: Optional[float] = None
    recommended_credit_limit: float
    recommended_tenor_days: int
    recommended_security: str
    risk_grade: str
    approval_status: str
    policy_score: float
    limit_haircut: float
    key_risk_drivers: Optional[List[str]] = None
    mitigating_factors: Optional[List[str]] = None
    model_assumptions: Optional[Dict[str, Any]] = None
    input_data_reference: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    created_at: datetime


class GroundedMemoResponse(BaseModel):
    company_name: str
    memo: str
class CreditProfileScoreRequest(BaseModel):
    counterparty_id: int
    counterparty_name: str
    current_ratio: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    interest_coverage: Optional[float] = None
    operating_margin: Optional[float] = None
    probability_of_default: Optional[float] = None
    loss_given_default: Optional[float] = None
    exposure_at_default: Optional[float] = None
    payment_tenor_days: int = 30
    collateral_strength: float = 0.0
    country_risk_score: Optional[float] = None
    market_stress_index: Optional[float] = None
    scenario_expected_loss: Optional[float] = None


class CreditProfileScoreResponse(BaseModel):
    model_name: str
    model_version: str
    counterparty_id: int
    counterparty_name: str
    score: float
    risk_segment: str
    segment_method: str
    drivers: List[str]
    weights: Dict[str, float]
    assumptions: Dict[str, Any]
    warnings: List[str] = []
    created_at: datetime


class PaymentTermsOptimizerRequest(BaseModel):
    profile: CreditProfileScoreRequest
    tenor_options: Optional[List[int]] = None


class TenorOptionResponse(BaseModel):
    tenor_days: int
    expected_loss: float
    marginal_risk_price: float
    recommended_security: str
    is_recommended: bool


class PaymentTermsOptimizerResponse(BaseModel):
    model_name: str
    model_version: str
    counterparty_id: int
    counterparty_name: str
    recommended_tenor_days: int
    options: List[TenorOptionResponse]
    assumptions: Dict[str, Any]
    warnings: List[str] = []
    created_at: datetime


class CounterpartyComparisonRequest(BaseModel):
    counterparties: List[CreditProfileScoreRequest]


class CounterpartyComparisonResponse(BaseModel):
    model_name: str
    model_version: str
    counterparties: List[Dict[str, Any]]
    safer_counterparty_id: int
    safer_counterparty_name: str
    comparison_summary: str
    ranking_factors: Dict[str, Any]
    assumptions: Dict[str, Any]
    created_at: datetime

