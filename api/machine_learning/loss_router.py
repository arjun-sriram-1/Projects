"""FastAPI routes for Phase 6 LGD, EAD, and Expected Loss."""

from datetime import date, datetime
from decimal import Decimal
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.machine_learning.loss_schemas import (
    LossEstimateCalculationResponse,
    LossEstimateResponse,
    TradeExposureRequest,
)
from api.db.session import get_db
from api.machine_learning.loss_model import TradeExposureInput
from api.machine_learning.loss_service import (
    calculate_and_store_loss_estimate,
    get_latest_loss_estimate,
)


router = APIRouter(prefix="/api/v1/credit-risk", tags=["credit-risk"])

JSON_FIELDS = {"model_assumptions", "input_data_reference", "warnings"}


def _row_to_dict(row):
    converted = {}
    for key, value in dict(row).items():
        if isinstance(value, Decimal):
            converted[key] = float(value)
        elif isinstance(value, (datetime, date)):
            converted[key] = value.isoformat()
        elif key in JSON_FIELDS and isinstance(value, str):
            converted[key] = json.loads(value)
        else:
            converted[key] = value
    return converted


@router.post(
    "/loss/calculate",
    response_model=LossEstimateCalculationResponse,
)
def calculate_loss_estimate_endpoint(
    request: TradeExposureRequest,
    db: Session = Depends(get_db),
):
    """Calculate and store LGD, EAD, and Expected Loss."""
    exposure = TradeExposureInput(
        counterparty_id=request.counterparty_id,
        invoice_amount=request.invoice_amount,
        fuel_volume=request.fuel_volume,
        fuel_price=request.fuel_price,
        approved_credit_limit=request.approved_credit_limit,
        requested_credit_limit=request.requested_credit_limit,
        outstanding_receivables=request.outstanding_receivables,
        payment_tenor_days=request.payment_tenor_days,
        utilization_rate=request.utilization_rate,
        collateral_type=request.collateral_type,
        letter_of_credit_flag=request.letter_of_credit_flag,
        guarantee_flag=request.guarantee_flag,
        deposit_percentage=request.deposit_percentage,
        counterparty_type=request.counterparty_type,
        country_risk_score=request.country_risk_score,
        seniority_score=request.seniority_score,
        notes=request.notes,
    )
    try:
        loss_estimate = calculate_and_store_loss_estimate(
            db,
            exposure,
            pd_prediction_id=request.pd_prediction_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return LossEstimateCalculationResponse(
        message="LGD, EAD, and Expected Loss calculated and stored.",
        loss_estimate=_row_to_dict(loss_estimate),
    )


@router.get(
    "/counterparty/{counterparty_id}/latest-loss",
    response_model=LossEstimateResponse,
)
def get_latest_counterparty_loss(
    counterparty_id: int,
    db: Session = Depends(get_db),
):
    """Return latest LGD/EAD/Expected Loss estimate for a counterparty."""
    loss_estimate = get_latest_loss_estimate(db, counterparty_id)
    if loss_estimate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No loss estimate found for counterparty {counterparty_id}",
        )
    return LossEstimateResponse(**_row_to_dict(loss_estimate))


__all__ = ["router"]


