#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
"""Tests for the MITRE ATT&CK mapping and analysis service."""

from datetime import UTC, datetime

import pytest

from api.models.attack_models import ATTCKCoverageReport, ATTCKTechnique
from api.models.schemas import (
    Department,
    GameState,
    Inventory,
    Organization,
    ThreatActor,
    ThreatActorState,
)
from api.services.mitre_attack_service import MITREAttackService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def service():
    """Singleton MITRE ATT&CK service loaded once for the module."""
    return MITREAttackService()


def make_game_state(**overrides):
    """Factory for minimal GameState instances."""
    org = Organization(
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
                compliance_requirements=[],
            )
        ],
        threat_actors=[],
        security_posture="developing",
        compliance_frameworks=[],
    )
    defaults = dict(
        session_id="test-session",
        organization=org,
        current_scenario="test",
        player_role="mixed",
        inventory=Inventory(),
        status="in-progress",
    )
    defaults.update(overrides)
    return GameState(**defaults)


# ---------------------------------------------------------------------------
# Data-loading tests
# ---------------------------------------------------------------------------


def test_service_loads_techniques(service):
    """Curated dataset must contain > 80 enterprise techniques."""
    assert len(service._techniques) > 80


def test_service_loads_tactics(service):
    """Tactic lookup should be populated from attack_tactics.json."""
    assert len(service._tactics) > 0


# ---------------------------------------------------------------------------
# Single-technique lookup tests
# ---------------------------------------------------------------------------


def test_get_technique_by_id(service):
    """T1566 (Phishing) must be retrievable by exact ID."""
    technique = service.get_technique("T1566")
    assert technique is not None
    assert technique.technique_id == "T1566"
    assert technique.name == "Phishing"


def test_get_technique_not_found(service):
    """Non-existent IDs should return None."""
    assert service.get_technique("T9999") is None


# ---------------------------------------------------------------------------
# Tactic-based retrieval
# ---------------------------------------------------------------------------


def test_get_techniques_by_tactic(service):
    """initial-access tactic should return a non-empty list of techniques."""
    techniques = service.get_techniques_by_tactic("initial-access")
    assert len(techniques) > 0
    assert all(isinstance(t, ATTCKTechnique) for t in techniques)


# ---------------------------------------------------------------------------
# Free-text TTP mapping
# ---------------------------------------------------------------------------


def test_map_ttp_exact_id(service):
    """Exact technique ID should return a single match."""
    results = service.map_ttp_to_attack("T1595")
    assert len(results) == 1
    assert results[0].technique_id == "T1595"


def test_map_ttp_keyword(service):
    """Keyword 'phishing' should resolve to at least one technique."""
    results = service.map_ttp_to_attack("phishing")
    assert len(results) >= 1
    ids = [t.technique_id for t in results]
    # At least one of the phishing techniques should appear
    assert any(tid.startswith("T1566") or tid == "T1598" for tid in ids)


def test_map_ttp_empty(service):
    """Empty input should produce an empty result."""
    assert service.map_ttp_to_attack("") == []


def test_resolve_ttps(service):
    """resolve_ttps_to_attack should return deduplicated ATT&CK IDs."""
    ids = service.resolve_ttps_to_attack(["phishing", "lateral-movement"])
    assert isinstance(ids, list)
    assert len(ids) > 0
    # No duplicates
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Session coverage analysis
# ---------------------------------------------------------------------------


def test_analyze_empty_session(service):
    """Session with no threat states should report 0% coverage."""
    gs = make_game_state(threat_states={})
    report = service.analyze_session_coverage(gs)
    assert isinstance(report, ATTCKCoverageReport)
    assert report.coverage_percentage == 0.0
    assert report.techniques_exercised == []


def test_analyze_session_with_techniques(service):
    """Session with active + detected techniques should compute coverage."""
    ts = ThreatActorState(
        threat_actor_id="ta-1",
        status="active",
        active_techniques=["T1566", "T1595", "T1059"],
        detected_techniques=["T1566"],
        mitigated_techniques=["T1566"],
        last_update=datetime.now(UTC),
    )
    gs = make_game_state(threat_states={"ta-1": ts})
    report = service.analyze_session_coverage(gs)
    assert "T1566" in report.techniques_exercised
    assert "T1566" in report.techniques_detected
    assert "T1566" in report.techniques_mitigated
    assert report.coverage_percentage > 0
    # T1595 and T1059 should appear as gaps (active but not detected)
    assert "T1595" in report.gaps


# ---------------------------------------------------------------------------
# Detection suggestions
# ---------------------------------------------------------------------------


def test_suggest_detection(service):
    """Valid technique ID should return a non-empty detection string."""
    detection = service.suggest_detection_for_technique("T1566")
    assert isinstance(detection, str)
    assert len(detection) > 0
    assert "not found" not in detection.lower()


def test_suggest_detection_invalid(service):
    """Invalid technique ID should return a 'not found' message."""
    detection = service.suggest_detection_for_technique("T9999")
    assert "not found" in detection.lower()


# ---------------------------------------------------------------------------
# Keyword aliases
# ---------------------------------------------------------------------------


def test_keyword_aliases(service):
    """Alias 'ransomware' should map to at least one ATT&CK technique."""
    results = service.map_ttp_to_attack("ransomware")
    assert len(results) >= 1


# ---------------------------------------------------------------------------
# Threat actor profiling
# ---------------------------------------------------------------------------


def test_threat_actor_profile(service):
    """Threat actor with explicit attack_techniques should resolve correctly."""
    actor = ThreatActor(
        id="ta-1",
        name="APT-Test",
        description="Test actor",
        motivation="espionage",
        sophistication="nation-state",
        ttps=["phishing", "lateral-movement"],
        attack_techniques=["T1566", "T1595"],
    )
    profile = service.get_threat_actor_attack_profile(actor)
    assert len(profile) == 2
    ids = {t.technique_id for t in profile}
    assert "T1566" in ids
    assert "T1595" in ids
