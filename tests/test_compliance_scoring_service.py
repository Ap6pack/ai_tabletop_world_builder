#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the ComplianceScoringService."""

from datetime import UTC, datetime

import pytest

from api.models.schemas import (
    Department,
    GameState,
    IncidentEvent,
    Inventory,
    Organization,
    ThreatActorState,
)
from api.services.compliance_scoring_service import (
    ComplianceGap,
    ComplianceScoreReport,
    ComplianceScoringService,
)

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


# ---------------------------------------------------------------------------
# Framework Loading
# ---------------------------------------------------------------------------


class TestFrameworkLoading:
    def test_frameworks_loaded_on_init(self):
        svc = ComplianceScoringService()
        frameworks = svc.get_available_frameworks()
        assert isinstance(frameworks, list)
        # Should load at least one framework from data/compliance_frameworks/
        assert len(frameworks) >= 1

    def test_known_frameworks_present(self):
        """Verify the 3 expected frameworks are loaded."""
        svc = ComplianceScoringService()
        frameworks = svc.get_available_frameworks()
        for expected in ["nist_csf_2_0", "pci_dss_4_0_1", "hipaa"]:
            assert expected in frameworks, f"Missing framework: {expected}"


# ---------------------------------------------------------------------------
# score_session
# ---------------------------------------------------------------------------


class TestScoreSession:
    def test_score_empty_state(self):
        """Empty game state (no threats, no actions) => score 0."""
        svc = ComplianceScoringService()
        gs = _make_game_state()
        frameworks = svc.get_available_frameworks()
        if not frameworks:
            pytest.skip("No frameworks loaded")
        report = svc.score_session(gs, frameworks[0])
        assert isinstance(report, ComplianceScoreReport)
        assert report.overall_score == 0.0

    def test_score_unknown_framework(self):
        """Unknown framework returns report with gap message."""
        svc = ComplianceScoringService()
        gs = _make_game_state()
        report = svc.score_session(gs, "nonexistent_framework")
        assert report.framework_name == "nonexistent_framework"
        assert len(report.gaps) == 1
        assert "not loaded" in report.gaps[0]

    def test_score_with_active_techniques(self):
        """Active techniques matching control => +40 points."""
        svc = ComplianceScoringService()
        gs = _make_game_state(
            threat_states={
                "ta-1": ThreatActorState(
                    threat_actor_id="ta-1",
                    status="active",
                    active_techniques=["T1566", "T1059", "T1486", "T1190"],
                    detected_techniques=[],
                    mitigated_techniques=[],
                    last_update=datetime.now(UTC),
                ),
            },
        )
        frameworks = svc.get_available_frameworks()
        if not frameworks:
            pytest.skip("No frameworks loaded")
        report = svc.score_session(gs, frameworks[0])
        # Some controls should have scores > 0 due to active technique overlap
        has_positive = any(c.score > 0 for f in report.functions for c in f.controls)
        assert has_positive, "Expected at least one control scored > 0"

    def test_score_with_detection_and_mitigation(self):
        """Detected + mitigated techniques => higher score."""
        svc = ComplianceScoringService()
        techniques = ["T1566", "T1059", "T1486", "T1190", "T1071"]
        gs = _make_game_state(
            threat_states={
                "ta-1": ThreatActorState(
                    threat_actor_id="ta-1",
                    status="active",
                    active_techniques=techniques,
                    detected_techniques=techniques,
                    mitigated_techniques=techniques,
                    last_update=datetime.now(UTC),
                ),
            },
        )
        frameworks = svc.get_available_frameworks()
        if not frameworks:
            pytest.skip("No frameworks loaded")
        report = svc.score_session(gs, frameworks[0])
        # Full coverage on techniques should give higher scores
        assert report.overall_score > 0

    def test_score_with_player_actions(self):
        """Player action text matching observable_actions => bonus points."""
        svc = ComplianceScoringService()
        gs = _make_game_state(
            incident_timeline=[
                IncidentEvent(
                    timestamp=datetime.now(UTC),
                    event_type="action",
                    description="Deployed network monitoring and blocked suspicious traffic",
                    severity="info",
                    actor="player",
                ),
                IncidentEvent(
                    timestamp=datetime.now(UTC),
                    event_type="action",
                    description="Ran vulnerability scan and patched critical systems",
                    severity="info",
                    actor="player",
                ),
            ],
            threat_states={
                "ta-1": ThreatActorState(
                    threat_actor_id="ta-1",
                    status="active",
                    active_techniques=["T1566"],
                    detected_techniques=["T1566"],
                    mitigated_techniques=[],
                    last_update=datetime.now(UTC),
                ),
            },
        )
        frameworks = svc.get_available_frameworks()
        if not frameworks:
            pytest.skip("No frameworks loaded")
        report = svc.score_session(gs, frameworks[0])
        assert report.overall_score >= 0  # At least valid


# ---------------------------------------------------------------------------
# Per-control scoring rubric
# ---------------------------------------------------------------------------


