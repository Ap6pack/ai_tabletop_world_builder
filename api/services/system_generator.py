"""
System/asset generator service for creating IT infrastructure components.
"""
from typing import List, Dict, Any
from api.models import System, Vulnerability
from api.providers import LLMProviderFactory
import json
import uuid


class SystemGenerator:
    """Generates realistic IT systems and assets for departments."""

    def __init__(self, llm_provider=None):
        """Initialize the system generator."""
        self.llm_provider = llm_provider or LLMProviderFactory.create_provider()

    async def generate_systems(
        self,
        organization_name: str,
        department_name: str,
        department_function: str,
        industry: str,
        num_systems: int = 4
    ) -> List[System]:
        """
        Generate IT systems for a department.

        Args:
            organization_name: Name of the organization
            department_name: Name of the department
            department_function: Department's business function
            industry: Industry sector
            num_systems: Number of systems to generate

        Returns:
            List of System instances
        """
        prompt = self._build_systems_prompt(
            organization_name,
            department_name,
            department_function,
            industry,
            num_systems
        )

        systems_data = await self._generate_with_llm(prompt)

        systems = []
        for system_info in systems_data.get("systems", []):
            system = self._parse_system(system_info)
            systems.append(system)

        return systems

    def _build_systems_prompt(
        self,
        organization_name: str,
        department_name: str,
        department_function: str,
        industry: str,
        num_systems: int
    ) -> str:
        """Build prompt for system generation."""

        prompt = f"""Generate {num_systems} realistic IT systems/assets for the {department_name} department at {organization_name} ({industry}).

DEPARTMENT CONTEXT:
- Department: {department_name}
- Function: {department_function}
- Industry: {industry}

For each system, provide:
1. System name
2. System type (server, workstation, network-device, application, database, cloud-service)
3. Description and purpose
4. Operating system or platform
5. Key services/applications running
6. Security controls in place
7. Criticality level (critical, high, medium, low)

Generate systems that would realistically exist in this department and support its business function.

Respond with valid JSON in this format:
{{
    "systems": [
        {{
            "name": "System Name",
            "type": "server",
            "description": "What this system does",
            "os": "Windows Server 2019" or "Linux Ubuntu 20.04" or platform name,
            "services": ["service1", "service2"],
            "security_controls": ["firewall", "antivirus", "encryption"],
            "criticality": "high"
        }}
    ]
}}

IMPORTANT: Respond ONLY with valid JSON. No additional text."""

        return prompt

    async def _generate_with_llm(self, prompt: str) -> Dict[str, Any]:
        """Generate content using LLM and parse JSON."""

        system_message = """You are generating realistic IT systems for cybersecurity training scenarios.

RULES:
1. Create systems that match the department's function
2. Use realistic technologies and platforms
3. Include appropriate security controls
4. Be specific about services and configurations
5. Always respond with valid JSON only"""

        result = await self.llm_provider.complete(
            prompt=prompt,
            system_message=system_message,
            temperature=0.7,
            max_tokens=2000
        )

        content = result["content"].strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse system data: {e}\nOutput: {content}")

    def _parse_system(self, system_info: Dict[str, Any]) -> System:
        """Parse system data into System model."""

        system_id = f"sys_{uuid.uuid4().hex[:8]}"

        return System(
            id=system_id,
            name=system_info.get("name", "Unknown System"),
            description=system_info.get("description", ""),
            type=system_info.get("type", "server"),
            os=system_info.get("os"),
            services=system_info.get("services", []),
            vulnerabilities=[],  # Will be populated separately
            security_controls=system_info.get("security_controls", []),
            criticality=system_info.get("criticality", "medium")
        )
