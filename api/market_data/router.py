"""FastAPI routes for stress index and market regime detection."""

from fastapi import APIRouter, HTTPException, status
import pandas as pd

from api.market_data.schemas import (
    CommodityFactorRequest,
    CommodityFactorResponse,
    ForecastRequest,
    ForecastResponse,
    LiveMarketRefreshResponse,
    MarketPriceHistoryResponse,
    MarketPricePoint,
    MarketRegimeResponse,
    Phase4RebuildResponse,
    StressIndexHistoryResponse,
    StressIndexResponse,
)
from api.market_data.commodity_factors import analyze_commodity_factors
from api.market_data.forecasting import run_forecast
from api.market_data.assets import CORE_MARKET_ASSETS
from api.market_data.service import fetch_all, fetch_one, rebuild_market_intelligence, refresh_live_market_intelligence


router = APIRouter(prefix="/api/v1/market-intelligence", tags=["market-intelligence"])


PROVIDER_PRIORITY_SQL = """
CASE
    WHEN asset IN ('brent_oil', 'crude_oil', 'heating_oil_proxy', 'vix', 'sp500', 'dxy', 'gold', 'freight_proxy')
         AND data_source = 'yfinance' THEN 1
    WHEN asset IN ('jet_fuel_proxy', 'eia_crude_inventories')
         AND data_source = 'eia' THEN 1
    WHEN asset IN ('us_10y_yield', 'us_2y_yield', 'yield_curve_spread', 'cpi_index')
         AND data_source = 'fred' THEN 1
    WHEN data_source = 'eia' THEN 2
    WHEN data_source = 'fred' THEN 3
    WHEN data_source = 'calculated_market_series' THEN 4
    WHEN data_source LIKE 'staged_csv%%' THEN 5
    WHEN data_source LIKE 'single_airline_deep_audit%%' THEN 9
    ELSE 6
END
"""


@router.post("/rebuild", response_model=Phase4RebuildResponse)
def rebuild_market_intelligence_endpoint():
    """Rebuild stress index and market regime history from market_prices."""
    try:
        result = rebuild_market_intelligence()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return Phase4RebuildResponse(
        message="Market stress index and regimes rebuilt.",
        **result,
    )


@router.post("/refresh-live", response_model=LiveMarketRefreshResponse)
def refresh_live_market_intelligence_endpoint(lookback_days: int = 730):
    """Fetch live FRED/EIA/yfinance data, store it, and rebuild stress/regime intelligence."""
    try:
        result = refresh_live_market_intelligence(lookback_days=lookback_days)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return LiveMarketRefreshResponse(
        message="Live market data refreshed, stored, and rebuilt.",
        **result,
    )


@router.get("/stress/latest", response_model=StressIndexResponse)
def get_latest_stress_index():
    """Return the latest stored market stress index record."""
    row = fetch_one(
        """
        SELECT
            date,
            stress_index::float AS stress_index,
            stress_level,
            pc1_score,
            explained_variance_ratio,
            pca_loadings,
            top_positive_drivers,
            top_negative_drivers,
            available_components,
            missing_components,
            model_version,
            updated_at
        FROM stress_index_history
        ORDER BY date DESC
        LIMIT 1
        """
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stress index history found. Run /api/v1/market-intelligence/rebuild first.",
        )
    return StressIndexResponse(**row)


@router.get("/stress/history", response_model=StressIndexHistoryResponse)
def get_stress_index_history(limit: int = 180):
    """Return recent stored market stress index rows for dashboard trend charts."""
    row_limit = max(10, min(int(limit or 180), 1000))
    rows = fetch_all(
        """
        SELECT
            date,
            stress_index::float AS stress_index,
            stress_level,
            pc1_score,
            explained_variance_ratio,
            pca_loadings,
            top_positive_drivers,
            top_negative_drivers,
            available_components,
            missing_components,
            model_version,
            updated_at
        FROM stress_index_history
        ORDER BY date DESC
        LIMIT :limit
        """,
        {"limit": row_limit},
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stress index history found. Run /api/v1/market-intelligence/rebuild first.",
        )
    ordered = sorted(rows, key=lambda row: row["date"])
    dates = [row["date"] for row in ordered]
    return StressIndexHistoryResponse(
        row_count=len(ordered),
        min_date=min(dates),
        max_date=max(dates),
        stress_history=[StressIndexResponse(**row) for row in ordered],
    )


@router.get("/regime/latest", response_model=MarketRegimeResponse)
def get_latest_market_regime():
    """Return the latest stored market regime record."""
    row = fetch_one(
        """
        SELECT
            date,
            regime_id,
            regime_label,
            regime_probability::float AS regime_probability,
            regime_characteristics,
            model_version,
            updated_at
        FROM market_regime_history
        ORDER BY date DESC
        LIMIT 1
        """
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No market regime history found. Run /api/v1/market-intelligence/rebuild first.",
        )
    return MarketRegimeResponse(**row)



