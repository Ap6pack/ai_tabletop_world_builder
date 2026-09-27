#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Database-backed store for settings edited through the Settings API.

Environment variables (and ``.env``) provide the baseline configuration; values
changed at runtime are stored in the ``app_settings`` table and layered on top.
Storing them in the database (instead of rewriting ``.env``) means changes
survive container restarts and are shared by every API instance: each instance
re-reads the overrides at most every ``REFRESH_SECONDS``.
"""

import threading
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select

from api.db import AppSettingRow, session_scope
from config.settings import settings

# Settings that may be changed at runtime through the API.
EDITABLE_KEYS = (
    "default_llm_provider",
    "openai_api_key",
    "openai_model",
    "openai_temperature",
    "anthropic_api_key",
    "anthropic_model",
    "anthropic_temperature",
    "together_api_key",
    "together_model",
    "together_temperature",
    "ollama_base_url",
    "ollama_model",
    "ollama_temperature",
    "default_content_policy",
    "session_timeout",
    "max_context_length",
    "scenarios_path",
    "data_path",
)
SECRET_KEYS = frozenset(k for k in EDITABLE_KEYS if k.endswith("_api_key"))

REFRESH_SECONDS = 10.0

# Environment/.env values captured at import, restored when an override is removed.
_baseline: dict[str, Any] = {key: getattr(settings, key) for key in EDITABLE_KEYS}
_lock = threading.Lock()
_last_refresh = 0.0
# Keys currently overridden in memory; only these are ever touched on refresh.
_applied: set[str] = set()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def load_overrides() -> dict[str, Any]:
    """Return every stored override."""
    with session_scope() as db:
        return {row.key: row.value for row in db.scalars(select(AppSettingRow)).all() if row.key in EDITABLE_KEYS}


def apply_overrides(force: bool = False) -> None:
    """Layer stored overrides onto the runtime settings (rate-limited unless forced)."""
    global _last_refresh, _applied
    with _lock:
        if not force and time.monotonic() - _last_refresh < REFRESH_SECONDS:
            return
        overrides = load_overrides()
        for key, value in overrides.items():
            setattr(settings, key, value)
        for key in _applied - overrides.keys():
            setattr(settings, key, _baseline[key])
        _applied = set(overrides)
        _last_refresh = time.monotonic()


def save_overrides(values: dict[str, Any]) -> None:
    """Store overrides and apply them immediately."""
    unknown = set(values) - set(EDITABLE_KEYS)
    if unknown:
        raise ValueError(f"Settings are not editable: {sorted(unknown)}")
    with session_scope() as db:
        for key, value in values.items():
            row = db.get(AppSettingRow, key)
            if row is None:
                db.add(AppSettingRow(key=key, value=value, updated_at=_now()))
            else:
                row.value = value
                row.updated_at = _now()
    apply_overrides(force=True)


def clear_overrides(keep_secrets: bool = True) -> None:
    """Remove overrides (optionally keeping stored API keys) and re-apply."""
    with session_scope() as db:
        stmt = delete(AppSettingRow)
        if keep_secrets:
            stmt = stmt.where(AppSettingRow.key.not_in(SECRET_KEYS))
        db.execute(stmt)
    apply_overrides(force=True)


def reset_runtime() -> None:
    """Restore the environment baseline in memory and force a re-read (used by tests)."""
    global _last_refresh, _applied
    with _lock:
        for key in _applied:
            setattr(settings, key, _baseline[key])
        _applied = set()
        _last_refresh = 0.0
