"""Pydantic schemas for Phase 4 market stress and regime intelligence."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class StressIndexResponse(BaseModel):
    date: date
    stress_index: float
    stress_level: str
    pc1_score: Optional[float] = None
    explained_variance_ratio: Optional[float] = None
    pca_loadings: Optional[Dict[str, float]] = None
    top_positive_drivers: Optional[List[Dict[str, Any]]] = None
    top_negative_drivers: Optional[List[Dict[str, Any]]] = None
    available_components: Optional[List[str]] = None
    missing_components: Optional[List[str]] = None
    model_version: Optional[str] = None
    updated_at: Optional[datetime] = None


class StressIndexHistoryResponse(BaseModel):
    row_count: int
    min_date: Optional[date] = None
    max_date: Optional[date] = None
    stress_history: List[StressIndexResponse]


class MarketRegimeResponse(BaseModel):
    date: date
    regime_id: int
    regime_label: str
    regime_probability: Optional[float] = None
    regime_characteristics: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = None
    updated_at: Optional[datetime] = None


class Phase4RebuildResponse(BaseModel):
    message: str
    stress_rows: int
    regime_rows: int
    latest_stress_index: float
    latest_stress_level: str
    latest_regime_label: str
    available_components: List[str]
    missing_components: List[str]


class LiveMarketRefreshResponse(BaseModel):
    message: str
    start_date: str
    end_date: str
    providers: List[str]
    fetched_rows: int
    market_prices_inserted: int
    market_prices_skipped: int
    macro_indicators_inserted: int
    macro_indicators_skipped: int
    latest_price_date: Optional[date] = None
    latest_prices: List[Dict[str, Any]] = []
    stress_regime_rebuild: Dict[str, Any]
    warnings: List[str] = []




class MarketPricePoint(BaseModel):
    date: date
    asset: str
    price: float
    source_id: Optional[str] = None
    data_source: Optional[str] = None
    units: Optional[str] = None
    freshness_status: Optional[str] = None
    is_stale: Optional[bool] = None


class ForecastRequest(BaseModel):
    model_type: str
    assets: List[str]
    horizon: int = 10
    market_prices: List[MarketPricePoint]


class ForecastResponse(BaseModel):
    model_name: str
    model_version: str
    forecast_horizon: int
    input_series: List[str]
    forecast_path: Dict[str, List[float]]
    forecast_value: Dict[str, float]
    confidence_interval: Dict[str, Dict[str, float]]
    forecast_error: Optional[float] = None
    backtest_error: Optional[float] = None
    forecast_volatility: Optional[float] = None
    volatility_regime: Optional[str] = None
    assumptions: Dict[str, Any]
    warnings: List[str] = []
    created_at: datetime


class CommodityFactorRequest(BaseModel):
    assets: List[str]
    rolling_window: int = 30
    market_prices: List[MarketPricePoint]


class CommodityFactorResponse(BaseModel):
    model_name: str
    model_version: str
    assets: List[str]
    latest_log_returns: Dict[str, float]
    rolling_volatility: Dict[str, float]
    spread_analysis: Dict[str, Dict[str, float]]
    correlation_matrix: Dict[str, Dict[str, float]]
    high_volatility_assets: List[str]
    assumptions: Dict[str, Any]
    warnings: List[str] = []
    created_at: datetime


class MarketPriceHistoryResponse(BaseModel):
    assets: List[str]
    row_count: int
    min_date: Optional[date] = None
    max_date: Optional[date] = None
    market_prices: List[MarketPricePoint]


