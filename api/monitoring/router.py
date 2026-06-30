"""FastAPI routes for early warning monitoring alerts."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db.session import get_db
from api.monitoring.schemas import AlertAnalysisRequest, AlertListResponse, AlertResponse
from api.monitoring.service import generate_alerts_from_database, generate_alerts_from_records, summarize_alerts


router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/alerts/latest", response_model=AlertListResponse)
def get_latest_alerts(db: Session = Depends(get_db)):
    """Generate explainable alerts from the latest stored backend records."""
    alerts, warnings = generate_alerts_from_database(db)
    counts = summarize_alerts(alerts)
    return AlertListResponse(
        message="Monitoring alerts generated from stored V2 risk outputs.",
        alerts=[AlertResponse(**alert.to_dict()) for alert in alerts],
        warnings=warnings,
        **counts,
    )

@router.post("/alerts/analyze", response_model=AlertListResponse)
def analyze_supplied_alert_sources(request: AlertAnalysisRequest):
    """Generate explainable alerts from supplied monitoring source records."""
    alerts, warnings = generate_alerts_from_records(**request.model_dump())
    counts = summarize_alerts(alerts)
    return AlertListResponse(
        message="Monitoring alerts generated from supplied V2 risk records.",
        alerts=[AlertResponse(**alert.to_dict()) for alert in alerts],
        warnings=warnings,
        **counts,
    )

__all__ = ["router"]

