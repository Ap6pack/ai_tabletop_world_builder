#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Content policy service for safety and moderation.
"""

from api.models import ContentCheckRequest, ContentCheckResponse, ContentPolicy
from api.providers import LLMProviderFactory


class ContentPolicyService:
    """Service for content moderation and policy enforcement."""

    # Define policy configurations
    POLICIES = {
        "defensive": {
            "description": "Defensive security only - no offensive techniques, exploit code, or attack methods",
            "allowed_categories": [
                "Security monitoring and detection",
                "Incident response procedures",
                "Security controls and hardening",
                "Compliance and auditing",
                "Risk assessment",
                "Security awareness training",
            ],
            "blocked_categories": [
                "Exploit code or payloads",
                "Offensive hacking techniques",
                "Social engineering attacks",
                "Malware development",
                "Network intrusion methods",
            ],
        },
        "educational": {
            "description": "Educational content - realistic scenarios with defensive focus and learning objectives",
            "allowed_categories": [
                "Security monitoring and detection",
                "Incident response procedures",
                "Vulnerability identification (educational)",
                "Threat modeling",
                "Security architecture",
                "Penetration testing concepts (theory)",
                "Forensics and investigation",
            ],
            "blocked_categories": [
                "Actual exploit code",
                "Real credential theft techniques",
                "Weaponized malware",
                "Active attack campaigns",
            ],
        },
        "advanced": {
            "description": "Advanced training - realistic attack/defense scenarios for experienced security professionals",
            "allowed_categories": [
                "All educational categories",
                "Red team tactics (educational context)",
                "Exploitation techniques (sandboxed)",
                "Advanced persistent threats (analysis)",
                "Zero-day vulnerability discussion",
                "Offensive security concepts",
            ],
            "blocked_categories": [
                "Production-ready exploit code",
                "Real-world attack coordination",
                "Illegal activities",
            ],
        },
        "unrestricted": {
            "description": "Unrestricted content - full realism for advanced security training (use with caution)",
            "allowed_categories": [
                "All security content",
                "Realistic attack scenarios",
                "Detailed exploitation techniques",
                "Advanced threat actor TTPs",
            ],
            "blocked_categories": ["Illegal activities unrelated to security training"],
        },
    }

    @staticmethod
    def get_policy(level: str) -> ContentPolicy:
        """
        Get a content policy by level.

        Args:
            level: Policy level (defensive, educational, advanced, unrestricted)

        Returns:
            ContentPolicy instance
        """
        policy_config = ContentPolicyService.POLICIES.get(level, ContentPolicyService.POLICIES["educational"])
        return ContentPolicy(
            level=level,
            description=policy_config["description"],
            allowed_categories=policy_config["allowed_categories"],
            blocked_categories=policy_config["blocked_categories"],
        )

    @staticmethod
    async def check_content(request: ContentCheckRequest) -> ContentCheckResponse:
        """
        Check if content complies with the specified policy.

        Args:
            request: Content check request with content and policy

        Returns:
            ContentCheckResponse with safety assessment
        """
        policy = request.policy
        content = request.content

        # Build a prompt to check content against policy
        system_message = f"""You are a content safety checker for cybersecurity training scenarios.
Your job is to determine if the provided content is appropriate for the "{policy.level}" policy level.

Policy Description: {policy.description}

Allowed Categories:
{chr(10).join(f"- {cat}" for cat in policy.allowed_categories)}

Blocked Categories:
{chr(10).join(f"- {cat}" for cat in policy.blocked_categories)}

Analyze the content and respond with:
1. "SAFE" if the content is appropriate for this policy level
2. "UNSAFE" if the content violates the policy
3. List any specific violations or concerns

Be strict but fair. Remember this is for legitimate security training purposes."""

        prompt = f"""Analyze this content for policy compliance:

Content:
{content}

Respond in this exact format:
STATUS: [SAFE or UNSAFE]
VIOLATIONS: [comma-separated list of violations, or "none"]
REASONING: [brief explanation]"""

        try:
            provider = LLMProviderFactory.create_provider()
            result = await provider.complete(
                prompt=prompt,
                system_message=system_message,
                temperature=0.3,  # Lower temperature for more consistent safety checks
                max_tokens=500,
            )

            response_text = result["content"].strip()

            # Parse the response
            is_safe = "STATUS: SAFE" in response_text
            violations = []

            # Extract violations if any
            if "VIOLATIONS:" in response_text:
                violations_line = response_text.split("VIOLATIONS:")[1].split("\n")[0].strip()
                if violations_line.lower() != "none":
                    violations = [v.strip() for v in violations_line.split(",")]

            message = None
            if "REASONING:" in response_text:
                message = response_text.split("REASONING:")[1].strip()

            return ContentCheckResponse(
                is_safe=is_safe, policy_level=policy.level, violations=violations, message=message
            )

        except Exception as e:
            # If policy check fails, default to unsafe for caution
            return ContentCheckResponse(
                is_safe=False,
                policy_level=policy.level,
                violations=["Error during policy check"],
                message=f"Policy check failed: {str(e)}",
            )

    @staticmethod
    def list_policies() -> dict:
        """
        List all available content policies.

        Returns:
            Dict of policy configurations
        """
        return ContentPolicyService.POLICIES
