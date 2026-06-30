"""Generate realistic synthetic trade recovery data for LGD calibration.

The generated rows are explicitly marked as synthetic. They are meant to reduce
hardcoded LGD assumptions for project/interview use, not to imitate confidential
bank recovery history.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from api.calibration.paths import (
    RECOVERY_PROXY_CSV,
    SYNTHETIC_TRADE_HISTORY_REPORT_JSON,
    TRADE_EXPOSURE_HISTORY_CSV,
    ensure_calibration_dirs,
)


COLLATERAL_PROFILES = {
    "unsecured": {"recovery": 0.28, "sigma": 0.13, "weight": 0.34, "deposit": 0.00},
    "letter_of_credit": {"recovery": 0.86, "sigma": 0.06, "weight": 0.18, "deposit": 0.00},
    "cash_deposit": {"recovery": 0.74, "sigma": 0.09, "weight": 0.16, "deposit": 0.35},
    "guarantee": {"recovery": 0.62, "sigma": 0.11, "weight": 0.18, "deposit": 0.00},
    "secured_collateral": {"recovery": 0.52, "sigma": 0.14, "weight": 0.14, "deposit": 0.00},
}

COUNTERPARTY_TYPES = ["airline", "fuel_trader", "shipping", "industrial", "retailer"]
COUNTRIES = ["US", "GB", "SG", "AE", "IN", "BR", "ZA", "DE"]
SENIORITIES = ["senior_secured", "senior_unsecured", "subordinated"]


def _choice(rng: np.random.Generator, values: list[str], probabilities: list[float] | None = None) -> str:
    return str(rng.choice(values, p=probabilities))


def _clip(value: float, low: float, high: float) -> float:
    return float(np.clip(value, low, high))


def _synthetic_row(index: int, rng: np.random.Generator, start_year: int, end_year: int) -> dict[str, Any]:
    collateral_types = list(COLLATERAL_PROFILES)
    collateral_weights = [COLLATERAL_PROFILES[item]["weight"] for item in collateral_types]
    collateral_type = _choice(rng, collateral_types, collateral_weights)
    profile = COLLATERAL_PROFILES[collateral_type]
    counterparty_type = _choice(rng, COUNTERPARTY_TYPES)
    seniority = _choice(rng, SENIORITIES, [0.40, 0.45, 0.15])
    country = _choice(rng, COUNTRIES)
    country_risk_score = {
        "US": 1.2,
        "GB": 1.4,
        "DE": 1.3,
        "SG": 1.2,
        "AE": 1.8,
        "IN": 2.3,
        "BR": 2.8,
        "ZA": 3.0,
    }[country] + rng.normal(0, 0.15)

    default_date = date(int(rng.integers(start_year, end_year + 1)), int(rng.integers(1, 13)), int(rng.integers(1, 28)))
    payment_tenor_days = int(_choice(rng, ["15", "30", "45", "60", "90"], [0.10, 0.36, 0.24, 0.20, 0.10]))
    approved_credit_limit = float(np.exp(rng.normal(np.log(4_000_000), 0.75)))
    requested_credit_limit = approved_credit_limit * rng.uniform(1.02, 1.35)
    utilization_rate = _clip(rng.beta(3.2, 2.4), 0.05, 1.0)
    realized_ead = approved_credit_limit * _clip(utilization_rate + rng.normal(0.05, 0.12), 0.05, 1.10)
    fuel_price = float(rng.normal(90, 22))
    fuel_price = _clip(fuel_price, 35, 170)
    fuel_volume = realized_ead / fuel_price * rng.uniform(0.55, 1.10)
    invoice_amount = fuel_volume * fuel_price
    outstanding_receivables = realized_ead * rng.uniform(0.35, 0.95)

    deposit_percentage = max(0.0, float(rng.normal(profile["deposit"], 0.07)))
    if collateral_type != "cash_deposit":
        deposit_percentage = 0.0 if rng.random() > 0.08 else float(rng.uniform(0.05, 0.20))
    deposit_percentage = _clip(deposit_percentage, 0.0, 0.70)

    stress_penalty = 0.035 * max(country_risk_score - 2.0, 0) + 0.025 * max(payment_tenor_days - 30, 0) / 30
    seniority_effect = {"senior_secured": 0.06, "senior_unsecured": 0.0, "subordinated": -0.08}[seniority]
    recovery_rate = rng.normal(profile["recovery"], profile["sigma"]) - stress_penalty + seniority_effect
    recovery_rate = max(recovery_rate, deposit_percentage)
    recovery_rate = _clip(recovery_rate, 0.03, 0.98)
    recovery_amount = realized_ead * recovery_rate
    lgd = 1 - recovery_rate
    legal_cost = realized_ead * _clip(rng.normal(0.025 + 0.015 * max(country_risk_score - 2, 0), 0.012), 0.003, 0.12)
    days_to_recovery = int(
        _clip(
            rng.normal(140 + 70 * max(country_risk_score - 1.5, 0) + 0.9 * payment_tenor_days, 45),
            30,
            720,
        )
    )
    write_off_amount = max(realized_ead - recovery_amount - legal_cost, 0)

    company_id = f"SYNTH-LGD-{index:06d}"
    company_name = f"Synthetic Trade Counterparty {index:06d}"
    return {
        "company_id": company_id,
        "company_name": company_name,
        "default_date": default_date.isoformat(),
        "facility_id": f"FAC-{index:06d}",
        "collateral_type": collateral_type,
        "seniority": seniority,
        "exposure_at_default": round(realized_ead, 2),
        "recovery_amount": round(recovery_amount, 2),
        "recovery_rate": round(recovery_rate, 6),
        "lgd": round(lgd, 6),
        "country": country,
        "data_source": "synthetic_phase6_trade_recovery",
        "resolution_date": (default_date + timedelta(days=days_to_recovery)).isoformat(),
        "days_to_recovery": days_to_recovery,
        "legal_cost": round(legal_cost, 2),
        "write_off_amount": round(write_off_amount, 2),
        "guarantor_type": "bank" if collateral_type in {"letter_of_credit", "guarantee"} else "",
        "payment_tenor_days": payment_tenor_days,
        "deposit_percentage": round(deposit_percentage, 6),
        "country_risk_score": round(country_risk_score, 4),
        "counterparty_type": counterparty_type,
        "letter_of_credit_flag": int(collateral_type == "letter_of_credit"),
        "guarantee_flag": int(collateral_type == "guarantee"),
        "approved_credit_limit": round(approved_credit_limit, 2),
        "requested_credit_limit": round(requested_credit_limit, 2),
        "observation_date": default_date.isoformat(),
        "invoice_amount": round(invoice_amount, 2),
        "fuel_volume": round(fuel_volume, 2),
        "fuel_price": round(fuel_price, 4),
        "outstanding_receivables": round(outstanding_receivables, 2),
        "utilization_rate": round(utilization_rate, 6),
        "days_past_due": int(_clip(rng.normal(38 + 0.28 * payment_tenor_days, 18), 0, 180)),
        "default_or_writeoff_flag": 1,
        "realized_ead": round(realized_ead, 2),
    }


def generate_synthetic_trade_history(
    rows: int = 5000,
    seed: int = 42,
    start_year: int = 2016,
    end_year: int = 2026,
    overwrite: bool = False,
) -> dict[str, Any]:
    ensure_calibration_dirs()
    if RECOVERY_PROXY_CSV.exists() and not overwrite:
        existing = pd.read_csv(RECOVERY_PROXY_CSV)
        if not existing.empty and "synthetic_phase6_trade_recovery" in set(existing.get("data_source", [])):
            return {
                "created": False,
                "reason": "synthetic_phase6_data_already_exists",
                "recovery_rows": int(len(existing)),
                "recovery_path": str(RECOVERY_PROXY_CSV),
                "trade_path": str(TRADE_EXPOSURE_HISTORY_CSV),
            }

    rng = np.random.default_rng(seed)
    frame = pd.DataFrame([_synthetic_row(i + 1, rng, start_year, end_year) for i in range(rows)])

    recovery_columns = [
        "company_id",
        "company_name",
        "default_date",
        "facility_id",
        "collateral_type",
        "seniority",
        "exposure_at_default",
        "recovery_amount",
        "recovery_rate",
        "lgd",
        "country",
        "data_source",
        "resolution_date",
        "days_to_recovery",
        "legal_cost",
        "write_off_amount",
        "guarantor_type",
        "payment_tenor_days",
        "deposit_percentage",
        "country_risk_score",
        "counterparty_type",
        "letter_of_credit_flag",
        "guarantee_flag",
    ]
    trade_columns = [
        "company_id",
        "company_name",
        "observation_date",
        "invoice_amount",
        "fuel_volume",
        "fuel_price",
        "approved_credit_limit",
        "requested_credit_limit",
        "outstanding_receivables",
        "payment_tenor_days",
        "utilization_rate",
        "collateral_type",
        "letter_of_credit_flag",
        "guarantee_flag",
        "deposit_percentage",
        "days_past_due",
        "default_or_writeoff_flag",
        "realized_ead",
        "data_source",
        "write_off_amount",
        "recovery_amount",
        "country_risk_score",
        "counterparty_type",
    ]
    frame[recovery_columns].to_csv(RECOVERY_PROXY_CSV, index=False)
    frame[trade_columns].to_csv(TRADE_EXPOSURE_HISTORY_CSV, index=False)

    summary = {
        "created": True,
        "phase": "phase_6_synthetic_trade_recovery_history",
        "rows": int(len(frame)),
        "seed": int(seed),
        "year_range": [int(start_year), int(end_year)],
        "recovery_path": str(RECOVERY_PROXY_CSV),
        "trade_path": str(TRADE_EXPOSURE_HISTORY_CSV),
        "average_lgd": float(frame["lgd"].mean()),
        "average_recovery_rate": float(frame["recovery_rate"].mean()),
        "average_ead": float(frame["exposure_at_default"].mean()),
        "collateral_mix": frame["collateral_type"].value_counts(normalize=True).round(4).to_dict(),
        "lgd_by_collateral": frame.groupby("collateral_type")["lgd"].mean().round(4).to_dict(),
        "important_note": "Synthetic rows are marked in data_source and should be replaced by real recovery/EAD history when available.",
    }
    SYNTHETIC_TRADE_HISTORY_REPORT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic trade recovery history for LGD calibration.")
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-year", type=int, default=2016)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            generate_synthetic_trade_history(
                rows=args.rows,
                seed=args.seed,
                start_year=args.start_year,
                end_year=args.end_year,
                overwrite=args.overwrite,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
