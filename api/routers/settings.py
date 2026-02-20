#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
API endpoints for managing application settings.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import os
from pathlib import Path
from config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    """Model for updating settings."""
    # LLM Provider
    default_llm_provider: Optional[Literal["openai", "anthropic", "ollama"]] = None

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openai_temperature: Optional[float] = None

    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: Optional[str] = None
    anthropic_temperature: Optional[float] = None

    # Ollama
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_temperature: Optional[float] = None

    # Content Policy
    default_content_policy: Optional[Literal["defensive", "educational", "advanced", "unrestricted"]] = None

    # Session Configuration
    session_timeout: Optional[int] = None
    max_context_length: Optional[int] = None

    # Storage
    scenarios_path: Optional[str] = None
    data_path: Optional[str] = None


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
async def update_settings(updates: SettingsUpdate):
    """
    Update application settings and persist to .env file.

    Note: This updates the runtime settings and writes to .env file.
    API restart may be required for some changes to take full effect.
    """
    env_path = Path(".env")

    # Read existing .env file
    env_lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            env_lines = f.readlines()

    # Build map of existing env vars
    env_dict = {}
    for line in env_lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env_dict[key.strip()] = value.strip()

    # Update settings based on provided values
    updates_dict = updates.model_dump(exclude_none=True)

    for key, value in updates_dict.items():
        # Convert to uppercase for env var names
        env_key = key.upper()

        # Update runtime settings
        setattr(settings, key, value)

        # Update env dict
        if isinstance(value, bool):
            env_dict[env_key] = str(value).lower()
        else:
            env_dict[env_key] = str(value)

    # Write back to .env file
    with open(env_path, "w") as f:
        f.write("# Application Settings\n")
        f.write("# Updated via Settings API\n\n")

        for key, value in sorted(env_dict.items()):
            f.write(f"{key}={value}\n")

    return {
        "message": "Settings updated successfully",
        "note": "Some settings may require API restart to take full effect",
        "updated_keys": list(updates_dict.keys())
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
                    try:
                        disk_usage_bytes += item.stat().st_size
                    except (OSError, PermissionError):
                        pass

    disk_usage_mb = disk_usage_bytes / (1024 * 1024)

    return StorageStats(
        saved_scenarios=saved_scenarios,
        disk_usage_mb=round(disk_usage_mb, 2),
        scenarios_path=str(scenarios_path),
        data_path=str(data_path)
    )


@router.post("/export")
async def export_config():
    """Export current configuration as JSON."""
    config_data = {
        "llm_providers": {
            "default": settings.default_llm_provider,
            "openai": {
                "model": settings.openai_model,
                "temperature": settings.openai_temperature,
                "api_key_configured": bool(settings.openai_api_key)
            },
            "anthropic": {
                "model": settings.anthropic_model,
                "temperature": settings.anthropic_temperature,
                "api_key_configured": bool(settings.anthropic_api_key)
            },
            "ollama": {
                "base_url": settings.ollama_base_url,
                "model": settings.ollama_model,
                "temperature": settings.ollama_temperature
            }
        },
        "content_policy": settings.default_content_policy,
        "session": {
            "timeout": settings.session_timeout,
            "max_context_length": settings.max_context_length
        },
        "storage": {
            "scenarios_path": settings.scenarios_path,
            "data_path": settings.data_path
        }
    }

    return config_data


@router.delete("/data/clear")
async def clear_all_data():
    """
    Clear all saved scenarios and game data.

    WARNING: This is destructive and cannot be undone!
    """
    scenarios_path = Path(settings.scenarios_path)
    data_path = Path(settings.data_path)

    deleted_files = 0
    errors = []

    # Delete scenario files
    if scenarios_path.exists():
        for file in scenarios_path.glob("*.json"):
            try:
                file.unlink()
                deleted_files += 1
            except Exception as e:
                errors.append(f"Failed to delete {file}: {str(e)}")

    # Delete data files (sessions)
    if data_path.exists():
        sessions_dir = data_path / "sessions"
        if sessions_dir.exists():
            for file in sessions_dir.glob("*.json"):
                try:
                    file.unlink()
                    deleted_files += 1
                except Exception as e:
                    errors.append(f"Failed to delete {file}: {str(e)}")

    if errors:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Deleted {deleted_files} files with {len(errors)} errors",
                "errors": errors
            }
        )

    return {
        "message": f"Successfully deleted {deleted_files} files",
        "deleted_files": deleted_files
    }


