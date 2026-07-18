#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the InjectService — crisis inject engine."""

from datetime import UTC, datetime

from api.models.exercise_models import (
    ExerciseEvent,
    ExerciseState,
    Inject,
    InjectTrigger,
    InjectType,
)
from api.models.schemas import (
    BusinessImpact,
    Department,
    GameState,
    Inventory,
    Organization,
    ThreatActorState,
)
from api.services.inject_service import InjectService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org():
    return Organization(
        id="org-1",
        name="Test Corp",
        description="Test",
        industry="Technology",
        size="medium",
        departments=[
            Department(
                id="d1",
                name="IT",
                description="IT",
                business_function="Tech",
                systems=[],
                data_classification="internal",
            )
        ],
        threat_actors=[],
        security_posture="developing",
        compliance_frameworks=[],
    )


def _make_game_state(**overrides):
    defaults = dict(
        session_id="s1",
        organization=_make_org(),
        current_scenario="test",
        player_role="mixed",
        inventory=Inventory(),
        status="in-progress",
    )
    defaults.update(overrides)
    return GameState(**defaults)


def _make_exercise_state(**overrides):
    defaults = dict(
        name="Test Exercise",
        game_state=_make_game_state(),
        phase="active",
        current_round=1,
    )
    defaults.update(overrides)
    return ExerciseState(**defaults)


# ---------------------------------------------------------------------------
# Template Loading
# ---------------------------------------------------------------------------


class TestTemplateLoading:
    def test_templates_loaded_from_data_dir(self):
        """InjectService loads templates from data/inject_templates/ on init."""
        svc = InjectService()
        # Should have loaded at least the generic templates
        categories = svc.get_template_categories()
        assert isinstance(categories, list)

    def test_get_all_templates_returns_dict(self):
        svc = InjectService()
        all_templates = svc.get_all_templates()
        assert isinstance(all_templates, dict)

    def test_get_templates_missing_category_returns_empty(self):
        svc = InjectService()
        assert svc.get_templates("nonexistent_category") == []


# ---------------------------------------------------------------------------
# create_inject
# ---------------------------------------------------------------------------


class TestCreateInject:
    def test_create_inject_valid_type(self):
        svc = InjectService()
        inject = svc.create_inject(
            inject_type="media_inquiry",
            title="Press Call",
            content="A reporter is asking questions.",
            severity="high",
        )
        assert inject.inject_type == InjectType.MEDIA_INQUIRY
        assert inject.title == "Press Call"
        assert inject.severity == "high"
        assert inject.inject_id  # UUID assigned

    def test_create_inject_invalid_type_defaults(self):
        svc = InjectService()
        inject = svc.create_inject(
            inject_type="totally_invalid",
            title="Fallback",
            content="Content",
        )
        assert inject.inject_type == InjectType.NEWS_ARTICLE  # default

    def test_create_inject_with_trigger(self):
        svc = InjectService()
        inject = svc.create_inject(
            inject_type="ceo_demand",
            title="CEO Wants Answers",
            content="Brief me now.",
            trigger_type="time",
            trigger_value=30,
        )
        assert inject.trigger.trigger_type == "time"
        assert inject.trigger.trigger_value == 30

    def test_create_inject_with_target_teams(self):
        svc = InjectService()
        inject = svc.create_inject(
            inject_type="vendor_alert",
            title="Vendor Advisory",
            content="Critical patch available.",
            target_teams=["blue-1", "blue-2"],
        )
        assert inject.target_teams == ["blue-1", "blue-2"]


# ---------------------------------------------------------------------------
# create_inject_from_template
# ---------------------------------------------------------------------------


class TestCreateInjectFromTemplate:
    def test_from_template_basic(self):
        svc = InjectService()
        template = {
            "inject_type": "regulator_call",
            "title": "Regulator Notice",
            "content": "You must comply within 72h.",
            "severity": "critical",
            "requires_response": True,
        }
        inject = svc.create_inject_from_template(template)
        assert inject.inject_type == InjectType.REGULATOR_CALL
        assert inject.requires_response is True
        assert inject.severity == "critical"

    def test_from_template_override_trigger(self):
        svc = InjectService()
        template = {
            "inject_type": "news_article",
            "title": "Breaking News",
            "content": "Report of breach.",
            "suggested_trigger_type": "round",
        }
        inject = svc.create_inject_from_template(
            template,
            trigger_type="time",
            trigger_value=15,
        )
        assert inject.trigger.trigger_type == "time"
        assert inject.trigger.trigger_value == 15


