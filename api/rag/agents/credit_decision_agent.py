"""Credit decision explanation agent backed by stored recommendations only."""

from api.rag.agents.decision_rules import make_decision
from api.rag.utils.company_extractor import extract_company


def run_credit_decision_agent(question):
    company = extract_company(question)
    if not company:
        return "Please specify a counterparty name with a stored credit recommendation."

    decision = make_decision(company)
    if decision["decision"] == "UNKNOWN":
        return decision["reason"]

    reasons = decision.get("reasons") or []
    reason_text = "\n".join(f"- {reason}" for reason in reasons) if reasons else "- No stored risk drivers."

    return f"""Stored Credit Decision for {company}

Approval Status: {decision["decision"]}
Risk Grade: {decision["risk_grade"]}
Recommended Credit Limit: {decision["recommended_credit_limit"]:,.2f}
Recommended Tenor: {decision["recommended_tenor_days"]} days
Recommended Security: {decision["recommended_security"]}

Stored Risk Drivers:
{reason_text}

Recommendation Run ID: {decision["run_id"]}

This answer is based only on the latest stored credit_recommendations record."""



