"""Credit committee explanation helpers backed by stored recommendations only."""

from api.rag.agents.decision_rules import make_decision


def evaluate_credit_request(company_name, requested_exposure=None, tenor_days=None):
    """Return the stored formal recommendation; never recompute AI decisions."""
    decision = make_decision(company_name)
    if decision["decision"] == "UNKNOWN":
        return decision

    return {
        **decision,
        "requested_exposure": requested_exposure,
        "tenor_days": tenor_days,
        "source": "latest stored credit_recommendations record",
        "note": "RAG explains the stored recommendation and does not create an independent credit decision.",
    }
