"""Multi-team exercise API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from api.services.exercise_orchestrator import ExerciseOrchestrator
from api.models.exercise_models import ExerciseConfig, TeamMember, Inject, InjectTrigger
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/exercise", tags=["exercises"])

orchestrator = ExerciseOrchestrator()


# Request models

class CreateExerciseRequest(BaseModel):
    name: str
    description: str = ""
    scenario_filename: str
    scenario_type: str = "incident-response"
    difficulty: str = "intermediate"
    teams: List[Dict[str, Any]] = Field(default_factory=list)
    max_rounds: Optional[int] = None
    round_time_limit_minutes: Optional[int] = None


class JoinExerciseRequest(BaseModel):
    display_name: str
    role: str = "SOC Analyst"
    team_id: str


class SubmitActionRequest(BaseModel):
    team_id: str
    member_id: str
    action: str


class InjectRequest(BaseModel):
    inject_type: str = "news_article"
    title: str
    content: str
    target_teams: List[str] = Field(default_factory=list)
    severity: str = "medium"
    requires_response: bool = False


# Endpoints

@router.post("/create", status_code=201)
async def create_exercise(request: CreateExerciseRequest):
    """Create a new multi-team exercise."""
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
        state = await orchestrator.create_exercise(config)
        return {
            "exercise_id": state.exercise_id,
            "name": state.name,
            "phase": state.phase,
            "teams": [{"team_id": t.team_id, "name": t.name, "type": t.team_type} for t in state.teams],
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to create exercise: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{exercise_id}/join")
async def join_exercise(exercise_id: str, request: JoinExerciseRequest):
    """Join an exercise as a team member."""
    member = TeamMember(
        display_name=request.display_name,
        role=request.role,
        team_id=request.team_id,
    )
    try:
        state = await orchestrator.join_exercise(exercise_id, member)
        return {
            "exercise_id": exercise_id,
            "member_id": member.member_id,
            "team_id": member.team_id,
            "display_name": member.display_name,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found")


@router.get("/{exercise_id}/state")
async def get_exercise_state(exercise_id: str, team_id: Optional[str] = None):
    """Get exercise state, optionally filtered for a specific team."""
    if team_id:
        view = await orchestrator.get_team_view(exercise_id, team_id)
        if not view:
            raise HTTPException(status_code=404, detail="Exercise or team not found")
        return view.model_dump(mode="json")
    else:
        state = orchestrator.store.get_exercise(exercise_id)
        if not state:
            raise HTTPException(status_code=404, detail="Exercise not found")
        return state.model_dump(mode="json")


@router.post("/{exercise_id}/action")
async def submit_action(exercise_id: str, request: SubmitActionRequest):
    """Submit a team action."""
    try:
        result = await orchestrator.submit_team_action(
            exercise_id, request.team_id, request.member_id, request.action
        )
        return result.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found")


@router.post("/{exercise_id}/advance")
async def advance_round(exercise_id: str, facilitator_id: str):
    """Advance to next round (facilitator only)."""
    try:
        state = await orchestrator.advance_round(exercise_id, facilitator_id)
        return {
            "exercise_id": exercise_id,
            "current_round": state.current_round,
            "phase": state.phase,
            "version": state.version,
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found")


@router.post("/{exercise_id}/inject")
async def fire_inject(exercise_id: str, request: InjectRequest):
    """Fire a crisis inject into the exercise."""
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
        raise HTTPException(status_code=404, detail="Exercise not found")


@router.post("/{exercise_id}/pause")
async def pause_exercise(exercise_id: str):
    """Pause the exercise."""
    try:
        state = await orchestrator.pause_exercise(exercise_id)
        return {"exercise_id": exercise_id, "phase": state.phase}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found")


@router.post("/{exercise_id}/end")
async def end_exercise(exercise_id: str):
    """End the exercise."""
    try:
        state = await orchestrator.end_exercise(exercise_id)
        return {
            "exercise_id": exercise_id,
            "phase": state.phase,
            "final_round": state.current_round,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exercise not found")


@router.get("/{exercise_id}/poll")
async def poll_exercise(exercise_id: str, since_version: int = 0):
    """Poll for exercise state changes since a given version."""
    state = orchestrator.store.get_exercise(exercise_id)
    if not state:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if state.version <= since_version:
        return {"changed": False, "version": state.version}

    # Return events since the requested version
    new_events = [
        e for e in state.exercise_log
        if True  # All events for now; version-based filtering can be added later
    ]

    return {
        "changed": True,
        "version": state.version,
        "phase": state.phase,
        "current_round": state.current_round,
        "new_events": [e.model_dump(mode="json") for e in new_events[-20:]],
        "team_scores": {t.team_id: t.score for t in state.teams},
    }


@router.get("/list")
async def list_exercises(phase: Optional[str] = None):
    """List all exercises."""
    exercises = orchestrator.store.list_exercises(phase=phase)
    return {"exercises": exercises}
