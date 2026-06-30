"""Database session layer for FastAPI routes, services, and scripts."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.core.config import settings


engine = create_engine(
    settings.require_database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    """Return True when the configured database accepts a connection."""
    try:
        with engine.connect():
            return True
    except Exception:
        return False


__all__ = ["engine", "SessionLocal", "get_db", "test_connection"]

