#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Real-time crisis inject service for multi-team tabletop exercises.

Provides:
- Template loading from sector-specific JSON files
- Pre-scripted inject creation with trigger evaluation (time, round, condition, event, manual)
- Dynamic inject suggestion based on game state heuristics
- Inject delivery tracking and team response recording
"""

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from api.models.exercise_models import (
    ExerciseState,
    Inject,
    InjectTrigger,
    InjectType,
)
from api.models.schemas import GameState
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# Inject Service
# ============================================================================


class InjectService:
    """Manages crisis injects for tabletop exercises.

    Two modes of operation:
    1. **Pre-scripted** - Facilitator loads templates or creates custom injects
       with triggers (time, round, condition). ``evaluate_triggers`` fires them
       automatically when conditions are met.
    2. **Dynamic** - ``suggest_inject`` uses heuristics against the current game
       state to recommend context-aware injects.
    """

    def __init__(self) -> None:
        self._templates: dict[str, list] = {}
        self._load_templates()

    # ------------------------------------------------------------------ #
    # Template Loading
    # ------------------------------------------------------------------ #

    def _load_templates(self) -> None:
        """Load inject templates from ``data/inject_templates/``."""
        templates_dir = Path(__file__).resolve().parent.parent.parent / "data" / "inject_templates"

        if not templates_dir.exists():
            logger.warning("Inject templates directory not found: %s", templates_dir)
            return

        for json_file in templates_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as fh:
                    data = json.load(fh)
                key = json_file.stem  # e.g. "generic", "financial_sector"
                self._templates[key] = data if isinstance(data, list) else []
                logger.info(
                    "Loaded %d inject templates from %s",
                    len(self._templates[key]),
                    json_file.name,
                )
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to load inject template %s: %s", json_file, exc)

        logger.info("Loaded inject templates from %d files", len(self._templates))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_template_categories(self) -> list[str]:
        """Return available template category names."""
        return list(self._templates.keys())

    def get_templates(self, category: str) -> list[dict]:
        """Return templates for a given category."""
        return self._templates.get(category, [])

    def get_all_templates(self) -> dict[str, list]:
        """Return all loaded templates keyed by category."""
        return dict(self._templates)

    def create_inject(
        self,
        inject_type: str,
        title: str,
        content: str,
        severity: str = "medium",
        trigger_type: str = "manual",
        trigger_value=None,
        target_teams: list[str] | None = None,
        requires_response: bool = False,
        response_time_limit_minutes: int | None = None,
        attack_technique_id: str | None = None,
    ) -> Inject:
        """Create a new inject, optionally from a trigger specification.

        Returns the ``Inject`` model ready to be queued on an exercise.
        """
        try:
            itype = InjectType(inject_type)
        except ValueError:
            itype = InjectType.NEWS_ARTICLE
            logger.warning(
                "Unknown inject type '%s', defaulting to news_article",
                inject_type,
            )

        inject = Inject(
            inject_id=str(uuid.uuid4()),
            inject_type=itype,
            title=title,
            content=content,
            trigger=InjectTrigger(
                trigger_type=trigger_type,
                trigger_value=trigger_value,
            ),
            target_teams=target_teams or [],
            severity=severity,
            requires_response=requires_response,
            response_time_limit_minutes=response_time_limit_minutes,
            attack_technique_id=attack_technique_id,
        )

        logger.info(
            "Created inject '%s' (type=%s, trigger=%s)",
            title,
            inject_type,
            trigger_type,
        )
        return inject

    def create_inject_from_template(
        self,
        template: dict,
        trigger_type: str | None = None,
        trigger_value=None,
        target_teams: list[str] | None = None,
    ) -> Inject:
        """Create an inject from a template dictionary."""
        return self.create_inject(
            inject_type=template.get("inject_type", "news_article"),
            title=template.get("title", "Untitled Inject"),
            content=template.get("content", ""),
            severity=template.get("severity", "medium"),
            trigger_type=trigger_type or template.get("suggested_trigger_type", "manual"),
            trigger_value=trigger_value,
            target_teams=target_teams,
            requires_response=template.get("requires_response", False),
            attack_technique_id=template.get("attack_technique_id"),
        )

    def evaluate_triggers(
        self,
        exercise_state: ExerciseState,
        elapsed_minutes: float = 0.0,
    ) -> list[Inject]:
        """Evaluate pending injects and return those whose triggers have fired.

        Trigger types:
        - ``time``  : fires when elapsed_minutes >= trigger_value
        - ``round`` : fires when current_round >= trigger_value
        - ``condition`` : fires when a regex pattern in trigger_value matches
          any recent event description in the exercise log
        - ``event`` : fires when the event type in trigger_value appears in the
          exercise log
        - ``manual`` : never fires automatically (facilitator must deliver)
        """
        fired: list[Inject] = []

        for inject in list(exercise_state.pending_injects):
            if inject.delivered:
                continue

            trigger = inject.trigger
            should_fire = False

            if trigger.trigger_type == "time":
                threshold = _safe_float(trigger.trigger_value, default=0.0)
                if elapsed_minutes >= threshold:
                    should_fire = True

            elif trigger.trigger_type == "round":
                threshold = _safe_int(trigger.trigger_value, default=1)
                if exercise_state.current_round >= threshold:
                    should_fire = True

            elif trigger.trigger_type == "condition":
                pattern = str(trigger.trigger_value) if trigger.trigger_value else ""
                if pattern and self._condition_matches(pattern, exercise_state):
                    should_fire = True

            elif trigger.trigger_type == "event":
                event_type = str(trigger.trigger_value) if trigger.trigger_value else ""
                if event_type and self._event_type_present(event_type, exercise_state):
                    should_fire = True

            # "manual" never auto-fires

            if should_fire:
                inject.delivered = True
                inject.delivered_at = datetime.now(UTC)
                fired.append(inject)
                logger.info(
                    "Inject triggered: '%s' (trigger=%s)",
                    inject.title,
                    trigger.trigger_type,
                )

        # Move fired injects from pending to delivered
        if fired:
            fired_ids = {i.inject_id for i in fired}
            exercise_state.pending_injects = [i for i in exercise_state.pending_injects if i.inject_id not in fired_ids]
            exercise_state.injects.extend(fired)

        return fired

    def suggest_inject(self, game_state: GameState, exercise_state: ExerciseState) -> Inject | None:
        """Suggest a context-aware inject based on current game state.

        Uses six heuristics to determine what inject would increase exercise
        realism and pressure:

        1. If breach is >30 min old with no media inject -> media inquiry
        2. If records_compromised > 1000 with no regulator inject -> regulator call
        3. If downtime_hours > 2 with no CEO inject -> CEO demand
        4. If ransomware technique active with no tech failure inject -> technical failure
        5. If data exfiltration detected with no customer inject -> customer complaint
        6. If incident uncontained after 3+ rounds -> vendor alert
        """
        delivered_types = {i.inject_type for i in exercise_state.injects if i.delivered}

        impact = game_state.business_impact
        if impact is None:
            downtime_hours = 0
            records = 0
        elif isinstance(impact, dict):
            downtime_hours = impact.get("downtime_hours", 0)
            records = impact.get("records_compromised", 0)
        else:
            downtime_hours = getattr(impact, "downtime_hours", 0)
            records = getattr(impact, "records_compromised", 0)

        # Collect active ATT&CK techniques across all threat states
        active_techniques: set = set()
        for ts in game_state.threat_states.values():
            active_techniques.update(ts.active_techniques)

        # Heuristic 1: Media inquiry after prolonged incident
        if downtime_hours > 0.5 and InjectType.MEDIA_INQUIRY not in delivered_types:
            return self.create_inject(
                inject_type="media_inquiry",
                title="Journalist Requests Comment on Reported Incident",
                content=(
                    "A journalist from a major publication has contacted the "
                    "communications department requesting comment on rumors of "
                    "a cybersecurity incident at your organization. They claim "
                    "to have sources confirming the breach and are publishing "
                    "within the hour."
                ),
                severity="high",
                trigger_type="manual",
                requires_response=True,
            )

        # Heuristic 2: Regulator call after significant data exposure
        if records > 1000 and InjectType.REGULATOR_CALL not in delivered_types:
            return self.create_inject(
                inject_type="regulator_call",
                title="Regulatory Authority Demands Incident Report",
                content=(
                    f"The relevant regulatory authority has been made aware of "
                    f"the incident involving {records:,} records. They are "
                    f"requiring a preliminary incident report within 72 hours "
                    f"detailing scope, affected individuals, and remediation "
                    f"steps taken."
                ),
                severity="critical",
                trigger_type="manual",
                requires_response=True,
            )

        # Heuristic 3: CEO demand after extended downtime
        if downtime_hours > 2 and InjectType.CEO_DEMAND not in delivered_types:
            return self.create_inject(
                inject_type="ceo_demand",
                title="CEO Demands Immediate Status Update",
                content=(
                    "The CEO has learned about the ongoing incident through "
                    "external channels and is demanding an immediate briefing. "
                    "They have a board meeting tomorrow and need talking points "
                    "on the incident impact, recovery timeline, and customer "
                    "communication strategy."
                ),
                severity="high",
                trigger_type="manual",
                requires_response=True,
            )

        # Heuristic 4: Technical failure if ransomware techniques are active
        ransomware_techniques = {"T1486", "T1490", "T1489", "T1529"}
        if active_techniques & ransomware_techniques and InjectType.TECHNICAL_FAILURE not in delivered_types:
            return self.create_inject(
                inject_type="technical_failure",
                title="Critical System Recovery Failure",
                content=(
                    "Attempts to restore affected systems from backup have "
                    "encountered unexpected failures. Backup integrity "
                    "verification shows corruption in the most recent backup "
                    "sets. The disaster recovery team estimates an additional "
                    "24-48 hours before clean restores can be attempted."
                ),
                severity="critical",
                trigger_type="manual",
                attack_technique_id="T1490",
            )

        # Heuristic 5: Customer complaint if exfiltration detected
        exfil_techniques = {"T1041", "T1048", "T1567", "T1537"}
        if active_techniques & exfil_techniques and InjectType.CUSTOMER_COMPLAINT not in delivered_types:
            return self.create_inject(
                inject_type="customer_complaint",
                title="Major Client Demands Security Assessment",
                content=(
                    "Your largest enterprise client has been contacted by "
                    "journalists about the incident. They are demanding an "
                    "emergency security assessment and threatening contract "
                    "termination unless they receive a detailed remediation "
                    "plan within 48 hours."
                ),
                severity="high",
                trigger_type="manual",
                requires_response=True,
            )

        # Heuristic 6: Vendor alert after extended exercise
        if exercise_state.current_round >= 3 and InjectType.VENDOR_ALERT not in delivered_types:
            return self.create_inject(
                inject_type="vendor_alert",
                title="Security Vendor Issues Urgent Advisory",
                content=(
                    "A key security vendor has issued an urgent advisory "
                    "related to the attack vector used in your incident. "
                    "They recommend immediate patching and configuration "
                    "changes to prevent further exploitation. The advisory "
                    "includes IOCs that should be checked against your "
                    "environment."
                ),
                severity="high",
                trigger_type="manual",
                attack_technique_id="T1190",
            )

        return None

    def get_inject_by_id(self, exercise_state: ExerciseState, inject_id: str) -> Inject | None:
        """Find an inject by ID across delivered and pending lists."""
        for inject in exercise_state.injects:
            if inject.inject_id == inject_id:
                return inject
        for inject in exercise_state.pending_injects:
            if inject.inject_id == inject_id:
                return inject
        return None

    def record_response(
        self,
        exercise_state: ExerciseState,
        inject_id: str,
        team_id: str,
        response: str,
    ) -> bool:
        """Record a team's response to an inject.

        Returns True if the inject was found and the response recorded.
        """
        inject = self.get_inject_by_id(exercise_state, inject_id)
        if not inject:
            logger.warning("Inject %s not found for response recording", inject_id)
            return False

        inject.responses[team_id] = response
        logger.info("Team %s responded to inject '%s'", team_id, inject.title)
        return True

    def get_unresponded_injects(self, exercise_state: ExerciseState, team_id: str) -> list[Inject]:
        """Return delivered injects that require a response from a team."""
        result: list[Inject] = []
        for inject in exercise_state.injects:
            if not inject.delivered or not inject.requires_response:
                continue
            # Check if team should respond
            if inject.target_teams and team_id not in inject.target_teams:
                continue
            if team_id not in inject.responses:
                result.append(inject)
        return result

    # ------------------------------------------------------------------ #
    # Internal Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _condition_matches(pattern: str, exercise_state: ExerciseState) -> bool:
        """Check if a regex condition matches any recent exercise event."""
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error:
            logger.warning("Invalid condition regex: %s", pattern)
            return False

        # Check last 20 events in the exercise log
        recent_events = exercise_state.exercise_log[-20:]
        for event in recent_events:
            if compiled.search(event.description):
                return True

        # Also check game state incident timeline
        if exercise_state.game_state:
            recent_timeline = exercise_state.game_state.incident_timeline[-20:]
            for event in recent_timeline:
                if compiled.search(event.description):
                    return True

        return False

    @staticmethod
    def _event_type_present(event_type: str, exercise_state: ExerciseState) -> bool:
        """Check if a specific event type has occurred in the exercise."""
        return any(event.event_type == event_type for event in exercise_state.exercise_log)


# ============================================================================
# Module-level helpers
# ============================================================================


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
