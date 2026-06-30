"""FastAPI routes for Phase 3 financial ratio calculation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.financials.service import (
    calculate_and_store_ratios,
    create_manual_financial_metrics,
    create_manual_financial_metrics_batch,
    get_financial_metrics_history,
    get_financial_trend_features,
    get_latest_financial_metrics_for_counterparty,
    get_latest_ratios_for_counterparty,
    mark_financial_metrics_as_latest,
)
from api.financials.schemas import (
    FinancialRatioCalculationResponse,
    FinancialRatiosResponse,
    FinancialMetricsHistoryResponse,
    FinancialTrendFeaturesResponse,
    MarkLatestFinancialMetricsResponse,
    ManualFinancialMetricsBatchCreate,
    ManualFinancialMetricsBatchCreateResponse,
    ManualFinancialMetricsCreate,
    ManualFinancialMetricsCreateResponse,
    ManualFinancialMetricsResponse,
)
from api.db.session import get_db
from api.db.models import FinancialRatios


router = APIRouter(prefix="/api/v1/financial-analysis", tags=["financial-analysis"])


@router.post(
    "/metrics/manual",
    response_model=ManualFinancialMetricsCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_financial_metrics_endpoint(
    payload: ManualFinancialMetricsCreate,
    db: Session = Depends(get_db),
):
    """Store analyst-entered financial statement metrics for a counterparty."""
    try:
        metrics = create_manual_financial_metrics(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ManualFinancialMetricsCreateResponse(
        message="Manual financial metrics captured.",
        metrics=ManualFinancialMetricsResponse.model_validate(metrics),
    )


@router.post(
    "/metrics/manual/batch",
    response_model=ManualFinancialMetricsBatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_financial_metrics_batch_endpoint(
    payload: ManualFinancialMetricsBatchCreate,
    db: Session = Depends(get_db),
):
    """Store multiple analyst-entered financial periods for one counterparty."""
    try:
        metrics, latest = create_manual_financial_metrics_batch(db, payload)
        for item in metrics:
            calculate_and_store_ratios(db, item.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ManualFinancialMetricsBatchCreateResponse(
        message="Manual financial history captured.",
        metrics=[ManualFinancialMetricsResponse.model_validate(item) for item in metrics],
        latest_metrics=ManualFinancialMetricsResponse.model_validate(latest),
    )


@router.get(
    "/counterparty/{counterparty_id}/metrics-history",
    response_model=FinancialMetricsHistoryResponse,
)
def get_counterparty_financial_metrics_history(
    counterparty_id: int,
    db: Session = Depends(get_db),
):
    """Fetch all stored financial periods for a counterparty."""
    periods = get_financial_metrics_history(db, counterparty_id)
    latest = get_latest_financial_metrics_for_counterparty(db, counterparty_id)
    return FinancialMetricsHistoryResponse(
        message="Financial metrics history loaded.",
        periods=[ManualFinancialMetricsResponse.model_validate(item) for item in periods],
        latest_metrics=ManualFinancialMetricsResponse.model_validate(latest) if latest else None,
    )


@router.post(
    "/metrics/{financial_metrics_id}/mark-latest",
    response_model=MarkLatestFinancialMetricsResponse,
)
def mark_financial_metrics_latest_endpoint(
    financial_metrics_id: int,
    db: Session = Depends(get_db),
):
    """Mark one financial metrics record as the current latest snapshot."""
    try:
        latest = mark_financial_metrics_as_latest(db, financial_metrics_id)
        calculate_and_store_ratios(db, latest.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return MarkLatestFinancialMetricsResponse(
        message="Latest financial snapshot updated.",
        latest_metrics=ManualFinancialMetricsResponse.model_validate(latest),
    )


@router.get(
    "/counterparty/{counterparty_id}/trend-features",
    response_model=FinancialTrendFeaturesResponse,
)
def get_counterparty_financial_trend_features(
    counterparty_id: int,
    db: Session = Depends(get_db),
):
    """Calculate trend features from stored financial periods."""
    return FinancialTrendFeaturesResponse(**get_financial_trend_features(db, counterparty_id))


@router.post(
    "/ratios/calculate/{financial_metrics_id}",
    response_model=FinancialRatioCalculationResponse,
)
def calculate_financial_ratios_endpoint(
    financial_metrics_id: int,
    db: Session = Depends(get_db),
):
    """Calculate and store ratios for a Phase 2 extracted financials record."""
    try:
        ratio_record = calculate_and_store_ratios(db, financial_metrics_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return FinancialRatioCalculationResponse(
        message="Financial ratios calculated and stored.",
        ratios=FinancialRatiosResponse.model_validate(ratio_record),
    )


@router.get(
    "/ratios/{ratio_id}",
    response_model=FinancialRatiosResponse,
)
def get_financial_ratios(
    ratio_id: int,
    db: Session = Depends(get_db),
):
    """Fetch one stored financial ratio record."""
    ratio_record = db.query(FinancialRatios).filter(FinancialRatios.id == ratio_id).first()
    if ratio_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Financial ratios record {ratio_id} not found",
        )
    return FinancialRatiosResponse.model_validate(ratio_record)


@router.get(
    "/counterparty/{counterparty_id}/latest-ratios",
    response_model=FinancialRatiosResponse,
)
def get_latest_counterparty_ratios(
    counterparty_id: int,
    db: Session = Depends(get_db),
):
    """Fetch the latest stored ratio set for a counterparty."""
    ratio_record = get_latest_ratios_for_counterparty(db, counterparty_id)
    if ratio_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No financial ratios found for counterparty {counterparty_id}",
        )
    return FinancialRatiosResponse.model_validate(ratio_record)


__all__ = ["router"]

