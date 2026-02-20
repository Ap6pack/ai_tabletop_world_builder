#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Tests for GameSessionService — session persistence and management."""
import json
import os

import pytest

from api.models.schemas import (
    Department,
    GameState,
    Inventory,
    Organization,
)
from api.services.game_session_service import GameSessionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_org():
    return Organization(
        id="org-1", name="Test Corp", description="Test",
        industry="Technology", size="medium",
        departments=[Department(
            id="d1", name="IT", description="IT",
            business_function="Tech", systems=[],
            data_classification="internal",
        )],
        threat_actors=[], security_posture="developing",
        compliance_frameworks=[],
    )


@pytest.fixture
def session_svc(tmp_path):
    """GameSessionService backed by a temp directory."""
    svc = GameSessionService()
    svc.sessions_dir = str(tmp_path / "sessions")
    os.makedirs(svc.sessions_dir, exist_ok=True)
    return svc


# ---------------------------------------------------------------------------
# create_session / get_session
# ---------------------------------------------------------------------------

class TestCreateGetSession:
    def test_create_session_returns_game_state(self, session_svc):
        gs = session_svc.create_session(
            organization=_make_org(),
            scenario_type="incident-response",
            player_role="soc-analyst",
            difficulty="intermediate",
        )
        assert isinstance(gs, GameState)
        assert gs.session_id.startswith("session_")
        assert gs.status == "in-progress"
        assert gs.player_role == "soc-analyst"

    def test_get_session_returns_saved(self, session_svc):
        gs = session_svc.create_session(
            organization=_make_org(),
            scenario_type="incident-response",
            player_role="soc-analyst",
            difficulty="intermediate",
        )
        loaded = session_svc.get_session(gs.session_id)
        assert loaded is not None
        assert loaded.session_id == gs.session_id
        assert loaded.organization.name == "Test Corp"

    def test_get_session_not_found(self, session_svc):
        result = session_svc.get_session("nonexistent-session")
        assert result is None


# ---------------------------------------------------------------------------
# Role-based inventory
# ---------------------------------------------------------------------------

class TestRoleInventory:
    @pytest.mark.parametrize("role,expected_tool", [
        ("soc-analyst", "IDS/IPS"),
        ("incident-responder", "Forensics Toolkit"),
        ("security-engineer", "Firewall Console"),
        ("ciso", "Executive Dashboard"),
    ])
    def test_role_gets_expected_tool(self, session_svc, role, expected_tool):
        gs = session_svc.create_session(
            organization=_make_org(),
            scenario_type="incident-response",
            player_role=role,
            difficulty="intermediate",
        )
        assert expected_tool in gs.inventory.tools


# ---------------------------------------------------------------------------
# list_sessions / update / end / delete
# ---------------------------------------------------------------------------

class TestSessionLifecycle:
    def test_list_sessions(self, session_svc):
        gs1 = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        # Add an event so created_at is not None for sorting
        session_svc.add_event(gs1.session_id, "detection", "Alert", "high")
        gs2 = session_svc.create_session(
            _make_org(), "threat-hunting", "ciso", "advanced",
        )
        session_svc.add_event(gs2.session_id, "detection", "Alert 2", "high")
        sessions = session_svc.list_sessions()
        assert len(sessions) == 2

    def test_list_sessions_with_status_filter(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        session_svc.end_session(gs.session_id, "completed")
        session_svc.create_session(
            _make_org(), "threat-hunting", "ciso", "advanced",
        )
        completed = session_svc.list_sessions(status_filter="completed")
        assert len(completed) == 1

    def test_update_session(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        updated = session_svc.update_session(gs.session_id, {"score": 100})
        assert updated is not None
        assert updated.score == 100

    def test_update_session_not_found(self, session_svc):
        result = session_svc.update_session("missing", {"score": 100})
        assert result is None

    def test_end_session(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        ended = session_svc.end_session(gs.session_id, "completed")
        assert ended is not None
        assert ended.status == "completed"

    def test_delete_session(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        assert session_svc.delete_session(gs.session_id) is True
        assert session_svc.get_session(gs.session_id) is None

    def test_delete_session_not_found(self, session_svc):
        with pytest.raises(FileNotFoundError):
            session_svc.delete_session("no-such-session")


# ---------------------------------------------------------------------------
# File persistence
# ---------------------------------------------------------------------------

class TestFilePersistence:
    def test_save_creates_json_file(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        filepath = os.path.join(session_svc.sessions_dir, f"{gs.session_id}.json")
        assert os.path.exists(filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert data["session_id"] == gs.session_id

    def test_round_trip_preserves_data(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        session_svc.update_score(gs.session_id, 50, "Good detection")
        loaded = session_svc.get_session(gs.session_id)
        assert loaded.score == 50


# ---------------------------------------------------------------------------
# add_event / update_inventory / complete_objective
# ---------------------------------------------------------------------------

class TestGameplayUpdates:
    def test_add_event(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        updated = session_svc.add_event(
            gs.session_id, "detection", "Malware found", "high", "system",
        )
        assert updated is not None
        assert len(updated.incident_timeline) == 1
        assert updated.time_elapsed == 1

    def test_update_inventory_add_tool(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        updated = session_svc.update_inventory(
            gs.session_id, tool_changes={"Malware Scanner": 1},
        )
        assert "Malware Scanner" in updated.inventory.tools

    def test_update_inventory_remove_tool(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        # First add, then remove
        session_svc.update_inventory(gs.session_id, tool_changes={"Temp Tool": 1})
        updated = session_svc.update_inventory(
            gs.session_id, tool_changes={"Temp Tool": -1},
        )
        assert "Temp Tool" not in updated.inventory.tools

    def test_complete_objective_success(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        updated = session_svc.complete_objective(gs.session_id, "Detect malware")
        assert "Detect malware" in updated.objectives_completed
        assert updated.score > 0

    def test_complete_objective_failure(self, session_svc):
        gs = session_svc.create_session(
            _make_org(), "incident-response", "soc-analyst", "intermediate",
        )
        updated = session_svc.complete_objective(
            gs.session_id, "Contain threat", success=False,
        )
        assert "Contain threat" in updated.objectives_failed
