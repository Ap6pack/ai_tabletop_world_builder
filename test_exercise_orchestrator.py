#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
"""Tests for the multi-team exercise orchestration service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from api.services.exercise_orchestrator import ExerciseOrchestrator
from api.models.exercise_models import (
    ExerciseConfig, TeamMember, ExerciseState, Inject, InjectTrigger,
    InjectType,
)
from api.models.schemas import (
    GameState, Organization, Department, Inventory, GameResponse,
    IncidentEvent, BusinessImpact,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_org():
    """Minimal Organization for test scenarios."""
    return Organization(
        id="org-1", name="Test Corp", description="Test",
        industry="Technology", size="medium",
        departments=[
            Department(
                id="d1", name="IT", description="IT",
                business_function="Tech", systems=[],
                data_classification="internal",
                compliance_requirements=[],
            )
        ],
        threat_actors=[], security_posture="developing",
        compliance_frameworks=[],
    )


def make_game_state(**overrides):
    """Factory for minimal GameState instances."""
    defaults = dict(
        session_id="test-session", organization=make_org(),
        current_scenario="test", player_role="mixed",
        inventory=Inventory(), status="in-progress",
    )
    defaults.update(overrides)
    return GameState(**defaults)


def make_config(**overrides):
    """Factory for ExerciseConfig with sensible defaults."""
    defaults = dict(
        name="Test Exercise", description="A test exercise",
        scenario_filename="test_scenario.yaml",
        scenario_type="incident-response", difficulty="intermediate",
        max_rounds=3,
    )
    defaults.update(overrides)
    return ExerciseConfig(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_orchestrator(tmp_path):
    """ExerciseOrchestrator with mocked sub-orchestrators and temp storage."""
    orch = ExerciseOrchestrator()

    # Point file storage to a temp directory
    orch.store._storage_dir = tmp_path / "exercises"
    orch.store._storage_dir.mkdir(parents=True, exist_ok=True)
    orch.store._archive_dir = tmp_path / "exercises" / "archive"
    orch.store._archive_dir.mkdir(parents=True, exist_ok=True)

    # Mock the sub-orchestrators so no real LLM / file IO happens
    orch.scenario_orchestrator.load_scenario = AsyncMock(return_value=make_org())

    mock_game_response = GameResponse(
        narrative="Test narrative",
        game_state=make_game_state(),
    )
    orch.game_orchestrator.start_new_game = AsyncMock(
        return_value=mock_game_response,
    )
    orch.game_orchestrator.process_player_action = AsyncMock(
        return_value=mock_game_response,
    )
    orch.game_orchestrator.end_game = AsyncMock()

    return orch


# ---------------------------------------------------------------------------
# Exercise creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_exercise_default_teams(mock_orchestrator):
    """No teams in config -> Blue Team + Facilitator created by default."""
    config = make_config(teams=[])
    state = await mock_orchestrator.create_exercise(config)

    assert isinstance(state, ExerciseState)
    assert len(state.teams) == 2
    team_types = {t.team_type for t in state.teams}
    assert "blue" in team_types
    assert "white" in team_types
    assert state.phase == "setup"


@pytest.mark.asyncio
async def test_create_exercise_custom_teams(mock_orchestrator):
    """Custom teams in config are honoured."""
    config = make_config(
        teams=[
            {"name": "SOC", "team_type": "blue", "roles": ["Analyst"]},
            {"name": "Red", "team_type": "red", "roles": ["Operator"]},
            {"name": "Facilitator", "team_type": "white", "roles": ["Lead"]},
        ],
    )
    state = await mock_orchestrator.create_exercise(config)
    assert len(state.teams) == 3
    assert state.teams[0].name == "SOC"


# ---------------------------------------------------------------------------
# Joining
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_join_exercise(mock_orchestrator):
    """A member can join an existing exercise team."""
    config = make_config()
    state = await mock_orchestrator.create_exercise(config)

    blue_team = [t for t in state.teams if t.team_type == "blue"][0]
    member = TeamMember(
        display_name="Alice", role="SOC Analyst",
        team_id=blue_team.team_id,
    )

    updated = await mock_orchestrator.join_exercise(state.exercise_id, member)
    blue = [t for t in updated.teams if t.team_type == "blue"][0]
    names = [m.display_name for m in blue.members]
    assert "Alice" in names


@pytest.mark.asyncio
async def test_join_exercise_not_found(mock_orchestrator):
    """Joining a non-existent exercise raises FileNotFoundError."""
    member = TeamMember(
        display_name="Bob", role="Analyst", team_id="no-such-team",
    )
    with pytest.raises(FileNotFoundError):
        await mock_orchestrator.join_exercise("nonexistent-id", member)


@pytest.mark.asyncio
async def test_join_duplicate_member(mock_orchestrator):
    """Adding the same display_name twice raises ValueError."""
    config = make_config()
    state = await mock_orchestrator.create_exercise(config)

    blue_team = [t for t in state.teams if t.team_type == "blue"][0]
    member = TeamMember(
        display_name="Alice", role="SOC Analyst",
        team_id=blue_team.team_id,
    )
    await mock_orchestrator.join_exercise(state.exercise_id, member)

    dup = TeamMember(
        display_name="Alice", role="Lead",
        team_id=blue_team.team_id,
    )
    with pytest.raises(ValueError, match="already on team"):
        await mock_orchestrator.join_exercise(state.exercise_id, dup)


# ---------------------------------------------------------------------------
# Round advancement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_round_start(mock_orchestrator):
    """Advancing from setup transitions to active round 1."""
    config = make_config()
    state = await mock_orchestrator.create_exercise(config)

    facilitator_id = state.facilitator_id
    updated = await mock_orchestrator.advance_round(
        state.exercise_id, facilitator_id,
    )
    assert updated.phase == "active"
    assert updated.current_round == 1


@pytest.mark.asyncio
async def test_advance_round_next(mock_orchestrator):
    """Advancing from round 1 moves to round 2."""
    config = make_config(max_rounds=5)
    state = await mock_orchestrator.create_exercise(config)

    fid = state.facilitator_id
    state = await mock_orchestrator.advance_round(state.exercise_id, fid)
    assert state.current_round == 1

    state = await mock_orchestrator.advance_round(state.exercise_id, fid)
    assert state.current_round == 2


@pytest.mark.asyncio
async def test_advance_round_max(mock_orchestrator):
    """Hitting max_rounds transitions the exercise into debrief."""
    config = make_config(max_rounds=2)
    state = await mock_orchestrator.create_exercise(config)

    fid = state.facilitator_id
    state = await mock_orchestrator.advance_round(state.exercise_id, fid)  # setup -> round 1
    state = await mock_orchestrator.advance_round(state.exercise_id, fid)  # round 1 -> round 2
    state = await mock_orchestrator.advance_round(state.exercise_id, fid)  # round 2 == max -> debrief

    assert state.phase == "debrief"


# ---------------------------------------------------------------------------
# Action submission
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_action(mock_orchestrator):
    """A team member action is processed through the game engine."""
    config = make_config()
    state = await mock_orchestrator.create_exercise(config)

    # Start the exercise
    fid = state.facilitator_id
    state = await mock_orchestrator.advance_round(state.exercise_id, fid)

    # Add a member
    blue_team = [t for t in state.teams if t.team_type == "blue"][0]
    member = TeamMember(
        display_name="Charlie", role="Analyst",
        team_id=blue_team.team_id,
    )
    state = await mock_orchestrator.join_exercise(state.exercise_id, member)

    result = await mock_orchestrator.submit_team_action(
        state.exercise_id,
        blue_team.team_id,
        member.member_id,
        "Check SIEM alerts",
    )
    assert result.narrative == "Test narrative"
    assert result.game_state_updated is True


# ---------------------------------------------------------------------------
# Inject delivery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inject_event(mock_orchestrator):
    """Delivering an inject adds it to the exercise state."""
    config = make_config()
    state = await mock_orchestrator.create_exercise(config)

    inject = Inject(
        inject_type=InjectType.NEWS_ARTICLE,
        title="Breaking News: Data Breach",
        content="A major breach has been reported.",
        trigger=InjectTrigger(trigger_type="manual"),
        severity="high",
    )
    updated = await mock_orchestrator.inject_event(state.exercise_id, inject)
    assert len(updated.injects) == 1
    assert updated.injects[0].delivered is True
    assert updated.injects[0].title == "Breaking News: Data Breach"


# ---------------------------------------------------------------------------
# Team view
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_team_view(mock_orchestrator):
    """get_team_view returns a filtered TeamGameView."""
    config = make_config()
    state = await mock_orchestrator.create_exercise(config)

    blue_team = [t for t in state.teams if t.team_type == "blue"][0]
    view = await mock_orchestrator.get_team_view(
        state.exercise_id, blue_team.team_id,
    )
    assert view is not None
    assert view.exercise_id == state.exercise_id
    assert view.team.team_id == blue_team.team_id


# ---------------------------------------------------------------------------
# Pause / resume
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pause_and_resume(mock_orchestrator):
    """Pausing then advancing resumes the exercise."""
    config = make_config()
    state = await mock_orchestrator.create_exercise(config)
    fid = state.facilitator_id

    # Start
    state = await mock_orchestrator.advance_round(state.exercise_id, fid)
    assert state.phase == "active"

    # Pause
    state = await mock_orchestrator.pause_exercise(state.exercise_id)
    assert state.phase == "paused"

    # Resume via advance_round
    state = await mock_orchestrator.advance_round(state.exercise_id, fid)
    assert state.phase == "active"
