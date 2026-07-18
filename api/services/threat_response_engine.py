#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Threat Response Engine - Simulates dynamic threat actor behavior during gameplay.
"""

import logging
import random
from datetime import datetime

from api.models import GameState, IncidentEvent, Organization, ThreatActor, ThreatActorState

logger = logging.getLogger(__name__)


class ThreatResponseEngine:
    """
    Simulates threat actor responses to player actions.
    Threat actors react dynamically based on detection level and player actions.
    """

    def __init__(self):
        """Initialize the threat response engine."""
        pass

    def initialize_threat_states(self, organization: Organization) -> dict[str, ThreatActorState]:
        """
        Initialize threat actor states for all threats in the scenario.
        All threats start active with base aggression levels.

        Args:
            organization: The organization with threat actors

        Returns:
            Dictionary mapping threat_actor_id to ThreatActorState
        """
        threat_states = {}

        for threat in organization.threat_actors:
            # Set initial aggression based on sophistication
            base_aggression = {"script-kiddie": 30, "hacktivist": 50, "organized-crime": 70, "nation-state": 85}.get(
                threat.sophistication, 50
            )

            threat_states[threat.id] = ThreatActorState(
                threat_actor_id=threat.id,
                status="active",
                current_tactics=threat.ttps[:2] if threat.ttps else [],  # Start with first 2 TTPs
                systems_compromised=[],
                detection_level=0,
                aggression_level=base_aggression,
                last_action="Initial access attempt",
                last_update=datetime.now(),
                notes=f"{threat.name} has begun operations",
            )

        logger.info(f"Initialized {len(threat_states)} threat actor states")
        return threat_states

    def evaluate_player_action(self, action: str, game_state: GameState) -> dict[str, any]:
        """
        Evaluate how threat actors respond to a player action.

        Args:
            action: Player's action description
            game_state: Current game state

        Returns:
            Dictionary with threat response data including new events
        """
        action_lower = action.lower()
        responses = {"threat_updates": [], "new_events": [], "system_impacts": []}

        # Determine action type
        is_detection_action = any(
            word in action_lower for word in ["scan", "investigate", "analyze", "check", "monitor", "detect"]
        )
        is_containment_action = any(
            word in action_lower for word in ["isolate", "block", "shutdown", "disable", "quarantine", "contain"]
        )
        is_mitigation_action = any(word in action_lower for word in ["patch", "fix", "remediate", "update", "remove"])

        # Process each active threat
        for threat_id, threat_state in game_state.threat_states.items():
            if threat_state.status not in ["active", "contained"]:
                continue  # Skip eliminated/dormant threats

            threat_actor = self._find_threat_actor(game_state.organization, threat_id)
            if not threat_actor:
                continue

            # Detection actions increase detection level
            if is_detection_action:
                detection_increase = random.randint(10, 25)
                threat_state.detection_level = min(100, threat_state.detection_level + detection_increase)

                if threat_state.detection_level > 60:
                    # Threat is aware they're being detected - may change tactics
                    response = self._generate_evasion_response(threat_actor, threat_state, game_state)
                    responses["threat_updates"].append(response)
                    responses["new_events"].extend(response.get("events", []))

            # Containment actions may contain or provoke threats
            if is_containment_action:
                if random.random() < 0.6:  # 60% chance of successful containment
                    old_status = threat_state.status
                    threat_state.status = "contained"
                    threat_state.aggression_level = max(20, threat_state.aggression_level - 30)

                    event = IncidentEvent(
                        timestamp=datetime.now(),
                        event_type="consequence",
                        description=f"{threat_actor.name} has been contained by player actions",
                        severity="medium",
                        actor="system",
                    )
                    responses["new_events"].append(event)
                    responses["threat_updates"].append(
                        {
                            "threat_id": threat_id,
                            "old_status": old_status,
                            "new_status": "contained",
                            "message": f"Successfully contained {threat_actor.name}",
                        }
                    )
                else:
                    # Containment failed - threat escalates
                    response = self._generate_escalation_response(threat_actor, threat_state, game_state)
                    responses["threat_updates"].append(response)
                    responses["new_events"].extend(response.get("events", []))

            # Mitigation actions reduce threat effectiveness — remove compromised
            # systems that are being patched.
            if is_mitigation_action and threat_state.systems_compromised:
                removed_systems = []
                for sys_id in threat_state.systems_compromised[:]:
                    if random.random() < 0.4:  # 40% chance to remove per system
                        threat_state.systems_compromised.remove(sys_id)
                        removed_systems.append(sys_id)

                if removed_systems:
                    event = IncidentEvent(
                        timestamp=datetime.now(),
                        event_type="consequence",
                        description=f"Mitigation actions have removed {len(removed_systems)} systems from {threat_actor.name}'s control",
                        severity="low",
                        actor="system",
                    )
                    responses["new_events"].append(event)

        return responses

    def escalate_threat(self, threat_id: str, game_state: GameState) -> dict[str, any]:
        """
        Escalate threat actor activities (automatic escalation over time).

        Args:
            threat_id: ID of threat actor to escalate
            game_state: Current game state

        Returns:
            Dictionary with escalation data
        """
        if threat_id not in game_state.threat_states:
            return {"success": False, "reason": "Threat not found"}

        threat_state = game_state.threat_states[threat_id]
        if threat_state.status != "active":
            return {"success": False, "reason": f"Threat is {threat_state.status}"}

        threat_actor = self._find_threat_actor(game_state.organization, threat_id)
        if not threat_actor:
            return {"success": False, "reason": "Threat actor not found in organization"}

        return self._generate_escalation_response(threat_actor, threat_state, game_state)

    def adapt_tactics(self, threat_id: str, game_state: GameState) -> bool:
        """
        Change threat actor tactics in response to detection.

        Args:
            threat_id: ID of threat actor
            game_state: Current game state

        Returns:
            True if tactics were adapted
        """
        if threat_id not in game_state.threat_states:
            return False

        threat_state = game_state.threat_states[threat_id]
        threat_actor = self._find_threat_actor(game_state.organization, threat_id)

        if not threat_actor or not threat_actor.ttps:
            return False

        # Change to different TTPs
        available_ttps = [ttp for ttp in threat_actor.ttps if ttp not in threat_state.current_tactics]
        if available_ttps:
            new_tactic = random.choice(available_ttps)
            threat_state.current_tactics = [new_tactic]
            threat_state.last_action = f"Switched tactics to: {new_tactic}"
            threat_state.last_update = datetime.now()
            logger.info(f"{threat_actor.name} adapted tactics to {new_tactic}")
            return True

        return False

    def generate_threat_event(
        self, threat_state: ThreatActorState, threat_actor: ThreatActor, game_state: GameState
    ) -> IncidentEvent:
        """
        Generate a random threat event based on current state.

        Args:
            threat_state: Current threat state
            threat_actor: Threat actor definition
            game_state: Current game state

        Returns:
            IncidentEvent describing the threat action
        """
        # Select action based on aggression level
        if threat_state.aggression_level > 70:
            actions = [
                f"{threat_actor.name} is attempting lateral movement across the network",
                f"{threat_actor.name} is escalating privileges on compromised systems",
                f"{threat_actor.name} is exfiltrating sensitive data",
                f"{threat_actor.name} has deployed ransomware on compromised systems",
            ]
            severity = "critical"
        elif threat_state.aggression_level > 40:
            actions = [
                f"{threat_actor.name} is establishing persistence mechanisms",
                f"{threat_actor.name} is conducting reconnaissance on internal systems",
                f"{threat_actor.name} is attempting to compromise additional systems",
                f"{threat_actor.name} is accessing sensitive databases",
            ]
            severity = "high"
        else:
            actions = [
                f"{threat_actor.name} is probing network defenses",
                f"{threat_actor.name} is gathering information about the environment",
                f"{threat_actor.name} activity detected but no immediate impact",
                f"{threat_actor.name} is testing security controls",
            ]
            severity = "medium"

        description = random.choice(actions)

        # Add tactic context if available
        if threat_state.current_tactics:
            tactic = threat_state.current_tactics[0]
            description += f" using {tactic}"

        return IncidentEvent(
            timestamp=datetime.now(),
            event_type="escalation",
            description=description,
            severity=severity,
            actor="threat_actor",
        )

    def _generate_escalation_response(
        self, threat_actor: ThreatActor, threat_state: ThreatActorState, game_state: GameState
    ) -> dict[str, any]:
        """Generate a threat escalation response."""
        # Increase aggression
        threat_state.aggression_level = min(100, threat_state.aggression_level + random.randint(10, 20))

        # Potentially compromise a new system
        new_compromise = None
        available_systems = []
        for dept in game_state.organization.departments:
            for system in dept.systems:
                if system.id not in threat_state.systems_compromised:
                    # Check if system is already compromised by other threats or offline
                    if system.id in game_state.system_states:
                        sys_state = game_state.system_states[system.id]
                        if sys_state.status not in ["compromised", "offline"]:
                            available_systems.append(system.id)
                    else:
                        available_systems.append(system.id)

        if available_systems and random.random() < 0.5:  # 50% chance of new compromise
            new_compromise = random.choice(available_systems)
            threat_state.systems_compromised.append(new_compromise)

        # Generate event
        if new_compromise:
            event_desc = f"{threat_actor.name} has escalated and compromised an additional system"
        else:
            event_desc = f"{threat_actor.name} is increasing attack intensity"

        event = IncidentEvent(
            timestamp=datetime.now(),
            event_type="escalation",
            description=event_desc,
            severity="high",
            actor="threat_actor",
        )

        threat_state.last_action = "Escalated operations"
        threat_state.last_update = datetime.now()

        return {
            "threat_id": threat_actor.id,
            "action": "escalation",
            "new_compromise": new_compromise,
            "aggression_level": threat_state.aggression_level,
            "events": [event],
        }

    def _generate_evasion_response(
        self, threat_actor: ThreatActor, threat_state: ThreatActorState, game_state: GameState
    ) -> dict[str, any]:
        """Generate a threat evasion response when detection is high."""
        # Threat is aware of detection - may go dormant or change tactics
        if threat_state.detection_level > 80:
            # High detection - consider going dormant
            if random.random() < 0.3:  # 30% chance to go dormant
                threat_state.status = "dormant"
                threat_state.aggression_level = max(10, threat_state.aggression_level - 40)
                event_desc = f"{threat_actor.name} has gone dormant after detecting heavy monitoring"
                severity = "medium"
            else:
                # Change tactics
                self.adapt_tactics(threat_actor.id, game_state)
                event_desc = f"{threat_actor.name} has changed tactics to evade detection"
                severity = "medium"
        else:
            # Medium detection - just reduce aggression slightly
            threat_state.aggression_level = max(20, threat_state.aggression_level - 15)
            event_desc = f"{threat_actor.name} is taking evasive action in response to detection efforts"
            severity = "low"

        event = IncidentEvent(
            timestamp=datetime.now(),
            event_type="consequence",
            description=event_desc,
            severity=severity,
            actor="threat_actor",
        )

        threat_state.last_action = "Evasive maneuver"
        threat_state.last_update = datetime.now()

        return {
            "threat_id": threat_actor.id,
            "action": "evasion",
            "detection_level": threat_state.detection_level,
            "events": [event],
        }

    def _find_threat_actor(self, organization: Organization, threat_id: str) -> ThreatActor | None:
        """Find a threat actor by ID in the organization."""
        for threat in organization.threat_actors:
            if threat.id == threat_id:
                return threat
        return None

    def get_threat_status_summary(self, game_state: GameState) -> dict[str, int]:
        """
        Get a summary of threat actor statuses.

        Args:
            game_state: Current game state

        Returns:
            Dictionary with counts of threats in each status
        """
        summary = {
            "active": 0,
            "contained": 0,
            "eliminated": 0,
            "dormant": 0,
            "total": len(game_state.organization.threat_actors),
        }

        for state in game_state.threat_states.values():
            summary[state.status] = summary.get(state.status, 0) + 1

        return summary
