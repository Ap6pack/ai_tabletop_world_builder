#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Multi-team exercise API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.middleware.auth import Caller, get_caller
from api.models.exercise_models import ExerciseConfig, ExerciseState, Inject, InjectTrigger, TeamMember
from api.routers.access import owner_filter, require_scenario_access
from api.services.exercise_orchestrator import ExerciseOrchestrator
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/exercise", tags=["exercises"])

orchestrator = ExerciseOrchestrator()


# Access control
#
# The user who creates an exercise is its facilitator: only they (or an admin)
# can start/advance rounds, fire injects, pause, end, and read the full state.
# Players act as the seat they joined with their own login; team and member
# IDs are never taken from the request. With auth disabled (dev mode) there is
# no identity and every caller is treated as the facilitator.


def _load(exercise_id: str) -> ExerciseState:
    state = orchestrator.store.get_exercise(exercise_id)
    if not state:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return state


def _is_facilitator(state: ExerciseState, caller: Caller) -> bool:
    return caller.owns(state.owner_id)


def _membership(state: ExerciseState, caller: Caller):
    return orchestrator.find_membership(state, caller.user_id) if caller.user_id else None


def _require_facilitator(state: ExerciseState, caller: Caller) -> None:
    if _is_facilitator(state, caller):
        return
    if _membership(state, caller):
        raise HTTPException(status_code=403, detail="Only the facilitator can do this")
    raise HTTPException(status_code=404, detail="Exercise not found")


# Request models


class CreateExerciseRequest(BaseModel):
    name: str
    description: str = ""
    scenario_filename: str
    scenario_type: str = "incident-response"
    difficulty: str = "intermediate"
    teams: list[dict[str, Any]] = Field(default_factory=list)
    max_rounds: int | None = None
    round_time_limit_minutes: int | None = None


class JoinExerciseRequest(BaseModel):
    team_id: str
    display_name: str | None = None  # defaults to the user's display name
    role: str = "SOC Analyst"


class SubmitActionRequest(BaseModel):
    action: str
    # Only used with auth disabled; with auth on, the seat comes from the login.
    team_id: str | None = None
    member_id: str | None = None


class InjectRequest(BaseModel):
    inject_type: str = "news_article"
    title: str
    content: str
    target_teams: list[str] = Field(default_factory=list)
    severity: str = "medium"
    requires_response: bool = False


# Endpoints


