#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
API endpoints for managing application settings.
"""

import contextlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import delete

from api.db import (
    ExerciseRow,
    GameSessionRow,
    GeneratedScenarioRow,
    LibraryScenarioRow,
    session_scope,
)
from api.middleware.auth import require_admin
from api.services import settings_store
from config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    """Model for updating settings."""

    # LLM Provider
    default_llm_provider: Literal["openai", "anthropic", "together", "ollama"] | None = None

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_temperature: float | None = None

    # Anthropic
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None
    anthropic_temperature: float | None = None

    # Together AI
    together_api_key: str | None = None
    together_model: str | None = None
    together_temperature: float | None = None

    # Ollama
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    ollama_temperature: float | None = None

    # Content Policy
    default_content_policy: Literal["defensive", "educational", "advanced", "unrestricted"] | None = None

    # Session Configuration
    session_timeout: int | None = None
    max_context_length: int | None = None

    # Storage
    scenarios_path: str | None = None
    data_path: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _reject_control_characters(cls, value):
        """Refuse line breaks and other control characters in any value."""
        if isinstance(value, str) and any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ValueError("control characters (including newlines) are not allowed")
        return value


class StorageStats(BaseModel):
    """Storage statistics."""

    saved_scenarios: int
    disk_usage_mb: float
    scenarios_path: str
    data_path: str


@router.get("/current")
async def get_current_settings():
    """Get current application settings."""
    return {
        "default_llm_provider": settings.default_llm_provider,
        "openai_model": settings.openai_model,
        "openai_temperature": settings.openai_temperature,
        "openai_api_key_configured": bool(settings.openai_api_key and settings.openai_api_key.strip()),
        "anthropic_model": settings.anthropic_model,
        "anthropic_temperature": settings.anthropic_temperature,
        "anthropic_api_key_configured": bool(settings.anthropic_api_key and settings.anthropic_api_key.strip()),
        "together_model": settings.together_model,
        "together_temperature": settings.together_temperature,
        "together_api_key_configured": bool(settings.together_api_key and settings.together_api_key.strip()),
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "ollama_temperature": settings.ollama_temperature,
        "default_content_policy": settings.default_content_policy,
        "session_timeout": settings.session_timeout,
        "max_context_length": settings.max_context_length,
        "scenarios_path": settings.scenarios_path,
        "data_path": settings.data_path,
    }


@router.post("/update")
async def update_settings(updates: SettingsUpdate, _admin: dict | None = Depends(require_admin)):
    """
    Update application settings.

    Changes are stored in the database, take effect immediately, survive
    restarts, and reach every API instance within a few seconds.
    """
    updates_dict = updates.model_dump(exclude_none=True)
    settings_store.save_overrides(updates_dict)

    return {
        "message": "Settings updated successfully",
        "updated_keys": list(updates_dict.keys()),
    }


@router.get("/storage/stats")
async def get_storage_stats() -> StorageStats:
    """Get storage statistics for scenarios and data."""
    scenarios_path = Path(settings.scenarios_path)
    data_path = Path(settings.data_path)

    # Count saved scenarios
    saved_scenarios = 0
    if scenarios_path.exists():
        saved_scenarios = len(list(scenarios_path.glob("*.json")))

    # Calculate disk usage
    disk_usage_bytes = 0

    for path in [scenarios_path, data_path]:
        if path.exists():
            for item in path.rglob("*"):
                if item.is_file():
                    with contextlib.suppress(OSError, PermissionError):
                        disk_usage_bytes += item.stat().st_size

    disk_usage_mb = disk_usage_bytes / (1024 * 1024)

    return StorageStats(
        saved_scenarios=saved_scenarios,
        disk_usage_mb=round(disk_usage_mb, 2),
        scenarios_path=str(scenarios_path),
        data_path=str(data_path),
    )


@router.post("/export")
async def export_config(_admin: dict | None = Depends(require_admin)):
    """Export current configuration as JSON."""
    config_data = {
        "llm_providers": {
            "default": settings.default_llm_provider,
            "openai": {
                "model": settings.openai_model,
                "temperature": settings.openai_temperature,
                "api_key_configured": bool(settings.openai_api_key),
            },
            "anthropic": {
                "model": settings.anthropic_model,
                "temperature": settings.anthropic_temperature,
                "api_key_configured": bool(settings.anthropic_api_key),
            },
            "together": {
                "model": settings.together_model,
                "temperature": settings.together_temperature,
                "api_key_configured": bool(settings.together_api_key),
            },
            "ollama": {
                "base_url": settings.ollama_base_url,
                "model": settings.ollama_model,
                "temperature": settings.ollama_temperature,
            },
        },
        "content_policy": settings.default_content_policy,
        "session": {"timeout": settings.session_timeout, "max_context_length": settings.max_context_length},
        "storage": {"scenarios_path": settings.scenarios_path, "data_path": settings.data_path},
    }

    return config_data


@router.delete("/data/clear")
async def clear_all_data(_admin: dict | None = Depends(require_admin)):
    """
    Clear all saved scenarios, game sessions, exercises, and library scenarios.

    User accounts, API keys, and webhooks are preserved.
    WARNING: This is destructive and cannot be undone!
    """
    deleted = 0
    with session_scope() as db:
        for model in (GameSessionRow, GeneratedScenarioRow, LibraryScenarioRow, ExerciseRow):
            result = db.execute(delete(model))
            deleted += result.rowcount or 0

    # Best-effort cleanup of any stray generated-scenario files from older versions.
    scenarios_path = Path(settings.scenarios_path)
    if scenarios_path.exists():
        for file in scenarios_path.glob("*.json"):
            with contextlib.suppress(OSError):
                file.unlink()

    return {"message": f"Successfully deleted {deleted} records", "deleted_records": deleted}


@router.post("/reset/defaults")
async def reset_to_defaults(_admin: dict | None = Depends(require_admin)):
    """
    Reset settings to the deployment defaults (environment variables / .env).

    Removes every setting changed through the API except stored provider API keys.
    """
    settings_store.clear_overrides(keep_secrets=True)
    return {"message": "Settings reset to defaults", "note": "API keys were preserved."}


@router.delete("/provider/{provider}/key")
async def clear_provider_key(
    provider: Literal["openai", "anthropic", "together", "ollama"],
    _admin: dict | None = Depends(require_admin),
):
    """
    Clear the API key for an LLM provider.

    Args:
        provider: Provider name (openai, anthropic, together, or ollama)

    Returns:
        Confirmation message
    """
    if provider == "ollama":
        raise HTTPException(status_code=400, detail="Ollama does not use API keys. Clear the base URL if needed.")

    key = f"{provider}_api_key"
    if not getattr(settings, key):
        raise HTTPException(status_code=404, detail=f"No API key found for {provider}")

    # Stored as an empty override so it also masks a key set in the environment.
    settings_store.save_overrides({key: ""})

    return {
        "message": f"API key for {provider} has been removed",
        "provider": provider,
        "note": "The provider will no longer be available until a new API key is added.",
    }
