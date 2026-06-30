"""Market intelligence service for stress index and regime detection."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from api.db.session import engine
from api.market_data.assets import MACRO_CONTEXT_ASSETS
from api.market_data.external_providers import fetch_provider_data
from api.market_data.regime_detection import detect_market_regimes
from api.market_data.stress_index import build_stress_index


YFINANCE_TICKERS = {
    "crude_oil": ("CL=F", "WTI Crude Oil Futures"),
    "brent_oil": ("BZ=F", "Brent Crude Oil Futures"),
    "heating_oil_proxy": ("HO=F", "Heating Oil Futures"),
    "natural_gas": ("NG=F", "Natural Gas Futures"),
    "vix": ("^VIX", "CBOE Volatility Index"),
    "sp500": ("^GSPC", "S&P 500 Index"),
    "usd_inr": ("USDINR=X", "USD/INR"),
    "eur_usd": ("EURUSD=X", "EUR/USD"),
    "dxy": ("DX-Y.NYB", "US Dollar Index"),
    "gold": ("GC=F", "Gold Futures"),
    "us_10y_yield": ("^TNX", "US 10-Year Treasury Yield"),
    "freight_proxy": ("BDRY", "Breakwave Dry Bulk Shipping ETF"),
}

MACRO_ASSETS = MACRO_CONTEXT_ASSETS

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


def _json_dumps(value: Any) -> str:
    """Serialize nested market metadata for PostgreSQL JSONB fields."""
    return json.dumps(value, default=str)


def load_market_prices(db_engine: Engine = engine) -> pd.DataFrame:
    """Load stored market prices for stress-index construction."""
    query = text(
        """
        SELECT
            date,
            COALESCE(asset, asset_name, ticker, source_id) AS asset,
            price
        FROM market_prices
        WHERE date IS NOT NULL
          AND price IS NOT NULL
        ORDER BY date
        """
    )
    with db_engine.connect() as conn:
        return pd.read_sql(query, conn)


def _to_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def fetch_yfinance_market_data(start_date: str, end_date: str | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Fetch normalized yfinance market rows for public market proxies."""
    try:
        import yfinance as yf
    except Exception as exc:
        return pd.DataFrame(), [f"yfinance import failed: {exc}"]

    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    frames: list[pd.DataFrame] = []
    warnings: list[str] = []
    for asset, (ticker, asset_name) in YFINANCE_TICKERS.items():
        try:
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if data.empty:
                warnings.append(f"yfinance:{ticker}: no rows returned")
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            close = pd.to_numeric(data["Close"], errors="coerce").dropna()
            frame = close.rename("price").reset_index()
            frame = frame.rename(columns={frame.columns[0]: "date"})
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
            frame = frame.dropna(subset=["date", "price"])
            frame = frame[frame["price"] > 0].sort_values("date")
            if frame.empty:
                warnings.append(f"yfinance:{ticker}: no usable close prices")
                continue
            frame["asset"] = asset
            frame["asset_name"] = asset_name
            frame["source_id"] = ticker
            frame["data_source"] = "yfinance"
            frame["frequency"] = "daily"
            frame["units"] = "market_price"
            frame["return"] = np.log(frame["price"] / frame["price"].shift(1)).replace([np.inf, -np.inf], np.nan)
            frame["rolling_volatility"] = frame["return"].rolling(30, min_periods=5).std()
            frames.append(frame[[
                "date",
                "asset",
                "asset_name",
                "source_id",
                "price",
                "data_source",
                "frequency",
                "units",
                "return",
                "rolling_volatility",
            ]])
        except Exception as exc:
            warnings.append(f"yfinance:{ticker}: {exc}")
    if not frames:
        return pd.DataFrame(), warnings
    return pd.concat(frames, ignore_index=True).sort_values(["asset", "date"]), warnings


