"""Pydantic schemas for Phase 7 scenario analysis and Monte Carlo simulation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScenarioResponse(BaseModel):
    scenario_name: str
    scenario_type: str
    scenario_quantile: float
    market_shocks: Dict[str, float]
    driver_zscores: Dict[str, float]
    source_start_date: Optional[str] = None
    source_end_date: Optional[str] = None
    source_observations: int
    market_regime: Optional[str] = None
    data_source: str
    model_name: str
    model_version: str
    assumptions: Dict[str, Any]


class ScenarioListResponse(BaseModel):
    message: str
    scenarios: List[ScenarioResponse]


class MonteCarloRunRequest(BaseModel):
    scenario_type: str = Field(default="adverse")
    counterparty_ids: Optional[List[int]] = None
    n_simulations: int = Field(default=1000, ge=1, le=100000)
    random_seed: Optional[int] = None
    persist: bool = True
    target_regime: Optional[str] = None
    copula_type: str = Field(default="gaussian", pattern="^(gaussian|gaussian_copula|t|student|student_t|t_copula)$")
    degrees_of_freedom: int = Field(default=5, ge=3, le=100)


class MonteCarloRunResponse(BaseModel):
    message: str
    run_id: str
    scenario_type: str
    scenario_name: str
    number_of_simulations: int
    random_seed: int
    expected_loss: float
    unexpected_loss: float
    credit_var_95: float
    credit_var_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    avg_defaults: float
    max_defaults: int
    max_loss: float
    default_correlation: float
    copula_type: str
    degrees_of_freedom: Optional[int] = None
    tail_dependence_note: str
    loss_distribution_summary: Dict[str, Any]
    marginal_risk_contribution: Dict[str, float]
    scenario_inputs: Dict[str, Any]
    scenario_impacts: Dict[str, Any]
    input_data_reference: Dict[str, Any]
    assumptions_reference: Dict[str, Any]


class StoredSimulationResponse(BaseModel):
    id: int
    run_id: Optional[str] = None
    scenario: Optional[str] = None
    scenario_result_id: Optional[int] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    expected_loss: Optional[float] = None
    var_95: Optional[float] = None
    var_99: Optional[float] = None
    expected_shortfall_95: Optional[float] = None
    expected_shortfall_99: Optional[float] = None
    expected_shortfall: Optional[float] = None
    unexpected_loss: Optional[float] = None
    avg_defaults: Optional[float] = None
    max_defaults: Optional[int] = None
    number_of_simulations: Optional[int] = None
    random_seed: Optional[int] = None
    loss_distribution_summary: Optional[Dict[str, Any]] = None
    marginal_risk_contribution: Optional[Dict[str, float]] = None
    default_correlation: Optional[float] = None
    input_data_reference: Optional[Dict[str, Any]] = None
    assumptions_reference: Optional[Dict[str, Any]] = None
    created_at: datetime




class HedgeSensitivityRequest(BaseModel):
    counterparty_id: Optional[int] = None
    exposure: float = Field(ge=0)
    probability_of_default: float = Field(ge=0, le=1)
    loss_given_default: float = Field(ge=0, le=1)
    hedge_type: str
    hedge_notional: float = Field(ge=0)
    hedge_ratio: float = Field(ge=0, le=1)
    scenario_market_move: float
    commodity_sensitivity_score: Optional[float] = Field(default=None, ge=0, le=1)
    fx_sensitivity_score: Optional[float] = Field(default=None, ge=0, le=1)
    hedge_price: Optional[float] = None
    reference_price: Optional[float] = None
    hedge_direction: str = "long"


class HedgeSensitivityResponse(BaseModel):
    run_id: str
    model_name: str
    model_version: str
    counterparty_id: Optional[int] = None
    hedge_type: str
    unhedged_exposure: float
    hedge_payoff: float
    hedge_benefit: float
    hedged_exposure: float
    unhedged_expected_loss: float
    hedged_expected_loss: float
    exposure_reduction: float
    expected_loss_reduction: float
    before_after_metrics: Dict[str, Any]
    assumptions: Dict[str, Any]
    warnings: List[str]
    created_at: datetime
