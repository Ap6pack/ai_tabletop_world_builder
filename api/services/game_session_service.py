"""
Game session service for managing war gaming sessions.
"""
from typing import Optional, Dict, Any
from api.models import GameState, Organization, Inventory, IncidentEvent
from datetime import datetime
import uuid
import json
import os


class GameSessionService:
    """Manages war gaming sessions and game state."""

    def __init__(self):
        """Initialize the game session service."""
        self.sessions_dir = "data/sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)

    def create_session(
        self,
        organization: Organization,
        scenario_type: str,
        player_role: str,
        difficulty: str
    ) -> GameState:
        """
        Create a new game session.

        Args:
            organization: The organization/scenario to use
            scenario_type: Type of scenario (incident-response, threat-hunting, etc.)
            player_role: Role the player assumes
            difficulty: Difficulty level

        Returns:
            Initial GameState
        """
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        # Create initial inventory based on role
        inventory = self._create_initial_inventory(player_role)

        # Create initial game state
        game_state = GameState(
            session_id=session_id,
            organization=organization,
            current_scenario=scenario_type,
            player_role=player_role,
            inventory=inventory,
            incident_timeline=[],
            score=0,
            time_elapsed=0,
            objectives_completed=[],
            objectives_failed=[],
            status="in-progress"
        )

        # Save initial state
        self.save_session(game_state)

        return game_state

    def _create_initial_inventory(self, player_role: str) -> Inventory:
        """Create initial inventory based on player role."""

        # Base tools available to all roles
        base_tools = {
            "SIEM Access": 1,
            "Email": 1,
            "Documentation": 1
        }

        # Role-specific tools
        role_tools = {
            "soc-analyst": {
                "IDS/IPS": 1,
                "Log Analysis Tools": 1,
                "Threat Intelligence Feed": 1
            },
            "incident-responder": {
                "IDS/IPS": 1,
                "EDR Console": 1,
                "Forensics Toolkit": 1,
                "Network Analyzer": 1,
                "Incident Response Playbook": 1
            },
            "security-engineer": {
                "Firewall Console": 1,
                "Vulnerability Scanner": 1,
                "Configuration Management": 1,
                "Network Diagram": 1,
                "EDR Console": 1
            },
            "ciso": {
                "Executive Dashboard": 1,
                "Risk Management Tools": 1,
                "Incident Reports": 1,
                "Board Communications": 1
            }
        }

        tools = {**base_tools, **role_tools.get(player_role, {})}

        # Role-based access levels
        access_mapping = {
            "soc-analyst": ["user", "siem"],
            "incident-responder": ["user", "admin", "siem"],
            "security-engineer": ["user", "admin", "network"],
            "ciso": ["user", "admin", "executive"],
            "mixed": ["user"]
        }

        return Inventory(
            tools=tools,
            access_levels=access_mapping.get(player_role, ["user"]),
            credentials=[]
        )

    def get_session(self, session_id: str) -> Optional[GameState]:
        """
        Load a game session.

        Args:
            session_id: Session ID

        Returns:
            GameState if found, None otherwise
        """
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")

        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r') as f:
            data = json.load(f)

        return GameState(**data)

    def save_session(self, game_state: GameState) -> str:
        """
        Save game session to disk.

        Args:
            game_state: Current game state

        Returns:
            Path to saved file
        """
        filepath = os.path.join(self.sessions_dir, f"{game_state.session_id}.json")

        with open(filepath, 'w') as f:
            json.dump(game_state.model_dump(), f, indent=2, default=str)

        return filepath

    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Optional[GameState]:
        """
        Update game session with new data.

        Args:
            session_id: Session ID
            updates: Dictionary of updates to apply

        Returns:
            Updated GameState or None if session not found
        """
        game_state = self.get_session(session_id)

        if game_state is None:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(game_state, key):
                setattr(game_state, key, value)

        # Save updated state
        self.save_session(game_state)

        return game_state

    def add_event(
        self,
        session_id: str,
        event_type: str,
        description: str,
        severity: str,
        actor: str = "system"
    ) -> Optional[GameState]:
        """
        Add an event to the incident timeline.

        Args:
            session_id: Session ID
            event_type: Type of event (detection, action, consequence, escalation)
            description: Event description
            severity: Event severity
            actor: Who caused the event (system, player, threat_actor)

        Returns:
            Updated GameState or None if session not found
        """
        game_state = self.get_session(session_id)

        if game_state is None:
            return None

        event = IncidentEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            description=description,
            severity=severity,
            actor=actor
        )

        game_state.incident_timeline.append(event)
        game_state.time_elapsed += 1  # Increment time

        self.save_session(game_state)

        return game_state

    def update_inventory(
        self,
        session_id: str,
        tool_changes: Optional[Dict[str, int]] = None,
        access_changes: Optional[list] = None,
        credential_changes: Optional[list] = None
    ) -> Optional[GameState]:
        """
        Update player inventory.

        Args:
            session_id: Session ID
            tool_changes: Tools to add/remove (negative to remove)
            access_changes: Access levels to add
            credential_changes: Credentials to add

        Returns:
            Updated GameState or None if session not found
        """
        game_state = self.get_session(session_id)

        if game_state is None:
            return None

        # Update tools
        if tool_changes:
            for tool, change in tool_changes.items():
                current = game_state.inventory.tools.get(tool, 0)
                new_value = current + change
                if new_value > 0:
                    game_state.inventory.tools[tool] = new_value
                elif tool in game_state.inventory.tools:
                    del game_state.inventory.tools[tool]

        # Update access levels
        if access_changes:
            for access in access_changes:
                if access not in game_state.inventory.access_levels:
                    game_state.inventory.access_levels.append(access)

        # Update credentials
        if credential_changes:
            for cred in credential_changes:
                if cred not in game_state.inventory.credentials:
                    game_state.inventory.credentials.append(cred)

        self.save_session(game_state)

        return game_state

    def update_score(
        self,
        session_id: str,
        points: int,
        reason: str
    ) -> Optional[GameState]:
        """
        Update player score.

        Args:
            session_id: Session ID
            points: Points to add (can be negative)
            reason: Reason for score change

        Returns:
            Updated GameState or None if session not found
        """
        game_state = self.get_session(session_id)

        if game_state is None:
            return None

        game_state.score += points

        # Add event for significant score changes
        if abs(points) >= 10:
            severity = "info" if points > 0 else "low"
            self.add_event(
                session_id,
                "action",
                f"Score change: {points:+d} points - {reason}",
                severity,
                "system"
            )

        self.save_session(game_state)

        return game_state

    def complete_objective(
        self,
        session_id: str,
        objective: str,
        success: bool = True
    ) -> Optional[GameState]:
        """
        Mark an objective as completed or failed.

        Args:
            session_id: Session ID
            objective: Objective description
            success: Whether objective was completed successfully

        Returns:
            Updated GameState or None if session not found
        """
        game_state = self.get_session(session_id)

        if game_state is None:
            return None

        if success:
            if objective not in game_state.objectives_completed:
                game_state.objectives_completed.append(objective)
                self.update_score(session_id, 25, f"Completed objective: {objective}")
        else:
            if objective not in game_state.objectives_failed:
                game_state.objectives_failed.append(objective)
                self.update_score(session_id, -10, f"Failed objective: {objective}")

        self.save_session(game_state)

        return game_state

    def end_session(
        self,
        session_id: str,
        status: str = "completed"
    ) -> Optional[GameState]:
        """
        End a game session.

        Args:
            session_id: Session ID
            status: Final status (completed, failed)

        Returns:
            Final GameState or None if session not found
        """
        game_state = self.get_session(session_id)

        if game_state is None:
            return None

        game_state.status = status

        # Add final event
        self.add_event(
            session_id,
            "action",
            f"Session ended - Status: {status}",
            "info",
            "system"
        )

        self.save_session(game_state)

        return game_state

    def list_sessions(self, status_filter: Optional[str] = None) -> list:
        """
        List all game sessions.

        Args:
            status_filter: Optional filter by status

        Returns:
            List of session metadata
        """
        sessions = []

        if not os.path.exists(self.sessions_dir):
            return sessions

        for filename in os.listdir(self.sessions_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.sessions_dir, filename)

                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    if status_filter and data.get('status') != status_filter:
                        continue

                    sessions.append({
                        "session_id": data.get("session_id"),
                        "organization": data.get("organization", {}).get("name"),
                        "player_role": data.get("player_role"),
                        "status": data.get("status"),
                        "score": data.get("score"),
                        "time_elapsed": data.get("time_elapsed"),
                        "created_at": data.get("incident_timeline", [{}])[0].get("timestamp") if data.get("incident_timeline") else None
                    })
                except Exception:
                    continue

        return sorted(sessions, key=lambda x: x.get("created_at", ""), reverse=True)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a game session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully

        Raises:
            FileNotFoundError: If session file doesn't exist
        """
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Session {session_id} not found")

        os.remove(filepath)
        return True
