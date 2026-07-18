#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Department generator service for creating business units within organizations.
"""

import json
import uuid
from typing import Any

from api.models import Department
from api.providers import LLMProviderFactory


class DepartmentGenerator:
    """Generates realistic departments for organizations."""

    def __init__(self, llm_provider=None):
        """Initialize the department generator."""
        self._llm_provider = llm_provider

    @property
    def llm_provider(self):
        """Lazily instantiate the LLM provider so construction needs no API key."""
        if self._llm_provider is None:
            self._llm_provider = LLMProviderFactory.create_provider()
        return self._llm_provider

    @llm_provider.setter
    def llm_provider(self, value):
        self._llm_provider = value

    async def generate_departments(
        self, organization_name: str, industry: str, size: str, num_departments: int = 3
    ) -> list[Department]:
        """
        Generate departments for an organization.

        Args:
            organization_name: Name of the organization
            industry: Industry sector
            size: Organization size
            num_departments: Number of departments to generate

        Returns:
            List of Department instances
        """
        prompt = self._build_departments_prompt(organization_name, industry, size, num_departments)

        dept_data = await self._generate_with_llm(prompt)

        departments = []
        for dept_info in dept_data.get("departments", []):
            department = self._parse_department(dept_info)
            departments.append(department)

        return departments

    def _build_departments_prompt(self, organization_name: str, industry: str, size: str, num_departments: int) -> str:
        """Build prompt for department generation."""

        prompt = f"""Generate {num_departments} realistic business departments for {organization_name}, a {size} {industry} organization.

For each department, provide:
1. Department name
2. Business function and purpose
3. Data classification level (public, internal, confidential, restricted)
4. Key compliance requirements
5. Approximate number of employees

Generate departments that make sense for a {industry} organization and would have IT systems/assets.

Respond with valid JSON in this format:
{{
    "departments": [
        {{
            "name": "Department Name",
            "description": "What this department does",
            "business_function": "Primary business function",
            "data_classification": "confidential",
            "compliance_requirements": ["requirement1", "requirement2"],
            "employee_count": 50
        }}
    ]
}}

IMPORTANT: Respond ONLY with valid JSON. No additional text."""

        return prompt

    async def _generate_with_llm(self, prompt: str) -> dict[str, Any]:
        """Generate content using LLM and parse JSON."""

        system_message = """You are generating realistic business departments for cybersecurity training scenarios.

RULES:
1. Create realistic but fictional departments
2. Focus on departments that would have IT systems
3. Be specific about data types and compliance
4. Always respond with valid JSON only"""

        result = await self.llm_provider.complete(
            prompt=prompt, system_message=system_message, temperature=0.7, max_tokens=1500
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
            raise ValueError(f"Failed to parse department data: {e}\nOutput: {content}") from e

    def _parse_department(self, dept_info: dict[str, Any]) -> Department:
        """Parse department data into Department model."""

        dept_id = f"dept_{uuid.uuid4().hex[:8]}"

        return Department(
            id=dept_id,
            name=dept_info.get("name", "Unknown Department"),
            description=dept_info.get("description", ""),
            business_function=dept_info.get("business_function", ""),
            systems=[],  # Will be populated separately
            data_classification=dept_info.get("data_classification", "internal"),
            compliance_requirements=dept_info.get("compliance_requirements", []),
        )
