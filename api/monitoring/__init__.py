"""Early warning and alert monitoring package."""

from api.monitoring.service import RiskAlert, generate_alerts_from_records

__all__ = ["RiskAlert", "generate_alerts_from_records"]
