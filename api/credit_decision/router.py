"""FastAPI routes for Phase 8 credit recommendations and grounded memos."""

from datetime import date, datetime
from decimal import Decimal
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.credit_decision.analysis import (
    CreditProfileInput,
    calculate_credit_profile_score,
    compare_counterparties,
    optimize_payment_terms,
)
from api.credit_decision.schemas import (
    CounterpartyComparisonRequest,
    CounterpartyComparisonResponse,
    CreditProfileScoreRequest,
    CreditProfileScoreResponse,
    CreditRecommendationCalculationResponse,
    CreditRecommendationResponse,
    GroundedMemoResponse,
    PaymentTermsOptimizerRequest,
    PaymentTermsOptimizerResponse,
)
from api.db.session import get_db
from api.credit_decision.service import (
    build_grounded_credit_memo,
    calculate_and_store_credit_recommendation,
    get_latest_credit_recommendation,
)


router = APIRouter(prefix="/api/v1/credit-decision", tags=["credit-decision"])

JSON_FIELDS = {
    "key_risk_drivers",
    "mitigating_factors",
    "model_assumptions",
    "input_data_reference",
    "warnings",
}

def _profile_from_request(request: CreditProfileScoreRequest) -> CreditProfileInput:
    return CreditProfileInput(**request.model_dump())


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
    "/counterparty/{counterparty_id}/recommend",
    response_model=CreditRecommendationCalculationResponse,
)
def calculate_recommendation_endpoint(
    counterparty_id: int,
    db: Session = Depends(get_db),
):
    """Calculate and store the formal rules-based credit recommendation."""
    try:
        row = calculate_and_store_credit_recommendation(db, counterparty_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CreditRecommendationCalculationResponse(
        message="Credit recommendation calculated and stored.",
        recommendation=_row_to_dict(row),
    )


@router.get(
    "/counterparty/{counterparty_id}/latest",
    response_model=CreditRecommendationResponse,
)
def get_latest_recommendation_endpoint(
    counterparty_id: int,
    db: Session = Depends(get_db),
):
    """Return the latest stored formal recommendation for a counterparty."""
    row = get_latest_credit_recommendation(db, counterparty_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credit recommendation found for counterparty {counterparty_id}",
        )
    return CreditRecommendationResponse(**_row_to_dict(row))


@router.post("/memo/{company_name}", response_model=GroundedMemoResponse)
def generate_grounded_memo_endpoint(
    company_name: str,
    db: Session = Depends(get_db),
):
    """Generate a memo from stored recommendation/model outputs only."""
    memo = build_grounded_credit_memo(db, company_name, persist=True)
    return GroundedMemoResponse(company_name=company_name, memo=memo)

@router.post("/scorecard/calculate", response_model=CreditProfileScoreResponse)
def calculate_scorecard_endpoint(request: CreditProfileScoreRequest):
    """Calculate first-pass weighted scorecard and risk segment."""
    result = calculate_credit_profile_score(_profile_from_request(request))
    return CreditProfileScoreResponse(**result.to_dict())


@router.post("/payment-terms/optimize", response_model=PaymentTermsOptimizerResponse)
def optimize_payment_terms_endpoint(request: PaymentTermsOptimizerRequest):
    """Compare expected loss across standard payment tenor options."""
    result = optimize_payment_terms(_profile_from_request(request.profile), request.tenor_options)
    return PaymentTermsOptimizerResponse(**result.to_dict())


@router.post("/counterparties/compare", response_model=CounterpartyComparisonResponse)
def compare_counterparties_endpoint(request: CounterpartyComparisonRequest):
    """Run formal deterministic side-by-side counterparty comparison."""
    try:
        result = compare_counterparties([_profile_from_request(item) for item in request.counterparties])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CounterpartyComparisonResponse(**result.to_dict())

__all__ = ["router"]