# ---------------------------------------------------------------------------
# evaluate_triggers
# ---------------------------------------------------------------------------


class TestEvaluateTriggers:
    def _make_pending_inject(self, trigger_type, trigger_value=None):
        return Inject(
            inject_type=InjectType.NEWS_ARTICLE,
            title=f"Inject ({trigger_type})",
            content="Test content",
            trigger=InjectTrigger(
                trigger_type=trigger_type,
                trigger_value=trigger_value,
            ),
        )

    def test_time_trigger_fires(self):
        svc = InjectService()
        state = _make_exercise_state()
        inject = self._make_pending_inject("time", 10)
        state.pending_injects = [inject]

        fired = svc.evaluate_triggers(state, elapsed_minutes=15)
        assert len(fired) == 1
        assert fired[0].delivered is True
        assert len(state.pending_injects) == 0
        assert len(state.injects) == 1

    def test_time_trigger_does_not_fire_early(self):
        svc = InjectService()
        state = _make_exercise_state()
        inject = self._make_pending_inject("time", 30)
        state.pending_injects = [inject]

        fired = svc.evaluate_triggers(state, elapsed_minutes=10)
        assert len(fired) == 0
        assert len(state.pending_injects) == 1

    def test_round_trigger_fires(self):
        svc = InjectService()
        state = _make_exercise_state(current_round=3)
        inject = self._make_pending_inject("round", 2)
        state.pending_injects = [inject]

        fired = svc.evaluate_triggers(state)
        assert len(fired) == 1

    def test_condition_trigger_fires_on_log_match(self):
        svc = InjectService()
        state = _make_exercise_state()
        state.exercise_log = [
            ExerciseEvent(
                event_type="team_action",
                description="ransomware detected on server",
            ),
        ]
        inject = self._make_pending_inject("condition", "ransomware")
        state.pending_injects = [inject]

        fired = svc.evaluate_triggers(state)
        assert len(fired) == 1

    def test_event_trigger_fires_on_event_type(self):
        svc = InjectService()
        state = _make_exercise_state()
        state.exercise_log = [
            ExerciseEvent(
                event_type="inject",
                description="Inject delivered",
            ),
        ]
        inject = self._make_pending_inject("event", "inject")
        state.pending_injects = [inject]

        fired = svc.evaluate_triggers(state)
        assert len(fired) == 1

    def test_manual_trigger_never_fires(self):
        svc = InjectService()
        state = _make_exercise_state()
        inject = self._make_pending_inject("manual")
        state.pending_injects = [inject]

        fired = svc.evaluate_triggers(state, elapsed_minutes=9999)
        assert len(fired) == 0


# ---------------------------------------------------------------------------
# suggest_inject — heuristic-based suggestions
# ---------------------------------------------------------------------------


