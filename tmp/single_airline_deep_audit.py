"""Deep audit for one fully populated synthetic airline through the V2 pipeline.

The goal is not to make the model fit this airline. The goal is to verify that
each stored data point follows the general formula or invariant it claims to
follow, so wiring bugs like portfolio VaR being shown as single-name VaR are
caught automatically.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api.market_data.external_providers import add_calculated_market_series
from api.market_data.service import rebuild_market_intelligence, store_market_provider_rows


RUN_TAG = "single_airline_deep_audit_20260624"
OUT = Path("tmp/single_airline_deep_audit_report.json")


@dataclass(frozen=True)
class AuditCase:
    name: str
    ctype: str
    country: str
    financials: dict[str, Any]
    terms: dict[str, Any]


def _market_rows() -> pd.DataFrame:
    rng = np.random.default_rng(424242)
    dates = pd.date_range("2025-01-01", periods=260, freq="D")
    assets = {
        "brent_oil": ("Brent Crude Audit", "usd_per_barrel", 82.0, 0.00015, 0.006),
        "crude_oil": ("WTI Crude Audit", "usd_per_barrel", 78.0, 0.00012, 0.006),
        "jet_fuel_proxy": ("Jet Fuel Spot Audit", "usd_per_gallon", 2.55, 0.00018, 0.005),
        "heating_oil_proxy": ("Heating Oil Audit", "usd_per_gallon", 2.40, 0.00012, 0.005),
        "vix": ("VIX Audit", "index", 17.0, 0.00005, 0.012),
        "sp500": ("S&P 500 Audit", "index", 5400.0, 0.00022, 0.005),
        "dxy": ("DXY Audit", "index", 102.0, 0.00002, 0.0025),
        "gold": ("Gold Audit", "usd_per_ounce", 2350.0, 0.00008, 0.0035),
        "us_10y_yield": ("US 10Y Audit", "percent", 4.25, 0.00001, 0.002),
        "us_2y_yield": ("US 2Y Audit", "percent", 4.40, -0.00001, 0.002),
        "yield_curve_spread": ("Yield Curve Audit", "percent", -0.15, 0.00001, 0.0015),
        "cpi_index": ("CPI Audit", "index", 318.0, 0.00004, 0.0004),
        "freight_proxy": ("Freight Audit", "index", 120.0, -0.00002, 0.004),
        "eia_crude_inventories": ("EIA Inventories Audit", "thousand_barrels", 425000.0, 0.00003, 0.001),
        "opec_production": ("OPEC Production Audit", "thousand_barrels_per_day", 27200.0, 0.00002, 0.001),
        "global_pmi": ("Global PMI Audit", "index", 52.0, -0.00001, 0.0008),
        "pmi": ("PMI Audit", "index", 51.8, -0.00001, 0.0008),
        "iata_passenger_traffic": ("IATA Traffic Audit", "index", 108.0, 0.00002, 0.0015),
    }
    rows: list[dict[str, Any]] = []
    for asset, (asset_name, units, start, drift, sigma) in assets.items():
        value = start
        for i, dt in enumerate(dates):
            shock = rng.normal(drift, sigma)
            if i > 200 and asset in {"brent_oil", "crude_oil", "jet_fuel_proxy", "heating_oil_proxy", "vix"}:
                shock += 0.0012
            if i > 200 and asset in {"sp500", "global_pmi", "iata_passenger_traffic"}:
                shock -= 0.0010
            value = max(0.01, value * (1.0 + shock))
            rows.append(
                {
                    "date": dt,
                    "asset": asset,
                    "asset_name": asset_name,
                    "source_id": f"{RUN_TAG}_{asset}",
                    "price": value,
                    "data_source": RUN_TAG,
                    "frequency": "daily",
                    "units": units,
                }
            )
    frame = pd.DataFrame(rows)
    frame["return"] = frame.groupby("asset")["price"].transform(lambda s: np.log(s / s.shift(1)))
    frame["rolling_volatility"] = frame.groupby("asset")["return"].transform(
        lambda s: s.rolling(30, min_periods=5).std()
    )
    return add_calculated_market_series(frame)


def _case() -> AuditCase:
    return AuditCase(
        name="Deep Audit Meridian Airways",
        ctype="Airline",
        country="United States",
        financials={
            "revenue": 1_250_000_000,
            "ebitda": 185_000_000,
            "ebit": 140_000_000,
            "interest_expense": 22_000_000,
            "net_income": 82_000_000,
            "cash_and_equivalents": 210_000_000,
            "accounts_receivable": 145_000_000,
            "inventory": 32_000_000,
            "current_assets": 430_000_000,
            "total_assets": 1_950_000_000,
            "current_liabilities": 255_000_000,
            "total_debt": 520_000_000,
            "total_liabilities": 960_000_000,
            "shareholders_equity": 990_000_000,
        },
        terms={
            "requested_credit_limit": 14_000_000,
            "approved_credit_limit": 14_000_000,
            "outstanding_receivables": 4_200_000,
            "payment_tenor_days": 45,
            "utilization_rate": 0.52,
            "collateral_type": "guarantee",
            "guarantee_flag": True,
            "deposit_percentage": 5,
            "fuel_volume": 3_200_000,
            "fuel_price": 2.72,
        },
    )


def _post(client: TestClient, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.post(path, json=payload or {})
    if response.status_code >= 400:
        raise RuntimeError(f"POST {path} failed {response.status_code}: {response.text}")
    return response.json()


def _get(client: TestClient, path: str) -> dict[str, Any]:
    response = client.get(path)
    if response.status_code >= 400:
        raise RuntimeError(f"GET {path} failed {response.status_code}: {response.text}")
    return response.json()


def _close(actual: Any, expected: float, tolerance: float, label: str, errors: list[str], checks: list[str]) -> None:
    actual_float = float(actual)
    if abs(actual_float - expected) > tolerance:
        errors.append(f"{label}: expected {expected:.8f}, got {actual_float:.8f}")
    else:
        checks.append(f"{label}: ok ({actual_float:.8f})")


def _risk_grade(pd_value: float) -> str:
    if pd_value < 0.01:
        return "A"
    if pd_value < 0.03:
        return "BBB"
    if pd_value < 0.07:
        return "BB"
    if pd_value < 0.15:
        return "B"
    return "CCC"


def main() -> None:
    errors: list[str] = []
    checks: list[str] = []
    market = _market_rows()
    store_counts = store_market_provider_rows(market)
    rebuild = rebuild_market_intelligence()
    client = TestClient(app)
    company = _case()

    cp = _post(
        client,
        "/api/v1/documents/counterparties",
        {
            "counterparty_name": company.name,
            "counterparty_type": company.ctype,
            "country": company.country,
        },
    )
    metrics_payload = {
        "counterparty_id": cp["id"],
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "currency": "USD",
        **company.financials,
        "created_by": RUN_TAG,
    }
    metrics = _post(client, "/api/v1/financial-analysis/metrics/manual", metrics_payload)["metrics"]
    ratios = _post(client, f"/api/v1/financial-analysis/ratios/calculate/{metrics['id']}")["ratios"]
    pd_result = _post(
        client,
        f"/api/v1/credit-risk/pd/calculate/{metrics['id']}",
        {"time_horizon_years": 1.0},
    )["prediction"]
    exposure_payload = {
        "counterparty_id": cp["id"],
        "pd_prediction_id": pd_result["id"],
        "country_risk_score": 2.0,
        "seniority_score": 2.0,
        "counterparty_type": company.ctype,
        "notes": RUN_TAG,
        **company.terms,
    }
    loss = _post(client, "/api/v1/credit-risk/loss/calculate", exposure_payload)["loss_estimate"]
    mc = _post(
        client,
        "/api/v1/scenario-analysis/monte-carlo/run",
        {
            "scenario_type": "adverse",
            "counterparty_ids": [cp["id"]],
            "n_simulations": 2500,
            "random_seed": 20260624,
            "persist": True,
            "copula_type": "t_copula",
        },
    )
    rec = _post(client, f"/api/v1/credit-decision/counterparty/{cp['id']}/recommend")["recommendation"]
    latest_rec = _get(client, f"/api/v1/credit-decision/counterparty/{cp['id']}/latest")
    latest_pd = _get(client, f"/api/v1/credit-risk/counterparty/{cp['id']}/latest-pd")
    latest_loss = _get(client, f"/api/v1/credit-risk/counterparty/{cp['id']}/latest-loss")
    latest_ratios = _get(client, f"/api/v1/financial-analysis/counterparty/{cp['id']}/latest-ratios")

    f = company.financials
    t = company.terms
    ratio_tolerance = 1e-6
    _close(ratios["current_ratio"], f["current_assets"] / f["current_liabilities"], ratio_tolerance, "current_ratio", errors, checks)
    _close(
        ratios["quick_ratio"],
        (f["cash_and_equivalents"] + f["accounts_receivable"]) / f["current_liabilities"],
        ratio_tolerance,
        "quick_ratio",
        errors,
        checks,
    )
    _close(ratios["cash_ratio"], f["cash_and_equivalents"] / f["current_liabilities"], ratio_tolerance, "cash_ratio", errors, checks)
    _close(ratios["working_capital"], f["current_assets"] - f["current_liabilities"], 0.01, "working_capital", errors, checks)
    _close(ratios["debt_to_equity"], f["total_debt"] / f["shareholders_equity"], ratio_tolerance, "debt_to_equity", errors, checks)
    _close(ratios["debt_to_ebitda"], f["total_debt"] / f["ebitda"], ratio_tolerance, "debt_to_ebitda", errors, checks)
    _close(ratios["liabilities_to_assets"], f["total_liabilities"] / f["total_assets"], ratio_tolerance, "liabilities_to_assets", errors, checks)
    _close(ratios["interest_coverage"], f["ebit"] / f["interest_expense"], ratio_tolerance, "interest_coverage", errors, checks)
    _close(ratios["operating_margin"], f["ebit"] / f["revenue"], ratio_tolerance, "operating_margin", errors, checks)
    _close(ratios["net_margin"], f["net_income"] / f["revenue"], ratio_tolerance, "net_margin", errors, checks)

    for label in ("structural_pd", "ml_pd", "final_pd", "model_confidence"):
        value = float(pd_result[label])
        if not (0.0 < value < 1.0):
            errors.append(f"{label}: expected probability/confidence in (0, 1), got {value}")
        else:
            checks.append(f"{label}: bounded ({value:.6f})")
    if float(pd_result["distance_to_default"]) <= 0:
        errors.append(f"distance_to_default: expected positive value, got {pd_result['distance_to_default']}")
    else:
        checks.append(f"distance_to_default: positive ({float(pd_result['distance_to_default']):.6f})")
    pd_assumptions = pd_result.get("model_assumptions") or {}
    pd_contrib = pd_result.get("feature_contributions") or {}
    structural_weight = float(pd_assumptions["structural_anchor_weight"])
    ml_weight = float(pd_assumptions["ml_proxy_weight"])
    blended_pd = structural_weight * float(pd_result["structural_pd"]) + ml_weight * float(pd_result["ml_pd"])
    distress_floor = float(pd_contrib.get("balance_sheet_distress_floor") or 0.0)
    expected_final_pd = max(blended_pd, distress_floor)
    _close(pd_result["final_pd"], expected_final_pd, 1e-8, "final_pd_blend_or_floor", errors, checks)
    expected_grade = _risk_grade(float(pd_result["final_pd"]))
    if pd_result["classification_label"] != expected_grade:
        errors.append(f"classification_label: expected {expected_grade}, got {pd_result['classification_label']}")
    else:
        checks.append(f"classification_label: ok ({expected_grade})")

    invoice_exposure = t["fuel_volume"] * t["fuel_price"]
    expected_drawdown = invoice_exposure * t["utilization_rate"] * max(1.0, t["payment_tenor_days"] / 30)
    business_ead = min(t["approved_credit_limit"], t["outstanding_receivables"] + expected_drawdown)
    _close(loss["invoice_exposure"], invoice_exposure, 0.01, "invoice_exposure", errors, checks)
    _close(loss["expected_drawdown"], expected_drawdown, 0.01, "expected_drawdown", errors, checks)
    if "Calibrated EAD model artifact used as exposure cross-check." not in (loss.get("warnings") or []):
        _close(loss["exposure_at_default"], business_ead, 0.01, "business_ead", errors, checks)
    elif float(loss["exposure_at_default"]) > t["approved_credit_limit"] + 0.01:
        errors.append("exposure_at_default: calibrated blend exceeded approved limit")
    else:
        checks.append("exposure_at_default: calibrated artifact used and approved-limit cap respected")
    if not (0.0 <= float(loss["predicted_lgd"]) <= 1.0):
        errors.append(f"predicted_lgd: expected [0, 1], got {loss['predicted_lgd']}")
    else:
        checks.append(f"predicted_lgd: bounded ({float(loss['predicted_lgd']):.6f})")
    expected_el = float(pd_result["final_pd"]) * float(loss["predicted_lgd"]) * float(loss["exposure_at_default"])
    _close(loss["expected_loss"], expected_el, max(0.05, expected_el * 0.000001), "loss_expected_loss", errors, checks)

    for label, payload in {
        "latest_ratios": latest_ratios,
        "latest_pd": latest_pd,
        "latest_loss": latest_loss,
    }.items():
        if int(payload["counterparty_id"]) != int(cp["id"]):
            errors.append(f"{label}: latest endpoint returned wrong counterparty_id")
        else:
            checks.append(f"{label}: counterparty lineage ok")

    if mc["expected_shortfall_95"] < mc["credit_var_95"]:
        errors.append("portfolio Monte Carlo: ES95 below VaR95")
    else:
        checks.append("portfolio Monte Carlo: ES95 >= VaR95")
    if mc["expected_shortfall_99"] < mc["credit_var_99"]:
        errors.append("portfolio Monte Carlo: ES99 below VaR99")
    else:
        checks.append("portfolio Monte Carlo: ES99 >= VaR99")
    if mc["credit_var_99"] < mc["credit_var_95"]:
        errors.append("portfolio Monte Carlo: VaR99 below VaR95")
    else:
        checks.append("portfolio Monte Carlo: VaR99 >= VaR95")
    marginal = (mc.get("marginal_risk_contribution") or {}).get(str(cp["id"]))
    if marginal is None:
        errors.append("marginal_risk_contribution: missing single airline entry")
        marginal = 0.0
    _close(marginal, 1.0, 1e-8, "single_name_marginal_contribution", errors, checks)

    exposure_cap = min(float(loss["exposure_at_default"]), float(t["requested_credit_limit"]))
    expected_var = min(float(mc["credit_var_95"]) * float(marginal or 0.0), exposure_cap)
    expected_es = min(float(mc["expected_shortfall_95"]) * float(marginal or 0.0), exposure_cap)
    _close(rec["credit_var_95"], expected_var, 0.05, "recommendation_single_name_var95", errors, checks)
    _close(rec["expected_shortfall_95"], expected_es, 0.05, "recommendation_single_name_es95", errors, checks)
    if float(rec["expected_shortfall_95"] or 0) < float(rec["credit_var_95"] or 0):
        errors.append("recommendation: single-name ES95 below VaR95")
    else:
        checks.append("recommendation: single-name ES95 >= VaR95")

    rec_expected_el = float(rec["probability_of_default"]) * float(rec["loss_given_default"]) * float(rec["exposure_at_default"])
    _close(rec["expected_loss"], rec_expected_el, max(0.05, rec_expected_el * 0.000001), "recommendation_expected_loss", errors, checks)
    base_limit = float(t["requested_credit_limit"])
    expected_limit = round(max(0.0, base_limit * (1.0 - float(rec["limit_haircut"]))), 2)
    _close(rec["recommended_credit_limit"], expected_limit, 0.01, "recommended_limit_formula", errors, checks)
    if float(rec["recommended_credit_limit"]) > base_limit + 0.01:
        errors.append("recommended_credit_limit: exceeds requested limit")
    else:
        checks.append("recommended_credit_limit: not above requested")
    rec_grade = _risk_grade(float(rec["probability_of_default"]))
    if rec["risk_grade"] != rec_grade:
        errors.append(f"recommendation risk_grade: expected {rec_grade}, got {rec['risk_grade']}")
    else:
        checks.append(f"recommendation risk_grade: ok ({rec_grade})")
    if latest_rec["run_id"] != rec["run_id"]:
        errors.append("latest recommendation endpoint did not return the just-created recommendation")
    else:
        checks.append("latest recommendation endpoint: run_id matches")

    report = {
        "run_tag": RUN_TAG,
        "counterparty": cp,
        "market_store_counts": store_counts,
        "market_rebuild": rebuild,
        "inputs": {"financials": company.financials, "terms": company.terms},
        "outputs": {
            "ratios": ratios,
            "pd": pd_result,
            "loss": loss,
            "monte_carlo": mc,
            "recommendation": rec,
        },
        "checks": checks,
        "errors": errors,
    }
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"report": str(OUT), "errors": errors, "checks": checks}, indent=2, default=str))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
