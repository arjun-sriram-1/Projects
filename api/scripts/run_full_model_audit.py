"""Run a destructive end-to-end audit of the credit risk workflow.

This script is intentionally HTTP-based: it exercises the same FastAPI routes
the frontend depends on. It backs up current API-visible counterparty data,
deletes counterparties through the public delete endpoint, seeds 10 synthetic
profiles, runs ratios, PD, LGD/EAD/EL, Monte Carlo, and recommendation, then
writes a Markdown audit report.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8010"
OUT_DIR = Path("data/audit_runs")


@dataclass
class Scenario:
    name: str
    counterparty_type: str
    country: str
    mode: str
    periods: list[dict[str, Any]]
    exposure: dict[str, Any]


def _json_default(value: Any) -> str:
    return str(value)


def request_json(method: str, path: str, payload: Any | None = None, timeout: int = 60) -> Any:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {path} -> connection failed: {exc}") from exc


def get(path: str, timeout: int = 60) -> Any:
    return request_json("GET", path, timeout=timeout)


def post(path: str, payload: Any | None = None, timeout: int = 60) -> Any:
    return request_json("POST", path, payload=payload, timeout=timeout)


def delete(path: str, timeout: int = 60) -> Any:
    return request_json("DELETE", path, timeout=timeout)


def nearly_equal(a: Any, b: Any, tolerance: float) -> bool:
    try:
        av = float(a)
        bv = float(b)
    except (TypeError, ValueError):
        return False
    return abs(av - bv) <= tolerance


def ratio_or_none(top: Any, bottom: Any) -> float | None:
    try:
        top_v = float(top)
        bottom_v = float(bottom)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(top_v) or not math.isfinite(bottom_v) or bottom_v == 0:
        return None
    return top_v / bottom_v


def base_period(
    *,
    fiscal_year: int,
    period_type: str = "annual",
    period_label: str = "FY",
    revenue: float,
    ebitda_margin: float,
    net_margin: float,
    debt_ratio: float,
    cash_ratio: float,
    current_ratio: float,
    asset_turnover: float = 0.82,
    interest_rate: float = 0.075,
    latest: bool = False,
) -> dict[str, Any]:
    ebitda = revenue * ebitda_margin
    ebit = ebitda * 0.82
    total_assets = revenue / asset_turnover
    total_debt = revenue * debt_ratio
    current_liabilities = max(revenue * 0.18, 1.0)
    current_assets = current_liabilities * current_ratio
    total_liabilities = total_debt + current_liabilities + revenue * 0.08
    shareholders_equity = total_assets - total_liabilities
    return {
        "counterparty_id": 0,
        "fiscal_year": fiscal_year,
        "period_type": period_type,
        "period_label": period_label,
        "is_latest_snapshot": latest,
        "fiscal_period": period_label,
        "currency": "USD",
        "revenue": round(revenue, 2),
        "ebitda": round(ebitda, 2),
        "ebit": round(ebit, 2),
        "interest_expense": round(max(total_debt * interest_rate, revenue * 0.003), 2),
        "net_income": round(revenue * net_margin, 2),
        "cash_and_equivalents": round(revenue * cash_ratio, 2),
        "accounts_receivable": round(revenue * 0.11, 2),
        "inventory": round(revenue * 0.035, 2),
        "current_assets": round(current_assets, 2),
        "total_assets": round(total_assets, 2),
        "current_liabilities": round(current_liabilities, 2),
        "total_debt": round(total_debt, 2),
        "total_liabilities": round(total_liabilities, 2),
        "shareholders_equity": round(shareholders_equity, 2),
        "created_by": "full_model_audit",
    }


def annual_history(
    start_year: int,
    revenues: list[float],
    ebitda_margins: list[float],
    net_margins: list[float],
    debt_ratios: list[float],
    cash_ratios: list[float],
    current_ratios: list[float],
) -> list[dict[str, Any]]:
    periods = []
    for index, revenue in enumerate(revenues):
        periods.append(
            base_period(
                fiscal_year=start_year + index,
                revenue=revenue,
                ebitda_margin=ebitda_margins[index],
                net_margin=net_margins[index],
                debt_ratio=debt_ratios[index],
                cash_ratio=cash_ratios[index],
                current_ratio=current_ratios[index],
                latest=index == len(revenues) - 1,
            )
        )
    return periods


def quarterly_history(
    start_year: int,
    quarters: list[tuple[int, str, float, float, float, float, float, float]],
) -> list[dict[str, Any]]:
    periods = []
    for index, (year, label, revenue, ebitda_margin, net_margin, debt_ratio, cash_ratio, current_ratio) in enumerate(quarters):
        periods.append(
            base_period(
                fiscal_year=year or start_year,
                period_type="quarterly",
                period_label=label,
                revenue=revenue,
                ebitda_margin=ebitda_margin,
                net_margin=net_margin,
                debt_ratio=debt_ratio,
                cash_ratio=cash_ratio,
                current_ratio=current_ratio,
                latest=index == len(quarters) - 1,
            )
        )
    return periods


def scenarios() -> list[Scenario]:
    return [
        Scenario(
            "Audit Single Strong Flag Carrier",
            "Airline (Jet Fuel)",
            "United States",
            "single_year",
            [base_period(fiscal_year=2026, revenue=4_800_000_000, ebitda_margin=0.18, net_margin=0.075, debt_ratio=0.24, cash_ratio=0.13, current_ratio=1.75, latest=True)],
            {"requested_credit_limit": 22_000_000, "approved_credit_limit": 18_000_000, "invoice_amount": 2_100_000, "fuel_volume": 720_000, "fuel_price": 2.75, "outstanding_receivables": 5_000_000, "payment_tenor_days": 30, "utilization_rate": 0.45, "collateral_type": "letter_of_credit", "letter_of_credit_flag": True, "deposit_percentage": 0},
        ),
        Scenario(
            "Audit Single Leveraged Regional Airline",
            "Airline (Jet Fuel)",
            "India",
            "single_year",
            [base_period(fiscal_year=2026, revenue=950_000_000, ebitda_margin=0.075, net_margin=-0.018, debt_ratio=0.78, cash_ratio=0.035, current_ratio=0.82, latest=True)],
            {"requested_credit_limit": 9_000_000, "approved_credit_limit": 5_500_000, "invoice_amount": 1_150_000, "fuel_volume": 410_000, "fuel_price": 2.81, "outstanding_receivables": 3_200_000, "payment_tenor_days": 45, "utilization_rate": 0.72, "collateral_type": "guarantee", "guarantee_flag": True, "deposit_percentage": 0},
        ),
        Scenario(
            "Audit Single Startup Carrier",
            "Airline (Jet Fuel)",
            "United Arab Emirates",
            "single_year",
            [base_period(fiscal_year=2026, revenue=210_000_000, ebitda_margin=0.035, net_margin=-0.055, debt_ratio=0.62, cash_ratio=0.055, current_ratio=1.02, latest=True)],
            {"requested_credit_limit": 3_500_000, "approved_credit_limit": 2_000_000, "invoice_amount": 520_000, "fuel_volume": 190_000, "fuel_price": 2.74, "outstanding_receivables": 980_000, "payment_tenor_days": 30, "utilization_rate": 0.56, "collateral_type": "cash_deposit", "deposit_percentage": 25},
        ),
        Scenario(
            "Audit Single Cargo Airline Stable",
            "Cargo Airline",
            "Singapore",
            "single_year",
            [base_period(fiscal_year=2026, revenue=1_650_000_000, ebitda_margin=0.145, net_margin=0.044, debt_ratio=0.42, cash_ratio=0.095, current_ratio=1.28, latest=True)],
            {"requested_credit_limit": 12_000_000, "approved_credit_limit": 9_500_000, "invoice_amount": 1_450_000, "fuel_volume": 500_000, "fuel_price": 2.90, "outstanding_receivables": 3_700_000, "payment_tenor_days": 35, "utilization_rate": 0.50, "collateral_type": "letter_of_credit", "letter_of_credit_flag": True, "deposit_percentage": 0},
        ),
        Scenario(
            "Audit Single Thin Margin Charter",
            "Airline Charter",
            "Turkey",
            "single_year",
            [base_period(fiscal_year=2026, revenue=620_000_000, ebitda_margin=0.058, net_margin=0.004, debt_ratio=0.55, cash_ratio=0.045, current_ratio=0.94, latest=True)],
            {"requested_credit_limit": 6_000_000, "approved_credit_limit": 3_800_000, "invoice_amount": 860_000, "fuel_volume": 300_000, "fuel_price": 2.86, "outstanding_receivables": 2_100_000, "payment_tenor_days": 45, "utilization_rate": 0.67, "collateral_type": "unsecured", "deposit_percentage": 0},
        ),
        Scenario(
            "Audit Multi Improving Airline",
            "Airline (Jet Fuel)",
            "United States",
            "multi_annual",
            annual_history(2022, [1.8e9, 2.0e9, 2.35e9, 2.75e9, 3.1e9], [0.08, 0.10, 0.12, 0.145, 0.165], [0.01, 0.022, 0.035, 0.052, 0.064], [0.62, 0.56, 0.49, 0.42, 0.34], [0.045, 0.055, 0.07, 0.085, 0.105], [0.92, 1.04, 1.18, 1.32, 1.48]),
            {"requested_credit_limit": 16_000_000, "approved_credit_limit": 13_500_000, "invoice_amount": 1_800_000, "fuel_volume": 640_000, "fuel_price": 2.82, "outstanding_receivables": 4_000_000, "payment_tenor_days": 30, "utilization_rate": 0.48, "collateral_type": "letter_of_credit", "letter_of_credit_flag": True, "deposit_percentage": 0},
        ),
        Scenario(
            "Audit Multi Deteriorating Airline",
            "Airline (Jet Fuel)",
            "Brazil",
            "multi_annual",
            annual_history(2022, [2.9e9, 2.7e9, 2.45e9, 2.12e9, 1.88e9], [0.16, 0.135, 0.105, 0.078, 0.045], [0.055, 0.036, 0.012, -0.018, -0.048], [0.34, 0.42, 0.51, 0.65, 0.82], [0.10, 0.085, 0.065, 0.048, 0.031], [1.46, 1.28, 1.08, 0.91, 0.76]),
            {"requested_credit_limit": 18_000_000, "approved_credit_limit": 8_000_000, "invoice_amount": 2_250_000, "fuel_volume": 790_000, "fuel_price": 2.85, "outstanding_receivables": 6_800_000, "payment_tenor_days": 60, "utilization_rate": 0.78, "collateral_type": "guarantee", "guarantee_flag": True, "deposit_percentage": 0},
        ),
        Scenario(
            "Audit Quarterly Seasonal Recovery",
            "Airline (Jet Fuel)",
            "India",
            "multi_quarterly",
            quarterly_history(2025, [(2025, "Q1", 310e6, 0.07, -0.01, 0.58, 0.045, 0.92), (2025, "Q2", 340e6, 0.09, 0.006, 0.56, 0.052, 1.00), (2025, "Q3", 390e6, 0.12, 0.025, 0.52, 0.064, 1.12), (2025, "Q4", 420e6, 0.14, 0.038, 0.48, 0.075, 1.24), (2026, "Q1", 435e6, 0.145, 0.041, 0.45, 0.083, 1.30), (2026, "Q2", 470e6, 0.155, 0.048, 0.42, 0.091, 1.38)]),
            {"requested_credit_limit": 11_000_000, "approved_credit_limit": 8_800_000, "invoice_amount": 1_320_000, "fuel_volume": 470_000, "fuel_price": 2.81, "outstanding_receivables": 3_300_000, "payment_tenor_days": 30, "utilization_rate": 0.52, "collateral_type": "letter_of_credit", "letter_of_credit_flag": True, "deposit_percentage": 0},
        ),
        Scenario(
            "Audit Quarterly Volatile Low Cost",
            "Low Cost Airline",
            "Thailand",
            "multi_quarterly",
            quarterly_history(2025, [(2025, "Q1", 260e6, 0.09, 0.008, 0.50, 0.055, 1.03), (2025, "Q2", 230e6, 0.05, -0.025, 0.58, 0.041, 0.88), (2025, "Q3", 285e6, 0.11, 0.019, 0.54, 0.050, 1.02), (2025, "Q4", 245e6, 0.045, -0.032, 0.64, 0.035, 0.80), (2026, "Q1", 270e6, 0.065, -0.008, 0.67, 0.034, 0.83), (2026, "Q2", 255e6, 0.055, -0.017, 0.70, 0.032, 0.79)]),
            {"requested_credit_limit": 7_000_000, "approved_credit_limit": 4_000_000, "invoice_amount": 990_000, "fuel_volume": 350_000, "fuel_price": 2.83, "outstanding_receivables": 2_800_000, "payment_tenor_days": 45, "utilization_rate": 0.70, "collateral_type": "cash_deposit", "deposit_percentage": 20},
        ),
        Scenario(
            "Audit Mixed Annual Quarterly Flag Carrier",
            "Airline (Jet Fuel)",
            "United Kingdom",
            "mixed_annual_quarterly",
            annual_history(2023, [3.0e9, 3.25e9, 3.45e9], [0.12, 0.135, 0.15], [0.03, 0.043, 0.052], [0.46, 0.42, 0.38], [0.075, 0.085, 0.095], [1.18, 1.28, 1.36])
            + quarterly_history(2026, [(2026, "Q1", 910e6, 0.155, 0.055, 0.37, 0.10, 1.40), (2026, "Q2", 960e6, 0.162, 0.060, 0.35, 0.105, 1.46)]),
            {"requested_credit_limit": 20_000_000, "approved_credit_limit": 16_500_000, "invoice_amount": 2_050_000, "fuel_volume": 710_000, "fuel_price": 2.89, "outstanding_receivables": 4_600_000, "payment_tenor_days": 30, "utilization_rate": 0.47, "collateral_type": "letter_of_credit", "letter_of_credit_flag": True, "deposit_percentage": 0},
        ),
    ]


def backup_existing(run_dir: Path) -> list[dict[str, Any]]:
    rows = get("/api/v1/documents/counterparties?limit=100")
    backup: list[dict[str, Any]] = []
    for row in rows:
        item = {"counterparty": row}
        cid = row["id"]
        for key, path in {
            "documents": f"/api/v1/documents/counterparty/{cid}",
            "metrics_history": f"/api/v1/financial-analysis/counterparty/{cid}/metrics-history",
            "trend_features": f"/api/v1/financial-analysis/counterparty/{cid}/trend-features",
            "latest_ratios": f"/api/v1/financial-analysis/counterparty/{cid}/latest-ratios",
            "latest_pd": f"/api/v1/credit-risk/counterparty/{cid}/latest-pd",
            "latest_loss": f"/api/v1/credit-risk/counterparty/{cid}/latest-loss",
            "latest_recommendation": f"/api/v1/credit-decision/counterparty/{cid}/latest",
        }.items():
            try:
                item[key] = get(path, timeout=20)
            except Exception as exc:
                item[key] = {"backup_warning": str(exc)}
        backup.append(item)
    (run_dir / "counterparty_backup.json").write_text(json.dumps(backup, indent=2, default=_json_default), encoding="utf-8")
    return rows


def delete_all_counterparties() -> list[dict[str, Any]]:
    deleted: list[dict[str, Any]] = []
    while True:
        rows = get("/api/v1/documents/counterparties?limit=100")
        if not rows:
            return deleted
        for row in rows:
            deleted.append(delete(f"/api/v1/documents/counterparties/{row['id']}"))


def run_one(scenario: Scenario, index: int) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    cp = post(
        "/api/v1/documents/counterparties",
        {
            "counterparty_name": scenario.name,
            "counterparty_type": scenario.counterparty_type,
            "country": scenario.country,
        },
    )
    cid = int(cp["id"])
    periods = []
    for period in scenario.periods:
        item = dict(period)
        item["counterparty_id"] = cid
        periods.append(item)
    batch = post("/api/v1/financial-analysis/metrics/manual/batch", {"counterparty_id": cid, "periods": periods})
    latest_metrics = batch["latest_metrics"]
    metrics_id = latest_metrics["id"]

    ratios = post(f"/api/v1/financial-analysis/ratios/calculate/{metrics_id}")["ratios"]
    pd = post(f"/api/v1/credit-risk/pd/calculate/{metrics_id}", {"time_horizon_years": 1.0})["prediction"]
    exposure = dict(scenario.exposure)
    exposure.update(
        {
            "counterparty_id": cid,
            "pd_prediction_id": pd["id"],
            "counterparty_type": scenario.counterparty_type,
            "country_risk_score": 2.0,
            "seniority_score": 2.0,
        }
    )
    loss = post("/api/v1/credit-risk/loss/calculate", exposure)["loss_estimate"]
    monte_carlo = post(
        "/api/v1/scenario-analysis/monte-carlo/run",
        {
            "scenario_type": "adverse",
            "counterparty_ids": [cid],
            "n_simulations": 1200,
            "random_seed": 7000 + index,
            "persist": True,
        },
        timeout=90,
    )
    recommendation = post(f"/api/v1/credit-decision/counterparty/{cid}/recommend")["recommendation"]
    history = get(f"/api/v1/financial-analysis/counterparty/{cid}/metrics-history")
    trends = get(f"/api/v1/financial-analysis/counterparty/{cid}/trend-features")
    latest_ratios = get(f"/api/v1/financial-analysis/counterparty/{cid}/latest-ratios")
    latest_pd = get(f"/api/v1/credit-risk/counterparty/{cid}/latest-pd")
    latest_loss = get(f"/api/v1/credit-risk/counterparty/{cid}/latest-loss")
    latest_recommendation = get(f"/api/v1/credit-decision/counterparty/{cid}/latest")

    latest_input = periods[-1]
    check("history period count", len(history["periods"]) == len(periods), f"{len(history['periods'])} vs {len(periods)}")
    check("latest snapshot selected", latest_metrics["fiscal_year"] == latest_input["fiscal_year"] and latest_metrics["fiscal_period"] == latest_input["fiscal_period"], f"{latest_metrics.get('fiscal_year')} {latest_metrics.get('fiscal_period')}")
    check("history frequency populated", bool(trends.get("history_frequency")), str(trends.get("history_frequency")))
    check("trend period count", int(trends.get("period_count") or 0) == len(periods), str(trends.get("period_count")))
    if len(periods) == 1:
        check("single-year trend overlay neutral/limited", trends.get("history_status") in {"single_period", "limited_history", "insufficient_history"} or trends.get("period_count") == 1, str(trends.get("history_status")))
    else:
        check("multi-period trend features active", trends.get("period_count", 0) > 1 and trends.get("latest_period"), str(trends.get("latest_period")))

    expected_current_ratio = ratio_or_none(latest_input["current_assets"], latest_input["current_liabilities"])
    expected_debt_to_ebitda = ratio_or_none(latest_input["total_debt"], latest_input["ebitda"])
    expected_interest_coverage = ratio_or_none(latest_input["ebit"], latest_input["interest_expense"])
    check("current ratio formula", nearly_equal(ratios.get("current_ratio"), expected_current_ratio, 0.02), f"got {ratios.get('current_ratio')} expected {expected_current_ratio}")
    check("debt/EBITDA formula", nearly_equal(ratios.get("debt_to_ebitda"), expected_debt_to_ebitda, 0.05), f"got {ratios.get('debt_to_ebitda')} expected {expected_debt_to_ebitda}")
    check("interest coverage formula", nearly_equal(ratios.get("interest_coverage"), expected_interest_coverage, 0.05), f"got {ratios.get('interest_coverage')} expected {expected_interest_coverage}")
    check("latest ratios endpoint matches", latest_ratios["financial_metrics_id"] == metrics_id, str(latest_ratios["financial_metrics_id"]))

    check("PD range", 0 < float(pd["final_pd"]) < 1, str(pd["final_pd"]))
    check("structural PD range", 0 <= float(pd["structural_pd"]) <= 1, str(pd["structural_pd"]))
    check("ML PD range", 0 <= float(pd["ml_pd"]) <= 1, str(pd["ml_pd"]))
    check("latest PD endpoint matches", latest_pd["id"] == pd["id"], str(latest_pd["id"]))
    check("PD has market sensitivities", all(pd.get(key) is not None for key in ["commodity_sensitivity_score", "fx_sensitivity_score", "macro_sensitivity_score"]), "")

    expected_loss = float(loss["probability_of_default"]) * float(loss["predicted_lgd"]) * float(loss["exposure_at_default"])
    check("expected loss formula", nearly_equal(loss["expected_loss"], expected_loss, max(1.0, expected_loss * 0.002)), f"got {loss['expected_loss']} expected {expected_loss}")
    exposure_cap = max(float(exposure["requested_credit_limit"]), float(exposure["approved_credit_limit"]), float(exposure["outstanding_receivables"]) + float(exposure["invoice_amount"]))
    check("EAD within exposure cap", 0 <= float(loss["exposure_at_default"]) <= exposure_cap * 1.01, f"EAD {loss['exposure_at_default']} cap {exposure_cap}")
    check("LGD range", 0 <= float(loss["predicted_lgd"]) <= 1, str(loss["predicted_lgd"]))
    check("latest loss endpoint matches", latest_loss["id"] == loss["id"], str(latest_loss["id"]))

    mc_max_reference = max(
        float(loss["exposure_at_default"]),
        float(exposure.get("requested_credit_limit") or 0),
        float(exposure.get("approved_credit_limit") or 0),
        1.0,
    )
    check("Monte Carlo run generated", bool(monte_carlo.get("run_id")), str(monte_carlo.get("run_id")))
    check("Monte Carlo EL non-negative", float(monte_carlo["expected_loss"]) >= 0, str(monte_carlo["expected_loss"]))
    check("Monte Carlo VaR capped to exposure", float(monte_carlo["credit_var_95"]) <= mc_max_reference * 1.05, f"VaR {monte_carlo['credit_var_95']} reference {mc_max_reference}")
    check("Monte Carlo ES capped to exposure", float(monte_carlo["expected_shortfall_95"]) <= mc_max_reference * 1.05, f"ES {monte_carlo['expected_shortfall_95']} reference {mc_max_reference}")
    check("Monte Carlo tail order", float(monte_carlo["expected_shortfall_95"]) + 1e-6 >= float(monte_carlo["credit_var_95"]), f"VaR {monte_carlo['credit_var_95']} ES {monte_carlo['expected_shortfall_95']}")

    check("recommendation generated", bool(recommendation.get("approval_status") and recommendation.get("recommended_security")), "")
    check("recommended limit bounded", 0 <= float(recommendation["recommended_credit_limit"]) <= float(exposure["requested_credit_limit"]) * 1.01, f"{recommendation['recommended_credit_limit']} vs {exposure['requested_credit_limit']}")
    check("recommendation latest endpoint matches", latest_recommendation["id"] == recommendation["id"], str(latest_recommendation["id"]))
    check("recommendation PD/EL coherence", nearly_equal(recommendation["probability_of_default"], pd["final_pd"], 0.0005) and float(recommendation["expected_loss"]) >= 0, "")
    if recommendation.get("credit_var_95") is not None:
        check("recommendation VaR bounded", float(recommendation["credit_var_95"]) <= mc_max_reference * 1.05, f"{recommendation['credit_var_95']} <= {mc_max_reference}")
    if recommendation.get("expected_shortfall_95") is not None:
        check("recommendation ES bounded", float(recommendation["expected_shortfall_95"]) <= mc_max_reference * 1.05, f"{recommendation['expected_shortfall_95']} <= {mc_max_reference}")

    graph_checks = {
        "financial_trend_points": len(history["periods"]),
        "pd_forecast_inputs": {
            "base_pd": pd["final_pd"],
            "scenario_pd_proxy": recommendation["probability_of_default"],
        },
        "monte_carlo_histogram": monte_carlo.get("loss_distribution_summary"),
        "market_watch_inputs_loaded": len(get("/api/v1/market-intelligence/prices/recent?assets=brent_oil,jet_fuel_proxy,usd_inr,dxy,vix,sp500,us_10y_yield,freight_proxy,global_pmi,iata_passenger_traffic&limit_per_asset=20").get("market_prices", [])),
    }
    check("chart data available", graph_checks["financial_trend_points"] >= 1 and graph_checks["market_watch_inputs_loaded"] > 0, str(graph_checks))

    failures = [item for item in checks if item["status"] != "PASS"]
    return {
        "scenario": scenario.name,
        "mode": scenario.mode,
        "counterparty_id": cid,
        "period_count": len(periods),
        "checks": checks,
        "failures": failures,
        "outputs": {
            "latest_metrics": latest_metrics,
            "ratios": ratios,
            "trend_features": trends,
            "pd": pd,
            "loss": loss,
            "monte_carlo": monte_carlo,
            "recommendation": recommendation,
            "graph_checks": graph_checks,
        },
    }


def write_report(run_dir: Path, backup_count: int, deleted_count: int, results: list[dict[str, Any]]) -> None:
    total_checks = sum(len(item["checks"]) for item in results)
    failures = [(item["scenario"], check) for item in results for check in item["failures"]]
    lines = [
        "# Full Model Audit Report",
        "",
        f"Run timestamp: `{datetime.utcnow().isoformat()}Z`",
        f"Backend: `{BASE_URL}`",
        f"Backed up counterparties: `{backup_count}`",
        f"Deleted counterparties before audit: `{deleted_count}`",
        f"Synthetic scenarios run: `{len(results)}`",
        f"Total checks: `{total_checks}`",
        f"Failures: `{len(failures)}`",
        "",
        "## Summary",
        "",
    ]
    lines.append("PASS: no failing checks." if not failures else "FAIL: one or more checks failed. See details below.")
    lines.extend(["", "## Scenario Results", ""])
    for item in results:
        fail_count = len(item["failures"])
        outputs = item["outputs"]
        rec = outputs.get("recommendation")
        pd = outputs.get("pd")
        loss = outputs.get("loss")
        trends = outputs.get("trend_features")
        if not all([rec, pd, loss, trends]):
            lines.extend(
                [
                    f"### {item['scenario']}",
                    "",
                    f"- Mode: `{item['mode']}`",
                    f"- Counterparty ID: `{item.get('counterparty_id')}`",
                    f"- Periods intended: `{item['period_count']}`",
                    f"- Check result: `FAIL ({len(item['checks']) - fail_count}/{len(item['checks'])} passed)`",
                    "",
                    "| Check | Status | Detail |",
                    "|---|---:|---|",
                ]
            )
            for check in item["checks"]:
                detail = str(check.get("detail") or "").replace("\n", " ")
                lines.append(f"| {check['name']} | {check['status']} | {detail} |")
            lines.append("")
            continue
        lines.extend(
            [
                f"### {item['scenario']}",
                "",
                f"- Mode: `{item['mode']}`",
                f"- Counterparty ID: `{item['counterparty_id']}`",
                f"- Periods loaded: `{item['period_count']}`",
                f"- Final PD: `{float(pd['final_pd']):.4%}`",
                f"- Structural PD / ML PD: `{float(pd['structural_pd']):.4%}` / `{float(pd['ml_pd']):.4%}`",
                f"- LGD / EAD / EL: `{float(loss['predicted_lgd']):.2%}` / `${float(loss['exposure_at_default']):,.0f}` / `${float(loss['expected_loss']):,.0f}`",
                f"- Recommended limit/security/status: `${float(rec['recommended_credit_limit']):,.0f}` / `{rec['recommended_security']}` / `{rec['approval_status']}`",
                f"- Trend status/frequency: `{trends.get('history_status')}` / `{trends.get('history_frequency')}`",
                f"- Check result: `{'PASS' if fail_count == 0 else 'FAIL'} ({len(item['checks']) - fail_count}/{len(item['checks'])} passed)`",
                "",
                "| Check | Status | Detail |",
                "|---|---:|---|",
            ]
        )
        for check in item["checks"]:
            detail = str(check.get("detail") or "").replace("\n", " ")
            lines.append(f"| {check['name']} | {check['status']} | {detail} |")
        lines.append("")
    if failures:
        lines.extend(["## Failures", ""])
        for scenario, check in failures:
            lines.append(f"- **{scenario}**: {check['name']} -> {check.get('detail') or 'no detail'}")
    report = "\n".join(lines)
    (run_dir / "FULL_MODEL_AUDIT_REPORT.md").write_text(report, encoding="utf-8")
    (run_dir / "full_model_audit_results.json").write_text(json.dumps(results, indent=2, default=_json_default), encoding="utf-8")


def main() -> int:
    global BASE_URL
    parser = argparse.ArgumentParser(description="Run destructive 10-scenario full model audit.")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--skip-delete", action="store_true", help="Do not delete existing counterparties before seeding.")
    args = parser.parse_args()
    BASE_URL = args.base_url.rstrip("/")

    run_dir = OUT_DIR / datetime.utcnow().strftime("full_model_audit_%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Audit output: {run_dir}")
    print("Checking backend health...")
    print(get("/health"))

    print("Backing up existing counterparties...")
    existing = backup_existing(run_dir)
    deleted_rows: list[dict[str, Any]] = []
    if not args.skip_delete:
        print("Deleting existing counterparties through API...")
        deleted_rows = delete_all_counterparties()
        (run_dir / "deleted_counterparties.json").write_text(json.dumps(deleted_rows, indent=2, default=_json_default), encoding="utf-8")

    results: list[dict[str, Any]] = []
    for index, scenario in enumerate(scenarios(), start=1):
        print(f"[{index}/10] Running {scenario.name} ({scenario.mode})")
        try:
            results.append(run_one(scenario, index))
        except Exception as exc:
            results.append(
                {
                    "scenario": scenario.name,
                    "mode": scenario.mode,
                    "counterparty_id": None,
                    "period_count": len(scenario.periods),
                    "checks": [{"name": "scenario execution", "status": "FAIL", "detail": str(exc)}],
                    "failures": [{"name": "scenario execution", "status": "FAIL", "detail": str(exc)}],
                    "outputs": {},
                }
            )
            print(f"  FAILED: {exc}")
        time.sleep(0.2)

    write_report(run_dir, backup_count=len(existing), deleted_count=len(deleted_rows), results=results)
    failure_count = sum(len(item["failures"]) for item in results)
    print(f"Report: {run_dir / 'FULL_MODEL_AUDIT_REPORT.md'}")
    print(f"Failures: {failure_count}")
    return 1 if failure_count else 0


if __name__ == "__main__":
    sys.exit(main())
