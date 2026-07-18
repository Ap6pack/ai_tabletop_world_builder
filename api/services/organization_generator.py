#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Organization generator service for creating realistic cybersecurity training scenarios.
"""

import json
import uuid
from typing import Any

from api.models import Organization
from api.providers import LLMProviderFactory
from api.services import ContentPolicyService


class OrganizationGenerator:
    """Generates realistic organizations for cybersecurity training scenarios."""

    # Industry-specific templates
    INDUSTRY_TEMPLATES = {
        "Financial Services": {
            "description": "Banks, credit unions, investment firms, and payment processors",
            "key_systems": [
                "Core Banking System",
                "ATM Network",
                "Online Banking Portal",
                "Payment Gateway",
                "Trading Platform",
            ],
            "common_departments": [
                "Retail Banking",
                "Commercial Banking",
                "IT Operations",
                "Compliance",
                "Risk Management",
                "Customer Service",
            ],
            "compliance_frameworks": ["PCI-DSS", "SOX", "GLBA", "FFIEC"],
            "threat_actors": ["Financially Motivated Crime Groups", "Nation-State APTs", "Insider Threats"],
            "data_types": ["Customer PII", "Financial Records", "Transaction Data", "Credit Card Data"],
        },
        "Healthcare": {
            "description": "Hospitals, clinics, medical practices, and health insurance providers",
            "key_systems": [
                "Electronic Health Records (EHR)",
                "Patient Portal",
                "Medical Imaging Systems",
                "Laboratory Information System",
                "Pharmacy Management",
            ],
            "common_departments": ["Patient Care", "Radiology", "Laboratory", "Pharmacy", "IT Services", "Billing"],
            "compliance_frameworks": ["HIPAA", "HITECH", "FDA 21 CFR Part 11"],
            "threat_actors": ["Ransomware Groups", "Data Brokers", "Insider Threats"],
            "data_types": [
                "PHI (Protected Health Information)",
                "Medical Records",
                "Insurance Information",
                "Prescription Data",
            ],
        },
        "Technology": {
            "description": "Software companies, SaaS providers, cloud platforms, and tech startups",
            "key_systems": [
                "Production Infrastructure",
                "CI/CD Pipeline",
                "Customer Portal",
                "API Gateway",
                "Database Clusters",
            ],
            "common_departments": ["Engineering", "DevOps", "Product", "Sales", "Customer Success", "Security"],
            "compliance_frameworks": ["SOC 2", "ISO 27001", "GDPR", "CCPA"],
            "threat_actors": ["APT Groups", "Competitor Espionage", "Hacktivists", "Supply Chain Attackers"],
            "data_types": ["Source Code", "Customer Data", "API Keys", "Business Intelligence"],
        },
        "Retail": {
            "description": "E-commerce, brick-and-mortar stores, and omnichannel retailers",
            "key_systems": [
                "E-commerce Platform",
                "Point of Sale (POS)",
                "Inventory Management",
                "Customer Database",
                "Payment Processing",
            ],
            "common_departments": ["Sales", "E-commerce", "Store Operations", "Supply Chain", "IT", "Marketing"],
            "compliance_frameworks": ["PCI-DSS", "CCPA", "GDPR"],
            "threat_actors": ["Payment Card Skimmers", "E-commerce Fraud", "Ransomware Groups"],
            "data_types": ["Payment Card Data", "Customer PII", "Purchase History", "Loyalty Program Data"],
        },
        "Manufacturing": {
            "description": "Industrial manufacturers, factories, and supply chain operations",
            "key_systems": [
                "SCADA/ICS Systems",
                "Manufacturing Execution System (MES)",
                "Enterprise Resource Planning (ERP)",
                "Supply Chain Management",
            ],
            "common_departments": ["Production", "Quality Assurance", "Supply Chain", "Maintenance", "IT/OT", "Safety"],
            "compliance_frameworks": ["NIST CSF", "IEC 62443", "ISO 27001"],
            "threat_actors": ["Nation-State APTs", "Industrial Espionage", "Ransomware Groups"],
            "data_types": [
                "Intellectual Property",
                "Manufacturing Processes",
                "Supply Chain Data",
                "Production Schedules",
            ],
        },
        "Government": {
            "description": "Federal, state, and local government agencies",
            "key_systems": [
                "Citizen Services Portal",
                "Records Management System",
                "Emergency Response Systems",
                "Internal Networks",
            ],
            "common_departments": ["Public Services", "IT", "Human Resources", "Finance", "Emergency Management"],
            "compliance_frameworks": ["FISMA", "NIST 800-53", "FedRAMP", "CJIS"],
            "threat_actors": ["Nation-State APTs", "Hacktivists", "Terrorist Groups"],
            "data_types": ["Citizen PII", "Classified Information", "Law Enforcement Data", "Government Records"],
        },
        "Education": {
            "description": "Universities, colleges, K-12 schools, and online learning platforms",
            "key_systems": [
                "Student Information System",
                "Learning Management System (LMS)",
                "Research Networks",
                "Library Systems",
            ],
            "common_departments": ["Academic Affairs", "Student Services", "IT Services", "Research", "Administration"],
            "compliance_frameworks": ["FERPA", "COPPA", "GDPR"],
            "threat_actors": ["Student Hackers", "Ransomware Groups", "Research Espionage"],
            "data_types": ["Student Records", "Research Data", "Faculty Information", "Financial Aid Data"],
        },
        "Energy/Utilities": {
            "description": "Power generation, water utilities, oil and gas companies",
            "key_systems": [
                "SCADA Systems",
                "Energy Management System",
                "Distribution Control",
                "Customer Billing System",
            ],
            "common_departments": ["Operations", "Grid Management", "Customer Service", "IT/OT Security", "Compliance"],
            "compliance_frameworks": ["NERC CIP", "TSA Pipeline Security", "NIST CSF"],
            "threat_actors": ["Nation-State APTs", "Eco-terrorists", "Ransomware Groups"],
            "data_types": ["Critical Infrastructure Data", "Customer Information", "Operational Technology Data"],
        },
    }

    def __init__(self, llm_provider=None, content_policy=None):
        """
        Initialize the organization generator.

        Args:
            llm_provider: Optional LLM provider instance. If None, creates default.
            content_policy: Optional content policy. If None, uses educational policy.
        """
        self._llm_provider = llm_provider
        self.content_policy = content_policy or ContentPolicyService.get_policy("educational")

    @property
    def llm_provider(self):
        """Lazily instantiate the LLM provider so construction needs no API key."""
        if self._llm_provider is None:
            self._llm_provider = LLMProviderFactory.create_provider()
        return self._llm_provider

    @llm_provider.setter
    def llm_provider(self, value):
        self._llm_provider = value

    async def generate_organization(
        self, industry: str, size: str = "medium", complexity: str = "moderate", focus_areas: list[str] | None = None
    ) -> Organization:
        """
        Generate a complete organization with IT infrastructure.

        Args:
            industry: Industry sector (e.g., "Financial Services", "Healthcare")
            size: Organization size (small, medium, large, enterprise)
            complexity: Scenario complexity (basic, moderate, complex)
            focus_areas: Optional list of focus areas (e.g., ["ransomware", "insider-threat"])

        Returns:
            Organization instance with complete infrastructure

        Raises:
            ValueError: If industry is not supported
        """
        if industry not in self.INDUSTRY_TEMPLATES:
            raise ValueError(f"Unsupported industry: {industry}. Supported: {list(self.INDUSTRY_TEMPLATES.keys())}")

        template = self.INDUSTRY_TEMPLATES[industry]

        # Generate organization profile
        org_prompt = self._build_organization_prompt(industry, size, complexity, template, focus_areas)
        org_data = await self._generate_with_llm(org_prompt, "organization")

        # Parse and structure the data
        organization = self._parse_organization(org_data, industry, size, template)

        return organization

    def _build_organization_prompt(
        self, industry: str, size: str, complexity: str, template: dict[str, Any], focus_areas: list[str] | None = None
    ) -> str:
        """Build the prompt for organization generation."""

        size_mapping = {
            "small": "50-100 employees",
            "medium": "100-1000 employees",
            "large": "1000-5000 employees",
            "enterprise": "5000+ employees",
        }

        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nSPECIFIC FOCUS AREAS: Emphasize these threat types: {', '.join(focus_areas)}"

        prompt = f"""Generate a realistic {industry} organization for cybersecurity training purposes.

