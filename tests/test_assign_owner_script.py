#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/assign_owner.py."""

import asyncio
import importlib.util
import sys
from pathlib import Path

from api.middleware.auth import auth_service
from api.services.game_session_service import GameSessionService
from api.services.scenario_orchestrator import ScenarioOrchestrator

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "assign_owner.py"


def _run(monkeypatch, *args) -> int:
    spec = importlib.util.spec_from_file_location("assign_owner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", ["assign_owner.py", *args])
    return module.main()


def test_assigns_unowned_records(monkeypatch, sample_organization):
    user = auth_service.register("heir", "heir@example.com", "password123")
    asyncio.run(ScenarioOrchestrator().save_scenario(sample_organization, "old.json"))
    session = GameSessionService().create_session(sample_organization, "incident-response", "ciso", "beginner")

    assert _run(monkeypatch, "heir", "--dry-run") == 0
    assert ScenarioOrchestrator().get_scenario_owner("old.json") is None

    assert _run(monkeypatch, "heir") == 0
    assert ScenarioOrchestrator().get_scenario_owner("old.json") == user["id"]
    assert GameSessionService().get_session(session.session_id).owner_id == user["id"]
    assert GameSessionService().list_sessions(owner_id=user["id"])


def test_unknown_user(monkeypatch):
    assert _run(monkeypatch, "ghost") == 1
