"""
Content validator service for post-generation validation.
Validates AI-generated content before returning to users.
"""
from typing import Optional, List, Dict
from datetime import datetime
from api.models import Organization, ValidationResult
from api.providers import LLMProviderFactory
from api.utils.pattern_matcher import PatternMatcher, PatternMatch
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class ContentValidatorService:
    """Service for validating AI-generated content."""

    def __init__(self, llm_provider=None):
        """
        Initialize content validator service.

        Args:
            llm_provider: Optional LLM provider for semantic validation
        """
        self.llm_provider = llm_provider

    async def validate_narrative(
        self,
        narrative: str,
        policy_level: str = "educational",
        context: Optional[Dict] = None
    ) -> ValidationResult:
        """
        Validate game narrative content.

        Args:
            narrative: Game master narrative to validate
            policy_level: Content policy level
            context: Optional context (session_id, action, etc.)

        Returns:
            ValidationResult with safety assessment
        """
        logger.info(f"Validating narrative for policy '{policy_level}'", extra={
            "context": context,
            "narrative_length": len(narrative)
        })

        # Find pattern matches
        matches = PatternMatcher.find_matches(narrative)

        if not matches:
            logger.info("Narrative validation passed - no violations")
            return ValidationResult(
                is_safe=True,
                violations=[]
            )

        # Analyze matches
        summary = PatternMatcher.get_match_summary(matches)
        highest_severity = summary["highest_severity"]

        # Determine if content is safe
        is_safe = self._is_content_safe(matches, policy_level)
        can_sanitize = self._can_sanitize(matches)

        violations = [
            f"{match.category}: {match.pattern_name}"
            for match in matches
        ]

        result = ValidationResult(
            is_safe=is_safe,
            can_sanitize=can_sanitize,
            violations=violations,
            severity=highest_severity,
            reason=self._generate_validation_reason(matches, policy_level)
        )

        if not is_safe:
            logger.warning(
                f"Narrative validation failed: {result.reason}",
                extra={"violations": violations, "severity": highest_severity}
            )

        return result

    async def validate_scenario(
        self,
        organization: Organization,
        policy_level: str = "educational"
    ) -> ValidationResult:
        """
        Validate generated scenario content.

        Args:
            organization: Generated organization/scenario
            policy_level: Content policy level

        Returns:
            ValidationResult with safety assessment
        """
        logger.info(f"Validating scenario for policy '{policy_level}'", extra={
            "org_name": organization.name
        })

        # Collect all text content from scenario
        content_parts = [
            organization.name,
            organization.description,
            organization.industry,
        ]

        # Add department descriptions
        for dept in organization.departments:
            content_parts.append(dept.name)
            content_parts.append(dept.description)

        # Add system descriptions
        for dept in organization.departments:
            for system in dept.systems:
                content_parts.append(system.name)
                content_parts.append(system.description)

        # Add vulnerability descriptions
        vulnerabilities = []
        for dept in organization.departments:
            for system in dept.systems:
                vulnerabilities.extend(system.vulnerabilities)

        for vuln in vulnerabilities:
            content_parts.append(vuln.description)
            if vuln.remediation:
                content_parts.append(vuln.remediation)

        # Add threat actor descriptions
        for threat in organization.threat_actors:
            content_parts.append(threat.name)
            content_parts.append(threat.motivation)
            content_parts.extend(threat.ttps)

        # Combine all content
        full_content = "\n".join(str(p) for p in content_parts if p)

        # Validate combined content
        matches = PatternMatcher.find_matches(full_content)

        if not matches:
            logger.info("Scenario validation passed - no violations")
            return ValidationResult(
                is_safe=True,
                violations=[]
            )

        # Analyze matches
        summary = PatternMatcher.get_match_summary(matches)
        highest_severity = summary["highest_severity"]

        is_safe = self._is_content_safe(matches, policy_level)
        can_sanitize = self._can_sanitize(matches)

        violations = [
            f"{match.category}: {match.pattern_name} in {self._locate_match(match, organization)}"
            for match in matches[:10]  # Limit to first 10 for readability
        ]

        result = ValidationResult(
            is_safe=is_safe,
            can_sanitize=can_sanitize,
            violations=violations,
            severity=highest_severity,
            reason=self._generate_validation_reason(matches, policy_level)
        )

        if not is_safe:
            logger.warning(
                f"Scenario validation failed: {result.reason}",
                extra={"violations": len(violations), "severity": highest_severity}
            )

        return result

    def sanitize_content(
        self,
        content: str,
        violations: List[str],
        redaction_style: str = "mask"
    ) -> str:
        """
        Sanitize content by redacting matched patterns.

        Args:
            content: Original content
            violations: List of violations to redact
            redaction_style: Style of redaction (mask, remove, replace)

        Returns:
            Sanitized content
        """
        # Find all matches
        matches = PatternMatcher.find_matches(content)

        if not matches:
            return content

        # Redact content
        sanitized = PatternMatcher.redact_content(content, matches, redaction_style)

        logger.info(
            f"Content sanitized: {len(matches)} patterns redacted",
            extra={"redaction_style": redaction_style}
        )

        return sanitized

    def _is_content_safe(
        self,
        matches: List[PatternMatch],
        policy_level: str
    ) -> bool:
        """
        Determine if content is safe based on matches and policy.

        Args:
            matches: Pattern matches found
            policy_level: Content policy level

        Returns:
            True if content is safe
        """
        if not matches:
            return True

        summary = PatternMatcher.get_match_summary(matches)
        highest_severity = summary["highest_severity"]

        # Critical severity always unsafe
        if highest_severity == "critical":
            return False

        # High severity unsafe except in unrestricted mode
        if highest_severity == "high" and policy_level != "unrestricted":
            return False

        # Medium severity credentials unsafe in defensive mode
        if highest_severity == "medium" and policy_level == "defensive":
            credential_matches = [m for m in matches if m.category == "credentials"]
            if credential_matches:
                return False

        # Otherwise safe (can be sanitized)
        return True

    def _can_sanitize(self, matches: List[PatternMatch]) -> bool:
        """
        Check if content can be sanitized.

        Args:
            matches: Pattern matches found

        Returns:
            True if content can be sanitized
        """
        # Can sanitize if there are matches and they're not too critical
        if not matches:
            return False

        summary = PatternMatcher.get_match_summary(matches)
        highest_severity = summary["highest_severity"]

        # Can't sanitize critical content - needs regeneration
        if highest_severity == "critical":
            return False

        # Can sanitize everything else
        return True

    def _generate_validation_reason(
        self,
        matches: List[PatternMatch],
        policy_level: str
    ) -> str:
        """
        Generate validation failure reason.

        Args:
            matches: Pattern matches found
            policy_level: Content policy level

        Returns:
            Human-readable reason
        """
        if not matches:
            return "Content passed validation"

        summary = PatternMatcher.get_match_summary(matches)

        category_counts = summary["by_category"]
        total = summary["total"]

        category_names = {
            "credentials": "credential",
            "pii": "PII",
            "exploits": "exploit code",
            "sensitive": "sensitive information"
        }

        # Build description of violations
        parts = []
        for category, count in category_counts.items():
            name = category_names.get(category, category)
            plural = "s" if count > 1 else ""
            parts.append(f"{count} {name} pattern{plural}")

        violations_desc = ", ".join(parts)

        return f"Content contains {violations_desc} that violate the '{policy_level}' policy level"

    def _locate_match(
        self,
        match: PatternMatch,
        organization: Organization
    ) -> str:
        """
        Locate where in the organization a match occurred.

        Args:
            match: Pattern match
            organization: Organization to search

        Returns:
            Location description
        """
        # This is a simplified version - could be enhanced to search
        # through organization structure and pinpoint exact location
        categories = {
            "credentials": "credentials section",
            "pii": "organization details",
            "exploits": "system descriptions",
            "sensitive": "technical details"
        }

        return categories.get(match.category, "scenario content")

    async def validate_objective(
        self,
        objective_text: str,
        policy_level: str = "educational"
    ) -> ValidationResult:
        """
        Validate objective content.

        Args:
            objective_text: Objective description/criteria
            policy_level: Content policy level

        Returns:
            ValidationResult
        """
        return await self.validate_narrative(
            objective_text,
            policy_level,
            context={"type": "objective"}
        )

    async def validate_hint(
        self,
        hint_text: str,
        policy_level: str = "educational"
    ) -> ValidationResult:
        """
        Validate hint content.

        Args:
            hint_text: Hint text
            policy_level: Content policy level

        Returns:
            ValidationResult
        """
        return await self.validate_narrative(
            hint_text,
            policy_level,
            context={"type": "hint"}
        )

    async def validate_and_sanitize(
        self,
        content: str,
        policy_level: str = "educational",
        auto_sanitize: bool = True
    ) -> tuple[bool, str]:
        """
        Validate content and optionally sanitize.

        Args:
            content: Content to validate
            policy_level: Content policy level
            auto_sanitize: Automatically sanitize if possible

        Returns:
            Tuple of (is_safe, content_or_sanitized)
        """
        result = await self.validate_narrative(content, policy_level)

        if result.is_safe:
            return True, content

        if auto_sanitize and result.can_sanitize:
            sanitized = self.sanitize_content(content, result.violations)
            return True, sanitized

        return False, content
