#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Alternative Path Service for suggesting alternative actions at key decision points.

Analyzes incident timelines and game state to identify consequential player
choices and suggest better alternatives for after-action review.
"""

from datetime import datetime

from api.models import (
    AlternativePath,
    GameState,
    IncidentEvent,
)
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class AlternativePathService:
    """Service for suggesting alternative actions at key decision points."""

    # Rule-based alternative suggestions keyed by scenario pattern
    ALTERNATIVE_RULES: dict[str, dict] = {
        "investigation_during_active_threat": {
            "condition_description": "Player investigated while threat was active",
            "suggested_action": "Initiate containment procedures on affected systems",
            "expected_outcome": (
                "Prioritize containment before investigation during active threats. "
                "Containing the threat first limits blast radius and preserves evidence."
            ),
            "difficulty": "medium",
        },
        "no_early_detection": {
            "condition_description": "No detection actions taken in the first few minutes",
            "suggested_action": "Run initial system scans in the first few minutes",
            "expected_outcome": (
                "Early scanning establishes a baseline and may detect indicators of "
                "compromise before the threat actor can establish persistence."
            ),
            "difficulty": "easy",
        },
        "ignored_critical_systems": {
            "condition_description": "Critical systems were not prioritized",
            "suggested_action": "Focus response efforts on critical infrastructure first",
            "expected_outcome": (
                "Critical systems carry the highest business impact when compromised. "
                "Prioritizing their protection reduces downtime costs and limits "
                "cascading failures across dependent services."
            ),
            "difficulty": "medium",
        },
        "escalation_lateral_movement": {
            "condition_description": "Threat escalated via lateral movement",
            "suggested_action": "Isolate affected systems to prevent lateral movement",
            "expected_outcome": (
                "Network segmentation and system isolation prevent the threat actor "
                "from moving laterally, buying time to investigate and remediate."
            ),
            "difficulty": "hard",
        },
        "budget_exhausted_non_critical": {
            "condition_description": "Budget spent on non-critical items",
            "suggested_action": "Prioritize resource allocation toward critical systems and high-impact actions",
            "expected_outcome": (
                "Focusing budget on high-impact actions first ensures resources are "
                "available when needed most. Non-critical spending can be deferred."
            ),
            "difficulty": "medium",
        },
    }

    # Action categories used for classifying player actions
    ACTION_CATEGORIES: dict[str, list[str]] = {
        "investigation": ["investigate", "analyze", "check_logs", "examine", "review", "forensic", "inspect"],
        "detection": ["scan", "monitor", "detect", "alert", "search", "hunt"],
        "containment": ["isolate", "block", "quarantine", "contain", "segment", "disconnect", "disable"],
        "mitigation": ["patch", "restore", "rebuild", "fix", "remediate", "update", "harden"],
        "communication": ["notify", "report", "escalate", "brief", "communicate", "call"],
    }

    def __init__(self):
        """Initialize the alternative path service."""
        pass

    def suggest_alternatives(self, game_state: GameState) -> list[AlternativePath]:
        """Identify key decision points and suggest better alternatives."""
        logger.info(f"Generating alternative path suggestions for session {game_state.session_id}")
        alternatives: list[AlternativePath] = []

        decision_points = self.identify_decision_points(game_state.incident_timeline)
        logger.debug(f"Found {len(decision_points)} decision points")

        for point in decision_points:
            event = point.get("event")
            if event is None:
                continue
            alternative = self._generate_alternative(event, game_state)
            if alternative is not None:
                alternatives.append(alternative)

        # Check for global pattern-based alternatives
        for check_fn in (self._check_early_detection, self._check_critical_systems, self._check_budget_usage):
            alt = check_fn(game_state)
            if alt is not None:
                alternatives.append(alt)

        logger.info(f"Generated {len(alternatives)} alternative path suggestions")
        return alternatives

    def identify_decision_points(self, timeline: list[IncidentEvent]) -> list[dict]:
        """
        Find moments where the player made consequential choices.

        Decision points are: player actions followed by escalation events,
        player actions during high-severity situations, and the first action
        of each category type.
        """
        decision_points: list[dict] = []
        seen_categories: set = set()

        for i, event in enumerate(timeline):
            if event.actor != "player":
                continue

            is_decision_point = False
            reason = ""

            # Player action followed by escalation
            if i + 1 < len(timeline) and timeline[i + 1].event_type == "escalation":
                is_decision_point = True
                reason = "Action followed by escalation"

            # Action during high-severity situation
            if event.severity in ("critical", "high"):
                is_decision_point = True
                reason = reason or "Action during high-severity situation"

            # First action of each category type
            category = self._categorize_action(event.description)
            if category not in seen_categories:
                seen_categories.add(category)
                is_decision_point = True
                reason = reason or f"First {category} action"

            if is_decision_point:
                decision_points.append(
                    {
                        "event": event,
                        "index": i,
                        "reason": reason,
                        "category": category,
                        "timestamp": event.timestamp,
                    }
                )

        return decision_points

    def _generate_alternative(self, event: IncidentEvent, game_state: GameState) -> AlternativePath | None:
        """Generate a specific alternative for a decision point using rule-based suggestions."""
        category = self._categorize_action(event.description)
        decision_label = f"Turn at {event.timestamp.strftime('%H:%M:%S')}: {event.description}"

        # Rule: Investigation during active threat -> suggest containment
        if category == "investigation" and self._has_active_threat(game_state):
            rule = self.ALTERNATIVE_RULES["investigation_during_active_threat"]
            return AlternativePath(
                decision_point=decision_label,
                original_action=event.description,
                suggested_action=rule["suggested_action"],
                expected_outcome=rule["expected_outcome"],
                difficulty=rule["difficulty"],
            )

        # Rule: Escalation happened -> suggest counter-action (isolate systems)
        if self._followed_by_escalation(event, game_state.incident_timeline):
            rule = self.ALTERNATIVE_RULES["escalation_lateral_movement"]
            return AlternativePath(
                decision_point=decision_label,
                original_action=event.description,
                suggested_action=rule["suggested_action"],
                expected_outcome=rule["expected_outcome"],
                difficulty=rule["difficulty"],
            )

        return None

    def _check_early_detection(self, game_state: GameState) -> AlternativePath | None:
        """Check if the player ran detection actions in the first 5 minutes."""
        early_detection_found = False
        first_event_time: datetime | None = None

        for event in game_state.incident_timeline:
            if first_event_time is None:
                first_event_time = event.timestamp
            elapsed = (event.timestamp - first_event_time).total_seconds()
            if elapsed > 300:
                break
            if event.actor == "player" and self._categorize_action(event.description) == "detection":
                early_detection_found = True
                break

        if not early_detection_found and first_event_time is not None:
            rule = self.ALTERNATIVE_RULES["no_early_detection"]
            return AlternativePath(
                decision_point="Opening minutes of the incident",
                original_action="No detection actions taken in the first 5 minutes",
                suggested_action=rule["suggested_action"],
                expected_outcome=rule["expected_outcome"],
                difficulty=rule["difficulty"],
            )
        return None

    def _check_critical_systems(self, game_state: GameState) -> AlternativePath | None:
        """Check if compromised/offline critical systems were addressed by the player."""
        neglected_critical = [
            sid
            for sid, state in game_state.system_states.items()
            if state.status in ("compromised", "offline") and state.health < 50
        ]
        if not neglected_critical:
            return None

        # Check if player actions targeted these systems
        player_addressed: set = set()
        for event in game_state.incident_timeline:
            if event.actor != "player":
                continue
            if self._categorize_action(event.description) in ("containment", "mitigation"):
                for sys_id in neglected_critical:
                    if sys_id.lower() in event.description.lower():
                        player_addressed.add(sys_id)

        still_neglected = [s for s in neglected_critical if s not in player_addressed]
        if still_neglected:
            rule = self.ALTERNATIVE_RULES["ignored_critical_systems"]
            return AlternativePath(
                decision_point=f"Critical systems neglected: {', '.join(still_neglected[:3])}",
                original_action="Response efforts did not prioritize critical infrastructure",
                suggested_action=rule["suggested_action"],
                expected_outcome=rule["expected_outcome"],
                difficulty=rule["difficulty"],
            )
        return None

    def _check_budget_usage(self, game_state: GameState) -> AlternativePath | None:
        """Check if budget was exhausted while critical systems remain unresolved."""
        if game_state.resource_pool is None or game_state.resource_pool.budget_total == 0:
            return None

        pool = game_state.resource_pool
        budget_spent_pct = ((pool.budget_total - pool.budget_remaining) / pool.budget_total) * 100
        has_unresolved = any(state.status in ("compromised", "offline") for state in game_state.system_states.values())

        if budget_spent_pct > 70 and has_unresolved:
            rule = self.ALTERNATIVE_RULES["budget_exhausted_non_critical"]
            return AlternativePath(
                decision_point=f"Budget usage at {budget_spent_pct:.0f}% with unresolved critical systems",
                original_action="Budget allocated without prioritizing critical system recovery",
                suggested_action=rule["suggested_action"],
                expected_outcome=rule["expected_outcome"],
                difficulty=rule["difficulty"],
            )
        return None

    def _categorize_action(self, description: str) -> str:
        """Categorize a player action description into a known action category."""
        description_lower = description.lower()
        for category, keywords in self.ACTION_CATEGORIES.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category
        return "other"

    def _has_active_threat(self, game_state: GameState) -> bool:
        """Return True if any threat actor has 'active' status."""
        return any(ts.status == "active" for ts in game_state.threat_states.values())

    def _followed_by_escalation(self, event: IncidentEvent, timeline: list[IncidentEvent]) -> bool:
        """Return True if the given event is immediately followed by an escalation."""
        for i, e in enumerate(timeline):
            if e is event and i + 1 < len(timeline):
                return timeline[i + 1].event_type == "escalation"
        return False
