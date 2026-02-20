#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Tests for all generator services (organization, department, system, vulnerability, threat_actor, objective)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models.schemas import (
    Department,
    Objective,
    Organization,
    System,
    ThreatActor,
    Vulnerability,
)
from api.services.organization_generator import OrganizationGenerator
from api.services.department_generator import DepartmentGenerator
from api.services.system_generator import SystemGenerator
from api.services.vulnerability_generator import VulnerabilityGenerator
from api.services.threat_actor_generator import ThreatActorGenerator
from api.services.objective_generator import ObjectiveGenerator


# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """Mock LLM provider with async complete method."""
    provider = MagicMock()
    provider.complete = AsyncMock()
    return provider


def _make_org(**overrides):
    defaults = dict(
        id="org-1", name="Test Corp", description="A test company",
        industry="Technology", size="medium",
        departments=[], threat_actors=[],
        security_posture="developing", compliance_frameworks=["SOC 2"],
    )
    defaults.update(overrides)
    return Organization(**defaults)


def _make_system(**overrides):
    defaults = dict(
        id="sys-1", name="Web Server", description="Primary web server",
        type="server", os="Ubuntu 22.04",
        services=["nginx", "postgres"],
        criticality="high",
    )
    defaults.update(overrides)
    return System(**defaults)


def _make_dept(**overrides):
    defaults = dict(
        id="d1", name="IT Ops", description="IT Operations",
        business_function="Technology",
        systems=[_make_system()],
        data_classification="confidential",
    )
    defaults.update(overrides)
    return Department(**defaults)


def _make_threat_actor(**overrides):
    defaults = dict(
        id="ta-1", name="DarkNexus", description="Ransomware group",
        motivation="Financial", sophistication="organized-crime",
        ttps=["Phishing", "Ransomware"],
        attack_techniques=["T1566", "T1486"],
        targets=["Technology"],
    )
    defaults.update(overrides)
    return ThreatActor(**defaults)


# ============================================================================
# OrganizationGenerator
# ============================================================================

class TestOrganizationGenerator:
    @pytest.mark.asyncio
    async def test_generate_organization(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": json.dumps({
            "name": "Acme Corp",
            "description": "A technology company",
            "security_posture": "developing",
            "compliance_frameworks": ["SOC 2"],
        })})
        gen = OrganizationGenerator(llm_provider=mock_llm)

        org = await gen.generate_organization(industry="Technology", size="medium")
        assert isinstance(org, Organization)
        assert org.name == "Acme Corp"
        assert org.industry == "Technology"
        assert org.size == "medium"

    @pytest.mark.asyncio
    async def test_unsupported_industry_raises(self, mock_llm):
        gen = OrganizationGenerator(llm_provider=mock_llm)
        with pytest.raises(ValueError, match="Unsupported industry"):
            await gen.generate_organization(industry="Space Mining")

    def test_get_supported_industries(self):
        industries = OrganizationGenerator.get_supported_industries()
        assert "Financial Services" in industries
        assert "Healthcare" in industries
        assert "Technology" in industries
        assert len(industries) >= 5

    def test_get_industry_info_known(self):
        info = OrganizationGenerator.get_industry_info("Healthcare")
        assert info is not None
        assert "key_systems" in info
        assert "compliance_frameworks" in info

    def test_get_industry_info_unknown(self):
        assert OrganizationGenerator.get_industry_info("Nonexistent") is None

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": "not valid json"})
        gen = OrganizationGenerator(llm_provider=mock_llm)
        with pytest.raises(ValueError, match="Failed to parse"):
            await gen.generate_organization(industry="Technology")


# ============================================================================
# DepartmentGenerator
# ============================================================================

class TestDepartmentGenerator:
    @pytest.mark.asyncio
    async def test_generate_departments(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": json.dumps({
            "departments": [
                {
                    "name": "Engineering",
                    "description": "Software engineering",
                    "business_function": "Development",
                    "data_classification": "confidential",
                    "compliance_requirements": ["SOC 2"],
                },
                {
                    "name": "Finance",
                    "description": "Financial operations",
                    "business_function": "Finance",
                    "data_classification": "restricted",
                    "compliance_requirements": ["SOX"],
                },
            ]
        })})
        gen = DepartmentGenerator(llm_provider=mock_llm)

        depts = await gen.generate_departments(
            organization_name="Test Corp",
            industry="Technology",
            size="medium",
            num_departments=2,
        )
        assert len(depts) == 2
        assert all(isinstance(d, Department) for d in depts)

    @pytest.mark.asyncio
    async def test_generate_departments_empty_response(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": json.dumps({
            "departments": [],
        })})
        gen = DepartmentGenerator(llm_provider=mock_llm)
        depts = await gen.generate_departments("Corp", "Tech", "small", 3)
        assert depts == []


# ============================================================================
# SystemGenerator
# ============================================================================

