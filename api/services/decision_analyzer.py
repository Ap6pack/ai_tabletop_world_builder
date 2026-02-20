"""
Decision Analyzer Service for evaluating player decisions from war game sessions.

This service analyzes:
- Individual player actions from incident timelines
- Decision quality scoring using rule-based evaluation
- Action categorization via keyword matching
- Impact assessment based on subsequent events
"""
from datetime import datetime, timezone
from typing import List, Optional

from api.models import GameState, DecisionEvaluation, IncidentEvent, Objective
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class DecisionAnalyzer:
    """Service for analyzing individual player decisions from a war game session
    timeline. Extracts player actions, categorizes them, and evaluates each
    decision using rule-based scoring that considers timing, consequences,
    objective alignment, and threat context."""

    CATEGORY_KEYWORDS = {
        "detection": ["scan", "check logs", "monitor", "detect", "observe", "review logs",
                       "check alerts", "inspect", "search for", "check siem", "query", "hunt"],
        "containment": ["isolate", "block", "quarantine", "disable", "disconnect",
                         "shut down", "firewall", "contain", "segment", "lock"],
        "mitigation": ["patch", "restore", "fix", "update", "remediate", "repair",
                        "rebuild", "recover", "reinstall", "rollback", "upgrade"],
        "communication": ["alert", "notify", "report", "escalate", "inform",
                           "brief", "communicate", "call", "email", "warn"],
        "investigation": ["investigate", "analyze", "forensic", "correlate", "trace",
                           "examine", "deep dive", "root cause", "determine", "assess",
                           "review evidence", "memory dump"],
    }
    PASSIVE_KEYWORDS = ["wait", "observe", "monitor", "watch", "hold",
                        "standby", "do nothing", "pause", "delay"]

    def __init__(self):
        """Initialize the decision analyzer."""
        pass

    def analyze_timeline(self, game_state: GameState) -> List[DecisionEvaluation]:
        """Extract all player actions from the incident timeline and evaluate each.

        Args:
            game_state: The complete game state with incident timeline.

        Returns:
            List of DecisionEvaluation objects, one per player action.
        """
        logger.info(
            f"Analyzing timeline for session {game_state.session_id}: "
            f"{len(game_state.incident_timeline)} events"
        )
        evaluations: List[DecisionEvaluation] = []
        for index, event in enumerate(game_state.incident_timeline):
            if event.actor != "player" or event.event_type != "action":
                continue
            evaluations.append(self.evaluate_decision(event, game_state, index))
        logger.info(f"Timeline analysis complete: {len(evaluations)} decisions evaluated")
        return evaluations

    def categorize_action(self, action_description: str) -> str:
        """Map action description to a category using keyword matching.

        Args:
            action_description: Free-text description of the player's action.

        Returns:
            One of: detection, containment, mitigation, communication,
            investigation, or other.
        """
        action_lower = action_description.lower()
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in action_lower:
                    return category
        return "other"

    def evaluate_decision(
        self, event: IncidentEvent, game_state: GameState, event_index: int,
    ) -> DecisionEvaluation:
        """Score a single player decision using rule-based evaluation.

        Scoring: base 50, +20 positive consequence, +15 timely action,
        +10 objective match, -15 escalation, -10 passive in high threat.
        Capped at 0-100.

        Args:
            event: The player's action event.
            game_state: The full game state for context.
            event_index: Index of this event in the incident timeline.

        Returns:
            DecisionEvaluation with score, impact, category, and reasoning.
        """
        score = 50
        reasoning_parts: List[str] = []
        category = self.categorize_action(event.description)
        subsequent_events = game_state.incident_timeline[event_index + 1:]
        impact = self._get_action_impact(event, subsequent_events)
        context = self._get_context(game_state, event_index)

        if impact == "positive":
            score += 20
            reasoning_parts.append("Action led to positive outcome (+20)")
        total_events = len(game_state.incident_timeline)
        if total_events > 0 and (event_index / max(total_events, 1)) <= 0.30:
            score += 15
            reasoning_parts.append("Action taken early in the incident timeline (+15)")
        if self._matches_objective_category(category, game_state.objectives):
            score += 10
            reasoning_parts.append(f"Category '{category}' aligns with active objective (+10)")
        if impact == "negative":
            score -= 15
            reasoning_parts.append("Action followed by escalation or negative event (-15)")
        if self._is_passive_during_high_threat(event, game_state):
            score -= 10
            reasoning_parts.append("Passive action during active high-threat state (-10)")

        score = max(0, min(100, score))
        if not reasoning_parts:
            reasoning_parts.append("Standard action with neutral outcome")
        reasoning = ". ".join(reasoning_parts) + "."
        better_alternative = self._suggest_alternative(event, category, score, game_state)

        evaluation = DecisionEvaluation(
            action=event.description, timestamp=event.timestamp,
            context=context, quality_score=score, impact=impact,
            reasoning=reasoning, better_alternative=better_alternative,
            category=category,
        )
        logger.debug(
            f"Decision evaluated: '{event.description[:50]}...' "
            f"score={score}, impact={impact}, category={category}"
        )
        return evaluation

    def _get_action_impact(
        self, event: IncidentEvent, subsequent_events: List[IncidentEvent],
    ) -> str:
        """Check the next 1-3 events to determine action impact.

        Args:
            event: The player's action event.
            subsequent_events: Events occurring after the player's action.

        Returns:
            One of: positive, negative, or neutral.
        """
        lookahead = subsequent_events[:3]
        if not lookahead:
            return "neutral"
        has_positive = False
        has_negative = False
        for subsequent in lookahead:
            if subsequent.event_type == "consequence":
                if subsequent.severity in ("low", "info"):
                    has_positive = True
                elif subsequent.severity in ("critical", "high"):
                    has_negative = True
            if subsequent.event_type == "escalation":
                has_negative = True
            if subsequent.event_type == "detection" and subsequent.actor == "system":
                has_positive = True
        if has_negative:
            return "negative"
        if has_positive:
            return "positive"
        return "neutral"

    def _get_context(self, game_state: GameState, event_index: int) -> str:
        """Build context string from surrounding events and system state.

        Args:
            game_state: The full game state.
            event_index: Index of the current event in the timeline.

        Returns:
            Human-readable context string.
        """
        parts: List[str] = []
        timeline = game_state.incident_timeline
        start = max(0, event_index - 2)
        preceding = timeline[start:event_index]
        if preceding:
            descs = [f"[{e.event_type}/{e.severity}] {e.description}" for e in preceding]
            parts.append("Preceding: " + "; ".join(descs))
        following = timeline[event_index + 1: event_index + 3]
        if following:
            descs = [f"[{e.event_type}/{e.severity}] {e.description}" for e in following]
            parts.append("Following: " + "; ".join(descs))
        threats = [
            f"{tid} (aggression={ts.aggression_level}%)"
            for tid, ts in game_state.threat_states.items() if ts.status == "active"
        ]
        if threats:
            parts.append("Active threats: " + ", ".join(threats))
        troubled = [
            f"{sid} ({ss.status}, health={ss.health}%)"
            for sid, ss in game_state.system_states.items()
            if ss.status in ("compromised", "offline")
        ]
        if troubled:
            parts.append("Affected systems: " + ", ".join(troubled))
        return " | ".join(parts) if parts else "No additional context available."

    def _matches_objective_category(
        self, action_category: str, objectives: List[Objective],
    ) -> bool:
        """Check if an action category matches any active objective type.

        Args:
            action_category: The categorized action type.
            objectives: List of game objectives.

        Returns:
            True if the action category aligns with an active objective.
        """
        category_to_objective = {
            "detection": "detect", "containment": "contain",
            "mitigation": "mitigate", "communication": "report",
            "investigation": "investigate",
        }
        objective_type = category_to_objective.get(action_category)
        if not objective_type:
            return False
        return any(
            obj.type == objective_type and obj.status in ("pending", "in-progress")
            for obj in objectives
        )

    def _is_passive_during_high_threat(
        self, event: IncidentEvent, game_state: GameState,
    ) -> bool:
        """Determine if action was passive while threats were highly active.

        Passive means matching passive keywords while at least one active
        threat has aggression above 70%.

        Args:
            event: The player's action event.
            game_state: The full game state with threat information.

        Returns:
            True if the action was passive during a high-threat state.
        """
        action_lower = event.description.lower()
        if not any(kw in action_lower for kw in self.PASSIVE_KEYWORDS):
            return False
        return any(
            ts.status == "active" and ts.aggression_level > 70
            for ts in game_state.threat_states.values()
        )

    def _suggest_alternative(
        self, event: IncidentEvent, category: str, score: int,
        game_state: GameState,
    ) -> Optional[str]:
        """Suggest a better alternative action if the decision scored below 50.

        Args:
            event: The player's action event.
            category: The determined action category.
            score: The computed quality score.
            game_state: The full game state for context.

        Returns:
            Suggested alternative string, or None if score is adequate.
        """
        if score >= 50:
            return None
        compromised = [
            sid for sid, ss in game_state.system_states.items()
            if ss.status == "compromised"
        ]
        active_threats = [
            ts for ts in game_state.threat_states.values() if ts.status == "active"
        ]
        if compromised and category != "containment":
            return (
                f"Consider isolating compromised systems "
                f"({', '.join(compromised[:2])}) to prevent lateral movement."
            )
        if active_threats and category not in ("detection", "investigation"):
            return (
                "Consider investigating active threats to gather intelligence "
                "before taking further action."
            )
        if score < 30 and category != "communication":
            return (
                "Consider escalating the incident and notifying relevant "
                "stakeholders for additional support."
            )
        if category == "other":
            return (
                "Consider taking a more targeted action such as scanning "
                "affected systems or reviewing security logs."
            )
        return None
