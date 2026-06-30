"""Database service for Phase 5 PD estimation."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.machine_learning.pd_model import MarketContext, PDPredictionResult, estimate_pd
from api.db.models import CounterpartyMaster, FinancialMetricsExtracted, FinancialRatios
from api.financials.service import get_financial_trend_features


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _json_value(db: Session, param_name: str) -> str:
    if db.get_bind().dialect.name == "postgresql":
        return f"CAST(:{param_name} AS JSONB)"
    return f":{param_name}"


def get_latest_market_context(db: Session) -> MarketContext:
    stress = db.execute(
        text(
            """
            SELECT stress_index, stress_level, component_values
            FROM stress_index_history
            ORDER BY date DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    regime = db.execute(
        text(
            """
            SELECT regime_label
            FROM market_regime_history
            ORDER BY date DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    rate = db.execute(
        text(
            """
            SELECT price
            FROM market_prices
            WHERE asset = 'us_10y_yield'
            ORDER BY date DESC
            LIMIT 1
            """
        )
    ).scalar()

    component_values = dict(stress["component_values"] or {}) if stress else {}
    risk_free_rate = 0.04
    if rate is not None:
        rate_float = float(rate)
        risk_free_rate = rate_float / 100 if rate_float > 1 else rate_float

    return MarketContext(
        stress_index=float(stress["stress_index"]) if stress else 50.0,
        stress_level=str(stress["stress_level"]) if stress else "Unknown",
        market_regime=str(regime["regime_label"]) if regime else "Unknown",
        risk_free_rate=risk_free_rate,
        oil_volatility_zscore=float(component_values.get("oil_volatility_zscore", 0.0)),
        fuel_return_zscore=float(component_values.get("jet_fuel_return_zscore", component_values.get("heating_oil_return_zscore", component_values.get("brent_return_zscore", 0.0)))),
        crack_spread_zscore=float(component_values.get("jet_crack_spread_zscore", 0.0)),
        fx_return_zscore=float(component_values.get("dxy_return_zscore", component_values.get("usd_inr_return_zscore", 0.0))),
        freight_loss_zscore=float(component_values.get("freight_loss_zscore", 0.0)),
        inventory_build_zscore=float(component_values.get("crude_inventory_build_zscore", 0.0)),
        opec_production_cut_zscore=float(component_values.get("opec_production_cut_zscore", 0.0)),
        pmi_weakness_zscore=float(component_values.get("global_pmi_weakness_zscore", 0.0)),
        iata_traffic_loss_zscore=float(component_values.get("iata_traffic_loss_zscore", 0.0)),
    )


def calculate_pd_for_financial_metrics(
    db: Session,
    financial_metrics_id: int,
    time_horizon_years: float = 1.0,
) -> PDPredictionResult:
    financials = (
        db.query(FinancialMetricsExtracted)
        .filter(FinancialMetricsExtracted.id == financial_metrics_id)
        .first()
    )
    if financials is None:
        raise ValueError(f"Financial metrics record {financial_metrics_id} not found")

    ratios = (
        db.query(FinancialRatios)
        .filter(FinancialRatios.financial_metrics_id == financial_metrics_id)
        .first()
    )
    if ratios is None:
        raise ValueError(
            f"Financial ratios for metrics record {financial_metrics_id} not found. Run Phase 3 first."
        )

    counterparty = (
        db.query(CounterpartyMaster)
        .filter(CounterpartyMaster.id == financials.counterparty_id)
        .first()
    )
    market_context = get_latest_market_context(db)
    financial_trends = get_financial_trend_features(db, financials.counterparty_id)
    return estimate_pd(
        counterparty_id=financials.counterparty_id,
        counterparty_type=counterparty.counterparty_type if counterparty else None,
        financials=financials,
        ratios=ratios,
        market_context=market_context,
        financial_metrics_id=financials.id,
        financial_ratios_id=ratios.id,
        time_horizon_years=time_horizon_years,
        financial_trends=financial_trends,
    )


def save_pd_prediction(db: Session, result: PDPredictionResult):
    db.execute(
        text(
            f"""
            INSERT INTO pd_model_predictions (
                run_id,
                counterparty_id,
                financial_metrics_id,
                financial_ratios_id,
                model_name,
                model_version,
                structural_pd,
                ml_pd,
                final_pd,
                classification_label,
                model_confidence,
                model_disagreement,
                pd_divergence,
                distance_to_default,
                asset_value_proxy,
                debt_threshold,
                asset_volatility,
                risk_free_rate,
                time_horizon_years,
                commodity_sensitivity_score,
                fx_sensitivity_score,
                macro_sensitivity_score,
                market_stress_index,
                market_regime,
                feature_contributions,
                model_assumptions,
                input_data_reference,
                warnings
            )
            VALUES (
                :run_id,
                :counterparty_id,
                :financial_metrics_id,
                :financial_ratios_id,
                :model_name,
                :model_version,
                :structural_pd,
                :ml_pd,
                :final_pd,
                :classification_label,
                :model_confidence,
                :model_disagreement,
                :pd_divergence,
                :distance_to_default,
                :asset_value_proxy,
                :debt_threshold,
                :asset_volatility,
                :risk_free_rate,
                :time_horizon_years,
                :commodity_sensitivity_score,
                :fx_sensitivity_score,
                :macro_sensitivity_score,
                :market_stress_index,
                :market_regime,
                {_json_value(db, "feature_contributions")},
                {_json_value(db, "model_assumptions")},
                {_json_value(db, "input_data_reference")},
                {_json_value(db, "warnings")}
            )
            RETURNING id
            """
        ),
        {
            **{
                key: value
                for key, value in result.__dict__.items()
                if key
                not in {
                    "feature_contributions",
                    "model_assumptions",
                    "input_data_reference",
                    "warnings",
                    "created_at",
                }
            },
            "feature_contributions": _json_dumps(result.feature_contributions),
            "model_assumptions": _json_dumps(result.model_assumptions),
            "input_data_reference": _json_dumps(result.input_data_reference),
            "warnings": _json_dumps(result.warnings),
        },
    )
    db.commit()
    return get_pd_prediction_by_run_id(db, result.run_id)


def calculate_and_store_pd(
    db: Session,
    financial_metrics_id: int,
    time_horizon_years: float = 1.0,
):
    result = calculate_pd_for_financial_metrics(
        db,
        financial_metrics_id=financial_metrics_id,
        time_horizon_years=time_horizon_years,
    )
    return save_pd_prediction(db, result)


def get_pd_prediction_by_run_id(db: Session, run_id: str):
    return db.execute(
        text(
            """
            SELECT *
            FROM pd_model_predictions
            WHERE run_id = :run_id
            """
        ),
        {"run_id": run_id},
    ).mappings().first()


def get_latest_pd_prediction(db: Session, counterparty_id: int):
    return db.execute(
        text(
            """
            SELECT *
            FROM pd_model_predictions
            WHERE counterparty_id = :counterparty_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"counterparty_id": counterparty_id},
    ).mappings().first()


