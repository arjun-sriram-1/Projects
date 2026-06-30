"""
External market and macro data providers.

Business purpose:
Pull real/free public market data from FRED, EIA, and Alpha Vantage so the
stress index, regime detection, scenarios, PD adjustments, and credit decisions
are grounded in stored data rather than hardcoded assumptions.

Inputs:
API keys from .env and provider series mappings.

Outputs:
Normalized time series rows with date, asset, price/value, source_id,
data_source, return, and rolling volatility.

Assumptions:
Provider-specific series are mapped to the project's canonical asset names.
When a provider is unavailable or rate-limited, the caller can keep existing
Yahoo Finance proxy data as a fallback.

Limitations:
Free API tiers may be rate-limited and some EIA petroleum routes can change
metadata. Errors are surfaced as provider warnings rather than silently filled.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from dotenv import load_dotenv


load_dotenv()

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
EIA_V2_BASE_URL = "https://api.eia.gov/v2"
ALPHAVANTAGE_QUERY_URL = "https://www.alphavantage.co/query"
STAGED_MARKET_INPUT_DIR = Path("data/external/market_inputs")


@dataclass(frozen=True)
class ProviderSeries:
    asset: str
    source_id: str
    asset_name: str
    frequency: str = "daily"
    units: Optional[str] = None
    provider_args: Dict[str, Any] | None = None


FRED_SERIES: Dict[str, ProviderSeries] = {
    "brent_oil": ProviderSeries("brent_oil", "DCOILBRENTEU", "Brent Crude Oil Price", units="usd_per_barrel"),
    "crude_oil": ProviderSeries("crude_oil", "DCOILWTICO", "WTI Crude Oil Price", units="usd_per_barrel"),
    "vix": ProviderSeries("vix", "VIXCLS", "CBOE Volatility Index", units="index"),
    "sp500": ProviderSeries("sp500", "SP500", "S&P 500 Index", units="index"),
    "dxy": ProviderSeries("dxy", "DTWEXBGS", "Nominal Broad U.S. Dollar Index", units="index"),
    "us_10y_yield": ProviderSeries("us_10y_yield", "DGS10", "US 10-Year Treasury Yield", units="percent"),
    "us_2y_yield": ProviderSeries("us_2y_yield", "DGS2", "US 2-Year Treasury Yield", units="percent"),
    "yield_curve_spread": ProviderSeries("yield_curve_spread", "T10Y2Y", "10Y minus 2Y Treasury Spread", units="percent"),
    "cpi_index": ProviderSeries("cpi_index", "CPIAUCSL", "Consumer Price Index", frequency="monthly", units="index"),
    "high_yield_spread": ProviderSeries("high_yield_spread", "BAMLH0A0HYM2", "US High Yield OAS", units="percent"),
    "heating_oil_proxy": ProviderSeries("heating_oil_proxy", "DHOILNYH", "NY Harbor No. 2 Heating Oil Spot Price", units="usd_per_gallon"),
    "pmi": ProviderSeries("pmi", "NAPM", "ISM Manufacturing PMI proxy for global PMI", frequency="monthly", units="index"),
}


EIA_SERIES: Dict[str, ProviderSeries] = {
    "brent_oil": ProviderSeries(
        "brent_oil",
        "RBRTE",
        "Europe Brent Spot Price FOB",
        units="usd_per_barrel",
        provider_args={"route": "petroleum/pri/spt/data/", "series": "RBRTE"},
    ),
    "crude_oil": ProviderSeries(
        "crude_oil",
        "RWTC",
        "WTI Cushing Crude Oil Spot Price",
        units="usd_per_barrel",
        provider_args={"route": "petroleum/pri/spt/data/", "series": "RWTC"},
    ),
    "heating_oil_proxy": ProviderSeries(
        "heating_oil_proxy",
        "EER_EPD2F_PF4_Y35NY_DPG",
        "NY Harbor No. 2 Heating Oil Spot Price",
        units="usd_per_gallon",
        provider_args={"route": "petroleum/pri/spt/data/", "series": "EER_EPD2F_PF4_Y35NY_DPG"},
    ),
    "jet_fuel_proxy": ProviderSeries(
        "jet_fuel_proxy",
        "EER_EPJK_PF4_RGC_DPG",
        "US Gulf Coast Kerosene-Type Jet Fuel Spot Price",
        units="usd_per_gallon",
        provider_args={"route": "petroleum/pri/spt/data/", "series": "EER_EPJK_PF4_RGC_DPG"},
    ),
    "eia_crude_inventories": ProviderSeries(
        "eia_crude_inventories",
        "WCESTUS1",
        "US Commercial Crude Oil Stocks Excluding SPR",
        frequency="weekly",
        units="thousand_barrels",
        provider_args={"route": "petroleum/stoc/wstk/data/", "series": "WCESTUS1"},
    ),
}


ALPHAVANTAGE_SERIES: Dict[str, ProviderSeries] = {
    "sp500_equity_proxy": ProviderSeries("sp500_equity_proxy", "SPY", "SPDR S&P 500 ETF Trust", units="usd"),
    "oil_equity_proxy": ProviderSeries("oil_equity_proxy", "XOM", "Exxon Mobil Equity Proxy", units="usd"),
    "airline_equity_proxy": ProviderSeries("airline_equity_proxy", "DAL", "Delta Air Lines Equity Proxy", units="usd"),
    "shipping_equity_proxy": ProviderSeries("shipping_equity_proxy", "MATX", "Matson Shipping Equity Proxy", units="usd"),
}


class ProviderIngestionError(RuntimeError):
    """Raised when a provider request cannot be parsed into usable rows."""


def _http_get_json(url: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    query = urlencode(params, doseq=True)
    request = Request(f"{url}?{query}", headers={"User-Agent": "fuel-credit-risk-agent/1.0"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
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
        ]
    )


def _normalize_rows(
    rows: Iterable[Dict[str, Any]],
    series: ProviderSeries,
    data_source: str,
) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return _empty_frame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["date", "price"])
    df = df[df["price"] > 0]
    if df.empty:
        return _empty_frame()

    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df["asset"] = series.asset
    df["asset_name"] = series.asset_name
    df["source_id"] = series.source_id
    df["data_source"] = data_source
    df["frequency"] = series.frequency
    df["units"] = series.units
    log_returns = np.log(df["price"] / df["price"].shift(1))
    df["return"] = log_returns.replace([np.inf, -np.inf], np.nan)
    df["rolling_volatility"] = df["return"].rolling(30, min_periods=5).std()
    return df[
        [
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
        ]
    ]


def _with_return_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add log return and rolling volatility per canonical asset/source."""
    if df.empty:
        return _empty_frame()
    frame = df.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame = frame.dropna(subset=["date", "asset", "price"])
    frame = frame[frame["price"] > 0]
    if frame.empty:
        return _empty_frame()
    frame = frame.sort_values(["asset", "source_id", "date"]).drop_duplicates(
        subset=["date", "asset", "source_id", "data_source"],
        keep="last",
    )
    group_keys = ["asset", "source_id", "data_source"]
    frame["return"] = frame.groupby(group_keys, dropna=False)["price"].transform(
        lambda values: np.log(values / values.shift(1))
    )
    frame["return"] = frame["return"].replace([np.inf, -np.inf], np.nan)
    frame["rolling_volatility"] = frame.groupby(group_keys, dropna=False)["return"].transform(
        lambda values: values.rolling(30, min_periods=5).std()
    )
    return frame[
        [
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
        ]
    ]