ORGANIZATION DETAILS:
- Industry: {industry}
- Size: {size_mapping.get(size, size)}
- Complexity: {complexity}
- Description: {template["description"]}

REQUIREMENTS:
1. Create a realistic company name (not a real company)
2. Brief company description and history (2-3 sentences)
3. Current security posture: {self._get_security_posture_for_complexity(complexity)}
4. Key business functions
5. Recent security concerns or incidents
{focus_text}

CONTEXT:
- Common departments in this industry: {", ".join(template["common_departments"])}
- Typical systems: {", ".join(template["key_systems"])}
- Compliance requirements: {", ".join(template["compliance_frameworks"])}
- Data types: {", ".join(template["data_types"])}

Generate a realistic organization profile in valid JSON format:
{{
    "name": "Company Name",
    "description": "Brief description...",
    "history": "Company background...",
    "security_posture": "immature|developing|defined|managed|optimized",
    "business_functions": ["function1", "function2", ...],
    "recent_security_concerns": ["concern1", "concern2", ...],
    "compliance_frameworks": ["framework1", "framework2", ...]
}}

IMPORTANT: Respond ONLY with valid JSON. No additional text."""

        return prompt

    def _get_security_posture_for_complexity(self, complexity: str) -> str:
        """Map complexity to security posture."""
        mapping = {
            "basic": "immature or developing (many vulnerabilities, limited controls)",
            "moderate": "developing or defined (some controls in place, room for improvement)",
            "complex": "defined or managed (mature security program with some gaps)",
        }
        return mapping.get(complexity, "developing")

    async def _generate_with_llm(self, prompt: str, context: str) -> dict[str, Any]:
        """
        Generate content using LLM and parse JSON response.

        Args:
            prompt: The generation prompt
            context: Context for error messages

        Returns:
            Parsed JSON data

        Raises:
            ValueError: If LLM output is not valid JSON
        """
        system_message = f"""You are a cybersecurity scenario generator creating realistic {context} profiles for security training.

