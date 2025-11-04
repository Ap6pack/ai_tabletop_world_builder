"""
Game API router for interactive war gaming sessions.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel, Field
from api.models import GameState, GameResponse
from api.services import GameOrchestrator, ScenarioOrchestrator
from api.utils import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/game", tags=["Game"])


# Request/Response models
class StartGameRequest(BaseModel):
    """Request to start a new game."""
    scenario_filename: str = Field(..., description="Filename of saved scenario to use")
    scenario_type: str = Field("incident-response", description="Type of scenario")
    player_role: str = Field(..., description="Player role", examples=["soc-analyst"])
    difficulty: str = Field("intermediate", description="Difficulty level")


class PlayerActionRequest(BaseModel):
    """Request to process player action."""
    session_id: str = Field(..., description="Game session ID")
    action: str = Field(..., description="Player's action", examples=["Check SIEM logs for suspicious activity"])


class EndGameRequest(BaseModel):
    """Request to end a game."""
    session_id: str = Field(..., description="Game session ID")
    status: str = Field("completed", description="Final status (completed, failed)")


@router.post("/start", response_model=GameResponse)
async def start_game(request: StartGameRequest):
    """
    Start a new war gaming session.

    This creates a new game session using a previously generated scenario
    and returns the opening narrative.

    Args:
        request: Game start request with scenario and player details

    Returns:
        GameResponse with opening narrative and initial game state

    Raises:
        HTTPException: If scenario not found or game creation fails
    """
    try:
        # Load the scenario
        scenario_service = ScenarioOrchestrator()
        organization = await scenario_service.load_scenario(request.scenario_filename)

        # Start the game
        game_orchestrator = GameOrchestrator()
        response = await game_orchestrator.start_new_game(
            organization=organization,
            scenario_type=request.scenario_type,
            player_role=request.player_role,
            difficulty=request.difficulty
        )

        return response

    except FileNotFoundError as e:
        logger.warning(f"Scenario not found: {request.scenario_filename}")
        raise HTTPException(status_code=404, detail=f"Scenario '{request.scenario_filename}' not found")
    except Exception as e:
        logger.error(f"Failed to start game: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start game: {str(e)}")


@router.post("/action", response_model=GameResponse)
async def process_action(request: PlayerActionRequest):
    """
    Process a player action in an ongoing game.

    The AI Game Master will evaluate the action, determine outcomes,
    and return a narrative response with any game state changes.

    Args:
        request: Player action request

    Returns:
        GameResponse with narrative and updated game state

    Raises:
        HTTPException: If session not found or action processing fails
    """
    try:
        game_orchestrator = GameOrchestrator()
        response = await game_orchestrator.process_player_action(
            session_id=request.session_id,
            action=request.action
        )

        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process action: {str(e)}")


@router.get("/state/{session_id}", response_model=GameState)
async def get_game_state(session_id: str):
    """
    Get the current state of a game session.

    Args:
        session_id: Game session ID

    Returns:
        Current GameState

    Raises:
        HTTPException: If session not found
    """
    try:
        game_orchestrator = GameOrchestrator()
        game_state = game_orchestrator.get_session_state(session_id)

        if game_state is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        return game_state

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get game state: {str(e)}")


@router.post("/hint")
async def get_hint(session_id: str):
    """
    Get a hint for the current situation.

    Args:
        session_id: Game session ID

    Returns:
        Hint text

    Raises:
        HTTPException: If session not found or hint generation fails
    """
    try:
        game_orchestrator = GameOrchestrator()
        hint = await game_orchestrator.get_hint(session_id)

        return {"hint": hint}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate hint: {str(e)}")


@router.post("/end", response_model=GameState)
async def end_game(request: EndGameRequest):
    """
    End a game session.

    Args:
        request: End game request

    Returns:
        Final GameState

    Raises:
        HTTPException: If session not found
    """
    try:
        game_orchestrator = GameOrchestrator()
        game_state = game_orchestrator.end_game(
            session_id=request.session_id,
            status=request.status
        )

        return game_state

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end game: {str(e)}")


@router.get("/sessions")
async def list_sessions(status: Optional[str] = None):
    """
    List all game sessions.

    Args:
        status: Optional filter by status (in-progress, completed, failed)

    Returns:
        List of session metadata
    """
    try:
        game_orchestrator = GameOrchestrator()
        sessions = game_orchestrator.list_sessions(status_filter=status)

        return {"sessions": sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a game session.

    Args:
        session_id: Game session ID to delete

    Returns:
        Success message

    Raises:
        HTTPException: If session not found or deletion fails
    """
    try:
        game_orchestrator = GameOrchestrator()
        success = game_orchestrator.delete_session(session_id)

        if success:
            return {"message": f"Session {session_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    except FileNotFoundError:
        logger.warning(f"Session not found for deletion: {session_id}")
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.post("/objective")
async def complete_objective(
    session_id: str,
    objective: str,
    success: bool = True
):
    """
    Mark an objective as completed or failed.

    Args:
        session_id: Game session ID
        objective: Objective description
        success: Whether objective was completed successfully

    Returns:
        Updated GameState

    Raises:
        HTTPException: If session not found
    """
    try:
        game_orchestrator = GameOrchestrator()
        game_state = game_orchestrator.complete_objective(
            session_id=session_id,
            objective=objective,
            success=success
        )

        return game_state

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete objective: {str(e)}")
