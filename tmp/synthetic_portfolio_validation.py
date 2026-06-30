"""Seed and validate a diverse synthetic portfolio through the live V2 pipeline."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api.main import app
from api.market_data.external_providers import add_calculated_market_series
from api.market_data.service import rebuild_market_intelligence, store_market_provider_rows


RUN_TAG = "synthetic_validation_20260624"
OUT = Path("tmp/synthetic_validation_report.json")


@dataclass(frozen=True)
class SyntheticCompany:
    name: str
    ctype: str
    country: str
    financials: dict[str, Any]
    terms: dict[str, Any]


def _market_rows() -> pd.DataFrame:
    rng = np.random.default_rng(20260624)
    dates = pd.date_range("2025-01-01", periods=220, freq="D")
    assets = {
        "brent_oil": ("Brent Crude Synthetic", "usd_per_barrel", 78.0, 0.0008, 0.006),
        "crude_oil": ("WTI Crude Synthetic", "usd_per_barrel", 73.0, 0.0007, 0.006),
        "jet_fuel_proxy": ("Jet Fuel Spot Synthetic", "usd_per_gallon", 2.42, 0.0009, 0.005),
        "heating_oil_proxy": ("Heating Oil Synthetic", "usd_per_gallon", 2.32, 0.0007, 0.005),
        "vix": ("VIX Synthetic", "index", 15.0, 0.0009, 0.018),
        "sp500": ("S&P 500 Synthetic", "index", 5200.0, 0.0004, 0.006),
        "dxy": ("DXY Synthetic", "index", 103.0, 0.0002, 0.003),
        "gold": ("Gold Synthetic", "usd_per_ounce", 2300.0, 0.0003, 0.004),
        "us_10y_yield": ("US 10Y Synthetic", "percent", 4.10, 0.0002, 0.003),
        "us_2y_yield": ("US 2Y Synthetic", "percent", 4.30, -0.0001, 0.003),
        "yield_curve_spread": ("Yield Curve Synthetic", "percent", -0.20, 0.0001, 0.002),
        "cpi_index": ("CPI Synthetic", "index", 315.0, 0.00005, 0.0005),
        "freight_proxy": ("Freight Proxy Synthetic", "index", 125.0, -0.0002, 0.006),
        "eia_crude_inventories": ("EIA Crude Inventories Synthetic", "thousand_barrels", 430000.0, 0.00015, 0.0015),
        "opec_production": ("OPEC Production Synthetic", "thousand_barrels_per_day", 27000.0, -0.0001, 0.001),
        "global_pmi": ("Global PMI Synthetic", "index", 51.5, -0.00005, 0.001),
        "pmi": ("PMI Proxy Synthetic", "index", 51.0, -0.00004, 0.001),
        "iata_passenger_traffic": ("IATA Passenger Traffic Synthetic", "index", 105.0, -0.0001, 0.002),
    }
    rows: list[dict[str, Any]] = []
    for asset, (asset_name, units, start, drift, sigma) in assets.items():
        value = start
        for i, dt in enumerate(dates):
            stress = i > 150
            shock = rng.normal(drift, sigma)
            if stress and asset in {"brent_oil", "crude_oil", "jet_fuel_proxy", "heating_oil_proxy", "vix", "dxy", "gold", "eia_crude_inventories"}:
                shock += 0.0025
            if stress and asset in {"sp500", "freight_proxy", "opec_production", "global_pmi", "pmi", "iata_passenger_traffic"}:
                shock -= 0.0025
            value = max(0.01, value * (1 + shock))
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
    frame["rolling_volatility"] = frame.groupby("asset")["return"].transform(lambda s: s.rolling(30, min_periods=5).std())
    return add_calculated_market_series(frame)


def _companies() -> list[SyntheticCompany]:
    return [
        SyntheticCompany("Validation Sky Prime", "Airline", "United States", dict(revenue=900_000_000, ebitda=130_000_000, ebit=95_000_000, interest_expense=14_000_000, net_income=60_000_000, cash_and_equivalents=120_000_000, accounts_receivable=95_000_000, inventory=25_000_000, current_assets=260_000_000, total_assets=1_200_000_000, current_liabilities=145_000_000, total_debt=330_000_000, total_liabilities=620_000_000, shareholders_equity=580_000_000), dict(requested_credit_limit=12_000_000, approved_credit_limit=12_000_000, outstanding_receivables=4_000_000, payment_tenor_days=45, utilization_rate=0.42, collateral_type="guarantee", guarantee_flag=True, deposit_percentage=5, fuel_volume=4_000_000, fuel_price=2.8)),
        SyntheticCompany("Validation Sky Distress", "Airline", "India", dict(revenue=520_000_000, ebitda=18_000_000, ebit=5_000_000, interest_expense=22_000_000, net_income=-45_000_000, cash_and_equivalents=12_000_000, accounts_receivable=130_000_000, inventory=15_000_000, current_assets=170_000_000, total_assets=600_000_000, current_liabilities=260_000_000, total_debt=520_000_000, total_liabilities=690_000_000, shareholders_equity=-90_000_000), dict(requested_credit_limit=18_000_000, approved_credit_limit=18_000_000, outstanding_receivables=11_000_000, payment_tenor_days=75, utilization_rate=0.88, collateral_type="unsecured", deposit_percentage=0, fuel_volume=5_500_000, fuel_price=3.0)),
        SyntheticCompany("Validation Ocean Carriers", "Shipping", "Singapore", dict(revenue=740_000_000, ebitda=105_000_000, ebit=76_000_000, interest_expense=20_000_000, net_income=40_000_000, cash_and_equivalents=72_000_000, accounts_receivable=88_000_000, inventory=34_000_000, current_assets=230_000_000, total_assets=980_000_000, current_liabilities=150_000_000, total_debt=420_000_000, total_liabilities=610_000_000, shareholders_equity=370_000_000), dict(requested_credit_limit=10_000_000, approved_credit_limit=10_000_000, outstanding_receivables=5_000_000, payment_tenor_days=60, utilization_rate=0.60, collateral_type="letter_of_credit", letter_of_credit_flag=True, deposit_percentage=0, fuel_volume=3_000_000, fuel_price=2.6)),
        SyntheticCompany("Validation Fuel Distributor", "Fuel Distributor", "United Arab Emirates", dict(revenue=420_000_000, ebitda=28_000_000, ebit=20_000_000, interest_expense=6_000_000, net_income=11_000_000, cash_and_equivalents=30_000_000, accounts_receivable=115_000_000, inventory=95_000_000, current_assets=255_000_000, total_assets=410_000_000, current_liabilities=190_000_000, total_debt=150_000_000, total_liabilities=285_000_000, shareholders_equity=125_000_000), dict(requested_credit_limit=8_000_000, approved_credit_limit=8_000_000, outstanding_receivables=6_200_000, payment_tenor_days=45, utilization_rate=0.78, collateral_type="cash_deposit", deposit_percentage=15, fuel_volume=2_200_000, fuel_price=2.7)),
        SyntheticCompany("Validation Commodity Trader", "Commodity Trader", "United Kingdom", dict(revenue=1_400_000_000, ebitda=42_000_000, ebit=32_000_000, interest_expense=17_000_000, net_income=12_000_000, cash_and_equivalents=85_000_000, accounts_receivable=280_000_000, inventory=360_000_000, current_assets=760_000_000, total_assets=1_050_000_000, current_liabilities=650_000_000, total_debt=500_000_000, total_liabilities=820_000_000, shareholders_equity=230_000_000), dict(requested_credit_limit=20_000_000, approved_credit_limit=20_000_000, outstanding_receivables=13_000_000, payment_tenor_days=30, utilization_rate=0.80, collateral_type="guarantee", guarantee_flag=True, deposit_percentage=8, fuel_volume=8_000_000, fuel_price=2.65)),
        SyntheticCompany("Validation Airport Services", "Airport Services", "France", dict(revenue=260_000_000, ebitda=55_000_000, ebit=44_000_000, interest_expense=5_000_000, net_income=24_000_000, cash_and_equivalents=65_000_000, accounts_receivable=35_000_000, inventory=6_000_000, current_assets=125_000_000, total_assets=360_000_000, current_liabilities=70_000_000, total_debt=90_000_000, total_liabilities=150_000_000, shareholders_equity=210_000_000), dict(requested_credit_limit=4_000_000, approved_credit_limit=4_000_000, outstanding_receivables=1_300_000, payment_tenor_days=30, utilization_rate=0.36, collateral_type="unsecured", deposit_percentage=0, fuel_volume=900_000, fuel_price=2.75)),
        SyntheticCompany("Validation Logistics Thin Margin", "Logistics", "Brazil", dict(revenue=310_000_000, ebitda=12_000_000, ebit=7_000_000, interest_expense=8_500_000, net_income=-4_000_000, cash_and_equivalents=8_000_000, accounts_receivable=70_000_000, inventory=20_000_000, current_assets=105_000_000, total_assets=280_000_000, current_liabilities=145_000_000, total_debt=190_000_000, total_liabilities=240_000_000, shareholders_equity=40_000_000), dict(requested_credit_limit=6_000_000, approved_credit_limit=6_000_000, outstanding_receivables=4_700_000, payment_tenor_days=60, utilization_rate=0.82, collateral_type="unsecured", deposit_percentage=0, fuel_volume=1_400_000, fuel_price=2.85)),
        SyntheticCompany("Validation Sovereign Buyer", "Government", "Saudi Arabia", dict(revenue=1_800_000_000, ebitda=320_000_000, ebit=260_000_000, interest_expense=25_000_000, net_income=180_000_000, cash_and_equivalents=450_000_000, accounts_receivable=120_000_000, inventory=40_000_000, current_assets=700_000_000, total_assets=2_400_000_000, current_liabilities=280_000_000, total_debt=500_000_000, total_liabilities=900_000_000, shareholders_equity=1_500_000_000), dict(requested_credit_limit=25_000_000, approved_credit_limit=25_000_000, outstanding_receivables=8_000_000, payment_tenor_days=90, utilization_rate=0.32, collateral_type="guarantee", guarantee_flag=True, deposit_percentage=0, fuel_volume=9_000_000, fuel_price=2.60)),
        SyntheticCompany("Validation Startup Air Mobility", "Airline Startup", "United States", dict(revenue=42_000_000, ebitda=-18_000_000, ebit=-22_000_000, interest_expense=4_500_000, net_income=-30_000_000, cash_and_equivalents=18_000_000, accounts_receivable=8_000_000, inventory=3_000_000, current_assets=35_000_000, total_assets=95_000_000, current_liabilities=55_000_000, total_debt=80_000_000, total_liabilities=115_000_000, shareholders_equity=-20_000_000), dict(requested_credit_limit=5_000_000, approved_credit_limit=5_000_000, outstanding_receivables=3_800_000, payment_tenor_days=45, utilization_rate=0.76, collateral_type="cash_deposit", deposit_percentage=25, fuel_volume=1_100_000, fuel_price=2.95)),
        SyntheticCompany("Validation Refinery Offtaker", "Refinery", "South Korea", dict(revenue=980_000_000, ebitda=88_000_000, ebit=64_000_000, interest_expense=16_000_000, net_income=31_000_000, cash_and_equivalents=90_000_000, accounts_receivable=175_000_000, inventory=250_000_000, current_assets=590_000_000, total_assets=1_200_000_000, current_liabilities=380_000_000, total_debt=470_000_000, total_liabilities=760_000_000, shareholders_equity=440_000_000), dict(requested_credit_limit=15_000_000, approved_credit_limit=15_000_000, outstanding_receivables=9_000_000, payment_tenor_days=45, utilization_rate=0.66, collateral_type="letter_of_credit", letter_of_credit_flag=True, deposit_percentage=0, fuel_volume=6_000_000, fuel_price=2.55)),
    ]


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


def main() -> None:
    market = _market_rows()
    store_counts = store_market_provider_rows(market)
    rebuild = rebuild_market_intelligence()
    client = TestClient(app)
    companies = _companies()
    company_results = []
    counterparty_ids = []

    for company in companies:
        cp = _post(
            client,
            "/api/v1/documents/counterparties",
            {"counterparty_name": company.name, "counterparty_type": company.ctype, "country": company.country},
        )
        counterparty_ids.append(cp["id"])
        metrics_payload = {"counterparty_id": cp["id"], "fiscal_year": 2025, "fiscal_period": "FY", "currency": "USD", **company.financials, "created_by": RUN_TAG}
        metrics = _post(client, "/api/v1/financial-analysis/metrics/manual", metrics_payload)["metrics"]
        ratios = _post(client, f"/api/v1/financial-analysis/ratios/calculate/{metrics['id']}")["ratios"]
        pd_result = _post(client, f"/api/v1/credit-risk/pd/calculate/{metrics['id']}", {"time_horizon_years": 1.0})["prediction"]
        exposure = {
            "counterparty_id": cp["id"],
            "pd_prediction_id": pd_result["id"],
            "country_risk_score": 2.0,
            "seniority_score": 2.0,
            "counterparty_type": company.ctype,
            "notes": RUN_TAG,
            **company.terms,
        }
        loss = _post(client, "/api/v1/credit-risk/loss/calculate", exposure)["loss_estimate"]
        company_results.append({"counterparty": cp, "metrics": metrics, "ratios": ratios, "pd": pd_result, "loss": loss, "terms": company.terms})

    mc = _post(
        client,
        "/api/v1/scenario-analysis/monte-carlo/run",
        {"scenario_type": "adverse", "counterparty_ids": counterparty_ids, "n_simulations": 1500, "random_seed": 20260624, "persist": True},
    )
    scenarios = _get(client, "/api/v1/scenario-analysis/scenarios")["scenarios"]
    market_prices = _get(
        client,
        "/api/v1/market-intelligence/prices/recent?assets=brent_oil,crude_oil,jet_fuel_proxy,jet_crack_spread,vix,sp500,dxy,eia_crude_inventories,opec_production,global_pmi,iata_passenger_traffic&limit_per_asset=120",
    )

    checks: list[str] = []
    errors: list[str] = []
    for result in company_results:
        cp = result["counterparty"]
        rec = _post(client, f"/api/v1/credit-decision/counterparty/{cp['id']}/recommend")["recommendation"]
        latest = _get(client, f"/api/v1/credit-decision/counterparty/{cp['id']}/latest")
        result["recommendation"] = rec
        result["latest_recommendation"] = latest

        pd_value = float(result["pd"]["final_pd"])
        lgd = float(result["loss"]["predicted_lgd"])
        ead = float(result["loss"]["exposure_at_default"])
        el = float(result["loss"]["expected_loss"])
        if not (0 < pd_value < 1):
            errors.append(f"{cp['counterparty_name']}: PD out of bounds {pd_value}")
        if not (0 <= lgd <= 1):
            errors.append(f"{cp['counterparty_name']}: LGD out of bounds {lgd}")
        if abs(el - pd_value * lgd * ead) > max(1.0, 0.01 * max(el, 1.0)):
            errors.append(f"{cp['counterparty_name']}: EL mismatch {el} vs {pd_value * lgd * ead}")
        requested_limit = float(result["terms"]["requested_credit_limit"] or 0)
        if float(rec["recommended_credit_limit"]) > requested_limit + 1:
            errors.append(f"{cp['counterparty_name']}: recommended limit exceeds requested")
        rec_var = float(rec["credit_var_95"] or 0)
        rec_es = float(rec["expected_shortfall_95"] or 0)
        if requested_limit > 0 and rec_var > requested_limit + 1:
            errors.append(
                f"{cp['counterparty_name']}: single-name credit VaR exceeds requested limit "
                f"({rec_var:.0f} > {requested_limit:.0f})"
            )
        if requested_limit > 0 and rec_es > requested_limit + 1:
            errors.append(
                f"{cp['counterparty_name']}: single-name expected shortfall exceeds requested limit "
                f"({rec_es:.0f} > {requested_limit:.0f})"
            )
        if rec_es and rec_var and rec_es < rec_var:
            errors.append(f"{cp['counterparty_name']}: single-name ES95 below VaR95")
        if rec["approval_status"] in {None, ""} or rec["risk_grade"] in {None, ""}:
            errors.append(f"{cp['counterparty_name']}: recommendation missing decision labels")
        checks.append(
            f"{cp['counterparty_name']}: PD={pd_value:.4f}, LGD={lgd:.4f}, EAD={ead:.0f}, EL={el:.0f}, VaR95={rec_var:.0f}, ES95={rec_es:.0f}, limit={float(rec['recommended_credit_limit']):.0f}, tenor={rec['recommended_tenor_days']}, grade={rec['risk_grade']}, status={rec['approval_status']}"
        )

    if mc["expected_shortfall_95"] < mc["credit_var_95"]:
        errors.append("Monte Carlo ES95 below VaR95")
    if mc["expected_shortfall_99"] < mc["credit_var_99"]:
        errors.append("Monte Carlo ES99 below VaR99")
    if len(scenarios) < 4:
        errors.append("Scenario endpoint returned fewer than four scenarios")
    required_shocks = {"jet_crack_spread_change", "crude_inventory_change", "opec_production_change", "global_pmi_change", "iata_passenger_traffic_change"}
    missing_shocks = required_shocks - set(scenarios[0]["market_shocks"])
    if missing_shocks:
        errors.append(f"Scenario shocks missing: {sorted(missing_shocks)}")
    assets_returned = {row["asset"] for row in market_prices["market_prices"]}
    missing_assets = {"jet_crack_spread", "eia_crude_inventories", "opec_production", "global_pmi", "iata_passenger_traffic"} - assets_returned
    if missing_assets:
        errors.append(f"Market graph assets missing: {sorted(missing_assets)}")

    report = {
        "run_tag": RUN_TAG,
        "market_store_counts": store_counts,
        "rebuild": rebuild,
        "counterparty_count": len(company_results),
        "scenario_count": len(scenarios),
        "market_price_rows": market_prices["row_count"],
        "monte_carlo": {
            "expected_loss": mc["expected_loss"],
            "credit_var_95": mc["credit_var_95"],
            "expected_shortfall_95": mc["expected_shortfall_95"],
            "credit_var_99": mc["credit_var_99"],
            "expected_shortfall_99": mc["expected_shortfall_99"],
            "avg_defaults": mc["avg_defaults"],
            "max_defaults": mc["max_defaults"],
        },
        "checks": checks,
        "errors": errors,
        "company_results": [
            {
                "name": item["counterparty"]["counterparty_name"],
                "type": item["counterparty"]["counterparty_type"],
                "pd": item["pd"]["final_pd"],
                "lgd": item["loss"]["predicted_lgd"],
                "ead": item["loss"]["exposure_at_default"],
                "expected_loss": item["loss"]["expected_loss"],
                "credit_var_95": item["recommendation"]["credit_var_95"],
                "expected_shortfall_95": item["recommendation"]["expected_shortfall_95"],
                "recommended_limit": item["recommendation"]["recommended_credit_limit"],
                "requested_limit": item["terms"]["requested_credit_limit"],
                "recommended_tenor": item["recommendation"]["recommended_tenor_days"],
                "recommended_security": item["recommendation"]["recommended_security"],
                "risk_grade": item["recommendation"]["risk_grade"],
                "approval_status": item["recommendation"]["approval_status"],
            }
            for item in company_results
        ],
    }
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"report": str(OUT), "errors": errors, "checks": checks}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
