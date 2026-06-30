"""Fetch external market data and store it in V2 PostgreSQL tables.

Sources: FRED, EIA, Alpha Vantage through api.market_data.external_providers.
Storage: market_prices, macro_indicators, then optional stress/regime rebuild.
"""

from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from api.db.session import engine
from api.market_data.assets import MACRO_CONTEXT_ASSETS
from api.market_data.external_providers import fetch_provider_data
from api.market_data.service import rebuild_market_intelligence_from_prices

MACRO_ASSETS = MACRO_CONTEXT_ASSETS


def _to_float(value):
    if pd.isna(value):
        return None
    return float(value)


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


def store_provider_rows(frame: pd.DataFrame) -> dict[str, int]:
    counts = {"market_prices_inserted": 0, "market_prices_skipped": 0, "macro_indicators_inserted": 0, "macro_indicators_skipped": 0}
    if frame.empty:
        return counts

    with engine.begin() as conn:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", nargs="+", default=["fred", "eia", "alphavantage"])
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default=datetime.today().strftime("%Y-%m-%d"))
    parser.add_argument("--assets", nargs="*", default=None)
    parser.add_argument("--rebuild-stress-regimes", action="store_true")
    args = parser.parse_args()

    frame, warnings = fetch_provider_data(
        providers=args.providers,
        start_date=args.start_date,
        end_date=args.end_date,
        selected_assets=args.assets,
    )
    counts = store_provider_rows(frame)
    print({"fetched_rows": int(len(frame)), **counts, "warnings": warnings})

    if args.rebuild_stress_regimes:
        rebuild = rebuild_market_intelligence_from_prices(frame, persist=True) if not frame.empty else None
        print({"stress_regime_rebuild": rebuild})


if __name__ == "__main__":
    main()
