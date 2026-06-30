"""Database service for Phase 6 LGD/EAD/Expected Loss estimation."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.machine_learning.loss_model import (
    LossEstimateResult,
    TradeExposureInput,
    estimate_loss,
)
from api.financials.service import get_financial_trend_features
from api.financials.trends import calculate_trend_risk_overlay


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _json_value(db: Session, param_name: str) -> str:
    if db.get_bind().dialect.name == "postgresql":
        return f"CAST(:{param_name} AS JSONB)"
    return f":{param_name}"


def _latest_pd_prediction(db: Session, counterparty_id: int):
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


def save_trade_exposure(db: Session, exposure: TradeExposureInput):
    result = db.execute(
        text(
            """
            INSERT INTO trade_exposures (
                counterparty_id,
                invoice_amount,
                fuel_volume,
                fuel_price,
                approved_credit_limit,
                requested_credit_limit,
                outstanding_receivables,
                payment_tenor_days,
                utilization_rate,
                collateral_type,
                letter_of_credit_flag,
                guarantee_flag,
                deposit_percentage,
                counterparty_type,
                country_risk_score,
                seniority_score,
                notes
            )
            VALUES (
                :counterparty_id,
                :invoice_amount,
                :fuel_volume,
                :fuel_price,
                :approved_credit_limit,
                :requested_credit_limit,
                :outstanding_receivables,
                :payment_tenor_days,
                :utilization_rate,
                :collateral_type,
                :letter_of_credit_flag,
                :guarantee_flag,
                :deposit_percentage,
                :counterparty_type,
                :country_risk_score,
                :seniority_score,
                :notes
            )
            RETURNING *
            """
        ),
        exposure.__dict__,
    ).mappings().first()
    db.commit()
    return result


def save_loss_estimate(db: Session, estimate: LossEstimateResult):
    stored_probability_of_default = round(float(estimate.probability_of_default), 8)
    stored_predicted_lgd = round(float(estimate.predicted_lgd), 8)
    stored_exposure_at_default = round(float(estimate.exposure_at_default), 2)
    stored_expected_loss = (
        stored_probability_of_default
        * stored_predicted_lgd
        * stored_exposure_at_default
    )
    result = db.execute(
        text(
            f"""
            INSERT INTO loss_estimates (
                run_id,
                counterparty_id,
                pd_prediction_id,
                trade_exposure_id,
                model_name,
                model_version,
                probability_of_default,
                predicted_lgd,
                exposure_at_default,
                expected_loss,
                collateral_strength,
                liquidity_score,
                ead_cap_applied,
                expected_drawdown,
                invoice_exposure,
                model_assumptions,
                input_data_reference,
                warnings
            )
            VALUES (
                :run_id,
                :counterparty_id,
                :pd_prediction_id,
                :trade_exposure_id,
                :model_name,
                :model_version,
                :probability_of_default,
                :predicted_lgd,
                :exposure_at_default,
                :expected_loss,
                :collateral_strength,
                :liquidity_score,
                :ead_cap_applied,
                :expected_drawdown,
                :invoice_exposure,
                {_json_value(db, "model_assumptions")},
                {_json_value(db, "input_data_reference")},
                {_json_value(db, "warnings")}
            )
            RETURNING *
            """
        ),
        {
            **{
                key: value
                for key, value in estimate.__dict__.items()
                if key
                not in {
                    "model_assumptions",
                    "input_data_reference",
                    "warnings",
                    "created_at",
                }
            },
            "probability_of_default": stored_probability_of_default,
            "predicted_lgd": stored_predicted_lgd,
            "exposure_at_default": stored_exposure_at_default,
            "expected_loss": stored_expected_loss,
            "model_assumptions": _json_dumps(estimate.model_assumptions),
            "input_data_reference": _json_dumps(estimate.input_data_reference),
            "warnings": _json_dumps(estimate.warnings),
        },
    ).mappings().first()
    db.commit()
    return result


def calculate_and_store_loss_estimate(
    db: Session,
    exposure: TradeExposureInput,
    pd_prediction_id: Optional[int] = None,
):
    if pd_prediction_id is not None:
        pd_prediction = db.execute(
            text("SELECT * FROM pd_model_predictions WHERE id = :id"),
            {"id": pd_prediction_id},
        ).mappings().first()
    else:
        pd_prediction = _latest_pd_prediction(db, exposure.counterparty_id)

    if pd_prediction is None:
        raise ValueError(
            f"No PD prediction found for counterparty {exposure.counterparty_id}. Run Phase 5 first."
        )

    stored_exposure = save_trade_exposure(db, exposure)
    trend_features = get_financial_trend_features(db, exposure.counterparty_id)
    trend_overlay = calculate_trend_risk_overlay(trend_features)
    estimate = estimate_loss(
        probability_of_default=float(pd_prediction["final_pd"]),
        exposure=exposure,
        pd_prediction_id=int(pd_prediction["id"]),
        trade_exposure_id=int(stored_exposure["id"]),
        liquidity_score=trend_overlay.get("liquidity_score"),
        financial_trend_overlay=trend_overlay,
    )
    return save_loss_estimate(db, estimate)


def get_latest_loss_estimate(db: Session, counterparty_id: int):
    return db.execute(
        text(
            """
            SELECT
                le.*,
                te.requested_credit_limit,
                te.approved_credit_limit,
                te.outstanding_receivables,
                te.payment_tenor_days,
                te.utilization_rate,
                te.collateral_type,
                te.letter_of_credit_flag,
                te.guarantee_flag,
                te.deposit_percentage,
                te.invoice_amount,
                te.fuel_volume,
                te.fuel_price
            FROM loss_estimates le
            LEFT JOIN trade_exposures te
                ON te.id = le.trade_exposure_id
            WHERE le.counterparty_id = :counterparty_id
            ORDER BY le.created_at DESC, le.id DESC
            LIMIT 1
            """
        ),
        {"counterparty_id": counterparty_id},
    ).mappings().first()

