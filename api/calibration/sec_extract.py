"""Extract company-level financial rows from SEC Financial Statement Data Set ZIPs."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from api.calibration.paths import COMPANY_FINANCIALS_CSV, SEC_FINANCIALS_DIR


TAG_MAP = {
    "revenue": [
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueGoodsNet",
    ],
    "ebit": ["OperatingIncomeLoss", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    "interest_expense": ["InterestExpenseNonOperating", "InterestExpense"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "accounts_receivable": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
    "inventory": ["InventoryNet"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "shareholders_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "free_cash_flow": ["FreeCashFlow"],
    "short_term_debt": ["ShortTermBorrowings", "ShortTermDebtCurrent"],
    "current_portion_long_term_debt": ["LongTermDebtCurrent", "CurrentPortionOfLongTermDebt"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "total_debt": ["DebtCurrent", "LongTermDebtAndFinanceLeaseObligationsCurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"],
}

FLAT_TAGS = {tag for tags in TAG_MAP.values() for tag in tags}


def _read_zip_table(zip_path: Path, name: str, columns: list[str] | None = None) -> pd.DataFrame:
    with ZipFile(zip_path) as archive:
        with archive.open(name) as handle:
            return pd.read_csv(handle, sep="\t", usecols=columns, low_memory=False)


def _first_available(row: pd.Series, tags: list[str]) -> float | None:
    for tag in tags:
        value = row.get(tag)
        if pd.notna(value):
            return float(value)
    return None


def extract_zip(zip_path: Path) -> pd.DataFrame:
    """Extract a compact financial row per filing from one SEC quarterly ZIP."""
    sub = _read_zip_table(
        zip_path,
        "sub.txt",
        ["adsh", "cik", "name", "sic", "countryba", "fy", "period", "form", "filed"],
    )
    num = _read_zip_table(zip_path, "num.txt", ["adsh", "tag", "ddate", "qtrs", "uom", "value"])
    num = num[(num["tag"].isin(FLAT_TAGS)) & (num["uom"].astype(str).str.upper() == "USD")]
    if num.empty:
        return pd.DataFrame()

    num["value"] = pd.to_numeric(num["value"], errors="coerce")
    num = num.dropna(subset=["value"])
    # Prefer annual duration facts for income/cash-flow tags and instant facts for balance-sheet tags.
    num = num.sort_values(["adsh", "tag", "ddate", "qtrs"])
    pivot = num.pivot_table(index="adsh", columns="tag", values="value", aggfunc="last")
    merged = sub.merge(pivot, left_on="adsh", right_index=True, how="inner")

    rows = []
    for _, row in merged.iterrows():
        extracted = {
            "company_id": str(row.get("cik", "")),
            "company_name": row.get("name"),
            "ticker": None,
            "cik": str(row.get("cik", "")),
            "fiscal_year": row.get("fy"),
            "period_end_date": row.get("period"),
            "currency": "USD",
            "industry": row.get("sic"),
            "country": row.get("countryba"),
            "data_source": f"sec_financial_statement_data_set:{zip_path.stem}",
        }
        for output_column, tags in TAG_MAP.items():
            extracted[output_column] = _first_available(row, tags)
        debt_parts = [
            extracted.get("short_term_debt"),
            extracted.get("current_portion_long_term_debt"),
            extracted.get("long_term_debt"),
        ]
        if extracted.get("total_debt") is None and any(value is not None for value in debt_parts):
            extracted["total_debt"] = sum(value or 0.0 for value in debt_parts)
        rows.append(extracted)

    frame = pd.DataFrame(rows)
    frame["period_end_date"] = pd.to_datetime(frame["period_end_date"], format="%Y%m%d", errors="coerce").dt.date
    return frame.dropna(subset=["company_id", "period_end_date"])


def extract_all_sec_quarterly_zips(overwrite: bool = False) -> pd.DataFrame:
    """Extract all downloaded SEC quarterly ZIPs into company_financials.csv."""
    zip_dir = SEC_FINANCIALS_DIR / "raw_sec_quarterly_zips"
    zips = sorted(zip_dir.glob("*.zip"))
    if not zips:
        return pd.DataFrame()
    if COMPANY_FINANCIALS_CSV.exists() and COMPANY_FINANCIALS_CSV.stat().st_size > 600 and not overwrite:
        existing = pd.read_csv(COMPANY_FINANCIALS_CSV)
        if len(existing) > 0:
            return existing
    frames = []
    for zip_path in zips:
        try:
            frame = extract_zip(zip_path)
        except Exception:
            continue
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.replace([np.inf, -np.inf], np.nan)
    combined = combined.drop_duplicates(subset=["company_id", "period_end_date"], keep="last")
    combined.to_csv(COMPANY_FINANCIALS_CSV, index=False)
    return combined