IMPORTANT RULES:
1. Generate realistic but fictional data (no real companies)
2. Focus on educational value for security training
3. Be specific and detailed
4. Always respond with valid JSON only
5. No markdown code blocks, just raw JSON"""

        result = await self.llm_provider.complete(
            prompt=prompt, system_message=system_message, temperature=0.7, max_tokens=2000
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
            raise ValueError(f"Failed to parse LLM output as JSON: {e}\nOutput: {content}") from e

    def _parse_organization(
        self, org_data: dict[str, Any], industry: str, size: str, template: dict[str, Any]
    ) -> Organization:
        """Parse LLM output into Organization model."""

        org_id = f"org_{uuid.uuid4().hex[:8]}"

        return Organization(
            id=org_id,
            name=org_data.get("name", f"Example {industry} Corp"),
            description=org_data.get("description", ""),
            industry=industry,
            size=size,
            departments=[],  # Will be populated separately
            threat_actors=[],  # Will be populated separately
            security_posture=org_data.get("security_posture", "developing"),
            compliance_frameworks=org_data.get("compliance_frameworks", template["compliance_frameworks"]),
        )

    @staticmethod
    def get_supported_industries() -> list[str]:
        """Get list of supported industries."""
        return list(OrganizationGenerator.INDUSTRY_TEMPLATES.keys())

    @staticmethod
    def get_industry_info(industry: str) -> dict[str, Any] | None:
        """Get information about a specific industry."""
        return OrganizationGenerator.INDUSTRY_TEMPLATES.get(industry)
