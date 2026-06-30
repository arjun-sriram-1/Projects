"""Financial history feature engineering for multi-period metrics."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
import math

from api.db.models import FinancialMetricsExtracted, FinancialRatios


QUARTERS = {"Q1", "Q2", "Q3", "Q4"}


def _num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _period_label(row: FinancialMetricsExtracted) -> str:
    period = str(row.fiscal_period or row.period_label or "FY").upper()
    return f"{row.fiscal_year or 'Unknown'} {period}"


def _period_order(row: FinancialMetricsExtracted) -> tuple[int, int, int]:
    order = {"FY": 5, "Q4": 4, "Q3": 3, "Q2": 2, "Q1": 1}
    return (
        int(row.fiscal_year or 0),
        order.get(str(row.fiscal_period or "FY").upper(), 0),
        int(row.id or 0),
    )


def _pct_change(latest: float | None, previous: float | None) -> float | None:
    if latest is None or previous is None or previous == 0:
        return None
    return (latest - previous) / abs(previous)


def _simple_slope(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if len(clean) < 2:
        return None
    return (clean[-1] - clean[0]) / max(len(clean) - 1, 1)


def _cagr(oldest: float | None, latest: float | None, years: int) -> float | None:
    if oldest is None or latest is None or oldest <= 0 or latest <= 0 or years <= 0:
        return None
    return (latest / oldest) ** (1 / years) - 1


def _ratio_value(ratio_map: dict[int, FinancialRatios], metrics_id: int, field: str) -> float | None:
    row = ratio_map.get(metrics_id)
    return _num(getattr(row, field, None)) if row is not None else None


def _clip(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))


def _risk_from_negative(value: float | None, weight: float, cap: float) -> float:
    if value is None or value >= 0:
        return 0.0
    return min(cap, abs(value) * weight)


def _risk_from_positive(value: float | None, weight: float, cap: float) -> float:
    if value is None or value <= 0:
        return 0.0
    return min(cap, value * weight)


def calculate_trend_risk_overlay(features: dict[str, Any] | None) -> dict[str, Any]:
    """Convert historical financial trends into capped model overlays.

    This deliberately acts as a thin layer over the existing engines. It does
    not replace Merton, logistic PD, LGD, EAD, or EL formulas; it gives those
    models a small, auditable adjustment when multi-period history is present.
    """
    features = features or {}
    period_count = int(features.get("period_count") or 0)
    status = features.get("history_status") or "none"
    if period_count < 2 or status != "available":
        return {
            "history_status": status,
            "period_count": period_count,
            "risk_score": 0.0,
            "pd_multiplier": 1.0,
            "asset_volatility_addon": 0.0,
            "lgd_addon": 0.0,
            "liquidity_score": None,
            "direction": "neutral",
            "drivers": {},
            "notes": ["Trend overlay is neutral because fewer than two comparable periods are available."],
        }

    drivers = {
        "negative_revenue_cagr": _risk_from_negative(features.get("revenue_cagr"), 1.20, 0.24),
        "latest_revenue_decline": _risk_from_negative(features.get("latest_revenue_growth"), 0.85, 0.18),
        "ebitda_margin_deterioration": _risk_from_negative(features.get("ebitda_margin_trend"), 3.00, 0.16),
        "net_margin_deterioration": _risk_from_negative(features.get("net_margin_trend"), 2.00, 0.12),
        "debt_growth_pressure": _risk_from_positive(features.get("debt_growth"), 0.35, 0.16),
        "leverage_deterioration": _risk_from_positive(features.get("leverage_trend"), 0.08, 0.16),
        "coverage_deterioration": _risk_from_negative(features.get("interest_coverage_trend"), 0.04, 0.14),
        "liquidity_deterioration": _risk_from_negative(features.get("current_ratio_trend"), 0.08, 0.12),
        "cash_decline": _risk_from_negative(features.get("cash_trend"), 0.45, 0.12),
        "fuel_cost_growth": _risk_from_positive(features.get("fuel_cost_growth"), 0.30, 0.10),
    }
    positive_offsets = {
        "revenue_growth_offset": _risk_from_positive(features.get("revenue_cagr"), 0.45, 0.10),
        "margin_improvement_offset": _risk_from_positive(features.get("ebitda_margin_trend"), 1.50, 0.08),
        "deleveraging_offset": _risk_from_negative(features.get("debt_growth"), 0.20, 0.08),
        "coverage_improvement_offset": _risk_from_positive(features.get("interest_coverage_trend"), 0.02, 0.08),
        "liquidity_improvement_offset": _risk_from_positive(features.get("current_ratio_trend"), 0.04, 0.06),
        "cash_growth_offset": _risk_from_positive(features.get("cash_trend"), 0.20, 0.06),
    }

    raw_risk = sum(drivers.values()) - sum(positive_offsets.values())
    risk_score = _clip(raw_risk, -0.18, 0.38)
    current_ratio_latest = features.get("current_ratio_latest")
    liquidity_score = None
    if current_ratio_latest is not None and math.isfinite(float(current_ratio_latest)):
        liquidity_score = _clip((float(current_ratio_latest) - 0.50) / 1.50, 0.05, 1.0)

    direction = "neutral"
    if risk_score >= 0.08:
        direction = "deteriorating"
    elif risk_score <= -0.05:
        direction = "improving"

    notes = [
        "Trend overlay uses stored annual/quarterly financial history as a capped adjustment layer.",
        f"Historical trend direction is {direction}.",
    ]
    if features.get("warnings"):
        notes.extend(str(item) for item in features.get("warnings", [])[:3])

    return {
        "history_status": status,
        "period_count": period_count,
        "history_frequency": features.get("history_frequency"),
        "latest_period": features.get("latest_period"),
        "oldest_period": features.get("oldest_period"),
        "risk_score": risk_score,
        "pd_multiplier": _clip(1.0 + risk_score, 0.85, 1.38),
        "asset_volatility_addon": max(0.0, risk_score) * 0.08,
        "lgd_addon": max(0.0, risk_score) * 0.10,
        "liquidity_score": liquidity_score,
        "direction": direction,
        "drivers": {**drivers, **{key: -value for key, value in positive_offsets.items()}},
        "notes": notes,
    }


def calculate_financial_trend_features(
    counterparty_id: int,
    metrics_rows: list[FinancialMetricsExtracted],
    ratio_rows: list[FinancialRatios],
) -> dict[str, Any]:
    rows = sorted(metrics_rows, key=_period_order)
    ratio_map = {int(row.financial_metrics_id): row for row in ratio_rows}
    warnings: list[str] = []
    period_count = len(rows)
    period_types = {
        "quarterly" if str(row.fiscal_period or "").upper() in QUARTERS else "annual"
        for row in rows
    }
    frequency = next(iter(period_types)) if len(period_types) == 1 and period_types else "mixed"
    if frequency == "mixed":
        warnings.append("Mixed annual and quarterly records detected; trend values are simple ordered-period estimates.")

    base = {
        "counterparty_id": counterparty_id,
        "period_count": period_count,
        "history_status": "insufficient_history" if period_count < 2 else "available",
        "history_frequency": frequency if period_count else "none",
        "latest_period": _period_label(rows[-1]) if rows else None,
        "oldest_period": _period_label(rows[0]) if rows else None,
        "revenue_cagr": None,
        "latest_revenue_growth": None,
        "ebitda_margin_trend": None,
        "net_margin_trend": None,
        "debt_growth": None,
        "leverage_trend": None,
        "interest_coverage_trend": None,
        "current_ratio_trend": None,
        "cash_trend": None,
        "fuel_cost_growth": None,
        "fuel_cost_to_revenue_latest": None,
        "warnings": warnings,
    }
    if period_count < 2:
        if period_count == 1:
            warnings.append("Only one financial period is stored; trend features require at least two periods.")
        return base

    revenue = [_num(row.revenue) for row in rows]
    ebitda = [_num(row.ebitda) for row in rows]
    net_income = [_num(row.net_income) for row in rows]
    total_debt = [_num(row.total_debt) for row in rows]
    cash = [_num(row.cash_and_equivalents) for row in rows]
    fuel_cost = [_num(row.cost_of_goods_sold) for row in rows]
    ebitda_margin = [
        e / r if e is not None and r not in {None, 0} else None
        for e, r in zip(ebitda, revenue)
    ]
    net_margin = [
        n / r if n is not None and r not in {None, 0} else None
        for n, r in zip(net_income, revenue)
    ]
    leverage = [_ratio_value(ratio_map, int(row.id), "debt_to_ebitda") for row in rows]
    interest_coverage = [_ratio_value(ratio_map, int(row.id), "interest_coverage") for row in rows]
    current_ratio = [_ratio_value(ratio_map, int(row.id), "current_ratio") for row in rows]
    interest_coverage_latest = interest_coverage[-1] if interest_coverage else None
    current_ratio_latest = current_ratio[-1] if current_ratio else None
    leverage_latest = leverage[-1] if leverage else None
    annual_years = max(int((rows[-1].fiscal_year or 0) - (rows[0].fiscal_year or 0)), period_count - 1)

    base.update(
        {
            "revenue_cagr": _cagr(revenue[0], revenue[-1], annual_years) if frequency == "annual" else None,
            "latest_revenue_growth": _pct_change(revenue[-1], revenue[-2]),
            "ebitda_margin_trend": _simple_slope(ebitda_margin),
            "net_margin_trend": _simple_slope(net_margin),
            "debt_growth": _pct_change(total_debt[-1], total_debt[0]),
            "leverage_trend": _simple_slope(leverage),
            "interest_coverage_trend": _simple_slope(interest_coverage),
            "current_ratio_trend": _simple_slope(current_ratio),
            "current_ratio_latest": current_ratio_latest,
            "interest_coverage_latest": interest_coverage_latest,
            "leverage_latest": leverage_latest,
            "ebitda_margin_latest": ebitda_margin[-1] if ebitda_margin else None,
            "net_margin_latest": net_margin[-1] if net_margin else None,
            "cash_trend": _pct_change(cash[-1], cash[0]),
            "fuel_cost_growth": _pct_change(fuel_cost[-1], fuel_cost[0]),
            "fuel_cost_to_revenue_latest": (
                fuel_cost[-1] / revenue[-1]
                if fuel_cost[-1] is not None and revenue[-1] not in {None, 0}
                else None
            ),
        }
    )
    return base
