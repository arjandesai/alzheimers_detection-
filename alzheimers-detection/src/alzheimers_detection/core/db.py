"""Database engine and session management.

Sync SQLAlchemy (not async) by design: this project's hot path (ASR +
signal processing) is CPU-bound, not I/O-bound, so async DB access buys
little here while adding real complexity (async session lifecycles, async
test fixtures). If a future milestone adds genuinely I/O-heavy concurrent
workloads, revisit this.

Schema management is via Alembic migrations (see migrations/), not
`Base.metadata.create_all()`, for any environment that matters -- that
function is provided only as a dev-convenience shortcut (see `init_db`)
and is never called automatically in production (ALZDX_ENVIRONMENT=production).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from alzheimers_detection.core.config import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models (core/models.py)."""


def _make_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # Needed for SQLite when the same connection may be used across
        # threads, which happens with TestClient in the test suite.
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, echo=settings.db_echo, connect_args=connect_args)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, guarantees it's closed after
    the request, and rolls back on unhandled exceptions so a failed
    request never leaves a half-committed transaction open."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Dev-only convenience: create tables directly from ORM metadata
    without going through Alembic. Use for quick local iteration or in
    tests with a throwaway SQLite DB. Never call this in production --
    use `alembic upgrade head` instead, so schema history stays tracked
    and reviewable.
    """
    from alzheimers_detection.core import models  # noqa: F401 - populate metadata

    Base.metadata.create_all(bind=engine)