@router.post("/reset/defaults")
async def reset_to_defaults():
    """
    Reset all settings to default values.

    This will update the .env file with default values.
    """
    defaults = {
        "DEFAULT_LLM_PROVIDER": "openai",
        "OPENAI_MODEL": "gpt-4-turbo-preview",
        "OPENAI_TEMPERATURE": "0.7",
        "ANTHROPIC_MODEL": "claude-3-5-sonnet-20241022",
        "ANTHROPIC_TEMPERATURE": "0.7",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3",
        "OLLAMA_TEMPERATURE": "0.7",
        "DEFAULT_CONTENT_POLICY": "educational",
        "SESSION_TIMEOUT": "3600",
        "MAX_CONTEXT_LENGTH": "4000",
        "SCENARIOS_PATH": "./scenarios/generated",
        "DATA_PATH": "./data"
    }

    # Keep API keys from current .env
    env_path = Path(".env")
    existing_keys = {}

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    if "API_KEY" in key:
                        existing_keys[key] = value.strip()

    # Merge defaults with existing API keys
    defaults.update(existing_keys)

    # Write to .env
    with open(env_path, "w") as f:
        f.write("# Application Settings\n")
        f.write("# Reset to defaults\n\n")

        for key, value in sorted(defaults.items()):
            f.write(f"{key}={value}\n")

    # Update runtime settings
    settings.default_llm_provider = "openai"
    settings.openai_model = "gpt-4-turbo-preview"
    settings.openai_temperature = 0.7
    settings.anthropic_model = "claude-3-5-sonnet-20241022"
    settings.anthropic_temperature = 0.7
    settings.ollama_base_url = "http://localhost:11434"
    settings.ollama_model = "llama3"
    settings.ollama_temperature = 0.7
    settings.default_content_policy = "educational"
    settings.session_timeout = 3600
    settings.max_context_length = 4000
    settings.scenarios_path = "./scenarios/generated"
    settings.data_path = "./data"

    return {
        "message": "Settings reset to defaults",
        "note": "API keys were preserved. API restart recommended."
    }


@router.delete("/provider/{provider}/key")
async def clear_provider_key(provider: Literal["openai", "anthropic", "ollama"]):
    """
    Clear API key for a specific LLM provider.

    This removes the API key from the .env file and runtime configuration.

    Args:
        provider: Provider name (openai, anthropic, or ollama)

    Returns:
        Confirmation message
    """
    # Map provider to env var key
    key_mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "ollama": None  # Ollama doesn't use API keys
    }

    if provider == "ollama":
        raise HTTPException(
            status_code=400,
            detail="Ollama does not use API keys. Clear the base URL if needed."
        )

    env_key = key_mapping[provider]
    env_path = Path(".env")

    if not env_path.exists():
        raise HTTPException(status_code=404, detail=".env file not found")

    # Read existing .env
    env_lines = []
    with open(env_path, "r") as f:
        env_lines = f.readlines()

    # Remove the API key line
    new_lines = []
    key_found = False

    for line in env_lines:
        stripped = line.strip()
        # Keep line if it's not the API key we're removing
        if stripped.startswith(env_key + "="):
            key_found = True
            continue  # Skip this line (removes it)
        new_lines.append(line)

    if not key_found:
        raise HTTPException(
            status_code=404,
            detail=f"No API key found for {provider}"
        )

    # Write updated .env
    with open(env_path, "w") as f:
        f.writelines(new_lines)

    # Clear from runtime settings
    if provider == "openai":
        settings.openai_api_key = None
    elif provider == "anthropic":
        settings.anthropic_api_key = None

    return {
        "message": f"API key for {provider} has been removed",
        "provider": provider,
        "note": "The provider will no longer be available until a new API key is added."
    }