def add_calculated_market_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Add internally calculated market series such as jet crack spread."""
    if frame.empty:
        return frame
    base = frame.copy()
    base["date"] = pd.to_datetime(base["date"], errors="coerce").dt.normalize()
    pivot = base.pivot_table(index="date", columns="asset", values="price", aggfunc="last").sort_index()
    if "jet_fuel_proxy" not in pivot or not {"brent_oil", "crude_oil"}.intersection(pivot.columns):
        return frame
    crude_column = "brent_oil" if "brent_oil" in pivot else "crude_oil"
    # EIA jet fuel is stored in dollars per gallon. Convert to dollars per barrel.
    crack = (pivot["jet_fuel_proxy"] * 42.0) - pivot[crude_column]
    crack = crack.dropna()
    if crack.empty:
        return frame
    rows = pd.DataFrame(
        {
            "date": crack.index,
            "asset": "jet_crack_spread",
            "asset_name": f"Jet fuel crack spread versus {crude_column}",
            "source_id": f"calculated_jet_fuel_minus_{crude_column}",
            "price": crack.values,
            "data_source": "calculated_market_series",
            "frequency": "daily",
            "units": "usd_per_barrel",
        }
    )
    calculated = _with_return_columns(rows)
    return pd.concat([frame, calculated], ignore_index=True).sort_values(["asset", "date"])


def load_staged_market_csvs(
    input_dir: Path | str = STAGED_MARKET_INPUT_DIR,
    selected_assets: Optional[Iterable[str]] = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Load manually staged free-source market CSVs.

    Expected columns:
    date, asset, price or value. Optional:
    source_id, asset_name, data_source, frequency, units.
    """
    directory = Path(input_dir)
    selected = set(selected_assets or [])
    warnings: list[str] = []
    if not directory.exists():
        return _empty_frame(), [f"csv:{directory}: directory not found; skipping staged market CSVs"]
    frames: list[pd.DataFrame] = []
    for path in sorted(directory.glob("*.csv")):
        try:
            raw = pd.read_csv(path)
            if "price" not in raw.columns and "value" in raw.columns:
                raw = raw.rename(columns={"value": "price"})
            required = {"date", "asset", "price"}
            if not required.issubset(raw.columns):
                warnings.append(f"csv:{path.name}: missing required columns {sorted(required - set(raw.columns))}")
                continue
            raw["asset"] = raw["asset"].astype(str).str.strip()
            if selected:
                raw = raw[raw["asset"].isin(selected)]
            if raw.empty:
                continue
            raw["source_id"] = raw.get("source_id", path.stem)
            raw["asset_name"] = raw.get("asset_name", raw["asset"])
            raw["data_source"] = raw.get("data_source", f"staged_csv:{path.name}")
            raw["frequency"] = raw.get("frequency", "monthly")
            raw["units"] = raw.get("units", "index")
            frames.append(_with_return_columns(raw))
        except Exception as exc:
            warnings.append(f"csv:{path.name}: {exc}")
    if not frames:
        return _empty_frame(), warnings
    return pd.concat(frames, ignore_index=True).sort_values(["asset", "date"]), warnings


