#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Root conftest for pytest — shared fixtures and collection config."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.models.exercise_models import (
    ExerciseState,
    ExerciseTeam,
)
from api.models.schemas import (
    BusinessImpact,
    Department,
    GameState,
    IncidentEvent,
    Inventory,
    Organization,
    System,
    SystemState,
    ThreatActor,
    ThreatActorState,
    Vulnerability,
)

# ============================================================================
# Database isolation
# ============================================================================


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path):
    """Bind the DB engine to a throwaway SQLite file for each test.

    Guarantees test isolation and keeps the suite from touching the real
    ``data/app.db``. Services read the engine from ``api.db`` at call time, so
    rebinding here transparently redirects all storage.
    """
    import api.db as db

    db.configure_engine(f"sqlite:///{tmp_path}/test.db")
    db.init_db()
    yield
    db.get_engine().dispose()


# ============================================================================
# Hermeticity guard
# ============================================================================


@pytest.fixture(autouse=True)
def _no_real_llm(monkeypatch):
    """Prevent any test from constructing a real LLM provider.

    Services build their provider lazily via ``LLMProviderFactory.create_provider``.
    Patching it here guarantees the suite never needs an API key or network:
    tests that exercise LLM calls should still mock the specific service method,
    but if one is missed it gets this deterministic fake instead of a
    ``ValueError`` (no key) or a real network call.
    """
    fake_provider = MagicMock(name="FakeLLMProvider")
    fake_provider.complete = AsyncMock(return_value={"content": "{}", "model": "fake"})
    fake_provider.health_check = AsyncMock(return_value=True)
    fake_provider.get_model_name = MagicMock(return_value="fake")
    fake_provider.get_provider_name = MagicMock(return_value="fake")

    monkeypatch.setattr(
        "api.providers.factory.LLMProviderFactory.create_provider",
        lambda *args, **kwargs: fake_provider,
    )
    return fake_provider


# ============================================================================
# Core Model Fixtures
# ============================================================================


@pytest.fixture
def sample_vulnerability():
    """A single realistic vulnerability."""
    return Vulnerability(
        id="vuln-1",
        name="CVE-2024-1234 RCE",
        description="Remote code execution in web server",
        severity="critical",
        cve_id="CVE-2024-1234",
        affected_systems=["sys-web-1"],
        exploitation_complexity="moderate",
        remediation="Apply vendor patch 2024-01",
    )


@pytest.fixture
def sample_system(sample_vulnerability):
    """A single IT system with one vulnerability."""
    return System(
        id="sys-web-1",
        name="Web Application Server",
        description="Primary web application server",
        type="server",
        os="Ubuntu 22.04",
        services=["nginx", "gunicorn", "postgres"],
        vulnerabilities=[sample_vulnerability],
        security_controls=["WAF", "IDS"],
        criticality="critical",
    )


@pytest.fixture
def sample_department(sample_system):
    """A department containing one system."""
    return Department(
        id="dept-it",
        name="IT Operations",
        description="Information Technology department",
        business_function="Technology Operations",
        systems=[sample_system],
        data_classification="confidential",
        compliance_requirements=["SOC 2", "ISO 27001"],
    )


@pytest.fixture
def sample_threat_actor():
    """A realistic threat actor profile."""
    return ThreatActor(
        id="ta-1",
        name="DarkNexus",
        description="Financially motivated ransomware group",
        motivation="Financial gain through ransomware and extortion",
        sophistication="organized-crime",
        ttps=["Initial Access via Phishing", "Lateral Movement", "Data Exfiltration"],
        attack_techniques=["T1566", "T1486", "T1041"],
        targets=["Financial Services", "Healthcare"],
    )


@pytest.fixture
def sample_organization(sample_department, sample_threat_actor):
    """A complete organization with departments and threat actors."""
    return Organization(
        id="org-test",
        name="TestCorp International",
        description="A medium-sized technology company for testing",
        industry="Technology",
        size="medium",
        departments=[sample_department],
        threat_actors=[sample_threat_actor],
        security_posture="developing",
        compliance_frameworks=["SOC 2", "ISO 27001"],
    )


@pytest.fixture
def sample_inventory():
    """A standard SOC analyst inventory."""
    return Inventory(
        tools={"SIEM Access": 1, "Email": 1, "IDS/IPS": 1, "Log Analysis Tools": 1},
        access_levels=["user", "siem"],
        credentials=[],
    )


@pytest.fixture
def sample_threat_actor_state():
    """An active threat actor state for game sessions."""
    return ThreatActorState(
        threat_actor_id="ta-1",
        status="active",
        current_tactics=["Initial Access"],
        active_techniques=["T1566", "T1486"],
        detected_techniques=["T1566"],
        mitigated_techniques=[],
        systems_compromised=[],
        detection_level=30,
        aggression_level=60,
        last_update=datetime.now(UTC),
    )


@pytest.fixture
def sample_game_state(sample_organization, sample_inventory, sample_threat_actor_state):
    """A complete GameState for testing game services."""
    return GameState(
        session_id="test-session-001",
        organization=sample_organization,
        current_scenario="incident-response",
        player_role="soc-analyst",
        inventory=sample_inventory,
        incident_timeline=[
            IncidentEvent(
                timestamp=datetime.now(UTC),
                event_type="detection",
                description="Suspicious login detected",
                severity="high",
                actor="system",
            ),
        ],
        score=0,
        time_elapsed=5,
        system_states={
            "sys-web-1": SystemState(
                system_id="sys-web-1",
                status="online",
                health=100,
                last_update=datetime.now(UTC),
                affected_services=[],
            )
        },
        threat_states={"ta-1": sample_threat_actor_state},
        status="in-progress",
    )


@pytest.fixture
def sample_business_impact():
    """A BusinessImpact instance with some damage."""
    return BusinessImpact(
        downtime_cost=50000.0,
        downtime_hours=2.5,
        data_loss_cost=100000.0,
        records_compromised=5000,
        compliance_penalties={"PCI-DSS": 25000.0},
        reputation_damage=75000.0,
        total_cost=250000.0,
        impact_description="Significant incident with data exposure",
    )


@pytest.fixture
def sample_exercise_state(sample_game_state):
    """An ExerciseState with teams and basic setup."""
    return ExerciseState(
        exercise_id="ex-test-001",
        name="Test Exercise",
        description="A test tabletop exercise",
        facilitator_id="facilitator-1",
        teams=[
            ExerciseTeam(
                team_id="blue-1",
                name="Blue Team",
                team_type="blue",
            ),
            ExerciseTeam(
                team_id="red-1",
                name="Red Team",
                team_type="red",
            ),
        ],
        game_state=sample_game_state,
        phase="active",
        current_round=1,
    )


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory with standard subdirectories."""
    sessions_dir = tmp_path / "data" / "sessions"
    sessions_dir.mkdir(parents=True)
    scenarios_dir = tmp_path / "scenarios" / "generated"
    scenarios_dir.mkdir(parents=True)
    return tmp_path