def _row_exists(conn, table: str, row: dict) -> bool:
    if table == "market_prices":
        query = text(
            """
            SELECT 1 FROM market_prices
            WHERE date = :date
              AND asset = :asset
              AND source_id = :source_id
              AND data_source = :data_source
            LIMIT 1
            """
        )
        params = {
            "date": row["date"],
            "asset": row["asset"],
            "source_id": row["source_id"],
            "data_source": row["data_source"],
        }
    else:
        query = text(
            """
            SELECT 1 FROM macro_indicators
            WHERE date = :date
              AND indicator = :indicator
              AND source_id = :source_id
              AND data_source = :data_source
            LIMIT 1
            """
        )
        params = {
            "date": row["date"],
            "indicator": row["asset"],
            "source_id": row["source_id"],
            "data_source": row["data_source"],
        }
    return conn.execute(query, params).first() is not None


def store_market_provider_rows(frame: pd.DataFrame, db_engine: Engine = engine) -> dict[str, int]:
    """Store normalized external market rows in market_prices and macro_indicators."""
    counts = {
        "market_prices_inserted": 0,
        "market_prices_skipped": 0,
        "macro_indicators_inserted": 0,
        "macro_indicators_skipped": 0,
    }
    if frame.empty:
        return counts
    with db_engine.begin() as conn:
        for _, raw_row in frame.iterrows():
            row = raw_row.to_dict()
            row["date"] = pd.to_datetime(row["date"]).to_pydatetime()
            row["price"] = _to_float(row.get("price"))
            row["return"] = _to_float(row.get("return"))
            row["rolling_volatility"] = _to_float(row.get("rolling_volatility"))
            if row["price"] is None:
                continue
            if _row_exists(conn, "market_prices", row):
                counts["market_prices_skipped"] += 1
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO market_prices (
                            date, price, asset, ticker, source_id, asset_name,
                            data_source, frequency, units, return, rolling_volatility
                        )
                        VALUES (
                            :date, :price, :asset, :ticker, :source_id, :asset_name,
                            :data_source, :frequency, :units, :return, :rolling_volatility
                        )
                        """
                    ),
                    {
                        "date": row["date"],
                        "price": row["price"],
                        "asset": row["asset"],
                        "ticker": row.get("source_id"),
                        "source_id": row.get("source_id"),
                        "asset_name": row.get("asset_name"),
                        "data_source": row.get("data_source"),
                        "frequency": row.get("frequency"),
                        "units": row.get("units"),
                        "return": row.get("return"),
                        "rolling_volatility": row.get("rolling_volatility"),
                    },
                )
                counts["market_prices_inserted"] += 1

            if row.get("asset") in MACRO_ASSETS:
                if _row_exists(conn, "macro_indicators", row):
                    counts["macro_indicators_skipped"] += 1
                else:
                    conn.execute(
                        text(
                            """
                            INSERT INTO macro_indicators (
                                date, indicator, value, source_id, data_source,
                                frequency, units, return, rolling_volatility
                            )
                            VALUES (
                                :date, :indicator, :value, :source_id, :data_source,
                                :frequency, :units, :return, :rolling_volatility
                            )
                            """
                        ),
                        {
                            "date": row["date"],
                            "indicator": row["asset"],
                            "value": row["price"],
                            "source_id": row.get("source_id"),
                            "data_source": row.get("data_source"),
                            "frequency": row.get("frequency"),
                            "units": row.get("units"),
                            "return": row.get("return"),
                            "rolling_volatility": row.get("rolling_volatility"),
                        },
                    )
                    counts["macro_indicators_inserted"] += 1
    return counts


def store_stress_history(stress_history: pd.DataFrame, db_engine: Engine = engine) -> int:
    """Upsert stress index rows into PostgreSQL."""
    if stress_history.empty:
        return 0
    with db_engine.begin() as conn:
        for _, row in stress_history.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO stress_index_history (
                        date,
                        stress_index,
                        stress_level,
                        pc1_score,
                        explained_variance_ratio,
                        pca_loadings,
                        top_positive_drivers,
                        top_negative_drivers,
                        component_values,
                        available_components,
                        missing_components,
                        model_version,
                        data_source,
                        updated_at
                    )
                    VALUES (
                        :date,
                        :stress_index,
                        :stress_level,
                        :pc1_score,
                        :explained_variance_ratio,
                        CAST(:pca_loadings AS JSONB),
                        CAST(:top_positive_drivers AS JSONB),
                        CAST(:top_negative_drivers AS JSONB),
                        CAST(:component_values AS JSONB),
                        CAST(:available_components AS JSONB),
                        CAST(:missing_components AS JSONB),
                        :model_version,
                        :data_source,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (date) DO UPDATE SET
                        stress_index = EXCLUDED.stress_index,
                        stress_level = EXCLUDED.stress_level,
                        pc1_score = EXCLUDED.pc1_score,
                        explained_variance_ratio = EXCLUDED.explained_variance_ratio,
                        pca_loadings = EXCLUDED.pca_loadings,
                        top_positive_drivers = EXCLUDED.top_positive_drivers,
                        top_negative_drivers = EXCLUDED.top_negative_drivers,
                        component_values = EXCLUDED.component_values,
                        available_components = EXCLUDED.available_components,
                        missing_components = EXCLUDED.missing_components,
                        model_version = EXCLUDED.model_version,
                        data_source = EXCLUDED.data_source,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "date": pd.to_datetime(row["date"]).date(),
                    "stress_index": round(float(row["stress_index"]), 2),
                    "stress_level": row["stress_level"],
                    "pc1_score": float(row["pc1_score"]),
                    "explained_variance_ratio": float(row["explained_variance_ratio"]),
                    "pca_loadings": _json_dumps(row["pca_loadings"]),
                    "top_positive_drivers": _json_dumps(row["top_positive_drivers"]),
                    "top_negative_drivers": _json_dumps(row["top_negative_drivers"]),
                    "component_values": _json_dumps(row["component_values"]),
                    "available_components": _json_dumps(row["available_components"]),
                    "missing_components": _json_dumps(row["missing_components"]),
                    "model_version": row["model_version"],
                    "data_source": row["data_source"],
                },
            )
    return len(stress_history)


def store_regime_history(regime_history: pd.DataFrame, db_engine: Engine = engine) -> int:
    """Upsert market regime rows into PostgreSQL."""
    if regime_history.empty:
        return 0
    with db_engine.begin() as conn:
        for _, row in regime_history.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO market_regime_history (
                        date,
                        regime_id,
                        regime_label,
                        regime_probability,
                        regime_characteristics,
                        feature_values,
                        model_version,
                        data_source,
                        updated_at
                    )
                    VALUES (
                        :date,
                        :regime_id,
                        :regime_label,
                        :regime_probability,
                        CAST(:regime_characteristics AS JSONB),
                        CAST(:feature_values AS JSONB),
                        :model_version,
                        :data_source,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (date) DO UPDATE SET
                        regime_id = EXCLUDED.regime_id,
                        regime_label = EXCLUDED.regime_label,
                        regime_probability = EXCLUDED.regime_probability,
                        regime_characteristics = EXCLUDED.regime_characteristics,
                        feature_values = EXCLUDED.feature_values,
                        model_version = EXCLUDED.model_version,
                        data_source = EXCLUDED.data_source,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "date": pd.to_datetime(row["date"]).date(),
                    "regime_id": int(row["regime_id"]),
                    "regime_label": row["regime_label"],
                    "regime_probability": float(row["regime_probability"]),
                    "regime_characteristics": _json_dumps(row["regime_characteristics"]),
                    "feature_values": _json_dumps(row["feature_values"]),
                    "model_version": row["model_version"],
                    "data_source": row["data_source"],
                },
            )
    return len(regime_history)


def rebuild_market_intelligence_from_prices(
    market_prices: pd.DataFrame,
    persist: bool = False,
    db_engine: Engine = engine,
) -> dict:
    """Build stress index/regimes from a price frame and optionally persist."""
    stress_result = build_stress_index(market_prices)
    regime_result = detect_market_regimes(
        stress_result.component_matrix,
        stress_result.history,
    )
    stress_rows = store_stress_history(stress_result.history, db_engine) if persist else len(stress_result.history)
    regime_rows = store_regime_history(regime_result.history, db_engine) if persist else len(regime_result.history)
    latest_stress = stress_result.history.sort_values("date").iloc[-1]
    latest_regime = regime_result.history.sort_values("date").iloc[-1]
    return {
        "stress_rows": stress_rows,
        "regime_rows": regime_rows,
        "latest_stress_index": round(float(latest_stress["stress_index"]), 2),
        "latest_stress_level": latest_stress["stress_level"],
        "latest_regime_label": latest_regime["regime_label"],
        "available_components": stress_result.available_components,
        "missing_components": stress_result.missing_components,
    }


def rebuild_market_intelligence(db_engine: Engine = engine) -> dict:
    """Load market prices from the database, rebuild stress/regimes, and persist."""
    market_prices = load_market_prices(db_engine)
    return rebuild_market_intelligence_from_prices(market_prices, persist=True, db_engine=db_engine)


def refresh_live_market_intelligence(
    db_engine: Engine = engine,
    lookback_days: int = 730,
    providers: list[str] | None = None,
) -> dict:
    """Fetch live public provider data, store it, and rebuild market intelligence."""
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=max(int(lookback_days or 730), 120))).strftime("%Y-%m-%d")
    providers = providers or ["fred", "eia", "csv"]

    provider_frame, provider_warnings = fetch_provider_data(
        providers=providers,
        start_date=start_date,
        end_date=end_date,
    )
    yfinance_frame, yfinance_warnings = fetch_yfinance_market_data(start_date=start_date, end_date=end_date)
    frames = [frame for frame in [provider_frame, yfinance_frame] if not frame.empty]
    combined = pd.concat(frames, ignore_index=True).sort_values(["asset", "date"]) if frames else pd.DataFrame()
    counts = store_market_provider_rows(combined, db_engine)
    rebuild = rebuild_market_intelligence(db_engine)
    latest_prices = fetch_all(
        f"""
        WITH ranked AS (
            SELECT
                asset,
                source_id,
                data_source,
                units,
                date::date AS date,
                price::float AS price,
                ROW_NUMBER() OVER (
                    PARTITION BY asset
                    ORDER BY date DESC, {PROVIDER_PRIORITY_SQL}, created_at DESC, id DESC
                ) AS rn
            FROM market_prices
            WHERE date IS NOT NULL
              AND price IS NOT NULL
        )
        SELECT asset, source_id, data_source, units, date, price
        FROM ranked
        WHERE rn = 1
        ORDER BY asset
        """,
        db_engine=db_engine,
    )
    latest_date = max((row["date"] for row in latest_prices), default=None)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "providers": providers + ["yfinance"],
        "fetched_rows": int(len(combined)),
        **counts,
        "warnings": provider_warnings + yfinance_warnings,
        "latest_price_date": latest_date,
        "latest_prices": latest_prices,
        "stress_regime_rebuild": rebuild,
    }


def fetch_one(query: str, db_engine: Engine = engine) -> dict | None:
    """Fetch one mapped row from the configured database engine."""
    with db_engine.connect() as conn:
        result = conn.execute(text(query)).mappings().first()
    return dict(result) if result else None

def fetch_all(query: str, params: dict | None = None, db_engine: Engine = engine) -> list[dict]:
    """Fetch mapped rows from the configured database engine."""
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params or {}).mappings().all()
    return [dict(row) for row in result]