@router.get("/prices/recent", response_model=MarketPriceHistoryResponse)
def get_recent_market_prices(assets: str = ",".join(CORE_MARKET_ASSETS), limit_per_asset: int = 180):
    """Return recent stored market prices for dashboard charts and forecast payloads."""
    asset_list = [asset.strip() for asset in assets.split(",") if asset.strip()]
    if not asset_list:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one asset is required.")
    limit = max(10, min(int(limit_per_asset or 180), 1000))
    rows = fetch_all(
        f"""
        WITH preferred AS (
            SELECT
                date::date AS date,
                asset,
                price::float AS price,
                source_id,
                data_source,
                units,
                frequency,
                ROW_NUMBER() OVER (
                    PARTITION BY asset, date::date
                    ORDER BY {PROVIDER_PRIORITY_SQL}, created_at DESC, id DESC
                ) AS provider_rn
            FROM market_prices
            WHERE asset = ANY(:assets)
              AND date IS NOT NULL
              AND price IS NOT NULL
        ),
        ranked AS (
            SELECT
                date,
                asset,
                price,
                source_id,
                data_source,
                units,
                CASE
                    WHEN data_source LIKE 'single_airline_deep_audit%%' THEN 'demo_stale'
                    WHEN (frequency = 'monthly' OR asset IN ('cpi_index', 'global_pmi', 'pmi', 'opec_production', 'iata_passenger_traffic'))
                         AND date < CURRENT_DATE - INTERVAL '75 days' THEN 'stale'
                    WHEN (frequency = 'weekly' OR asset IN ('eia_crude_inventories'))
                         AND date < CURRENT_DATE - INTERVAL '14 days' THEN 'stale'
                    WHEN NOT (
                            frequency IN ('weekly', 'monthly')
                            OR asset IN (
                                'cpi_index',
                                'global_pmi',
                                'pmi',
                                'opec_production',
                                'iata_passenger_traffic',
                                'eia_crude_inventories'
                            )
                         )
                         AND date < CURRENT_DATE - INTERVAL '5 days' THEN 'stale'
                    WHEN date < CURRENT_DATE - INTERVAL '1 day' THEN 'latest_available'
                    ELSE 'fresh'
                END AS freshness_status,
                CASE
                    WHEN data_source LIKE 'single_airline_deep_audit%%' THEN TRUE
                    WHEN (frequency = 'monthly' OR asset IN ('cpi_index', 'global_pmi', 'pmi', 'opec_production', 'iata_passenger_traffic'))
                         AND date < CURRENT_DATE - INTERVAL '75 days' THEN TRUE
                    WHEN (frequency = 'weekly' OR asset IN ('eia_crude_inventories'))
                         AND date < CURRENT_DATE - INTERVAL '14 days' THEN TRUE
                    WHEN NOT (
                            frequency IN ('weekly', 'monthly')
                            OR asset IN (
                                'cpi_index',
                                'global_pmi',
                                'pmi',
                                'opec_production',
                                'iata_passenger_traffic',
                                'eia_crude_inventories'
                            )
                         )
                         AND date < CURRENT_DATE - INTERVAL '5 days' THEN TRUE
                    ELSE FALSE
                END AS is_stale,
                ROW_NUMBER() OVER (PARTITION BY asset ORDER BY date DESC) AS rn
            FROM preferred
            WHERE provider_rn = 1
        )
        SELECT date, asset, price, source_id, data_source, units, freshness_status, is_stale
        FROM ranked
        WHERE rn <= :limit
        ORDER BY asset, date
        """,
        {"assets": asset_list, "limit": limit},
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No market prices found for requested assets.")
    dates = [row["date"] for row in rows]
    return MarketPriceHistoryResponse(
        assets=asset_list,
        row_count=len(rows),
        min_date=min(dates),
        max_date=max(dates),
        market_prices=[MarketPricePoint(**row) for row in rows],
    )

@router.post("/forecast", response_model=ForecastResponse)
def run_market_forecast(request: ForecastRequest):
    """Run an ARIMA, VAR, or GARCH market forecast from supplied price history."""
    if not request.assets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one asset is required.")
    try:
        market_prices = pd.DataFrame([point.model_dump() for point in request.market_prices])
        result = run_forecast(
            market_prices=market_prices,
            model_type=request.model_type,
            assets=request.assets,
            horizon=request.horizon,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ForecastResponse(**result.to_dict())

@router.post("/commodity-factors/analyze", response_model=CommodityFactorResponse)
def analyze_commodity_factors_endpoint(request: CommodityFactorRequest):
    """Calculate commodity returns, volatility, spreads, and correlations."""
    try:
        market_prices = pd.DataFrame([point.model_dump() for point in request.market_prices])
        result = analyze_commodity_factors(
            market_prices=market_prices,
            assets=request.assets,
            rolling_window=request.rolling_window,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CommodityFactorResponse(**result.to_dict())

__all__ = ["router"]