@router.post("/create", status_code=201)
async def create_exercise(request: CreateExerciseRequest, caller: Caller = Depends(get_caller)):
    """Create a new multi-team exercise; the caller becomes its facilitator."""
    require_scenario_access(request.scenario_filename, caller)
    config = ExerciseConfig(
        name=request.name,
        description=request.description,
        scenario_filename=request.scenario_filename,
        scenario_type=request.scenario_type,
        difficulty=request.difficulty,
        teams=request.teams,
        max_rounds=request.max_rounds,
        round_time_limit_minutes=request.round_time_limit_minutes,
    )
    try:
        state = await orchestrator.create_exercise(config, owner_id=caller.user_id)
        return {
            "exercise_id": state.exercise_id,
            "name": state.name,
            "phase": state.phase,
            "teams": [{"team_id": t.team_id, "name": t.name, "type": t.team_type} for t in state.teams],
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Failed to create exercise: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create exercise") from e


@router.get("/{exercise_id}/teams")
async def get_exercise_teams(exercise_id: str, caller: Caller = Depends(get_caller)):
    """Teams available to join, plus the caller's seat and role.

    Anyone with the exercise ID may call this (the ID is the invitation); it
    reveals team names only, never game state.
    """
    state = _load(exercise_id)
    membership = _membership(state, caller)
    return {
        "exercise_id": state.exercise_id,
        "name": state.name,
        "phase": state.phase,
        "teams": [{"team_id": t.team_id, "name": t.name, "team_type": t.team_type} for t in state.teams],
        "is_facilitator": _is_facilitator(state, caller),
        "my_seat": (
            {
                "team_id": membership[0].team_id,
                "member_id": membership[1].member_id,
                "display_name": membership[1].display_name,
            }
            if membership
            else None
        ),
    }


@router.post("/{exercise_id}/join")
async def join_exercise(exercise_id: str, request: JoinExerciseRequest, caller: Caller = Depends(get_caller)):
    """Join a team in an exercise. The exercise ID acts as the invitation."""
    _load(exercise_id)
    display_name = request.display_name or caller.display_name
    if not display_name:
        raise HTTPException(status_code=422, detail="display_name is required")
    member = TeamMember(
        display_name=display_name,
        role=request.role,
        team_id=request.team_id,
        user_id=caller.user_id,
    )
    try:
        await orchestrator.join_exercise(exercise_id, member)
        return {
            "exercise_id": exercise_id,
            "member_id": member.member_id,
            "team_id": member.team_id,
            "display_name": member.display_name,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found") from None


@router.get("/{exercise_id}/state")
async def get_exercise_state(exercise_id: str, team_id: str | None = None, caller: Caller = Depends(get_caller)):
    """Get exercise state.

    The facilitator gets the full state, or any team's view with ``team_id``.
    Players always get their own team's view.
    """
    state = _load(exercise_id)
    if _is_facilitator(state, caller):
        if not team_id:
            return state.model_dump(mode="json")
    else:
        membership = _membership(state, caller)
        if membership is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        own_team_id = membership[0].team_id
        if team_id and team_id != own_team_id:
            raise HTTPException(status_code=403, detail="You can only view your own team")
        team_id = own_team_id

    view = await orchestrator.get_team_view(exercise_id, team_id)
    if not view:
        raise HTTPException(status_code=404, detail="Exercise or team not found")
    return view.model_dump(mode="json")


@router.post("/{exercise_id}/action")
async def submit_action(exercise_id: str, request: SubmitActionRequest, caller: Caller = Depends(get_caller)):
    """Submit an action for the caller's own team seat."""
    state = _load(exercise_id)
    if caller.user_id is None:
        # Auth disabled: no identity, so the seat is taken from the request.
        if not request.team_id or not request.member_id:
            raise HTTPException(status_code=422, detail="team_id and member_id are required")
        team_id, member_id = request.team_id, request.member_id
    else:
        membership = _membership(state, caller)
        if membership is None:
            if _is_facilitator(state, caller):
                raise HTTPException(status_code=403, detail="Join a team to submit actions")
            raise HTTPException(status_code=404, detail="Exercise not found")
        team, member = membership
        if (request.team_id and request.team_id != team.team_id) or (
            request.member_id and request.member_id != member.member_id
        ):
            raise HTTPException(status_code=403, detail="You can only act for your own seat")
        team_id, member_id = team.team_id, member.member_id
    try:
        result = await orchestrator.submit_team_action(exercise_id, team_id, member_id, request.action)
        return result.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found") from None


@router.post("/{exercise_id}/advance")
async def advance_round(exercise_id: str, facilitator_id: str | None = None, caller: Caller = Depends(get_caller)):
    """Start the exercise or advance to the next round (facilitator only).

    ``facilitator_id`` is accepted for backward compatibility and ignored; the
    facilitator is identified by login.
    """
    state = _load(exercise_id)
    _require_facilitator(state, caller)
    try:
        state = await orchestrator.advance_round(exercise_id, state.facilitator_id)
        return {
            "exercise_id": exercise_id,
            "current_round": state.current_round,
            "phase": state.phase,
            "version": state.version,
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found") from None


@router.post("/{exercise_id}/inject")
async def fire_inject(exercise_id: str, request: InjectRequest, caller: Caller = Depends(get_caller)):
    """Fire a crisis inject into the exercise (facilitator only)."""
    _require_facilitator(_load(exercise_id), caller)
    inject = Inject(
        inject_type=request.inject_type,
        title=request.title,
        content=request.content,
        trigger=InjectTrigger(trigger_type="manual"),
        target_teams=request.target_teams,
        severity=request.severity,
        requires_response=request.requires_response,
    )
    try:
        state = await orchestrator.inject_event(exercise_id, inject)
        return {
            "exercise_id": exercise_id,
            "inject_id": inject.inject_id,
            "delivered": True,
            "version": state.version,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found") from None


@router.post("/{exercise_id}/pause")
async def pause_exercise(exercise_id: str, caller: Caller = Depends(get_caller)):
    """Pause the exercise (facilitator only)."""
    _require_facilitator(_load(exercise_id), caller)
    try:
        state = await orchestrator.pause_exercise(exercise_id)
        return {"exercise_id": exercise_id, "phase": state.phase}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found") from None


@router.post("/{exercise_id}/end")
async def end_exercise(exercise_id: str, caller: Caller = Depends(get_caller)):
    """End the exercise (facilitator only)."""
    _require_facilitator(_load(exercise_id), caller)
    try:
        state = await orchestrator.end_exercise(exercise_id)
        return {
            "exercise_id": exercise_id,
            "phase": state.phase,
            "final_round": state.current_round,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found") from None


@router.get("/{exercise_id}/poll")
async def poll_exercise(exercise_id: str, since_version: int = 0, caller: Caller = Depends(get_caller)):
    """Poll for exercise state changes since a given version."""
    state = _load(exercise_id)
    if _is_facilitator(state, caller):
        events = state.exercise_log
    else:
        membership = _membership(state, caller)
        if membership is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        events = orchestrator.visible_events(state, membership[0].team_id)

    if state.version <= since_version:
        return {"changed": False, "version": state.version}

    return {
        "changed": True,
        "version": state.version,
        "phase": state.phase,
        "current_round": state.current_round,
        "new_events": [e.model_dump(mode="json") for e in events[-20:]],
        "team_scores": {t.team_id: t.score for t in state.teams},
    }


@router.get("/list")
async def list_exercises(phase: str | None = None, caller: Caller = Depends(get_caller)):
    """List exercises the caller created or joined (all exercises for admins)."""
    exercises = orchestrator.store.list_exercises(phase=phase, user_id=owner_filter(caller))
    for summary in exercises:
        summary.pop("participant_ids", None)
    return {"exercises": exercises}
