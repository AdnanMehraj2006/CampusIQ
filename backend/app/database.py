"""Database engine, session factory and declarative base.

The backend is database-agnostic: SQLite is used for zero-config local
development and PostgreSQL for Docker/production. The URL is selected purely
from ``DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

connect_args: dict = {}
if settings.sqlite_in_use:
    # SQLite connections cannot be shared across threads by default; FastAPI
    # uses a threadpool, so we relax this constraint.
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_sync() -> Session:
    """Return a session for use outside the request lifecycle (services/seed)."""
    return SessionLocal()
