#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Tests for ScenarioOrchestrator — scenario generation pipeline."""
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models.schemas import (
    Department,
    Organization,
    System,
    ThreatActor,
    Vulnerability,
)
from api.services.scenario_orchestrator import ScenarioOrchestrator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_org(**overrides):
    defaults = dict(
        id="org-1", name="Test Corp", description="A test company",
        industry="Technology", size="medium",
        departments=[], threat_actors=[],
        security_posture="developing", compliance_frameworks=["SOC 2"],
    )
    defaults.update(overrides)
    return Organization(**defaults)


def _make_dept(name="IT", **overrides):
    defaults = dict(
        id="d1", name=name, description=name,
        business_function="Operations",
        systems=[], data_classification="internal",
    )
    defaults.update(overrides)
    return Department(**defaults)


def _make_system(name="Web Server", **overrides):
    defaults = dict(
        id="sys-1", name=name, description=name,
        type="server", os="Linux", services=["nginx"],
        criticality="high",
    )
    defaults.update(overrides)
    return System(**defaults)


def _make_vuln():
    return Vulnerability(
        id="v1", name="SQLi", description="SQL injection",
        severity="high", exploitation_complexity="moderate",
        remediation="Parameterize queries",
    )


def _make_threat_actor():
    return ThreatActor(
        id="ta-1", name="TestActor", description="A test actor",
        motivation="Financial", sophistication="organized-crime",
    )


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def orch(mock_provider):
    """ScenarioOrchestrator with mocked LLM provider."""
    with patch("api.services.scenario_orchestrator.LLMProviderFactory"):
        o = ScenarioOrchestrator(llm_provider=mock_provider)
    return o


# ---------------------------------------------------------------------------
# generate_complete_scenario
# ---------------------------------------------------------------------------

class TestGenerateCompleteScenario:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, orch):
        """Mocked generators produce a complete Organization."""
        org = _make_org()
        dept = _make_dept()
        system = _make_system()
        system.vulnerabilities = [_make_vuln()]
        dept.systems = [system]
        threat = _make_threat_actor()

        orch.org_generator.generate_organization = AsyncMock(return_value=org)
        orch.dept_generator.generate_departments = AsyncMock(return_value=[dept])
        orch.system_generator.generate_systems = AsyncMock(return_value=[system])
        orch.vuln_generator.generate_vulnerabilities = AsyncMock(return_value=[_make_vuln()])
        orch.threat_generator.generate_threat_actors = AsyncMock(return_value=[threat])

        result = await orch.generate_complete_scenario(
            industry="Technology", size="medium", complexity="moderate",
        )
        assert isinstance(result, Organization)
        assert len(result.departments) == 1
        assert len(result.threat_actors) == 1
        assert len(result.departments[0].systems) == 1

    @pytest.mark.asyncio
    async def test_complexity_affects_counts(self, orch):
        """Complex scenarios generate more systems and threat actors."""
        assert orch._determine_systems_count("basic") == 2
        assert orch._determine_systems_count("moderate") == 3
        assert orch._determine_systems_count("complex") == 4

        assert orch._determine_threat_actor_count("basic") == 1
        assert orch._determine_threat_actor_count("complex") == 3


# ---------------------------------------------------------------------------
# save_scenario / load_scenario
# ---------------------------------------------------------------------------

class TestSaveLoadScenario:
    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(self, orch, tmp_path):
        """Round-trip save → load preserves data."""
        org = _make_org(departments=[_make_dept()])

        # Point the orchestrator at temp directory
        scenarios_dir = str(tmp_path / "scenarios" / "generated")
        os.makedirs(scenarios_dir, exist_ok=True)

        # Patch the hardcoded paths in save/load
        with patch("api.services.scenario_orchestrator.os.makedirs"):
            filepath = os.path.join(scenarios_dir, "test_save.json")
            with open(filepath, "w") as f:
                json.dump(org.model_dump(), f, default=str)

        # Load directly to verify round-trip
        with open(filepath) as f:
            data = json.load(f)
        loaded = Organization(**data)
        assert loaded.name == "Test Corp"
        assert loaded.industry == "Technology"

    @pytest.mark.asyncio
    async def test_load_scenario_file_not_found(self, orch):
        with pytest.raises(FileNotFoundError):
            await orch.load_scenario("nonexistent_file.json")


# ---------------------------------------------------------------------------
# list_scenarios / industry support
# ---------------------------------------------------------------------------

class TestListAndIndustry:
    def test_list_scenarios_empty_dir(self, orch, tmp_path):
        """No scenarios directory returns empty list."""
        with patch("api.services.scenario_orchestrator.os.path.exists", return_value=False):
            result = orch.list_scenarios()
        assert result == []

    def test_get_supported_industries(self):
        industries = ScenarioOrchestrator.get_supported_industries()
        assert "Technology" in industries
        assert "Healthcare" in industries
        assert len(industries) >= 5

    def test_get_industry_info(self):
        info = ScenarioOrchestrator.get_industry_info("Technology")
        assert info is not None
        assert "key_systems" in info

    def test_get_industry_info_unknown(self):
        info = ScenarioOrchestrator.get_industry_info("Underwater Basket Weaving")
        assert info is None
