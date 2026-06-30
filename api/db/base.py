"""SQLAlchemy declarative base shared by all V2 ORM models."""

from sqlalchemy.orm import declarative_base


Base = declarative_base()


__all__ = ["Base"]

