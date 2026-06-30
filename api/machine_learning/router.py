"""FastAPI routes for Phase 5 probability of default estimation."""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import date, datetime
from decimal import Decimal
import json
from sqlalchemy.orm import Session

from api.machine_learning.schemas import (
    PDCalculationResponse,
    PDCalculateRequest,
    PDPredictionResponse,
)
from api.db.session import get_db
from api.machine_learning.pd_service import (
    calculate_and_store_pd,
    get_latest_pd_prediction,
)


router = APIRouter(prefix="/api/v1/credit-risk", tags=["credit-risk"])

JSON_FIELDS = {"feature_contributions", "model_assumptions", "input_data_reference", "warnings"}


def _row_to_dict(row):
    if row is None:
        return None
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
    "/pd/calculate/{financial_metrics_id}",
    response_model=PDCalculationResponse,
)
def calculate_pd_endpoint(
    financial_metrics_id: int,
    request: PDCalculateRequest = PDCalculateRequest(),
    db: Session = Depends(get_db),
):
    """Calculate and store structural/ML probability of default."""
    try:
        prediction = calculate_and_store_pd(
            db,
            financial_metrics_id=financial_metrics_id,
            time_horizon_years=request.time_horizon_years,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return PDCalculationResponse(
        message="Probability of default calculated and stored.",
        prediction=_row_to_dict(prediction),
    )


@router.get(
    "/counterparty/{counterparty_id}/latest-pd",
    response_model=PDPredictionResponse,
)
def get_latest_counterparty_pd(
    counterparty_id: int,
    db: Session = Depends(get_db),
):
    """Return latest stored PD prediction for a counterparty."""
    prediction = get_latest_pd_prediction(db, counterparty_id)
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No PD prediction found for counterparty {counterparty_id}",
        )
    return PDPredictionResponse(**_row_to_dict(prediction))


__all__ = ["router"]

