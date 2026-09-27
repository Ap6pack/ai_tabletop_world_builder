#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Settings API and its database-backed override store."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.db import AppSettingRow, session_scope
from api.services import settings_store
from config.settings import settings


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def test_update_persists_to_database_not_env(client):
    env = Path(".env")
    before = env.read_bytes() if env.exists() else None
    resp = client.post("/settings/update", json={"openai_model": "gpt-test", "session_timeout": 99})
    assert resp.status_code == 200
    assert sorted(resp.json()["updated_keys"]) == ["openai_model", "session_timeout"]

    assert settings.openai_model == "gpt-test"
    assert settings.session_timeout == 99
    assert settings_store.load_overrides() == {"openai_model": "gpt-test", "session_timeout": 99}
    assert (env.read_bytes() if env.exists() else None) == before


def test_current_settings_reflect_update(client):
    client.post("/settings/update", json={"anthropic_model": "claude-test"})
    assert client.get("/settings/current").json()["anthropic_model"] == "claude-test"


@pytest.mark.parametrize("value", ["gpt\nREQUIRE_AUTH=false", "gpt\rX=1", "a\x00b"])
def test_update_rejects_control_characters(client, value):
    resp = client.post("/settings/update", json={"openai_model": value})
    assert resp.status_code == 422
    assert settings_store.load_overrides() == {}


def test_overrides_survive_restart():
    """A fresh process (simulated by resetting runtime state) re-applies stored overrides."""
    settings_store.save_overrides({"ollama_model": "llama-test"})
    settings_store.reset_runtime()
    assert settings.ollama_model != "llama-test"
    settings_store.apply_overrides(force=True)
    assert settings.ollama_model == "llama-test"


def test_change_from_another_instance_is_picked_up():
    with session_scope() as db:
        db.add(AppSettingRow(key="max_context_length", value=1234, updated_at="now"))
    settings_store.apply_overrides(force=True)
    assert settings.max_context_length == 1234

    with session_scope() as db:
        db.delete(db.get(AppSettingRow, "max_context_length"))
    settings_store.apply_overrides(force=True)
    assert settings.max_context_length != 1234


def test_save_rejects_unknown_keys():
    with pytest.raises(ValueError, match="not editable"):
        settings_store.save_overrides({"jwt_secret_key": "nope"})


def test_reset_defaults_keeps_api_keys(client):
    client.post("/settings/update", json={"openai_model": "gpt-test", "openai_api_key": "sk-stored"})
    resp = client.post("/settings/reset/defaults")
    assert resp.status_code == 200
    assert settings_store.load_overrides() == {"openai_api_key": "sk-stored"}
    assert settings.openai_model != "gpt-test"
    assert settings.openai_api_key == "sk-stored"


def test_clear_provider_key(client):
    client.post("/settings/update", json={"together_api_key": "tk-123"})
    resp = client.delete("/settings/provider/together/key")
    assert resp.status_code == 200
    assert settings.together_api_key == ""
    assert client.delete("/settings/provider/together/key").status_code == 404
    assert client.delete("/settings/provider/ollama/key").status_code == 400
