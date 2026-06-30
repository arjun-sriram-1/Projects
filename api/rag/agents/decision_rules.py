"""Compatibility wrapper over the canonical stored credit recommendation."""

import pandas as pd

from api.db.session import SessionLocal
from api.credit_decision.service import get_latest_credit_recommendation_by_name


def get_counterparty(company_name):
    """Return latest stored recommendation as a dataframe for legacy callers."""
    with SessionLocal() as db:
        row = get_latest_credit_recommendation_by_name(db, company_name)
        if row is None:
            return pd.DataFrame()
        data = dict(row)
        data["company_name"] = data.get("counterparty_name")
        data["pd"] = data.get("probability_of_default")
        data["lgd"] = data.get("loss_given_default")
        data["exposure"] = data.get("exposure_at_default")
        data["expected_loss"] = data.get("expected_loss")
        data["risk_segment"] = data.get("risk_grade")
        data["credit_days"] = data.get("recommended_tenor_days")
        data["security"] = data.get("recommended_security")
        return pd.DataFrame([data])


def make_decision(company_name):
    """Return the latest formal decision; never recompute independent AI rules."""
    with SessionLocal() as db:
        row = get_latest_credit_recommendation_by_name(db, company_name)
        if row is None:
            return {
                "decision": "UNKNOWN",
                "reason": "No stored credit recommendation found. Run the credit decision engine first.",
                "reasons": ["No stored credit recommendation found."],
            }
        return {
            "decision": row["approval_status"],
            "reason": "; ".join(row["key_risk_drivers"] or []),
            "reasons": row["key_risk_drivers"] or [],
            "recommended_credit_limit": float(row["recommended_credit_limit"]),
            "recommended_tenor_days": int(row["recommended_tenor_days"]),
            "recommended_security": row["recommended_security"],
            "risk_grade": row["risk_grade"],
            "run_id": row["run_id"],
        }


