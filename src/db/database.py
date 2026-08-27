"""Shared database engine/session setup (requirement N7).

One engine, one Base, imported by every stage of the pipeline so
Connect/Parse/Model/Estimate/Deliver all read and write the same schema
instead of each stage inventing its own storage.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import get_settings


class Base(DeclarativeBase):
    """Shared declarative base - every model in src/db/models.py inherits this."""


_settings = get_settings()

# check_same_thread=False is only needed for SQLite (single dev DB file);
# harmless to pass for other engines is NOT true in general, so gate it.
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(_settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create all tables that don't exist yet.

    Fine for local dev / early Phase 1. Once the schema stabilises the team
    should move to Alembic migrations rather than relying on create_all, so
    changes to production data aren't destructive.
    """
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """Context-managed session: `with get_session() as session: ...`."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
