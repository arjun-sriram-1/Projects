"""Download free public source data into the calibration staging area.

The downloader is intentionally conservative. It stores raw public files under
data/external/free_sources and never mutates live application tables.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from api.calibration.paths import MARKET_CONTEXT_CSV, SEC_FINANCIALS_DIR, ensure_calibration_dirs
from api.market_data.assets import PD_MARKET_FEATURES


SEC_USER_AGENT = "JetFuelCreditRiskResearch/1.0 contact@example.com"
SEC_FS_BASE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
SEC_COMPANYFACTS_URL = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
WORLD_BANK_JSON = "https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&per_page=20000"


WORLD_BANK_INDICATORS = {
    "gdp_current_usd": "NY.GDP.MKTP.CD",
    "inflation_cpi": "FP.CPI.TOTL.ZG",
    "real_interest_rate": "FR.INR.RINR",
    "exports_goods_services_pct_gdp": "NE.EXP.GNFS.ZS",
    "imports_goods_services_pct_gdp": "NE.IMP.GNFS.ZS",
}


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": SEC_USER_AGENT,
            "Accept-Encoding": "identity",
        },
    )


def download_file(url: str, output_path: Path, *, overwrite: bool = False, pause_seconds: float = 0.2) -> bool:
    """Download a URL if the target does not already exist."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        return False
    try:
        with urllib.request.urlopen(_request(url), timeout=60) as response:
            output_path.write_bytes(response.read())
        time.sleep(pause_seconds)
        return True
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Download failed for {url}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Download failed for {url}: {exc}") from exc


def download_sec_financial_statement_zips(
    start_year: int = 2020,
    end_year: int | None = None,
    quarters: Iterable[int] = (1, 2, 3, 4),
    overwrite: bool = False,
) -> list[Path]:
    """Download SEC quarterly Financial Statement Data Set ZIP files."""
    ensure_calibration_dirs()
    end_year = end_year or date.today().year
    downloaded: list[Path] = []
    for year in range(int(start_year), int(end_year) + 1):
        for quarter in quarters:
            if quarter not in {1, 2, 3, 4}:
                continue
            url = f"{SEC_FS_BASE}/{year}q{quarter}.zip"
            output = SEC_FINANCIALS_DIR / "raw_sec_quarterly_zips" / f"{year}q{quarter}.zip"
            try:
                if download_file(url, output, overwrite=overwrite):
                    downloaded.append(output)
            except RuntimeError:
                # Some current-year future quarters may not exist yet.
                continue
    return downloaded


def download_sec_companyfacts_zip(overwrite: bool = False) -> Path:
    """Download the large SEC companyfacts bulk ZIP file."""
    ensure_calibration_dirs()
    output = SEC_FINANCIALS_DIR / "companyfacts.zip"
    download_file(SEC_COMPANYFACTS_URL, output, overwrite=overwrite, pause_seconds=1.0)
    return output


def download_world_bank_indicators(overwrite: bool = False) -> Path:
    """Download selected World Bank indicators to a tidy CSV."""
    ensure_calibration_dirs()
    output = MARKET_CONTEXT_CSV.parent / "world_bank_indicators.csv"
    if output.exists() and not overwrite:
        return output
    rows: list[dict] = []
    for label, indicator in WORLD_BANK_INDICATORS.items():
        url = WORLD_BANK_JSON.format(indicator=indicator)
        with urllib.request.urlopen(_request(url), timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        observations = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        for obs in observations:
            rows.append(
                {
                    "country": (obs.get("country") or {}).get("value"),
                    "country_code": obs.get("countryiso3code"),
                    "date": obs.get("date"),
                    "indicator": label,
                    "indicator_code": indicator,
                    "value": obs.get("value"),
                    "data_source": "world_bank",
                }
            )
        time.sleep(0.2)
    pd.DataFrame(rows).to_csv(output, index=False)
    return output


def download_yfinance_market_context(start: str = "2010-01-01", overwrite: bool = False) -> Path:
    """Download broad market proxies through yfinance when available."""
    ensure_calibration_dirs()
    output = MARKET_CONTEXT_CSV.parent / "yfinance_market_context.csv"
    if output.exists() and not overwrite:
        return output
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed") from exc

    tickers = {
        "brent_oil": "BZ=F",
        "crude_oil": "CL=F",
        "heating_oil_proxy": "HO=F",
        "vix": "^VIX",
        "sp500": "^GSPC",
        "dxy": "DX-Y.NYB",
        "gold": "GC=F",
        "us_10y_yield": "^TNX",
        "us_2y_yield": "^IRX",
        "freight_proxy": "BDRY",
    }
    frames = []
    for asset, ticker in tickers.items():
        data = yf.download(ticker, start=start, progress=False, auto_adjust=False)
        if data.empty:
            continue
        close = data["Adj Close"] if "Adj Close" in data else data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.dropna()
        if close.empty:
            continue
        frame = pd.DataFrame({"date": close.index.date, asset: close.to_numpy().reshape(-1)})
        frames.append(frame)
    if not frames:
        raise RuntimeError("No yfinance market data downloaded")
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="date", how="outer")
    merged["data_source"] = "yfinance"
    merged.sort_values("date").to_csv(output, index=False)
    return output


