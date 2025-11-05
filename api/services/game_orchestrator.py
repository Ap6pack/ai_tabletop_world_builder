"""
Game orchestrator service that coordinates game sessions and the AI game master.
"""
from typing import Optional
from datetime import datetime
from api.models import GameState, GameResponse, Organization
from api.services.game_session_service import GameSessionService
from api.services.game_master_service import GameMasterService
from api.services.objective_generator import ObjectiveGenerator
from api.services.system_state_manager import SystemStateManager
from api.services.threat_response_engine import ThreatResponseEngine
from api.services.business_impact_service import BusinessImpactService
from api.services.time_pressure_service import TimePressureService
from api.services.resource_manager import ResourceManager
from api.providers import LLMProviderFactory


class GameOrchestrator:
    """
    Orchestrates war gaming sessions by coordinating the game master and session management.
    """

    def __init__(self, llm_provider=None, content_policy=None):
        """Initialize the game orchestrator."""
        self.session_service = GameSessionService()
        self.game_master = GameMasterService(llm_provider, content_policy)
        self.objective_generator = ObjectiveGenerator()
        self.system_state_manager = SystemStateManager()
        self.threat_response_engine = ThreatResponseEngine()
        self.business_impact_service = BusinessImpactService()  # Phase 5B
        self.time_pressure_service = TimePressureService()  # Phase 5B
        self.resource_manager = ResourceManager()  # Phase 5B

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

        # Generate objectives automatically
        objectives = self.objective_generator.generate_objectives_from_scenario(
            organization=organization,
            scenario_type=scenario_type,
            difficulty=difficulty,
            player_role=player_role
        )
        game_state.objectives = objectives

        # Initialize system states
        system_states = self.system_state_manager.initialize_system_states(organization)
        game_state.system_states = system_states

        # Initialize threat states
        threat_states = self.threat_response_engine.initialize_threat_states(organization)
        game_state.threat_states = threat_states

        # Phase 5B: Initialize business impact tracking
        game_state.business_impact = self.business_impact_service.initialize_business_impact(organization)
        game_state.game_started_at = datetime.utcnow()

        # Phase 5B: Initialize resource pool
        game_state.resource_pool = self.resource_manager.initialize_resource_pool(difficulty)

        # Phase 5B: Create timers for objectives with time limits
        for objective in game_state.objectives:
            if objective.time_limit_minutes:
                timer = self.time_pressure_service.create_objective_timer(objective)
                game_state.timers.append(timer)

        # Phase 5B: Create escalation rules based on scenario parameters
        threat_ids = [t.id for t in organization.threat_actors]
        system_ids = []
        for dept in organization.departments:
            for sys in dept.systems:
                system_ids.append(sys.id)

        # Get scenario duration from metadata (default 60 minutes)
        scenario_duration = 60  # TODO: Get from scenario metadata

        escalation_rules = self.time_pressure_service.create_scenario_escalation_rules(
            scenario_type=scenario_type,
            difficulty=difficulty,
            duration_minutes=scenario_duration,
            threat_ids=threat_ids,
            system_ids=system_ids,
        )
        game_state.escalation_rules.extend(escalation_rules)

        # Save session with objectives, system states, threat states, business impact, timers, and escalation rules
        self.session_service.save_session(game_state)

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

        # Phase 5B: Regenerate action points
        resource_messages = []
        if game_state.resource_pool:
            game_state.resource_pool = self.resource_manager.clear_expired_cooldowns(game_state.resource_pool)
            game_state.resource_pool, points_regen = self.resource_manager.regenerate_action_points(
                game_state.resource_pool, game_state.time_elapsed
            )
            if points_regen > 0:
                resource_messages.append(f"⚡ Regenerated {points_regen} action point(s)")

        # Phase 5B: Check action cost and affordability
        if game_state.resource_pool:
            action_cost = self.resource_manager.get_action_cost(action)
            can_afford, reason = self.resource_manager.can_afford_action(game_state.resource_pool, action_cost)

            if not can_afford:
                # Return early with resource constraint message
                return GameResponse(
                    narrative=f"❌ **Action Blocked**: {reason}\n\nYou cannot perform this action right now. Try a different approach or wait for resources to regenerate.",
                    game_state=game_state,
                    inventory_changes=None,
                    new_events=[],
                    hints=["Check your resource status", "Try less expensive actions", "Wait for action points to regenerate"]
                )

            # Spend resources for the action
            game_state.resource_pool = self.resource_manager.spend_resources(game_state.resource_pool, action_cost)
            resource_messages.append(f"💰 Spent: {action_cost.points} AP, ${action_cost.budget:,.0f}")

        # Phase 5B: Update timers and check for expiries
        timer_messages = []
        if game_state.timers:
            game_state, timer_messages = self.time_pressure_service.update_timers(
                game_state, game_state.time_elapsed
            )

        # Phase 5B: Check escalation rules
        escalation_messages = []
        if game_state.escalation_rules:
            game_state, escalation_messages = self.time_pressure_service.check_escalation_rules(
                game_state, game_state.time_elapsed
            )

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

        # Phase 5B: Append resource, timer, and escalation messages to narrative
        narrative = gm_response["narrative"]
        if resource_messages:
            narrative += "\n\n**💰 Resources:**\n" + "\n".join(resource_messages)
        if timer_messages:
            narrative += "\n\n**⏰ Time Updates:**\n" + "\n".join(timer_messages)
        if escalation_messages:
            narrative += "\n\n**⚠️ Escalations:**\n" + "\n".join(escalation_messages)

        return GameResponse(
            narrative=narrative,
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

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a game session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        return self.session_service.delete_session(session_id)

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

    def update_business_impact(
        self,
        session_id: str,
        event_type: str,
        system_id: Optional[str] = None,
        hours: Optional[float] = None,
        records: Optional[int] = None,
        department: Optional[str] = None,
        severity: str = "medium",
    ) -> GameState:
        """
        Update business impact for a session (Phase 5B).

        Args:
            session_id: Session ID
            event_type: Type of impact event ("downtime", "data_loss", "compliance", "reputation")
            system_id: System ID for downtime events
            hours: Hours of downtime
            records: Number of records compromised
            department: Department name for data loss
            severity: Severity level

        Returns:
            Updated GameState
        """
        game_state = self.session_service.get_session(session_id)

        if game_state is None:
            raise ValueError(f"Session {session_id} not found")

        # Update business impact
        game_state = self.business_impact_service.update_impact(
            game_state=game_state,
            organization=game_state.organization,
            event_type=event_type,
            system_id=system_id,
            hours=hours,
            records=records,
            department=department,
            severity=severity,
        )

        # Save updated game state
        self.session_service.save_session(game_state)

        return game_state

    def calculate_system_downtime(
        self,
        session_id: str,
        system_id: str,
    ) -> GameState:
        """
        Calculate and apply business impact from system downtime (Phase 5B).

        This is called automatically when a system status changes to offline/compromised.

        Args:
            session_id: Session ID
            system_id: System ID

        Returns:
            Updated GameState
        """
        game_state = self.session_service.get_session(session_id)

        if game_state is None:
            raise ValueError(f"Session {session_id} not found")

        # Calculate system downtime impact
        game_state = self.business_impact_service.calculate_system_downtime_impact(
            game_state=game_state,
            organization=game_state.organization,
            system_id=system_id,
        )

        # Save updated game state
        self.session_service.save_session(game_state)

        return game_state

    def get_timer_status(self, session_id: str) -> dict:
        """
        Get timer status summary for a session (Phase 5B).

        Args:
            session_id: Session ID

        Returns:
            Timer status dictionary
        """
        game_state = self.session_service.get_session(session_id)

        if game_state is None:
            raise ValueError(f"Session {session_id} not found")

        return self.time_pressure_service.get_active_timers_summary(game_state)

    def get_next_escalation(self, session_id: str) -> Optional[dict]:
        """
        Get next scheduled escalation for a session (Phase 5B).

        Args:
            session_id: Session ID

        Returns:
            Next escalation info or None
        """
        game_state = self.session_service.get_session(session_id)

        if game_state is None:
            raise ValueError(f"Session {session_id} not found")

        return self.time_pressure_service.get_next_escalation(
            game_state, game_state.time_elapsed
        )