def fetch_fred_series(
    series: ProviderSeries,
    api_key: Optional[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    if not api_key:
        raise ProviderIngestionError("FRED_API_KEY is missing.")
    payload = _http_get_json(
        FRED_OBSERVATIONS_URL,
        {
            "series_id": series.source_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
        },
    )
    observations = payload.get("observations", [])
    rows = [
        {"date": item.get("date"), "price": item.get("value")}
        for item in observations
        if item.get("value") not in {None, "."}
    ]
    frame = _normalize_rows(rows, series, "fred")
    if frame.empty:
        raise ProviderIngestionError(f"FRED returned no usable rows for {series.source_id}.")
    return frame


def fetch_eia_series(
    series: ProviderSeries,
    api_key: Optional[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    if not api_key:
        raise ProviderIngestionError("EIA_API_KEY is missing.")
    provider_args = series.provider_args or {}
    route = provider_args.get("route")
    series_id = provider_args.get("series", series.source_id)
    if not route:
        raise ProviderIngestionError(f"EIA route missing for {series.source_id}.")

    payload = _http_get_json(
        f"{EIA_V2_BASE_URL}/{route.strip('/')}/",
        {
            "api_key": api_key,
            "frequency": series.frequency,
            "data[0]": "value",
            "facets[series][]": series_id,
            "start": start_date,
            "end": end_date,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": 0,
            "length": 5000,
        },
    )
    data = payload.get("response", {}).get("data", [])
    rows = [
        {
            "date": item.get("period"),
            "price": item.get("value"),
        }
        for item in data
    ]
    frame = _normalize_rows(rows, series, "eia")
    if frame.empty:
        raise ProviderIngestionError(f"EIA returned no usable rows for {series.source_id}.")
    return frame


def fetch_alphavantage_series(
    series: ProviderSeries,
    api_key: Optional[str],
    start_date: str,
    end_date: str,
    outputsize: str = "compact",
) -> pd.DataFrame:
    if not api_key:
        raise ProviderIngestionError("ALPHAVANTAGE_API_KEY is missing.")
    payload = _http_get_json(
        ALPHAVANTAGE_QUERY_URL,
        {
            "function": "TIME_SERIES_DAILY",
            "symbol": series.source_id,
            "outputsize": outputsize,
            "apikey": api_key,
        },
    )
    if "Note" in payload:
        raise ProviderIngestionError(f"Alpha Vantage rate limit note for {series.source_id}: {payload['Note']}")
    if "Error Message" in payload:
        raise ProviderIngestionError(f"Alpha Vantage error for {series.source_id}: {payload['Error Message']}")
    if "Information" in payload and "premium endpoint" in str(payload["Information"]).lower():
        payload = _http_get_json(
            ALPHAVANTAGE_QUERY_URL,
            {
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": series.source_id,
                "outputsize": outputsize,
                "apikey": api_key,
            },
        )
    if "Information" in payload:
        raise ProviderIngestionError(f"Alpha Vantage information for {series.source_id}: {payload['Information']}")
    time_series = payload.get("Time Series (Daily)", {})
    rows = []
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    for dt, values in time_series.items():
        parsed_date = pd.to_datetime(dt, errors="coerce")
        if pd.isna(parsed_date) or parsed_date < start or parsed_date > end:
            continue
        price = values.get("5. adjusted close") or values.get("4. close")
        rows.append({"date": parsed_date, "price": price})
    frame = _normalize_rows(rows, series, "alphavantage")
    if frame.empty:
        raise ProviderIngestionError(f"Alpha Vantage returned no usable rows for {series.source_id}.")
    return frame


def fetch_provider_data(
    providers: Iterable[str],
    start_date: str,
    end_date: Optional[str] = None,
    selected_assets: Optional[Iterable[str]] = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Fetch configured external provider data and return rows plus warnings."""
    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    selected = set(selected_assets or [])
    frames: list[pd.DataFrame] = []
    warnings: list[str] = []
    provider_set = {provider.lower() for provider in providers}

    if "fred" in provider_set:
        api_key = os.getenv("FRED_API_KEY")
        for asset, series in FRED_SERIES.items():
            if selected and asset not in selected:
                continue
            try:
                frames.append(fetch_fred_series(series, api_key, start_date, end_date))
            except Exception as exc:
                warnings.append(f"fred:{series.source_id}: {exc}")

    if "eia" in provider_set:
        api_key = os.getenv("EIA_API_KEY")
        for asset, series in EIA_SERIES.items():
            if selected and asset not in selected:
                continue
            try:
                frames.append(fetch_eia_series(series, api_key, start_date, end_date))
            except Exception as exc:
                warnings.append(f"eia:{series.source_id}: {exc}")

    if "alphavantage" in provider_set:
        api_key = os.getenv("ALPHAVANTAGE_API_KEY")
        for asset, series in ALPHAVANTAGE_SERIES.items():
            if selected and asset not in selected:
                continue
            try:
                frames.append(fetch_alphavantage_series(series, api_key, start_date, end_date))
                sleep(1.1)
            except Exception as exc:
                warnings.append(f"alphavantage:{series.source_id}: {exc}")

    if "csv" in provider_set or "staged_csv" in provider_set:
        csv_frame, csv_warnings = load_staged_market_csvs(selected_assets=selected_assets)
        if not csv_frame.empty:
            frames.append(csv_frame)
        warnings.extend(csv_warnings)

    if not frames:
        return _empty_frame(), warnings
    combined = pd.concat(frames, ignore_index=True).sort_values(["data_source", "asset", "date"])
    return add_calculated_market_series(combined), warnings
