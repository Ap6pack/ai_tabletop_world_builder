#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Scenario orchestrator service that coordinates all generators to create complete scenarios.
"""

import json
from datetime import datetime

from sqlalchemy import select

from api.db import GeneratedScenarioRow, init_db, session_scope
from api.models import Organization
from api.providers import LLMProviderFactory
from api.services.department_generator import DepartmentGenerator
from api.services.organization_generator import OrganizationGenerator
from api.services.system_generator import SystemGenerator
from api.services.threat_actor_generator import ThreatActorGenerator
from api.services.vulnerability_generator import VulnerabilityGenerator
from api.utils import setup_logger

logger = setup_logger(__name__)


class ScenarioOrchestrator:
    """
    Orchestrates the generation of complete cybersecurity training scenarios.

    This service coordinates multiple generators to create hierarchical scenarios:
    Organization → Departments → Systems → Vulnerabilities + Threat Actors
    """

    def __init__(self, llm_provider=None):
        """Initialize the scenario orchestrator with all generators.

        The LLM provider is created lazily by each generator on first use, so
        constructing the orchestrator does not require an API key.
        """
        init_db()
        self._llm_provider = llm_provider

        # Share the (possibly None) provider with all generators; each will
        # lazily create a default provider on first use if none was supplied.
        self.org_generator = OrganizationGenerator(llm_provider)
        self.dept_generator = DepartmentGenerator(llm_provider)
        self.system_generator = SystemGenerator(llm_provider)
        self.vuln_generator = VulnerabilityGenerator(llm_provider)
        self.threat_generator = ThreatActorGenerator(llm_provider)

    @property
    def llm_provider(self):
        """Lazily instantiate the LLM provider so construction needs no API key."""
        if self._llm_provider is None:
            self._llm_provider = LLMProviderFactory.create_provider()
        return self._llm_provider

    @llm_provider.setter
    def llm_provider(self, value):
        self._llm_provider = value

    async def generate_complete_scenario(
        self,
        industry: str,
        size: str = "medium",
        complexity: str = "moderate",
        focus_areas: list[str] | None = None,
        num_departments: int = 3,
    ) -> Organization:
        """
        Generate a complete training scenario with full hierarchy.

        Args:
            industry: Industry sector
            size: Organization size (small, medium, large, enterprise)
            complexity: Scenario complexity (basic, moderate, complex)
            focus_areas: Optional focus areas (e.g., ["ransomware"])
            num_departments: Number of departments to generate

        Returns:
            Complete Organization with all nested data

        Process:
            1. Generate organization profile
            2. Generate departments for organization
            3. For each department, generate systems
            4. For each system, generate vulnerabilities
            5. Generate threat actors targeting the organization
        """
        logger.info(f"Generating {industry} organization (size: {size}, complexity: {complexity})")

        # Step 1: Generate organization
        organization = await self.org_generator.generate_organization(
            industry=industry, size=size, complexity=complexity, focus_areas=focus_areas
        )

        # Step 2: Generate departments
        logger.info(f"Generating {num_departments} departments for {organization.name}")
        departments = await self.dept_generator.generate_departments(
            organization_name=organization.name, industry=industry, size=size, num_departments=num_departments
        )

        # Step 3: Generate systems for each department
        for dept in departments:
            num_systems = self._determine_systems_count(complexity)
            logger.info(f"Generating {num_systems} systems for department: {dept.name}")
            systems = await self.system_generator.generate_systems(
                organization_name=organization.name,
                department_name=dept.name,
                department_function=dept.business_function,
                industry=industry,
                num_systems=num_systems,
            )

            # Step 4: Generate vulnerabilities for each system
            for system in systems:
                logger.debug(f"Generating vulnerabilities for system: {system.name}")
                vulnerabilities = await self.vuln_generator.generate_vulnerabilities(
                    system_name=system.name,
                    system_type=system.type,
                    os=system.os,
                    services=system.services,
                    complexity=complexity,
                    focus_areas=focus_areas,
                )

                system.vulnerabilities = vulnerabilities

            dept.systems = systems

        organization.departments = departments

        # Step 5: Generate threat actors
        num_threat_actors = self._determine_threat_actor_count(complexity)
        logger.info(f"Generating {num_threat_actors} threat actors")
        threat_actors = await self.threat_generator.generate_threat_actors(
            organization_name=organization.name,
            industry=industry,
            focus_areas=focus_areas,
            num_actors=self._determine_threat_actor_count(complexity),
        )

        organization.threat_actors = threat_actors

        logger.info(
            f"Scenario generation complete: {organization.name} ({len(departments)} departments, {num_threat_actors} threat actors)"
        )
        return organization

    def _determine_systems_count(self, complexity: str) -> int:
        """Determine number of systems per department based on complexity."""
        mapping = {"basic": 2, "moderate": 3, "complex": 4}
        return mapping.get(complexity, 3)

    def _determine_threat_actor_count(self, complexity: str) -> int:
        """Determine number of threat actors based on complexity."""
        mapping = {"basic": 1, "moderate": 2, "complex": 3}
        return mapping.get(complexity, 2)

    async def save_scenario(self, organization: Organization, filename: str | None = None) -> str:
        """
        Save generated scenario to JSON file.

        Args:
            organization: Complete organization to save
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = organization.name.replace(" ", "_").replace("/", "_")
            filename = f"{safe_name}_{timestamp}.json"

        payload = organization.model_dump(mode="json")
        with session_scope() as db:
            row = db.get(GeneratedScenarioRow, filename)
            if row is None:
                row = GeneratedScenarioRow(filename=filename, created_at=datetime.now().isoformat())
                db.add(row)
            row.name = organization.name
            row.industry = organization.industry
            row.size = organization.size
            row.data = payload

        return filename

    async def load_scenario(self, filename: str) -> Organization:
        """
        Load a saved scenario by filename.

        Args:
            filename: Identifier of the saved scenario

        Returns:
            Organization instance

        Raises:
            FileNotFoundError: If the scenario does not exist
        """
        with session_scope() as db:
            row = db.get(GeneratedScenarioRow, filename)
            if row is None:
                raise FileNotFoundError(f"Scenario not found: {filename}")
            return Organization(**row.data)

    def delete_scenario(self, filename: str) -> None:
        """
        Delete a saved scenario.

        Raises:
            FileNotFoundError: If the scenario does not exist
        """
        with session_scope() as db:
            row = db.get(GeneratedScenarioRow, filename)
            if row is None:
                raise FileNotFoundError(f"Scenario not found: {filename}")
            db.delete(row)

    def list_scenarios(self) -> list[dict]:
        """
        List all saved scenarios.

        Returns:
            List of scenario metadata (filename, name, industry, size, created_at)
        """
        with session_scope() as db:
            rows = db.scalars(select(GeneratedScenarioRow)).all()
            scenarios = [
                {
                    "filename": row.filename,
                    "name": row.name or "Unknown",
                    "industry": row.industry or "Unknown",
                    "size": row.size or "Unknown",
                    "created_at": row.created_at,
                    "file_size": len(json.dumps(row.data)),
                }
                for row in rows
            ]

        return sorted(scenarios, key=lambda x: x["created_at"], reverse=True)

    @staticmethod
    def get_supported_industries() -> list[str]:
        """Get list of supported industries."""
        return OrganizationGenerator.get_supported_industries()

    @staticmethod
    def get_industry_info(industry: str) -> dict | None:
        """Get information about a specific industry."""
        return OrganizationGenerator.get_industry_info(industry)
