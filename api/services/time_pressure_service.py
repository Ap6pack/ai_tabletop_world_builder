"""
Time Pressure Service for managing countdown timers and automatic escalation.

This service manages:
- Countdown timers for objectives and threats
- Automatic threat escalation over time
- Time-based scoring multipliers
- Deadline tracking and expiry events
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import uuid

from api.models import (
    GameState,
    Timer,
    EscalationRule,
    Objective,
    ThreatActorState,
    SystemState,
)
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class TimePressureService:
    """
    Service for managing time pressure mechanics during incidents.
    """

    # Time-based score multipliers (bonus for fast completion)
    TIME_MULTIPLIERS = {
        "easy": {
            "fast": 1.5,      # < 50% of time limit
            "normal": 1.0,    # 50-100% of time limit
            "slow": 0.5,      # > 100% of time limit
        },
        "medium": {
            "fast": 2.0,
            "normal": 1.0,
            "slow": 0.3,
        },
        "hard": {
            "fast": 3.0,
            "normal": 1.0,
            "slow": 0.1,
        }
    }

    def __init__(self):
        """Initialize the time pressure service."""
        pass

    def create_timer(
        self,
        name: str,
        description: str,
        duration_minutes: int,
        is_critical: bool = False,
        on_expiry_event: str = "Time limit exceeded",
        related_objective_id: Optional[str] = None,
    ) -> Timer:
        """
        Create a new countdown timer.

        Args:
            name: Timer name
            description: Timer description
            duration_minutes: Duration in minutes
            is_critical: Whether this is a critical timer
            on_expiry_event: Description of what happens on expiry
            related_objective_id: Optional objective ID

        Returns:
            New Timer object
        """
        logger.info(f"Creating timer: {name} ({duration_minutes}min, critical={is_critical})")

        duration_seconds = duration_minutes * 60
        return Timer(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            duration_seconds=duration_seconds,
            remaining_seconds=duration_seconds,
            started_at=datetime.now(timezone.utc),
            is_critical=is_critical,
            on_expiry_event=on_expiry_event,
            related_objective_id=related_objective_id,
        )

    def create_escalation_rule(
        self,
        trigger_time_minutes: int,
        action: str,
        target_id: Optional[str] = None,
        severity_increase: int = 10,
        description: str = "Automatic escalation",
    ) -> EscalationRule:
        """
        Create an automatic escalation rule.

        Args:
            trigger_time_minutes: Minutes after game start to trigger
            action: Action type ("threat_escalate", "system_degrade", "spread", "alert")
            target_id: Target system or threat ID
            severity_increase: Severity increase amount
            description: Rule description

        Returns:
            New EscalationRule object
        """
        return EscalationRule(
            id=str(uuid.uuid4()),
            trigger_time_minutes=trigger_time_minutes,
            action=action,
            target_id=target_id,
            severity_increase=severity_increase,
            description=description,
            triggered=False,
        )

    def update_timers(
        self,
        game_state: GameState,
        time_elapsed_minutes: int,
    ) -> Tuple[GameState, List[str]]:
        """
        Update all active timers and check for expiries.

        Args:
            game_state: Current game state
            time_elapsed_minutes: Total time elapsed since game start

        Returns:
            Tuple of (updated game_state, list of expiry messages)
        """
        expiry_messages = []

        for timer in game_state.timers:
            was_expired = timer.is_expired

            # Calculate elapsed time since timer started (using game time, not real time)
            # Game time is more appropriate for turn-based scenarios
            elapsed = time_elapsed_minutes * 60

            # Update remaining seconds
            timer.remaining_seconds = max(0, timer.duration_seconds - int(elapsed))

            # Check for expiry (only report if just expired)
            if timer.is_expired and not was_expired:
                # Timer just expired
                expiry_messages.append(
                    f"⏰ **Timer Expired:** {timer.name} - {timer.on_expiry_event}"
                )

                # If related to an objective, mark it as failed
                if timer.related_objective_id:
                    for obj in game_state.objectives:
                        if obj.id == timer.related_objective_id and obj.status != "completed":
                            obj.status = "failed"
                            expiry_messages.append(
                                f"❌ **Objective Failed:** {obj.description} (time limit exceeded)"
                            )

        return game_state, expiry_messages

    def check_escalation_rules(
        self,
        game_state: GameState,
        time_elapsed_minutes: int,
    ) -> Tuple[GameState, List[str]]:
        """
        Check and trigger escalation rules based on elapsed time.

        Args:
            game_state: Current game state
            time_elapsed_minutes: Total time elapsed since game start

        Returns:
            Tuple of (updated game_state, list of escalation messages)
        """
        escalation_messages = []

        for rule in game_state.escalation_rules:
            if rule.triggered:
                continue  # Already triggered

            # Check if it's time to trigger
            if time_elapsed_minutes >= rule.trigger_time_minutes:
                logger.info(f"Triggering escalation rule: {rule.action} at {time_elapsed_minutes}min")
                rule.triggered = True

                # Execute the escalation action
                if rule.action == "threat_escalate":
                    # Increase threat aggression
                    if rule.target_id and rule.target_id in game_state.threat_states:
                        threat_state = game_state.threat_states[rule.target_id]
                        old_aggression = threat_state.aggression_level
                        threat_state.aggression_level = min(100, old_aggression + rule.severity_increase)
                        threat_state.last_update = datetime.now(timezone.utc)

                        escalation_messages.append(
                            f"⚠️ **Threat Escalation:** {rule.description} "
                            f"(aggression {old_aggression}% → {threat_state.aggression_level}%)"
                        )

                elif rule.action == "system_degrade":
                    # Degrade system health
                    if rule.target_id and rule.target_id in game_state.system_states:
                        system_state = game_state.system_states[rule.target_id]
                        old_health = system_state.health
                        system_state.health = max(0, old_health - rule.severity_increase)
                        system_state.last_update = datetime.now(timezone.utc)

                        escalation_messages.append(
                            f"⚠️ **System Degradation:** {rule.description} "
                            f"(health {old_health}% → {system_state.health}%)"
                        )

                        # If health reaches 0, mark as offline
                        if system_state.health == 0 and system_state.status != "offline":
                            system_state.status = "offline"
                            escalation_messages.append(
                                f"🔴 **System Offline:** System has gone offline due to degradation"
                            )

                elif rule.action == "spread":
                    # Threat spreads to new systems
                    escalation_messages.append(
                        f"🔴 **Threat Spreading:** {rule.description} - "
                        f"Threat actor attempting lateral movement"
                    )

                elif rule.action == "alert":
                    # General alert
                    escalation_messages.append(
                        f"🚨 **Alert:** {rule.description}"
                    )

        return game_state, escalation_messages

    def calculate_time_multiplier(
        self,
        objective: Objective,
        completion_time_minutes: int,
    ) -> float:
        """
        Calculate time-based score multiplier for objective completion.

        Args:
            objective: The completed objective
            completion_time_minutes: Time taken to complete

        Returns:
            Score multiplier
        """
        if not objective.time_limit_minutes:
            return 1.0  # No time limit = no multiplier

        difficulty = objective.difficulty
        time_limit = objective.time_limit_minutes

        # Calculate percentage of time used
        time_percentage = (completion_time_minutes / time_limit) * 100

        if time_percentage < 50:
            # Fast completion
            return self.TIME_MULTIPLIERS[difficulty]["fast"]
        elif time_percentage <= 100:
            # Normal completion
            return self.TIME_MULTIPLIERS[difficulty]["normal"]
        else:
            # Slow completion (over time limit)
            return self.TIME_MULTIPLIERS[difficulty]["slow"]

    def get_timer_status(self, timer: Timer) -> Dict[str, any]:
        """
        Get human-readable timer status.

        Args:
            timer: Timer object

        Returns:
            Status dictionary
        """
        remaining_minutes = timer.remaining_seconds // 60
        remaining_seconds = timer.remaining_seconds % 60

        if timer.is_expired:
            status = "expired"
            urgency = "critical"
        elif timer.remaining_seconds < 300:  # < 5 minutes
            status = "urgent"
            urgency = "high"
        elif timer.remaining_seconds < 600:  # < 10 minutes
            status = "warning"
            urgency = "medium"
        else:
            status = "active"
            urgency = "low"

        return {
            "status": status,
            "urgency": urgency,
            "remaining_minutes": remaining_minutes,
            "remaining_seconds": remaining_seconds,
            "time_string": f"{remaining_minutes}:{remaining_seconds:02d}",
            "percentage_remaining": (timer.remaining_seconds / timer.duration_seconds) * 100,
        }

    def create_objective_timer(
        self,
        objective: Objective,
    ) -> Optional[Timer]:
        """
        Create a timer for an objective with a time limit.

        Args:
            objective: Objective to create timer for

        Returns:
            Timer or None if objective has no time limit
        """
        if not objective.time_limit_minutes:
            return None

        return self.create_timer(
            name=f"Objective: {objective.description[:30]}...",
            description=f"Time limit for objective: {objective.description}",
            duration_minutes=objective.time_limit_minutes,
            is_critical=objective.difficulty == "hard",
            on_expiry_event=f"Objective failed: {objective.description}",
            related_objective_id=objective.id,
        )

    def create_scenario_escalation_rules(
        self,
        scenario_type: str,
        difficulty: str,
        duration_minutes: int,
        threat_ids: List[str],
        system_ids: List[str],
    ) -> List[EscalationRule]:
        """
        Create escalation rules based on scenario parameters.

        Args:
            scenario_type: Type of scenario
            difficulty: Difficulty level
            duration_minutes: Expected scenario duration
            threat_ids: List of threat actor IDs
            system_ids: List of system IDs

        Returns:
            List of escalation rules
        """
        rules = []

        # Escalation timing based on difficulty
        escalation_intervals = {
            "beginner": [0.5, 0.75],     # 50%, 75% of duration
            "intermediate": [0.33, 0.66],  # 33%, 66% of duration
            "advanced": [0.25, 0.5, 0.75],  # 25%, 50%, 75% of duration
            "expert": [0.2, 0.4, 0.6, 0.8],  # 20%, 40%, 60%, 80% of duration
        }

        intervals = escalation_intervals.get(difficulty, [0.5])

        # Create threat escalation rules
        for i, interval in enumerate(intervals):
            trigger_time = int(duration_minutes * interval)

            if threat_ids:
                # Pick a threat to escalate (cycle through them)
                threat_id = threat_ids[i % len(threat_ids)]

                rules.append(self.create_escalation_rule(
                    trigger_time_minutes=trigger_time,
                    action="threat_escalate",
                    target_id=threat_id,
                    severity_increase=15 if difficulty == "expert" else 10,
                    description=f"Threat actor increases aggression (checkpoint {i+1})"
                ))

            # System degradation rules (if systems available)
            if system_ids and i < len(system_ids):
                rules.append(self.create_escalation_rule(
                    trigger_time_minutes=trigger_time + 2,  # Slightly after threat escalation
                    action="system_degrade",
                    target_id=system_ids[i],
                    severity_increase=20,
                    description=f"System health degrading due to ongoing attack"
                ))

        # Add spread rule for advanced scenarios
        if difficulty in ["advanced", "expert"] and threat_ids:
            spread_time = int(duration_minutes * 0.6)
            rules.append(self.create_escalation_rule(
                trigger_time_minutes=spread_time,
                action="spread",
                target_id=threat_ids[0],
                severity_increase=0,
                description="Threat actor attempts lateral movement to additional systems"
            ))

        return rules

    def get_active_timers_summary(self, game_state: GameState) -> Dict[str, any]:
        """
        Get a summary of all active timers.

        Args:
            game_state: Current game state

        Returns:
            Summary dictionary
        """
        active_timers = [t for t in game_state.timers if not t.is_expired]
        expired_timers = [t for t in game_state.timers if t.is_expired]
        critical_timers = [t for t in active_timers if t.is_critical]

        # Find most urgent timer
        most_urgent = None
        if active_timers:
            most_urgent = min(active_timers, key=lambda t: t.remaining_seconds)

        return {
            "total_timers": len(game_state.timers),
            "active_count": len(active_timers),
            "expired_count": len(expired_timers),
            "critical_count": len(critical_timers),
            "most_urgent": most_urgent,
            "active_timers": active_timers,
            "expired_timers": expired_timers,
        }

    def get_next_escalation(self, game_state: GameState, time_elapsed_minutes: int) -> Optional[Dict[str, any]]:
        """
        Get information about the next scheduled escalation.

        Args:
            game_state: Current game state
            time_elapsed_minutes: Current elapsed time

        Returns:
            Next escalation info or None
        """
        pending_rules = [r for r in game_state.escalation_rules if not r.triggered]

        if not pending_rules:
            return None

        # Find next rule to trigger
        next_rule = min(pending_rules, key=lambda r: r.trigger_time_minutes)

        minutes_until = next_rule.trigger_time_minutes - time_elapsed_minutes

        return {
            "rule": next_rule,
            "minutes_until": max(0, minutes_until),
            "trigger_time": next_rule.trigger_time_minutes,
            "description": next_rule.description,
            "action": next_rule.action,
        }
