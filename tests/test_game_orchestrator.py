#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Tests for GameOrchestrator — game session coordination."""

import os
from unittest.mock import AsyncMock

import pytest

from api.models.schemas import (
    Department,
    GameResponse,
    Organization,
    System,
    ThreatActor,
)
from api.services.game_orchestrator import GameOrchestrator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_system():
    return System(
        id="sys-1",
        name="Web Server",
        description="Primary web server",
        type="server",
        os="Linux",
        services=["nginx"],
        criticality="high",
    )


def _make_org():
    return Organization(
        id="org-1",
        name="Test Corp",
        description="Test",
        industry="Technology",
        size="medium",
        departments=[
            Department(
                id="d1",
                name="IT",
                description="IT",
                business_function="Tech",
                systems=[_make_system()],
                data_classification="internal",
            )
        ],
        threat_actors=[
            ThreatActor(
                id="ta-1",
                name="TestActor",
                description="Test threat",
                motivation="Financial",
                sophistication="organized-crime",
                attack_techniques=["T1566"],
            )
        ],
        security_posture="developing",
        compliance_frameworks=[],
    )


@pytest.fixture
def orch(tmp_path):
    """GameOrchestrator with session service pointed at temp dir.

    The autouse ``_no_real_llm`` fixture (see conftest) stubs the provider
    factory, so the orchestrator constructs without an API key or network.
    """
    go = GameOrchestrator()
    go.session_service.sessions_dir = str(tmp_path / "sessions")
    os.makedirs(go.session_service.sessions_dir, exist_ok=True)
    return go


# ---------------------------------------------------------------------------
# start_new_game
# ---------------------------------------------------------------------------


class TestStartNewGame:
    @pytest.mark.asyncio
    async def test_start_creates_session(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="The alert fires...")

        response = await orch.start_new_game(
            organization=_make_org(),
            scenario_type="incident-response",
            player_role="soc-analyst",
            difficulty="intermediate",
        )
        assert isinstance(response, GameResponse)
        assert response.narrative == "The alert fires..."
        assert response.game_state is not None
        assert response.game_state.status == "in-progress"

    @pytest.mark.asyncio
    async def test_start_generates_objectives(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Begin!")

        response = await orch.start_new_game(
            organization=_make_org(),
            player_role="incident-responder",
            difficulty="advanced",
        )
        # ObjectiveGenerator should produce at least 1 objective
        assert len(response.game_state.objectives) >= 1

    @pytest.mark.asyncio
    async def test_start_initializes_system_states(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Begin!")

        response = await orch.start_new_game(
            organization=_make_org(),
        )
        assert "sys-1" in response.game_state.system_states

    @pytest.mark.asyncio
    async def test_start_initializes_threat_states(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Begin!")

        response = await orch.start_new_game(
            organization=_make_org(),
        )
        assert "ta-1" in response.game_state.threat_states


# ---------------------------------------------------------------------------
# process_player_action
# ---------------------------------------------------------------------------


class TestProcessPlayerAction:
    @pytest.mark.asyncio
    async def test_process_action_basic(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Start")
        orch.game_master.process_action = AsyncMock(
            return_value={
                "narrative": "You investigate the logs...",
                "new_events": [],
                "inventory_changes": {},
                "score_change": {"points": 10, "reason": "Good investigation"},
                "hints": ["Check the firewall"],
            }
        )

        response = await orch.start_new_game(organization=_make_org())
        sid = response.game_state.session_id

        action_response = await orch.process_player_action(sid, "Check SIEM logs")
        assert isinstance(action_response, GameResponse)
        assert "investigate" in action_response.narrative.lower()

    @pytest.mark.asyncio
    async def test_process_action_session_not_found(self, orch):
        with pytest.raises(ValueError, match="not found"):
            await orch.process_player_action("nonexistent", "do something")

    @pytest.mark.asyncio
    async def test_process_action_inactive_session(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Start")
        response = await orch.start_new_game(organization=_make_org())
        sid = response.game_state.session_id

        # End the session
        orch.end_game(sid, "completed")

        with pytest.raises(ValueError, match="not active"):
            await orch.process_player_action(sid, "try something")


# ---------------------------------------------------------------------------
# get_hint / get_session_state
# ---------------------------------------------------------------------------


class TestHintAndState:
    @pytest.mark.asyncio
    async def test_get_hint(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Start")
        orch.game_master.generate_hint = AsyncMock(return_value="Try checking the logs")

        response = await orch.start_new_game(organization=_make_org())
        hint = await orch.get_hint(response.game_state.session_id)
        assert hint == "Try checking the logs"

    @pytest.mark.asyncio
    async def test_get_hint_missing_session(self, orch):
        with pytest.raises(ValueError):
            await orch.get_hint("no-session")

    @pytest.mark.asyncio
    async def test_get_session_state(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Start")
        response = await orch.start_new_game(organization=_make_org())
        state = orch.get_session_state(response.game_state.session_id)
        assert state is not None
        assert state.session_id == response.game_state.session_id

    def test_get_session_state_missing(self, orch):
        assert orch.get_session_state("nope") is None


# ---------------------------------------------------------------------------
# end_game / complete_objective
# ---------------------------------------------------------------------------


class TestEndGame:
    @pytest.mark.asyncio
    async def test_end_game_completed(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Start")
        response = await orch.start_new_game(organization=_make_org())
        sid = response.game_state.session_id

        final = orch.end_game(sid, "completed")
        assert final.status == "completed"

    @pytest.mark.asyncio
    async def test_end_game_failed(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Start")
        response = await orch.start_new_game(organization=_make_org())
        sid = response.game_state.session_id

        final = orch.end_game(sid, "failed")
        assert final.status == "failed"

    def test_end_game_missing_session(self, orch):
        with pytest.raises(ValueError):
            orch.end_game("no-session")

    @pytest.mark.asyncio
    async def test_complete_objective(self, orch):
        orch.game_master.start_game = AsyncMock(return_value="Start")
        response = await orch.start_new_game(organization=_make_org())
        sid = response.game_state.session_id

        updated = orch.complete_objective(sid, "Detect the breach")
        assert "Detect the breach" in updated.objectives_completed

    def test_complete_objective_missing_session(self, orch):
        with pytest.raises(ValueError):
            orch.complete_objective("no-session", "objective")