def merge_market_context_sources() -> Path:
    """Create the Phase 2 market_context.csv from available free-source files."""
    ensure_calibration_dirs()
    yf_path = MARKET_CONTEXT_CSV.parent / "yfinance_market_context.csv"
    if yf_path.exists():
        frame = pd.read_csv(yf_path)
    else:
        frame = pd.read_csv(MARKET_CONTEXT_CSV) if MARKET_CONTEXT_CSV.exists() else pd.DataFrame()
    if frame.empty:
        return MARKET_CONTEXT_CSV

    if "jet_fuel_proxy" not in frame.columns or frame["jet_fuel_proxy"].isna().all():
        frame["jet_fuel_proxy"] = frame.get("heating_oil_proxy")
    if {"jet_fuel_proxy", "brent_oil"}.issubset(frame.columns) and (
        "jet_crack_spread" not in frame.columns or frame["jet_crack_spread"].isna().all()
    ):
        frame["jet_crack_spread"] = (
            pd.to_numeric(frame["jet_fuel_proxy"], errors="coerce") * 42
            - pd.to_numeric(frame["brent_oil"], errors="coerce")
        )
    if "global_pmi" not in frame.columns or frame["global_pmi"].isna().all():
        frame["global_pmi"] = frame.get("pmi")
    if {"us_10y_yield", "us_2y_yield"}.issubset(frame.columns):
        frame["yield_curve_spread"] = frame["us_10y_yield"] - frame["us_2y_yield"]
    if "stress_index" not in frame.columns or frame["stress_index"].isna().all():
        vix = pd.to_numeric(frame.get("vix"), errors="coerce")
        crude = pd.to_numeric(frame.get("crude_oil"), errors="coerce")
        sp500 = pd.to_numeric(frame.get("sp500"), errors="coerce")
        vix_score = ((vix - 12) / 28).clip(0, 1)
        oil_score = crude.pct_change(21, fill_method=None).abs().rolling(21, min_periods=5).mean().mul(10).clip(0, 1)
        equity_score = sp500.pct_change(21, fill_method=None).mul(-4).clip(0, 1)
        frame["stress_index"] = (100 * (0.55 * vix_score + 0.25 * oil_score + 0.20 * equity_score)).clip(0, 100)
    if "market_regime" not in frame.columns or frame["market_regime"].isna().all():
        stress = pd.to_numeric(frame.get("stress_index"), errors="coerce")
        frame["market_regime"] = np.select(
            [stress >= 70, stress >= 40],
            ["Stress", "Watch"],
            default="Normal",
        )
    if "recession_flag" not in frame.columns or frame["recession_flag"].isna().all():
        spread = pd.to_numeric(frame.get("yield_curve_spread"), errors="coerce")
        frame["recession_flag"] = (spread < 0).astype(int)

    required = list(
        dict.fromkeys(
            [
                "date",
                "gold",
                "us_2y_yield",
                "cpi_index",
                "market_regime",
                "recession_flag",
                "high_yield_spread",
                "country_risk_score",
                "data_source",
            ]
            + PD_MARKET_FEATURES
        )
    )
    for column in required:
        if column not in frame.columns:
            frame[column] = None
    frame[required].to_csv(MARKET_CONTEXT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    return MARKET_CONTEXT_CSV


def run_downloads(args: argparse.Namespace) -> list[Path]:
    outputs: list[Path] = []
    if args.sec_quarterly:
        outputs.extend(
            download_sec_financial_statement_zips(
                start_year=args.start_year,
                end_year=args.end_year,
                overwrite=args.overwrite,
            )
        )
    if args.sec_companyfacts:
        outputs.append(download_sec_companyfacts_zip(overwrite=args.overwrite))
    if args.world_bank:
        outputs.append(download_world_bank_indicators(overwrite=args.overwrite))
    if args.yfinance:
        outputs.append(download_yfinance_market_context(start=args.market_start, overwrite=args.overwrite))
        outputs.append(merge_market_context_sources())
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Download free calibration data sources.")
    parser.add_argument("--sec-quarterly", action="store_true", help="Download SEC quarterly financial ZIPs.")
    parser.add_argument("--sec-companyfacts", action="store_true", help="Download the large SEC companyfacts bulk ZIP.")
    parser.add_argument("--world-bank", action="store_true", help="Download selected World Bank indicators.")
    parser.add_argument("--yfinance", action="store_true", help="Download market proxies using yfinance.")
    parser.add_argument("--all-light", action="store_true", help="Download SEC quarterly, World Bank, and yfinance data.")
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=date.today().year)
    parser.add_argument("--market-start", default="2010-01-01")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.all_light:
        args.sec_quarterly = True
        args.world_bank = True
        args.yfinance = True

    outputs = run_downloads(args)
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
