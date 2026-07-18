#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Multi-team exercise orchestration service.

Manages the lifecycle of collaborative tabletop exercises with multiple
teams, round-based play, and facilitator controls. Wraps the single-player
GameOrchestrator for action processing.
"""

from datetime import UTC, datetime

from api.models.exercise_models import (
    ExerciseConfig,
    ExerciseEvent,
    ExerciseState,
    ExerciseTeam,
    Inject,
    TeamAction,
    TeamActionResult,
    TeamGameView,
    TeamMember,
)
from api.models.schemas import IncidentEvent
from api.services.exercise_store import ExerciseStore
from api.services.game_orchestrator import GameOrchestrator
from api.services.scenario_orchestrator import ScenarioOrchestrator
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExerciseOrchestrator:
    """Orchestrates multi-team exercises on top of the single-player game engine."""

    def __init__(self):
        self.store = ExerciseStore()
        self.game_orchestrator = GameOrchestrator()
        self.scenario_orchestrator = ScenarioOrchestrator()

    async def create_exercise(self, config: ExerciseConfig) -> ExerciseState:
        """Create a new multi-team exercise from a scenario."""
        logger.info("Creating exercise: %s", config.name)

        # Load scenario
        try:
            organization = await self.scenario_orchestrator.load_scenario(config.scenario_filename)
        except FileNotFoundError:
            raise FileNotFoundError(f"Scenario file not found: {config.scenario_filename}") from None

        # Initialize game state via the single-player engine
        game_response = await self.game_orchestrator.start_new_game(
            organization=organization,
            scenario_type=config.scenario_type,
            player_role="mixed",
            difficulty=config.difficulty,
        )
        game_state = game_response.game_state

        # Build teams from config
        teams = []
        for team_cfg in config.teams:
            team = ExerciseTeam(
                name=team_cfg.get("name", "Team"),
                team_type=team_cfg.get("team_type", "blue"),
            )
            # Pre-populate roles if specified
            for role_name in team_cfg.get("roles", []):
                member = TeamMember(
                    display_name=f"[Unassigned] {role_name}",
                    role=role_name,
                    team_id=team.team_id,
                )
                team.members.append(member)
            teams.append(team)

        # Create default teams if none specified
        if not teams:
            teams = [
                ExerciseTeam(name="Blue Team", team_type="blue"),
                ExerciseTeam(name="Facilitator", team_type="white"),
            ]

        # Set facilitator
        facilitator_id = ""
        for team in teams:
            if team.team_type == "white":
                facilitator_id = team.team_id
                break
        if not facilitator_id and teams:
            facilitator_id = teams[0].team_id

        state = ExerciseState(
            name=config.name,
            description=config.description,
            facilitator_id=facilitator_id,
            teams=teams,
            game_state=game_state,
            max_rounds=config.max_rounds,
            round_time_limit_minutes=config.round_time_limit_minutes,
            config=config,
        )

        # Log creation event
        state.exercise_log.append(
            ExerciseEvent(
                event_type="facilitator",
                description=f"Exercise '{config.name}' created with {len(teams)} teams",
                visibility="all",
            )
        )

        self.store.save_exercise(state)
        logger.info("Exercise %s created with %d teams", state.exercise_id, len(teams))
        return state

    async def join_exercise(self, exercise_id: str, member: TeamMember) -> ExerciseState:
        """Add a member to a team in the exercise."""
        state = self.store.get_exercise(exercise_id)
        if not state:
            raise FileNotFoundError(f"Exercise {exercise_id} not found")

        # Find the target team
        target_team = None
        for team in state.teams:
            if team.team_id == member.team_id:
                target_team = team
                break

        if not target_team:
            raise ValueError(f"Team {member.team_id} not found in exercise")

        # Check for duplicate member names on the team
        for existing in target_team.members:
            if existing.display_name == member.display_name:
                raise ValueError(f"Member '{member.display_name}' already on team")

        target_team.members.append(member)

        state.exercise_log.append(
            ExerciseEvent(
                event_type="system",
                source_team_id=member.team_id,
                description=f"{member.display_name} joined {target_team.name} as {member.role}",
                visibility="all",
            )
        )

        self.store.save_exercise(state)
        logger.info("%s joined exercise %s", member.display_name, exercise_id)
        return state

    async def submit_team_action(
        self,
        exercise_id: str,
        team_id: str,
        member_id: str,
        action_text: str,
    ) -> TeamActionResult:
        """Process an action from a team member."""
        state = self.store.get_exercise(exercise_id)
        if not state:
            raise FileNotFoundError(f"Exercise {exercise_id} not found")

        if state.phase != "active":
            raise ValueError(f"Exercise is {state.phase}, not active")

        # Validate team and member
        team = self._find_team(state, team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")

        member = self._find_member(team, member_id)
        if not member:
            raise ValueError(f"Member {member_id} not found on team {team_id}")

        # Create the action record
        team_action = TeamAction(
            team_id=team_id,
            member_id=member_id,
            action=action_text,
            round_number=state.current_round,
        )

        # Process through the game engine
        try:
            game_response = await self.game_orchestrator.process_player_action(state.game_state.session_id, action_text)
            team_action.result = game_response.narrative
            team_action.processed = True
            state.game_state = game_response.game_state
        except Exception as e:
            logger.error("Action processing failed: %s", e)
            team_action.result = f"Action failed: {str(e)}"

        # Store the action
        if team_id not in state.team_actions:
            state.team_actions[team_id] = []
        state.team_actions[team_id].append(team_action)

        # Log the event
        event = ExerciseEvent(
            event_type="team_action",
            source_team_id=team_id,
            description=f"[{team.name}] {member.display_name}: {action_text}",
            visibility="all",
            round_number=state.current_round,
        )
        state.exercise_log.append(event)

        # Update team score from game state
        team.score = state.game_state.score if state.game_state else 0

        self.store.save_exercise(state)

        return TeamActionResult(
            action_id=team_action.action_id,
            team_id=team_id,
            narrative=team_action.result or "",
            game_state_updated=team_action.processed,
            events_generated=[event],
        )

    async def advance_round(self, exercise_id: str, facilitator_id: str) -> ExerciseState:
        """Advance to the next round. Facilitator only."""
        state = self.store.get_exercise(exercise_id)
        if not state:
            raise FileNotFoundError(f"Exercise {exercise_id} not found")

        # Verify facilitator
        if not self._is_facilitator(state, facilitator_id):
            raise ValueError("Only the facilitator can advance rounds")

        # Start exercise if in setup
        if state.phase == "setup":
            state.phase = "active"
            state.started_at = datetime.now(UTC)
            state.current_round = 1
            state.round_started_at = datetime.now(UTC)

            state.exercise_log.append(
                ExerciseEvent(
                    event_type="round_change",
                    description="Exercise started - Round 1",
                    visibility="all",
                    round_number=1,
                )
            )
        elif state.phase == "active":
            # Check max rounds
            if state.max_rounds and state.current_round >= state.max_rounds:
                state.phase = "debrief"
                state.exercise_log.append(
                    ExerciseEvent(
                        event_type="round_change",
                        description=f"Final round ({state.current_round}) completed. Entering debrief.",
                        visibility="all",
                        round_number=state.current_round,
                    )
                )
            else:
                state.current_round += 1
                state.round_started_at = datetime.now(UTC)
                state.exercise_log.append(
                    ExerciseEvent(
                        event_type="round_change",
                        description=f"Round {state.current_round} started",
                        visibility="all",
                        round_number=state.current_round,
                    )
                )
        elif state.phase == "paused":
            state.phase = "active"
            state.exercise_log.append(
                ExerciseEvent(
                    event_type="facilitator",
                    description="Exercise resumed",
                    visibility="all",
                    round_number=state.current_round,
                )
            )

        self.store.save_exercise(state)
        logger.info("Exercise %s advanced to round %d", exercise_id, state.current_round)
        return state

    async def inject_event(self, exercise_id: str, inject: Inject) -> ExerciseState:
        """Deliver a crisis inject to the exercise."""
        state = self.store.get_exercise(exercise_id)
        if not state:
            raise FileNotFoundError(f"Exercise {exercise_id} not found")

        inject.delivered = True
        inject.delivered_at = datetime.now(UTC)
        state.injects.append(inject)

        # Determine target description
        if inject.target_teams:
            target_names = []
            for team in state.teams:
                if team.team_id in inject.target_teams:
                    target_names.append(team.name)
            target_desc = ", ".join(target_names)
        else:
            target_desc = "all teams"

        # Add to exercise log
        visibility = "team_only" if inject.target_teams else "all"
        state.exercise_log.append(
            ExerciseEvent(
                event_type="inject",
                description=f"[INJECT] {inject.title} (to {target_desc})",
                visibility=visibility,
                round_number=state.current_round,
            )
        )

        # Also add to game timeline for narrative continuity
        if state.game_state:
            state.game_state.incident_timeline.append(
                IncidentEvent(
                    timestamp=datetime.now(UTC),
                    event_type="consequence",
                    description=f"[Crisis Inject] {inject.title}: {inject.content[:200]}",
                    severity=inject.severity
                    if inject.severity in ("critical", "high", "medium", "low", "info")
                    else "medium",
                    actor="system",
                )
            )

        self.store.save_exercise(state)
        logger.info("Inject '%s' delivered to exercise %s", inject.title, exercise_id)
        return state

    async def get_team_view(self, exercise_id: str, team_id: str) -> TeamGameView | None:
        """Get a team-filtered view of the exercise state."""
        state = self.store.get_exercise(exercise_id)
        if not state:
            return None

        team = self._find_team(state, team_id)
        if not team:
            return None

        is_facilitator = self._is_facilitator_team(state, team_id)

        # Filter events by visibility
        visible_events = []
        for event in state.exercise_log:
            if (
                event.visibility == "all"
                or event.visibility == "team_only"
                and event.source_team_id == team_id
                or event.visibility == "facilitator_only"
                and is_facilitator
            ):
                visible_events.append(event)

        # Filter injects visible to this team
        active_injects = []
        for inject in state.injects:
            if inject.delivered and (not inject.target_teams or team_id in inject.target_teams or is_facilitator):
                active_injects.append(inject)

        return TeamGameView(
            exercise_id=exercise_id,
            team=team,
            game_state=state.game_state,
            visible_events=visible_events[-50:],
            active_injects=active_injects,
            current_round=state.current_round,
            phase=state.phase,
            version=state.version,
        )

    async def pause_exercise(self, exercise_id: str) -> ExerciseState:
        """Pause the exercise."""
        state = self.store.get_exercise(exercise_id)
        if not state:
            raise FileNotFoundError(f"Exercise {exercise_id} not found")

        state.phase = "paused"
        state.exercise_log.append(
            ExerciseEvent(
                event_type="facilitator",
                description="Exercise paused",
                visibility="all",
                round_number=state.current_round,
            )
        )

        self.store.save_exercise(state)
        return state

    async def end_exercise(self, exercise_id: str) -> ExerciseState:
        """End the exercise and archive."""
        state = self.store.get_exercise(exercise_id)
        if not state:
            raise FileNotFoundError(f"Exercise {exercise_id} not found")

        state.phase = "completed"
        state.ended_at = datetime.now(UTC)

        state.exercise_log.append(
            ExerciseEvent(
                event_type="facilitator",
                description=f"Exercise completed after {state.current_round} rounds",
                visibility="all",
                round_number=state.current_round,
            )
        )

        # End the underlying game session
        if state.game_state:
            try:
                await self.game_orchestrator.end_game(state.game_state.session_id, "completed")
            except Exception as e:
                logger.warning("Failed to end game session: %s", e)

        self.store.save_exercise(state)

        # Archive to permanent storage
        try:
            self.store.archive_exercise(exercise_id)
        except Exception as e:
            logger.warning("Failed to archive exercise: %s", e)

        return state

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _find_team(self, state: ExerciseState, team_id: str) -> ExerciseTeam | None:
        """Find a team by ID."""
        for team in state.teams:
            if team.team_id == team_id:
                return team
        return None

    def _find_member(self, team: ExerciseTeam, member_id: str) -> TeamMember | None:
        """Find a member by ID on a team."""
        for member in team.members:
            if member.member_id == member_id:
                return member
        return None

    def _is_facilitator(self, state: ExerciseState, identifier: str) -> bool:
        """Check if identifier is a facilitator (team_id or member_id)."""
        if identifier == state.facilitator_id:
            return True
        for team in state.teams:
            if team.team_type == "white":
                if team.team_id == identifier:
                    return True
                for member in team.members:
                    if member.member_id == identifier:
                        return True
        return False

    def _is_facilitator_team(self, state: ExerciseState, team_id: str) -> bool:
        """Check if a team is a facilitator/white team."""
        return any(team.team_id == team_id and team.team_type == "white" for team in state.teams)
