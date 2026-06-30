"""Pydantic schemas for monitoring and early warning alerts."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AlertResponse(BaseModel):
    alert_id: Optional[str] = None
    counterparty_id: Optional[int] = None
    severity: str
    category: str
    alert_reason: str
    triggering_metric: str
    triggering_value: float
    threshold: Optional[float] = None
    comparison_baseline: Optional[float] = None
    data_source: str
    model_version: str
    created_at: datetime
    metadata: Dict[str, Any] = {}


class AlertListResponse(BaseModel):
    message: str
    alerts: List[AlertResponse]
    alert_count: int
    high_count: int
    medium_count: int
    low_count: int
    warnings: List[str] = []
class AlertAnalysisRequest(BaseModel):
    predictions: Optional[List[Dict[str, Any]]] = None
    loss_estimates: Optional[List[Dict[str, Any]]] = None
    portfolio: Optional[List[Dict[str, Any]]] = None
    scenario_results: Optional[List[Dict[str, Any]]] = None
    simulations: Optional[List[Dict[str, Any]]] = None
    stress_history: Optional[List[Dict[str, Any]]] = None
    anomaly_outputs: Optional[List[Dict[str, Any]]] = None
    payment_delays: Optional[List[Dict[str, Any]]] = None
    news_sentiment: Optional[List[Dict[str, Any]]] = None
    thresholds: Optional[Dict[str, float]] = None

