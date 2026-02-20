#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Threat actor generator service for creating realistic adversary profiles.
"""
from typing import List, Dict, Any, Optional
from api.models import ThreatActor
from api.providers import LLMProviderFactory
import json
import uuid


class ThreatActorGenerator:
    """Generates realistic threat actor profiles for scenarios."""

    def __init__(self, llm_provider=None):
        """Initialize the threat actor generator."""
        self.llm_provider = llm_provider or LLMProviderFactory.create_provider()

    async def generate_threat_actors(
        self,
        organization_name: str,
        industry: str,
        focus_areas: Optional[List[str]] = None,
        num_actors: int = 2
    ) -> List[ThreatActor]:
        """
        Generate threat actors targeting an organization.

        Args:
            organization_name: Name of the target organization
            industry: Industry sector
            focus_areas: Optional focus areas (e.g., ["ransomware", "insider-threat"])
            num_actors: Number of threat actors to generate

        Returns:
            List of ThreatActor instances
        """
        prompt = self._build_threat_actors_prompt(
            organization_name,
            industry,
            focus_areas,
            num_actors
        )

        actors_data = await self._generate_with_llm(prompt)

        threat_actors = []
        for actor_info in actors_data.get("threat_actors", []):
            threat_actor = self._parse_threat_actor(actor_info)
            threat_actors.append(threat_actor)

        return threat_actors

    def _build_threat_actors_prompt(
        self,
        organization_name: str,
        industry: str,
        focus_areas: Optional[List[str]],
        num_actors: int
    ) -> str:
        """Build prompt for threat actor generation."""

        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nFOCUS AREAS: Generate threat actors related to: {', '.join(focus_areas)}"

        prompt = f"""Generate {num_actors} realistic threat actor profiles targeting {organization_name}, a {industry} organization.

TARGET ORGANIZATION:
- Name: {organization_name}
- Industry: {industry}
{focus_text}

For each threat actor, provide:
1. Threat actor name/group name (realistic but fictional)
2. Description and background
3. Primary motivation (financial, espionage, disruption, ideology, etc.)
4. Sophistication level (nation-state, organized-crime, hacktivist, script-kiddie)
5. Tactics, Techniques, and Procedures (TTPs) - list 4-6 specific techniques
6. Target preferences (what they typically target in this industry)

Create diverse threat actors with different motivations and capabilities.

Respond with valid JSON in this format:
{{
    "threat_actors": [
        {{
            "name": "Threat Actor Name",
            "description": "Background and profile of this threat actor",
            "motivation": "Their primary goal",
            "sophistication": "organized-crime",
            "ttps": [
                "Initial Access: Phishing",
                "Execution: PowerShell",
                "Persistence: Registry modification",
                "Lateral Movement: RDP",
                "Exfiltration: HTTPS tunnel",
                "Impact: Ransomware deployment"
            ],
            "targets": ["Customer databases", "Financial systems", "Intellectual property"]
        }}
    ]
}}

IMPORTANT:
- Use MITRE ATT&CK style TTPs
- Be specific and realistic
- Respond ONLY with valid JSON
- No additional text"""

        return prompt

    async def _generate_with_llm(self, prompt: str) -> Dict[str, Any]:
        """Generate content using LLM and parse JSON."""

        system_message = """You are generating realistic threat actor profiles for cybersecurity training scenarios.

RULES:
1. Create realistic but fictional threat actors
2. Use proper security terminology
3. Reference MITRE ATT&CK tactics when describing TTPs
4. Match sophistication to capabilities
5. Make motivations realistic for the industry
6. Always respond with valid JSON only
7. Keep it educational and realistic"""

        result = await self.llm_provider.complete(
            prompt=prompt,
            system_message=system_message,
            temperature=0.8,  # Slightly higher for creative threat actor names
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
            raise ValueError(f"Failed to parse threat actor data: {e}\nOutput: {content}")

    def _parse_threat_actor(self, actor_info: Dict[str, Any]) -> ThreatActor:
        """Parse threat actor data into ThreatActor model."""

        actor_id = f"actor_{uuid.uuid4().hex[:8]}"

        return ThreatActor(
            id=actor_id,
            name=actor_info.get("name", "Unknown Threat Actor"),
            description=actor_info.get("description", ""),
            motivation=actor_info.get("motivation", "Unknown"),
            sophistication=actor_info.get("sophistication", "script-kiddie"),
            ttps=actor_info.get("ttps", []),
            targets=actor_info.get("targets", [])
        )
