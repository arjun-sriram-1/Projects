"""Deterministic PCA and market-factor explanation helpers."""

from __future__ import annotations

from typing import Any

from api.market_data.stress_index import COMPONENT_DESCRIPTIONS


FACTOR_COMPONENTS = {
    "brent": ["brent_return_zscore", "oil_volatility_zscore"],
    "oil": ["brent_return_zscore", "heating_oil_return_zscore", "jet_fuel_return_zscore", "oil_volatility_zscore"],
    "jet": ["jet_fuel_return_zscore", "heating_oil_return_zscore", "jet_crack_spread_zscore", "oil_volatility_zscore"],
    "fuel": ["jet_fuel_return_zscore", "heating_oil_return_zscore", "jet_crack_spread_zscore", "brent_return_zscore", "oil_volatility_zscore"],
    "crack": ["jet_crack_spread_zscore"],
    "spread": ["jet_crack_spread_zscore"],
    "vix": ["vix_zscore"],
    "sp500": ["sp500_loss_zscore"],
    "equity": ["sp500_loss_zscore"],
    "dxy": ["dxy_return_zscore"],
    "usd": ["dxy_return_zscore", "usd_inr_return_zscore"],
    "fx": ["dxy_return_zscore", "usd_inr_return_zscore"],
    "rates": ["yield_10y_change_zscore", "yield_curve_stress_zscore"],
    "yield": ["yield_10y_change_zscore", "yield_curve_stress_zscore"],
    "inflation": ["inflation_zscore"],
    "freight": ["freight_loss_zscore"],
    "credit": ["high_yield_spread_zscore"],
    "inventory": ["crude_inventory_build_zscore"],
    "inventories": ["crude_inventory_build_zscore"],
    "eia": ["crude_inventory_build_zscore"],
    "opec": ["opec_production_cut_zscore"],
    "pmi": ["global_pmi_weakness_zscore"],
    "iata": ["iata_traffic_loss_zscore"],
    "passenger": ["iata_traffic_loss_zscore"],
    "traffic": ["iata_traffic_loss_zscore"],
}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _factor_components(factor: str | None) -> list[str]:
    if not factor:
        return []
    clean = factor.lower().strip()
    matched: list[str] = []
    for key, components in FACTOR_COMPONENTS.items():
        if key in clean:
            matched.extend(components)
    return list(dict.fromkeys(matched))


def _component_contributions(
    loadings: dict[str, Any],
    component_values: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component, loading_value in loadings.items():
        loading = _safe_float(loading_value)
        value = _safe_float(component_values.get(component))
        if loading is None:
            continue
        contribution = loading * value if value is not None else None
        rows.append(
            {
                "component": component,
                "description": COMPONENT_DESCRIPTIONS.get(component, component),
                "loading": loading,
                "component_value": value,
                "pc1_contribution": contribution,
                "direction": "raises stress" if loading >= 0 else "offsets stress",
            }
        )
    rows.sort(
        key=lambda item: abs(item["pc1_contribution"] if item["pc1_contribution"] is not None else item["loading"]),
        reverse=True,
    )
    return rows


def explain_market_factor(
    *,
    factor: str | None = None,
    stress_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Explain how a market factor moves through PCA into credit outputs."""
    stress_record = stress_record or {}
    loadings = _as_dict(stress_record.get("pca_loadings"))
    component_values = _as_dict(stress_record.get("component_values"))
    all_contributions = _component_contributions(loadings, component_values)
    selected_components = _factor_components(factor)
    selected = [
        row for row in all_contributions if row["component"] in selected_components
    ] if selected_components else all_contributions[:6]

    stress_index = _safe_float(stress_record.get("stress_index"))
    pc1_score = _safe_float(stress_record.get("pc1_score"))
    explained_variance = _safe_float(stress_record.get("explained_variance_ratio"))

    if selected:
        factor_text = factor or "the strongest current market drivers"
        summary = (
            f"{factor_text} affects the project through the market stress layer. "
            "The relevant market component is standardized, multiplied by its PCA loading, "
            "rolled into PC1, scaled into the 0-100 stress index, then used as context for PD, "
            "scenario losses, and credit decision haircuts."
        )
    else:
        summary = (
            "I do not have a matching PCA component for that factor in the current stress record. "
            "The project can still discuss the general route: market data -> z-scored components -> PCA PC1 -> stress index -> PD/scenario/decision context."
        )

    return {
        "factor": factor,
        "stress_index": stress_index,
        "pc1_score": pc1_score,
        "explained_variance_ratio": explained_variance,
        "selected_components": selected,
        "top_components": all_contributions[:8],
        "calculation_chain": [
            "market_prices are pivoted by date and asset",
            "returns, volatility, rate changes, spread changes, and loss proxies are transformed into stress-oriented components",
            "each component is standardized with a z-score",
            "PCA(n_components=1) creates pc1_score when enough component history exists",
            "PC1 sign is aligned so higher PC1 means higher average stress",
            "pc1_score is percentile-scaled into stress_index from 0 to 100",
            "stress_index and market_regime feed PD context, scenario multipliers, Monte Carlo assumptions, and credit decision haircuts",
        ],
        "formulas": [
            "z = (x - mean(x)) / std(x)",
            "pc1_score = sum(component_zscore_i * pca_loading_i)",
            "stress_index = percentile_scale(pc1_score)",
            "expected_loss = PD * LGD * EAD",
        ],
        "summary": summary,
        "sources": [
            "api/market_data/stress_index.py",
            "api/market_data/regime_detection.py",
            "api/machine_learning/pd_model.py",
            "api/credit_decision/engine.py",
        ],
        "limitations": [
            "PCA explains common movement across market proxies; it does not prove causality.",
            "Stress index is a project market-proxy score, not an official geopolitical risk index.",
            "Exact stress_index reproduction requires the historical PC1 distribution, not just one latest point.",
        ],
    }
