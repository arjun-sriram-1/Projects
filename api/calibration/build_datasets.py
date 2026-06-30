"""Build model-ready calibration datasets from free-source CSV inputs."""

from __future__ import annotations

import argparse
import json
from typing import Iterable

import numpy as np
import pandas as pd

from api.calibration.paths import (
    COMPANY_FINANCIALS_CSV,
    DEFAULT_LABELS_CSV,
    EAD_TRAINING_CSV,
    LGD_TRAINING_CSV,
    MARKET_CONTEXT_CSV,
    PD_TRAINING_CSV,
    PROCESSED_ROOT,
    RECOVERY_PROXY_CSV,
    REPORT_ROOT,
    TRADE_EXPOSURE_HISTORY_CSV,
    ensure_calibration_dirs,
)
from api.calibration.sec_extract import extract_all_sec_quarterly_zips


RATIO_COLUMNS = [
    "current_ratio",
    "quick_ratio",
    "cash_ratio",
    "working_capital",
    "debt_to_equity",
    "debt_to_ebitda",
    "liabilities_to_assets",
    "interest_coverage",
    "operating_margin",
    "net_margin",
    "return_on_assets",
    "return_on_equity",
]


def _read_csv(path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if len(frame) == 0:
        return frame
    return frame.dropna(how="all")


def _numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def calculate_ratios(financials: pd.DataFrame) -> pd.DataFrame:
    frame = financials.copy()
    numeric_columns = [
        "revenue",
        "ebitda",
        "ebit",
        "interest_expense",
        "net_income",
        "cash_and_equivalents",
        "accounts_receivable",
        "inventory",
        "current_assets",
        "current_liabilities",
        "total_assets",
        "total_debt",
        "total_liabilities",
        "shareholders_equity",
    ]
    for column in numeric_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    frame = _numeric(frame, numeric_columns)
    if frame["ebitda"].isna().all() and not frame["ebit"].isna().all():
        frame["ebitda"] = frame["ebit"]
    if "current_ratio" not in frame or frame["current_ratio"].isna().all():
        frame["current_ratio"] = _safe_divide(frame["current_assets"], frame["current_liabilities"])
    if "quick_ratio" not in frame or frame["quick_ratio"].isna().all():
        quick_assets = frame["cash_and_equivalents"].fillna(0) + frame["accounts_receivable"].fillna(0)
        fallback_quick_assets = frame["current_assets"] - frame["inventory"]
        quick_assets = quick_assets.where(quick_assets > 0, fallback_quick_assets)
        frame["quick_ratio"] = _safe_divide(quick_assets, frame["current_liabilities"])
    if "cash_ratio" not in frame or frame["cash_ratio"].isna().all():
        frame["cash_ratio"] = _safe_divide(frame["cash_and_equivalents"], frame["current_liabilities"])
    if "working_capital" not in frame or frame["working_capital"].isna().all():
        frame["working_capital"] = frame["current_assets"] - frame["current_liabilities"]
    if "debt_to_equity" not in frame or frame["debt_to_equity"].isna().all():
        frame["debt_to_equity"] = _safe_divide(frame["total_debt"], frame["shareholders_equity"])
    if "debt_to_ebitda" not in frame or frame["debt_to_ebitda"].isna().all():
        frame["debt_to_ebitda"] = _safe_divide(frame["total_debt"], frame["ebitda"])
    if "liabilities_to_assets" not in frame or frame["liabilities_to_assets"].isna().all():
        frame["liabilities_to_assets"] = _safe_divide(frame["total_liabilities"], frame["total_assets"])
    if "interest_coverage" not in frame or frame["interest_coverage"].isna().all():
        frame["interest_coverage"] = _safe_divide(frame["ebit"], frame["interest_expense"])
    if "operating_margin" not in frame or frame["operating_margin"].isna().all():
        frame["operating_margin"] = _safe_divide(frame["ebit"], frame["revenue"])
    if "net_margin" not in frame or frame["net_margin"].isna().all():
        frame["net_margin"] = _safe_divide(frame["net_income"], frame["revenue"])
    if "return_on_assets" not in frame or frame["return_on_assets"].isna().all():
        frame["return_on_assets"] = _safe_divide(frame["net_income"], frame["total_assets"])
    if "return_on_equity" not in frame or frame["return_on_equity"].isna().all():
        frame["return_on_equity"] = _safe_divide(frame["net_income"], frame["shareholders_equity"])
    return frame


def _merge_market(financials: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    if financials.empty or market.empty or "period_end_date" not in financials or "date" not in market:
        return financials
    left = financials.copy()
    right = market.copy()
    left["period_end_date"] = pd.to_datetime(left["period_end_date"], errors="coerce")
    right["date"] = pd.to_datetime(right["date"], errors="coerce")
    right = right.dropna(subset=["date"]).sort_values("date")
    left = left.dropna(subset=["period_end_date"]).sort_values("period_end_date")
    merged = pd.merge_asof(left, right, left_on="period_end_date", right_on="date", direction="backward")
    return merged


def _proxy_default_label(frame: pd.DataFrame) -> pd.Series:
    liabilities = pd.to_numeric(frame.get("liabilities_to_assets"), errors="coerce")
    equity = pd.to_numeric(frame.get("shareholders_equity"), errors="coerce")
    coverage = pd.to_numeric(frame.get("interest_coverage"), errors="coerce")
    leverage = pd.to_numeric(frame.get("debt_to_ebitda"), errors="coerce")
    net_margin = pd.to_numeric(frame.get("net_margin"), errors="coerce")
    distress = (
        (equity <= 0)
        | (liabilities >= 1.0)
        | ((liabilities >= 0.90) & (coverage < 1.0))
        | ((leverage > 8.0) & (net_margin < 0))
    )
    return distress.fillna(False).astype(int)


def build_pd_dataset(use_proxy_labels: bool = True) -> pd.DataFrame:
    financials = _read_csv(COMPANY_FINANCIALS_CSV)
    if financials.empty:
        financials = extract_all_sec_quarterly_zips()
    if financials.empty:
        return pd.DataFrame()
    financials = calculate_ratios(financials)
    market = _read_csv(MARKET_CONTEXT_CSV)
    labels = _read_csv(DEFAULT_LABELS_CSV)
    if financials.empty:
        return pd.DataFrame()
    frame = _merge_market(financials, market)
    if not labels.empty:
        label_cols = ["company_id", "label_date", "default_label", "default_type", "label_horizon_months", "data_source"]
        labels = labels[[col for col in label_cols if col in labels.columns]].copy()
        labels["label_date"] = pd.to_datetime(labels.get("label_date"), errors="coerce")
        frame["period_end_date"] = pd.to_datetime(frame.get("period_end_date"), errors="coerce")
        frame = frame.merge(labels, on="company_id", how="left", suffixes=("", "_label"))
    if "default_label" not in frame or frame["default_label"].isna().all():
        if use_proxy_labels:
            frame["default_label"] = _proxy_default_label(frame)
            frame["default_type"] = "financial_distress_proxy"
            frame["label_horizon_months"] = 12
        else:
            return pd.DataFrame()
    frame["data_source"] = frame.get("data_source", "free_source_csv")
    return frame


def build_lgd_dataset(use_proxy_lgd: bool = True) -> pd.DataFrame:
    recovery = _read_csv(RECOVERY_PROXY_CSV)
    if not recovery.empty:
        recovery = _numeric(recovery, ["exposure_at_default", "recovery_amount", "recovery_rate", "lgd"])
        if "lgd" not in recovery or recovery["lgd"].isna().all():
            recovery["lgd"] = 1 - recovery["recovery_rate"]
        return recovery
    if not use_proxy_lgd:
        return pd.DataFrame()
    trades = _read_csv(TRADE_EXPOSURE_HISTORY_CSV)
    if trades.empty:
        return pd.DataFrame()
    trades = _numeric(
        trades,
        [
            "default_or_writeoff_flag",
            "write_off_amount",
            "recovery_amount",
            "realized_ead",
            "approved_credit_limit",
            "requested_credit_limit",
            "payment_tenor_days",
            "deposit_percentage",
        ],
    )
    ead = trades["realized_ead"].fillna(trades["approved_credit_limit"]).fillna(trades["requested_credit_limit"])
    loss = trades["write_off_amount"].fillna((ead - trades["recovery_amount"].fillna(0)).clip(lower=0))
    trades["exposure_at_default"] = ead
    trades["lgd"] = (loss / ead.replace(0, np.nan)).clip(0, 1)
    return trades.dropna(subset=["lgd"])


def build_ead_dataset() -> pd.DataFrame:
    trades = _read_csv(TRADE_EXPOSURE_HISTORY_CSV)
    if trades.empty:
        return pd.DataFrame()
    trades = _numeric(
        trades,
        [
            "invoice_amount",
            "fuel_volume",
            "fuel_price",
            "approved_credit_limit",
            "requested_credit_limit",
            "outstanding_receivables",
            "payment_tenor_days",
            "utilization_rate",
            "realized_ead",
        ],
    )
    if "realized_ead" not in trades:
        return pd.DataFrame()
    invoice_exposure = trades["invoice_amount"].fillna(trades["fuel_volume"] * trades["fuel_price"])
    trades["invoice_exposure"] = invoice_exposure
    trades["ead_ratio"] = trades["realized_ead"] / trades["approved_credit_limit"].fillna(trades["requested_credit_limit"]).replace(0, np.nan)
    return trades.dropna(subset=["realized_ead"])


def build_all(use_proxy_labels: bool = True, use_proxy_lgd: bool = True) -> dict[str, int]:
    ensure_calibration_dirs()
    pd_frame = build_pd_dataset(use_proxy_labels=use_proxy_labels)
    lgd_frame = build_lgd_dataset(use_proxy_lgd=use_proxy_lgd)
    ead_frame = build_ead_dataset()
    if not pd_frame.empty:
        pd_frame.to_csv(PD_TRAINING_CSV, index=False)
    if not lgd_frame.empty:
        lgd_frame.to_csv(LGD_TRAINING_CSV, index=False)
    if not ead_frame.empty:
        ead_frame.to_csv(EAD_TRAINING_CSV, index=False)
    summary = {
        "pd_rows": int(len(pd_frame)),
        "lgd_rows": int(len(lgd_frame)),
        "ead_rows": int(len(ead_frame)),
        "proxy_default_labels_allowed": bool(use_proxy_labels),
        "proxy_lgd_allowed": bool(use_proxy_lgd),
    }
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / "dataset_build_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build calibration datasets from free-source CSV files.")
    parser.add_argument("--no-proxy-labels", action="store_true", help="Require explicit default labels.")
    parser.add_argument("--no-proxy-lgd", action="store_true", help="Require explicit recovery/LGD data.")
    args = parser.parse_args()
    summary = build_all(
        use_proxy_labels=not args.no_proxy_labels,
        use_proxy_lgd=not args.no_proxy_lgd,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
