"""Document and counterparty workflow helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from api.db.models import CounterpartyMaster


def list_counterparties(
    db: Session,
    search: str | None = None,
    limit: int = 50,
) -> list[CounterpartyMaster]:
    """Return counterparties for selector/search workflows."""
    query = db.query(CounterpartyMaster)
    if search:
        query = query.filter(CounterpartyMaster.counterparty_name.ilike(f"%{search}%"))
    return (
        query.order_by(CounterpartyMaster.counterparty_name.asc())
        .limit(limit)
        .all()
    )
