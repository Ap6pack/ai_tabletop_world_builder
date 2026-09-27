#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for ThreatResponseEngine (randomness pinned for determinism)."""

import pytest

import api.services.threat_response_engine as tre
from api.services.threat_response_engine import ThreatResponseEngine


@pytest.fixture
def engine():
    return ThreatResponseEngine()


def _pin_random(monkeypatch, value):
    monkeypatch.setattr(tre.random, "random", lambda: value)
    monkeypatch.setattr(tre.random, "randint", lambda a, b: b)
    monkeypatch.setattr(tre.random, "choice", lambda seq: seq[0])


def test_initialize_threat_states(engine, sample_organization):
    states = engine.initialize_threat_states(sample_organization)
    assert set(states) == {"ta-1"}
    assert states["ta-1"].status == "active"


def test_detection_raises_detection_level_and_triggers_evasion(engine, sample_game_state, monkeypatch):
    _pin_random(monkeypatch, 0.9)
    state = sample_game_state.threat_states["ta-1"]
    state.detection_level = 50
    result = engine.evaluate_player_action("Investigate the SIEM alerts", sample_game_state)
    assert state.detection_level == 75
    assert result["threat_updates"][0]["action"] == "evasion"
    assert result["new_events"]


def test_high_detection_can_send_threat_dormant(engine, sample_game_state, monkeypatch):
    _pin_random(monkeypatch, 0.1)
    state = sample_game_state.threat_states["ta-1"]
    state.detection_level = 90
    engine.evaluate_player_action("scan everything", sample_game_state)
    assert state.status == "dormant"


def test_successful_containment(engine, sample_game_state, monkeypatch):
    _pin_random(monkeypatch, 0.1)
    result = engine.evaluate_player_action("Isolate the web server", sample_game_state)
    assert sample_game_state.threat_states["ta-1"].status == "contained"
    assert result["threat_updates"][0]["new_status"] == "contained"


def test_failed_containment_escalates(engine, sample_game_state, monkeypatch):
    _pin_random(monkeypatch, 0.9)
    # First draw fails containment (needs < 0.6); second compromises a new system (< 0.5).
    monkeypatch.setattr(tre.random, "random", iter([0.9, 0.1]).__next__)
    state = sample_game_state.threat_states["ta-1"]
    before = state.aggression_level
    result = engine.evaluate_player_action("block the attacker", sample_game_state)
    assert result["threat_updates"][0]["action"] == "escalation"
    assert state.aggression_level > before
    assert result["threat_updates"][0]["new_compromise"] == "sys-web-1"


def test_mitigation_removes_compromised_systems(engine, sample_game_state, monkeypatch):
    _pin_random(monkeypatch, 0.1)
    state = sample_game_state.threat_states["ta-1"]
    state.systems_compromised = ["sys-web-1"]
    result = engine.evaluate_player_action("patch the server", sample_game_state)
    assert state.systems_compromised == []
    assert "removed 1 systems" in result["new_events"][0].description


def test_inactive_threats_are_skipped(engine, sample_game_state):
    sample_game_state.threat_states["ta-1"].status = "eliminated"
    result = engine.evaluate_player_action("scan", sample_game_state)
    assert result == {"threat_updates": [], "new_events": [], "system_impacts": []}


def test_escalate_threat_paths(engine, sample_game_state, monkeypatch):
    _pin_random(monkeypatch, 0.9)
    assert engine.escalate_threat("missing", sample_game_state)["success"] is False
    assert engine.escalate_threat("ta-1", sample_game_state)["action"] == "escalation"
    sample_game_state.threat_states["ta-1"].status = "contained"
    assert engine.escalate_threat("ta-1", sample_game_state)["success"] is False


def test_adapt_tactics(engine, sample_game_state, monkeypatch):
    _pin_random(monkeypatch, 0.5)
    state = sample_game_state.threat_states["ta-1"]
    assert engine.adapt_tactics("ta-1", sample_game_state) is True
    assert state.current_tactics[0] != "Initial Access"
    assert engine.adapt_tactics("missing", sample_game_state) is False


@pytest.mark.parametrize(("aggression", "severity"), [(90, "critical"), (50, "high"), (10, "medium")])
def test_generate_threat_event_severity(engine, sample_game_state, sample_threat_actor, aggression, severity):
    state = sample_game_state.threat_states["ta-1"]
    state.aggression_level = aggression
    event = engine.generate_threat_event(state, sample_threat_actor, sample_game_state)
    assert event.severity == severity
    assert "using Initial Access" in event.description


def test_status_summary(engine, sample_game_state):
    summary = engine.get_threat_status_summary(sample_game_state)
    assert summary["total"] == 1
    assert summary["active"] == 1
