"""Grounded credit memo agent.

The AI layer explains stored model outputs. It does not invent credit numbers or
make an independent recommendation.
"""

from api.db.session import SessionLocal
from api.credit_decision.service import build_grounded_credit_memo


def generate_credit_memo(company_name):
    """Generate a memo using only stored credit recommendation/model outputs."""
    with SessionLocal() as db:
        return build_grounded_credit_memo(db, company_name, persist=True)



