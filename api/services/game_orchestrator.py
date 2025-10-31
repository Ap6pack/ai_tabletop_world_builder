"""
Game orchestrator service that coordinates game sessions and the AI game master.
"""
from typing import Optional
from api.models import GameState, GameResponse, Organization
from api.services.game_session_service import GameSessionService
from api.services.game_master_service import GameMasterService
from api.providers import LLMProviderFactory


class GameOrchestrator:
    """
    Orchestrates war gaming sessions by coordinating the game master and session management.
    """

    def __init__(self, llm_provider=None, content_policy=None):
        """Initialize the game orchestrator."""
        self.session_service = GameSessionService()
        self.game_master = GameMasterService(llm_provider, content_policy)

    async def start_new_game(
        self,
        organization: Organization,
        scenario_type: str = "incident-response",
        player_role: str = "soc-analyst",
        difficulty: str = "intermediate"
    ) -> GameResponse:
        """
        Start a new war game session.

        Args:
            organization: The organization/scenario to use
            scenario_type: Type of scenario
            player_role: Role the player assumes
            difficulty: Difficulty level

        Returns:
            GameResponse with initial narrative and game state
        """
        # Create new session
        game_state = self.session_service.create_session(
            organization=organization,
            scenario_type=scenario_type,
            player_role=player_role,
            difficulty=difficulty
        )

        # Generate opening narrative
        opening_narrative = await self.game_master.start_game(game_state)

        # Add initial event
        game_state = self.session_service.add_event(
            session_id=game_state.session_id,
            event_type="detection",
            description="Initial security alert detected",
            severity="high",
            actor="system"
        )

        return GameResponse(
            narrative=opening_narrative,
            game_state=game_state,
            inventory_changes=None,
            new_events=game_state.incident_timeline,
            hints=["Investigate the alert details", "Check what systems are affected"]
        )

    async def process_player_action(
        self,
        session_id: str,
        action: str
    ) -> GameResponse:
        """
        Process a player action in an ongoing game.

        Args:
            session_id: Session ID
            action: Player's action description

        Returns:
            GameResponse with narrative and updated game state
        """
        # Get current game state
        game_state = self.session_service.get_session(session_id)

        if game_state is None:
            raise ValueError(f"Session {session_id} not found")

        if game_state.status != "in-progress":
            raise ValueError(f"Session {session_id} is not active (status: {game_state.status})")

        # Process action with game master
        gm_response = await self.game_master.process_action(action, game_state)

        # Update game state based on response
        # Add player action to timeline
        game_state = self.session_service.add_event(
            session_id=session_id,
            event_type="action",
            description=f"Player action: {action}",
            severity="info",
            actor="player"
        )

        # Add consequence events
        for event in gm_response.get("new_events", []):
            game_state = self.session_service.add_event(
                session_id=session_id,
                event_type=event.event_type,
                description=event.description,
                severity=event.severity,
                actor=event.actor
            )

        # Update inventory if needed
        inv_changes = gm_response.get("inventory_changes", {})
        if inv_changes:
            game_state = self.session_service.update_inventory(
                session_id=session_id,
                tool_changes=inv_changes
            )

        # Update score if needed
        score_change = gm_response.get("score_change", {})
        if score_change.get("points", 0) != 0:
            game_state = self.session_service.update_score(
                session_id=session_id,
                points=score_change["points"],
                reason=score_change.get("reason", "Action performed")
            )

        return GameResponse(
            narrative=gm_response["narrative"],
            game_state=game_state,
            inventory_changes=inv_changes if inv_changes else None,
            new_events=gm_response.get("new_events", []),
            hints=gm_response.get("hints")
        )

    async def get_hint(self, session_id: str) -> str:
        """
        Get a hint for the player.

        Args:
            session_id: Session ID

        Returns:
            Hint text
        """
        game_state = self.session_service.get_session(session_id)

        if game_state is None:
            raise ValueError(f"Session {session_id} not found")

        hint = await self.game_master.generate_hint(game_state)

        # Add hint request to timeline
        self.session_service.add_event(
            session_id=session_id,
            event_type="action",
            description="Player requested a hint",
            severity="info",
            actor="player"
        )

        return hint

    def get_session_state(self, session_id: str) -> Optional[GameState]:
        """
        Get current game state.

        Args:
            session_id: Session ID

        Returns:
            GameState or None if not found
        """
        return self.session_service.get_session(session_id)

    def end_game(self, session_id: str, status: str = "completed") -> GameState:
        """
        End a game session.

        Args:
            session_id: Session ID
            status: Final status (completed, failed)

        Returns:
            Final GameState
        """
        game_state = self.session_service.end_session(session_id, status)

        if game_state is None:
            raise ValueError(f"Session {session_id} not found")

        return game_state

    def list_sessions(self, status_filter: Optional[str] = None) -> list:
        """
        List all game sessions.

        Args:
            status_filter: Optional filter by status

        Returns:
            List of session metadata
        """
        return self.session_service.list_sessions(status_filter)

    def complete_objective(
        self,
        session_id: str,
        objective: str,
        success: bool = True
    ) -> GameState:
        """
        Mark an objective as completed or failed.

        Args:
            session_id: Session ID
            objective: Objective description
            success: Whether objective was completed successfully

        Returns:
            Updated GameState
        """
        game_state = self.session_service.complete_objective(session_id, objective, success)

        if game_state is None:
            raise ValueError(f"Session {session_id} not found")

        return game_state
