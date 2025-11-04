"""
Scenario orchestrator service that coordinates all generators to create complete scenarios.
"""
from typing import Optional, List
from api.models import Organization, GenerateScenarioRequest
from api.services.organization_generator import OrganizationGenerator
from api.services.department_generator import DepartmentGenerator
from api.services.system_generator import SystemGenerator
from api.services.vulnerability_generator import VulnerabilityGenerator
from api.services.threat_actor_generator import ThreatActorGenerator
from api.providers import LLMProviderFactory
from api.utils import setup_logger
import json
import os
from datetime import datetime

logger = setup_logger(__name__)


class ScenarioOrchestrator:
    """
    Orchestrates the generation of complete cybersecurity training scenarios.

    This service coordinates multiple generators to create hierarchical scenarios:
    Organization → Departments → Systems → Vulnerabilities + Threat Actors
    """

    def __init__(self, llm_provider=None):
        """Initialize the scenario orchestrator with all generators."""
        self.llm_provider = llm_provider or LLMProviderFactory.create_provider()

        # Initialize all generators with shared LLM provider
        self.org_generator = OrganizationGenerator(self.llm_provider)
        self.dept_generator = DepartmentGenerator(self.llm_provider)
        self.system_generator = SystemGenerator(self.llm_provider)
        self.vuln_generator = VulnerabilityGenerator(self.llm_provider)
        self.threat_generator = ThreatActorGenerator(self.llm_provider)

    async def generate_complete_scenario(
        self,
        industry: str,
        size: str = "medium",
        complexity: str = "moderate",
        focus_areas: Optional[List[str]] = None,
        num_departments: int = 3
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
            industry=industry,
            size=size,
            complexity=complexity,
            focus_areas=focus_areas
        )

        # Step 2: Generate departments
        logger.info(f"Generating {num_departments} departments for {organization.name}")
        departments = await self.dept_generator.generate_departments(
            organization_name=organization.name,
            industry=industry,
            size=size,
            num_departments=num_departments
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
                num_systems=num_systems
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
                    focus_areas=focus_areas
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
            num_actors=self._determine_threat_actor_count(complexity)
        )

        organization.threat_actors = threat_actors

        logger.info(f"Scenario generation complete: {organization.name} ({len(departments)} departments, {num_threat_actors} threat actors)")
        return organization

    def _determine_systems_count(self, complexity: str) -> int:
        """Determine number of systems per department based on complexity."""
        mapping = {
            "basic": 2,
            "moderate": 3,
            "complex": 4
        }
        return mapping.get(complexity, 3)

    def _determine_threat_actor_count(self, complexity: str) -> int:
        """Determine number of threat actors based on complexity."""
        mapping = {
            "basic": 1,
            "moderate": 2,
            "complex": 3
        }
        return mapping.get(complexity, 2)

    async def save_scenario(self, organization: Organization, filename: Optional[str] = None) -> str:
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

        # Ensure scenarios directory exists
        scenarios_dir = "scenarios/generated"
        os.makedirs(scenarios_dir, exist_ok=True)

        filepath = os.path.join(scenarios_dir, filename)

        # Convert to dict and save
        with open(filepath, 'w') as f:
            json.dump(organization.model_dump(), f, indent=2, default=str)

        return filepath

    async def load_scenario(self, filename: str) -> Organization:
        """
        Load scenario from JSON file.

        Args:
            filename: Name of file in scenarios/generated directory

        Returns:
            Organization instance

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        filepath = os.path.join("scenarios/generated", filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Scenario file not found: {filepath}")

        with open(filepath, 'r') as f:
            data = json.load(f)

        return Organization(**data)

    def list_scenarios(self) -> List[dict]:
        """
        List all saved scenarios.

        Returns:
            List of scenario metadata (name, size, created_at)
        """
        scenarios_dir = "scenarios/generated"

        if not os.path.exists(scenarios_dir):
            return []

        scenarios = []
        for filename in os.listdir(scenarios_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(scenarios_dir, filename)
                stat = os.stat(filepath)

                # Try to load and get basic info
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    scenarios.append({
                        "filename": filename,
                        "name": data.get("name", "Unknown"),
                        "industry": data.get("industry", "Unknown"),
                        "size": data.get("size", "Unknown"),
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "file_size": stat.st_size
                    })
                except Exception as e:
                    logger.warning(f"Failed to read scenario file {filename}: {str(e)}")
                    continue

        return sorted(scenarios, key=lambda x: x["created_at"], reverse=True)

    @staticmethod
    def get_supported_industries() -> List[str]:
        """Get list of supported industries."""
        return OrganizationGenerator.get_supported_industries()

    @staticmethod
    def get_industry_info(industry: str) -> Optional[dict]:
        """Get information about a specific industry."""
        return OrganizationGenerator.get_industry_info(industry)