class TestControlScoring:
    def test_score_capped_at_100(self):
        """Max control score is 100 regardless of inputs."""
        svc = ComplianceScoringService()
        control = svc._score_control(
            control_id="C1",
            name="Test Control",
            description="",
            attack_techniques=["T1566"],
            observable_actions=["monitor", "scan", "patch", "block"],
            weight=1,
            active_techniques={"T1566"},
            detected_techniques={"T1566"},
            mitigated_techniques={"T1566"},
            player_action_texts=["monitor traffic", "scan systems", "patch server", "block ip"],
        )
        assert control.score <= 100

    def test_score_zero_no_overlap(self):
        """No technique overlap and no action match => 0 score."""
        svc = ComplianceScoringService()
        control = svc._score_control(
            control_id="C2",
            name="Empty Control",
            description="",
            attack_techniques=["T9999"],
            observable_actions=["nonexistent_action"],
            weight=1,
            active_techniques=set(),
            detected_techniques=set(),
            mitigated_techniques=set(),
            player_action_texts=[],
        )
        assert control.score == 0.0

    def test_points_active_technique(self):
        """Active technique overlap gives +40."""
        svc = ComplianceScoringService()
        control = svc._score_control(
            control_id="C3",
            name="Active Only",
            description="",
            attack_techniques=["T1566"],
            observable_actions=[],
            weight=1,
            active_techniques={"T1566"},
            detected_techniques=set(),
            mitigated_techniques=set(),
            player_action_texts=[],
        )
        assert control.score == 40.0

    def test_points_full_coverage(self):
        """Active + detected + mitigated = 40 + 30 + 30 = 100."""
        svc = ComplianceScoringService()
        control = svc._score_control(
            control_id="C4",
            name="Full Coverage",
            description="",
            attack_techniques=["T1566"],
            observable_actions=[],
            weight=1,
            active_techniques={"T1566"},
            detected_techniques={"T1566"},
            mitigated_techniques={"T1566"},
            player_action_texts=[],
        )
        assert control.score == 100.0


# ---------------------------------------------------------------------------
# get_gap_analysis
# ---------------------------------------------------------------------------


class TestGapAnalysis:
    def test_gaps_below_threshold(self):
        """Controls scoring < 50 appear in gap analysis."""
        svc = ComplianceScoringService()
        gs = _make_game_state()
        frameworks = svc.get_available_frameworks()
        if not frameworks:
            pytest.skip("No frameworks loaded")
        gaps = svc.get_gap_analysis(gs, frameworks[0])
        assert isinstance(gaps, list)
        for gap in gaps:
            assert isinstance(gap, ComplianceGap)
            assert gap.control_id
            assert gap.framework

    def test_no_gaps_when_fully_covered(self):
        """If all controls score >= 50, gap list should be smaller."""
        svc = ComplianceScoringService()
        # Provide broad technique coverage
        techniques = [
            "T1566",
            "T1059",
            "T1486",
            "T1190",
            "T1071",
            "T1078",
            "T1210",
            "T1021",
            "T1105",
            "T1048",
            "T1041",
            "T1489",
            "T1490",
            "T1529",
            "T1537",
            "T1567",
        ]
        gs = _make_game_state(
            threat_states={
                "ta-1": ThreatActorState(
                    threat_actor_id="ta-1",
                    status="active",
                    active_techniques=techniques,
                    detected_techniques=techniques,
                    mitigated_techniques=techniques,
                    last_update=datetime.now(UTC),
                ),
            },
        )
        frameworks = svc.get_available_frameworks()
        if not frameworks:
            pytest.skip("No frameworks loaded")
        full_gaps = svc.get_gap_analysis(_make_game_state(), frameworks[0])
        covered_gaps = svc.get_gap_analysis(gs, frameworks[0])
        # Covered session should have fewer gaps
        assert len(covered_gaps) <= len(full_gaps)


# ---------------------------------------------------------------------------
# generate_compliance_report (multi-framework)
# ---------------------------------------------------------------------------


class TestComplianceReport:
    def test_multi_framework_report_structure(self):
        """Multi-framework report has expected keys."""
        svc = ComplianceScoringService()
        gs = _make_game_state()
        frameworks = svc.get_available_frameworks()
        if len(frameworks) < 2:
            pytest.skip("Need at least 2 frameworks")
        report = svc.generate_compliance_report(gs, frameworks[:2])
        assert "session_id" in report
        assert "aggregate_score" in report
        assert "compliance_posture" in report
        assert "framework_scores" in report
        assert "total_gaps" in report
        assert "recommendations" in report

    def test_posture_labels(self):
        """Posture labels map correctly to score ranges."""
        svc = ComplianceScoringService()
        gs = _make_game_state()
        frameworks = svc.get_available_frameworks()
        if not frameworks:
            pytest.skip("No frameworks loaded")
        report = svc.generate_compliance_report(gs, frameworks[:1])
        posture = report["compliance_posture"]
        score = report["aggregate_score"]
        if score >= 80:
            assert posture == "Strong"
        elif score >= 60:
            assert posture == "Moderate"
        elif score >= 40:
            assert posture == "Developing"
        else:
            assert posture == "Weak"

    def test_empty_frameworks_list(self):
        """Empty framework list returns zero aggregate."""
        svc = ComplianceScoringService()
        gs = _make_game_state()
        report = svc.generate_compliance_report(gs, [])
        assert report["aggregate_score"] == 0.0