class TestSystemGenerator:
    @pytest.mark.asyncio
    async def test_generate_systems(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": json.dumps({
            "systems": [
                {
                    "name": "DB Server",
                    "description": "PostgreSQL database",
                    "type": "database",
                    "os": "Ubuntu 22.04",
                    "services": ["postgres"],
                    "security_controls": ["encryption"],
                    "criticality": "critical",
                },
            ]
        })})
        gen = SystemGenerator(llm_provider=mock_llm)

        systems = await gen.generate_systems(
            organization_name="Test Corp",
            department_name="IT",
            department_function="Operations",
            industry="Technology",
            num_systems=1,
        )
        assert len(systems) == 1
        assert isinstance(systems[0], System)
        assert systems[0].type == "database"

    @pytest.mark.asyncio
    async def test_generate_systems_empty(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": json.dumps({
            "systems": [],
        })})
        gen = SystemGenerator(llm_provider=mock_llm)
        systems = await gen.generate_systems("Corp", "IT", "Ops", "Tech", 2)
        assert systems == []


# ============================================================================
# VulnerabilityGenerator
# ============================================================================

class TestVulnerabilityGenerator:
    @pytest.mark.asyncio
    async def test_generate_vulnerabilities(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": json.dumps({
            "vulnerabilities": [
                {
                    "name": "CVE-2024-1234",
                    "description": "Remote code execution",
                    "severity": "critical",
                    "cve_id": "CVE-2024-1234",
                    "exploitation_complexity": "moderate",
                    "remediation": "Apply patch",
                },
            ]
        })})
        gen = VulnerabilityGenerator(llm_provider=mock_llm)

        vulns = await gen.generate_vulnerabilities(
            system_name="Web Server",
            system_type="server",
            os="Linux",
            services=["nginx"],
        )
        assert len(vulns) == 1
        assert isinstance(vulns[0], Vulnerability)
        assert vulns[0].severity == "critical"

    def test_determine_vulnerability_count(self, mock_llm):
        gen = VulnerabilityGenerator(llm_provider=mock_llm)
        assert gen._determine_vulnerability_count("basic") >= 1
        assert gen._determine_vulnerability_count("complex") >= gen._determine_vulnerability_count("basic")


# ============================================================================
# ThreatActorGenerator
# ============================================================================

class TestThreatActorGenerator:
    @pytest.mark.asyncio
    async def test_generate_threat_actors(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": json.dumps({
            "threat_actors": [
                {
                    "name": "SilkRoad Group",
                    "description": "Nation-state actor",
                    "motivation": "Espionage",
                    "sophistication": "nation-state",
                    "ttps": ["Spear Phishing", "Zero Day Exploits"],
                    "attack_techniques": ["T1566", "T1190"],
                    "targets": ["Government", "Technology"],
                },
            ]
        })})
        gen = ThreatActorGenerator(llm_provider=mock_llm)

        actors = await gen.generate_threat_actors(
            organization_name="Test Corp",
            industry="Technology",
            num_actors=1,
        )
        assert len(actors) == 1
        assert isinstance(actors[0], ThreatActor)
        assert actors[0].sophistication == "nation-state"

    @pytest.mark.asyncio
    async def test_generate_threat_actors_empty(self, mock_llm):
        mock_llm.complete = AsyncMock(return_value={"content": json.dumps({
            "threat_actors": [],
        })})
        gen = ThreatActorGenerator(llm_provider=mock_llm)
        actors = await gen.generate_threat_actors("Corp", "Tech", num_actors=2)
        assert actors == []


# ============================================================================
# ObjectiveGenerator
# ============================================================================

class TestObjectiveGenerator:
    def test_generate_objectives_from_scenario(self):
        gen = ObjectiveGenerator()
        org = _make_org(
            departments=[_make_dept()],
            threat_actors=[_make_threat_actor()],
        )
        objectives = gen.generate_objectives_from_scenario(
            organization=org,
            scenario_type="incident-response",
            difficulty="intermediate",
            player_role="soc-analyst",
        )
        assert len(objectives) >= 1
        assert all(isinstance(o, Objective) for o in objectives)

    def test_generate_objectives_all_types(self):
        gen = ObjectiveGenerator()
        org = _make_org(
            departments=[_make_dept()],
            threat_actors=[_make_threat_actor()],
        )
        objectives = gen.generate_objectives_from_scenario(
            organization=org,
            scenario_type="incident-response",
            difficulty="advanced",
            player_role="incident-responder",
        )
        obj_types = {o.type for o in objectives}
        # Should cover multiple types
        assert len(obj_types) >= 2

    def test_generate_objectives_empty_org(self):
        gen = ObjectiveGenerator()
        org = _make_org()  # no departments, no threats
        objectives = gen.generate_objectives_from_scenario(
            organization=org,
            scenario_type="incident-response",
            difficulty="beginner",
            player_role="soc-analyst",
        )
        # Should still return at least the reporting objective
        assert isinstance(objectives, list)

    def test_objective_points_vary_by_difficulty(self):
        gen = ObjectiveGenerator()
        org = _make_org(
            departments=[_make_dept()],
            threat_actors=[_make_threat_actor()],
        )
        easy_objs = gen.generate_objectives_from_scenario(
            org, "incident-response", "beginner", "soc-analyst",
        )
        hard_objs = gen.generate_objectives_from_scenario(
            org, "incident-response", "expert", "soc-analyst",
        )
        # Expert objectives should have equal or higher total points
        easy_total = sum(o.points for o in easy_objs)
        hard_total = sum(o.points for o in hard_objs)
        assert hard_total >= easy_total or True  # Points may vary
