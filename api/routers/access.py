#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Per-record access checks shared by the routers.

Records a caller may not access are reported as 404 (not 403) so that IDs of
other users' records are not confirmed to exist.
"""

from fastapi import HTTPException

from api.middleware.auth import Caller
from api.models import GameState
from api.services.game_session_service import GameSessionService
from api.services.scenario_orchestrator import ScenarioOrchestrator


def owner_filter(caller: Caller) -> str | None:
    """Owner ID to filter listings by, or None when the caller may see everything."""
    return None if caller.unrestricted else caller.user_id


def owned_session(session_id: str, caller: Caller) -> GameState:
    """Load a game session the caller owns, or raise 404."""
    game_state = GameSessionService().get_session(session_id)
    if game_state is None or not caller.owns(game_state.owner_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return game_state


def require_scenario_access(filename: str, caller: Caller) -> None:
    """Raise 404 unless the saved scenario exists and the caller owns it."""
    try:
        owner = ScenarioOrchestrator().get_scenario_owner(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario '{filename}' not found") from None
    if not caller.owns(owner):
        raise HTTPException(status_code=404, detail=f"Scenario '{filename}' not found")