class TestSuggestInject:
    def test_heuristic_media_inquiry(self):
        """Heuristic 1: downtime > 0.5h => media inquiry."""
        svc = InjectService()
        gs = _make_game_state(
            business_impact=BusinessImpact(
                downtime_hours=1.0,
                records_compromised=0,
            )
        )
        es = _make_exercise_state(game_state=gs)

        inject = svc.suggest_inject(gs, es)
        assert inject is not None
        assert inject.inject_type == InjectType.MEDIA_INQUIRY

    def test_heuristic_regulator(self):
        """Heuristic 2: records > 1000 => regulator call."""
        svc = InjectService()
        gs = _make_game_state(
            business_impact=BusinessImpact(
                downtime_hours=0,
                records_compromised=5000,
            )
        )
        es = _make_exercise_state(game_state=gs)

        inject = svc.suggest_inject(gs, es)
        assert inject is not None
        assert inject.inject_type == InjectType.REGULATOR_CALL

    def test_heuristic_ceo_demand(self):
        """Heuristic 3: downtime > 2h => CEO demand."""
        svc = InjectService()
        gs = _make_game_state(
            business_impact=BusinessImpact(
                downtime_hours=3.0,
                records_compromised=0,
            )
        )
        # Mark media inquiry as already delivered so heuristic 1 doesn't fire
        es = _make_exercise_state(game_state=gs)
        es.injects = [
            Inject(
                inject_type=InjectType.MEDIA_INQUIRY,
                title="Already delivered",
                content="x",
                trigger=InjectTrigger(trigger_type="manual"),
                delivered=True,
            ),
        ]

        inject = svc.suggest_inject(gs, es)
        assert inject is not None
        assert inject.inject_type == InjectType.CEO_DEMAND

    def test_heuristic_technical_failure_ransomware(self):
        """Heuristic 4: ransomware technique active => technical failure."""
        svc = InjectService()
        gs = _make_game_state(
            threat_states={
                "ta-1": ThreatActorState(
                    threat_actor_id="ta-1",
                    status="active",
                    active_techniques=["T1486"],  # ransomware
                    last_update=datetime.now(UTC),
                ),
            },
        )
        es = _make_exercise_state(game_state=gs)

        inject = svc.suggest_inject(gs, es)
        assert inject is not None
        assert inject.inject_type == InjectType.TECHNICAL_FAILURE

    def test_heuristic_customer_complaint_exfil(self):
        """Heuristic 5: exfiltration technique => customer complaint."""
        svc = InjectService()
        gs = _make_game_state(
            threat_states={
                "ta-1": ThreatActorState(
                    threat_actor_id="ta-1",
                    status="active",
                    active_techniques=["T1041"],  # exfiltration
                    last_update=datetime.now(UTC),
                ),
            },
        )
        es = _make_exercise_state(game_state=gs)

        inject = svc.suggest_inject(gs, es)
        assert inject is not None
        assert inject.inject_type == InjectType.CUSTOMER_COMPLAINT

    def test_heuristic_vendor_alert_extended(self):
        """Heuristic 6: round >= 3 => vendor alert."""
        svc = InjectService()
        gs = _make_game_state()
        es = _make_exercise_state(game_state=gs, current_round=4)

        inject = svc.suggest_inject(gs, es)
        assert inject is not None
        assert inject.inject_type == InjectType.VENDOR_ALERT

    def test_no_suggestion_when_all_delivered(self):
        """Returns None when no heuristic triggers."""
        svc = InjectService()
        gs = _make_game_state()
        es = _make_exercise_state(game_state=gs, current_round=1)

        inject = svc.suggest_inject(gs, es)
        assert inject is None


# ---------------------------------------------------------------------------
# record_response / get_unresponded_injects
# ---------------------------------------------------------------------------


class TestResponseTracking:
    def test_record_response_success(self):
        svc = InjectService()
        es = _make_exercise_state()
        inject = Inject(
            inject_id="inj-1",
            inject_type=InjectType.REGULATOR_CALL,
            title="Regulator",
            content="Respond now",
            trigger=InjectTrigger(trigger_type="manual"),
            delivered=True,
            requires_response=True,
        )
        es.injects = [inject]

        result = svc.record_response(es, "inj-1", "blue-1", "We are investigating.")
        assert result is True
        assert "blue-1" in inject.responses

    def test_record_response_inject_not_found(self):
        svc = InjectService()
        es = _make_exercise_state()
        result = svc.record_response(es, "no-such-id", "blue-1", "Response")
        assert result is False

    def test_get_unresponded_injects(self):
        svc = InjectService()
        es = _make_exercise_state()
        inject = Inject(
            inject_id="inj-2",
            inject_type=InjectType.CEO_DEMAND,
            title="CEO",
            content="Brief me",
            trigger=InjectTrigger(trigger_type="manual"),
            delivered=True,
            requires_response=True,
        )
        es.injects = [inject]

        unresponded = svc.get_unresponded_injects(es, "blue-1")
        assert len(unresponded) == 1
        assert unresponded[0].inject_id == "inj-2"

    def test_get_unresponded_excludes_wrong_team(self):
        svc = InjectService()
        es = _make_exercise_state()
        inject = Inject(
            inject_id="inj-3",
            inject_type=InjectType.CEO_DEMAND,
            title="CEO",
            content="Brief me",
            trigger=InjectTrigger(trigger_type="manual"),
            delivered=True,
            requires_response=True,
            target_teams=["red-1"],
        )
        es.injects = [inject]

        unresponded = svc.get_unresponded_injects(es, "blue-1")
        assert len(unresponded) == 0
