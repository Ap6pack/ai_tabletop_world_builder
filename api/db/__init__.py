#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Database engine and session management.

Exposes a synchronous SQLAlchemy engine + session factory backed by the
``DATABASE_URL`` setting (SQLite by default, Postgres-ready). The engine is
rebindable via :func:`configure_engine` so tests can point at a throwaway
database.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings

from .models import (
    ApiKeyRow,
    Base,
    ExerciseRow,
    GameSessionRow,
    GeneratedScenarioRow,
    LibraryScenarioRow,
    UserRow,
    WebhookDeliveryRow,
    WebhookRow,
)

__all__ = [
    "Base",
    "UserRow",
    "GameSessionRow",
    "ExerciseRow",
    "ApiKeyRow",
    "WebhookRow",
    "WebhookDeliveryRow",
    "GeneratedScenarioRow",
    "LibraryScenarioRow",
    "configure_engine",
    "get_engine",
    "init_db",
    "session_scope",
]

engine: Engine
SessionLocal: sessionmaker[Session]


def _make_engine(url: str) -> Engine:
    """Create an engine with SQLite-friendly defaults."""
    connect_args = {}
    if url.startswith("sqlite"):
        # Allow use across FastAPI's threadpool; concurrency tuned below.
        connect_args["check_same_thread"] = False
        # Ensure the parent directory exists for file-based SQLite.
        path = url.split("sqlite:///", 1)[-1]
        if path and path not in (":memory:",) and not path.startswith(":"):
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)

    new_engine = create_engine(url, connect_args=connect_args, future=True)

    if url.startswith("sqlite"):

        @event.listens_for(new_engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - trivial
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return new_engine


def configure_engine(url: str) -> Engine:
    """(Re)bind the global engine and session factory to ``url``.

    Disposes any existing engine. Used at import time and by tests.
    """
    global engine, SessionLocal
    if "engine" in globals() and engine is not None:
        engine.dispose()
    engine = _make_engine(url)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return engine


def get_engine() -> Engine:
    """Return the current engine."""
    return engine


def init_db() -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session scope: commit on success, rollback on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Initialize the default engine/session factory at import time.
configure_engine(settings.database_url)
