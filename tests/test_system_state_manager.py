#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Tests for SystemStateManager — system health and status tracking."""

import pytest

from api.models.schemas import (
    Department,
    GameState,
    Inventory,
    Organization,
    System,
)
from api.services.system_state_manager import SystemStateManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_system(sid="sys-1", name="Web Server", criticality="critical"):
    return System(
        id=sid,
        name=name,
        description=name,
        type="server",
        os="Linux",
        services=["nginx"],
        criticality=criticality,
    )


def _make_org(systems=None):
    if systems is None:
        systems = [_make_system()]
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
                systems=systems,
                data_classification="internal",
            )
        ],
        threat_actors=[],
        security_posture="developing",
        compliance_frameworks=[],
    )


def _make_game_state(systems=None, **overrides):
    org = _make_org(systems)
    defaults = dict(
        session_id="s1",
        organization=org,
        current_scenario="test",
        player_role="mixed",
        inventory=Inventory(),
        status="in-progress",
    )
    defaults.update(overrides)
    return GameState(**defaults)


# ---------------------------------------------------------------------------
# initialize_system_states
# ---------------------------------------------------------------------------


class TestInitialize:
    def test_initialize_all_online(self):
        mgr = SystemStateManager()
        org = _make_org([_make_system("s1"), _make_system("s2", "DB Server")])
        states = mgr.initialize_system_states(org)
        assert len(states) == 2
        for _sid, state in states.items():
            assert state.status == "online"
            assert state.health == 100

    def test_initialize_empty_org(self):
        mgr = SystemStateManager()
        org = _make_org([])
        states = mgr.initialize_system_states(org)
        assert states == {}


# ---------------------------------------------------------------------------
# update_system_state
# ---------------------------------------------------------------------------


class TestUpdateState:
    def test_update_status_and_health(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)

        result = mgr.update_system_state(
            gs,
            "sys-1",
            "compromised",
            health_change=-40,
            reason="Malware detected",
        )
        assert result.status == "compromised"
        assert result.health == 60

    def test_health_clamped_at_zero(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)

        mgr.update_system_state(gs, "sys-1", "offline", health_change=-200)
        assert gs.system_states["sys-1"].health == 0

    def test_health_clamped_at_100(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)

        mgr.update_system_state(gs, "sys-1", "patched", health_change=50)
        assert gs.system_states["sys-1"].health == 100

    def test_update_affected_services(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)

        mgr.update_system_state(
            gs,
            "sys-1",
            "compromised",
            affected_services=["web", "api"],
        )
        assert gs.system_states["sys-1"].affected_services == ["web", "api"]

    def test_update_unknown_system_raises(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        # No system states initialized, and sys-999 not in org
        with pytest.raises(ValueError, match="not found"):
            mgr.update_system_state(gs, "sys-999", "offline")


# ---------------------------------------------------------------------------
# get_compromised_systems / get_critical_systems_at_risk
# ---------------------------------------------------------------------------


class TestQuerySystems:
    def test_get_compromised_systems(self):
        mgr = SystemStateManager()
        gs = _make_game_state(
            [
                _make_system("s1"),
                _make_system("s2", "DB"),
            ]
        )
        gs.system_states = mgr.initialize_system_states(gs.organization)
        mgr.apply_compromise(gs, "s1", "high")

        compromised = mgr.get_compromised_systems(gs)
        assert "s1" in compromised
        assert "s2" not in compromised

    def test_get_critical_systems_at_risk(self):
        mgr = SystemStateManager()
        gs = _make_game_state(
            [
                _make_system("s1", "Critical Server", "critical"),
                _make_system("s2", "Low Server", "low"),
            ]
        )
        gs.system_states = mgr.initialize_system_states(gs.organization)
        mgr.apply_compromise(gs, "s1", "critical")

        at_risk = mgr.get_critical_systems_at_risk(gs)
        assert "s1" in at_risk
        assert "s2" not in at_risk


# ---------------------------------------------------------------------------
# apply_compromise / apply_recovery
# ---------------------------------------------------------------------------


class TestCompromiseRecovery:
    @pytest.mark.parametrize(
        "severity,expected_max_health",
        [
            ("low", 80),
            ("medium", 65),
            ("high", 50),
            ("critical", 30),
        ],
    )
    def test_apply_compromise_severity(self, severity, expected_max_health):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)

        mgr.apply_compromise(gs, "sys-1", severity)
        assert gs.system_states["sys-1"].status == "compromised"
        assert gs.system_states["sys-1"].health == expected_max_health

    def test_apply_recovery_partial(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)
        mgr.apply_compromise(gs, "sys-1", "high")  # health -> 50

        mgr.apply_recovery(gs, "sys-1", "partial")
        assert gs.system_states["sys-1"].status == "recovering"
        assert gs.system_states["sys-1"].health == 80  # 50 + 30

    def test_apply_recovery_full(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)
        mgr.apply_compromise(gs, "sys-1", "critical")  # health -> 30

        mgr.apply_recovery(gs, "sys-1", "full")
        assert gs.system_states["sys-1"].status == "online"
        assert gs.system_states["sys-1"].health == 100


# ---------------------------------------------------------------------------
# get_system_status_summary / check_system_availability
# ---------------------------------------------------------------------------


class TestSummaryAndAvailability:
    def test_status_summary(self):
        mgr = SystemStateManager()
        gs = _make_game_state(
            [
                _make_system("s1"),
                _make_system("s2", "DB"),
                _make_system("s3", "Mail"),
            ]
        )
        gs.system_states = mgr.initialize_system_states(gs.organization)
        mgr.apply_compromise(gs, "s1", "high")

        summary = mgr.get_system_status_summary(gs)
        assert summary["total"] == 3
        assert summary["compromised"] == 1
        assert summary["online"] == 2

    def test_system_available_when_online(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)
        assert mgr.check_system_availability("sys-1", gs) is True

    def test_system_unavailable_when_offline(self):
        mgr = SystemStateManager()
        gs = _make_game_state()
        gs.system_states = mgr.initialize_system_states(gs.organization)
        mgr.update_system_state(gs, "sys-1", "offline", health_change=-100)
        assert mgr.check_system_availability("sys-1", gs) is False
