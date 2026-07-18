#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Action filter service for pre-action content checking.
Checks player actions before they are processed to ensure policy compliance.
"""

from api.providers import LLMProviderFactory
from api.utils.logger import setup_logger
from api.utils.pattern_matcher import PatternMatch, PatternMatcher

logger = setup_logger(__name__)


class ActionCheckResult:
    """Result of action content check."""

    def __init__(
        self,
        is_allowed: bool,
        reason: str | None = None,
        violations: list[str] | None = None,
        severity: str = "medium",
        suggested_alternative: str | None = None,
        matched_patterns: list[PatternMatch] | None = None,
    ):
        self.is_allowed = is_allowed
        self.reason = reason
        self.violations = violations or []
        self.severity = severity
        self.suggested_alternative = suggested_alternative
        self.matched_patterns = matched_patterns or []

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "is_allowed": self.is_allowed,
            "reason": self.reason,
            "violations": self.violations,
            "severity": self.severity,
            "suggested_alternative": self.suggested_alternative,
            "pattern_matches": len(self.matched_patterns),
        }


class ActionFilterService:
    """Service for filtering player actions based on content policy."""

    def __init__(self, llm_provider=None):
        """
        Initialize action filter service.

        Args:
            llm_provider: Optional LLM provider for semantic analysis
        """
        self.llm_provider = llm_provider

    async def check_action(
        self,
        action: str,
        policy_level: str = "educational",
        session_id: str | None = None,
        enable_quick_check: bool = True,
        enable_llm_check: bool = True,
    ) -> ActionCheckResult:
        """
        Check if an action is allowed under the given policy.

        Args:
            action: Player action text
            policy_level: Content policy level
            session_id: Optional session ID for logging
            enable_quick_check: Enable fast pattern-based checks
            enable_llm_check: Enable LLM semantic analysis

        Returns:
            ActionCheckResult with decision and details
        """
        logger.info(
            f"Checking action for policy '{policy_level}'",
            extra={"session_id": session_id, "action_length": len(action)},
        )

        # Stage 1: Quick pattern-based check (fast)
        if enable_quick_check:
            quick_result = self._quick_pattern_check(action, policy_level)
            if not quick_result.is_allowed:
                logger.warning(
                    f"Action blocked by quick check: {quick_result.reason}",
                    extra={"session_id": session_id, "violations": quick_result.violations},
                )
                return quick_result

        # Stage 2: LLM-based semantic analysis (thorough but slower)
        if enable_llm_check:
            llm_result = await self._llm_semantic_check(action, policy_level)
            if not llm_result.is_allowed:
                logger.warning(
                    f"Action blocked by LLM check: {llm_result.reason}",
                    extra={"session_id": session_id, "violations": llm_result.violations},
                )
                return llm_result

        # Action is allowed
        logger.info("Action approved", extra={"session_id": session_id})
        return ActionCheckResult(is_allowed=True, reason="Action complies with content policy")

    def _quick_pattern_check(self, action: str, policy_level: str) -> ActionCheckResult:
        """
        Quick pattern-based check for obvious violations.

        Args:
            action: Player action text
            policy_level: Content policy level

        Returns:
            ActionCheckResult
        """
        # Determine which categories to check based on policy level
        categories_to_check = self._get_categories_for_policy(policy_level)

        # Find pattern matches
        matches = PatternMatcher.find_matches(action, categories_to_check)

        if not matches:
            return ActionCheckResult(is_allowed=True)

        # Analyze matches
        summary = PatternMatcher.get_match_summary(matches)
        highest_severity = summary["highest_severity"]

        # Determine if action should be blocked
        should_block = False
        violations = []

        # Critical patterns always block
        if highest_severity == "critical":
            should_block = True
            violations.append("Critical security violation detected")

        # High severity patterns block except in unrestricted mode
        elif highest_severity == "high" and policy_level != "unrestricted":
            should_block = True
            violations.append("High-risk content detected")

        # Medium severity only blocks in defensive mode for non-credential patterns
        elif highest_severity == "medium" and policy_level == "defensive":
            # Only block medium severity credentials in defensive mode
            credential_matches = [m for m in matches if m.category == "credentials"]
            if credential_matches:
                should_block = True
                violations.append("Content not appropriate for this policy level")

        # Low severity never blocks (informational only)

        if should_block:
            # Generate reason and suggestions
            reason = self._generate_block_reason(matches, policy_level)
            suggested_alternative = self._suggest_alternative(matches, action)

            return ActionCheckResult(
                is_allowed=False,
                reason=reason,
                violations=violations,
                severity=highest_severity,
                suggested_alternative=suggested_alternative,
                matched_patterns=matches,
            )

        return ActionCheckResult(is_allowed=True, matched_patterns=matches)

    async def _llm_semantic_check(self, action: str, policy_level: str) -> ActionCheckResult:
        """
        LLM-based semantic analysis for context-aware checking.

        Args:
            action: Player action text
            policy_level: Content policy level

        Returns:
            ActionCheckResult
        """
        try:
            # Get policy configuration
            from api.services.content_policy_service import ContentPolicyService

            policy = ContentPolicyService.get_policy(policy_level)

            # Build prompt for LLM
            system_message = f"""You are a content safety checker for a cybersecurity training platform.
Your job is to determine if a player action is appropriate for the "{policy_level}" policy level.

Policy Description: {policy.description}

Allowed Categories:
{chr(10).join(f"- {cat}" for cat in policy.allowed_categories)}

Blocked Categories:
{chr(10).join(f"- {cat}" for cat in policy.blocked_categories)}

Analyze the action and respond with:
1. "ALLOWED" if the action is appropriate and educational
2. "BLOCKED" if the action violates the policy or is inappropriate
3. A brief explanation
4. If blocked, suggest a safer alternative

Remember: This is for legitimate cybersecurity training. Focus on educational value vs. risk."""

            prompt = f"""Analyze this player action:

Action: "{action}"

Respond in this format:
STATUS: [ALLOWED or BLOCKED]
REASON: [brief explanation]
ALTERNATIVE: [suggested alternative if blocked, or "none"]
SEVERITY: [low, medium, high, or critical if blocked]"""

            # Get LLM provider
            if not self.llm_provider:
                self.llm_provider = LLMProviderFactory.create_provider()

            # Call LLM
            result = await self.llm_provider.complete(
                prompt=prompt,
                system_message=system_message,
                temperature=0.3,  # Lower temperature for consistent safety checks
                max_tokens=300,
            )

            response_text = result["content"].strip()

            # Parse response
            is_allowed = "STATUS: ALLOWED" in response_text
            reason = None
            suggested_alternative = None
            severity = "medium"

            if "REASON:" in response_text:
                reason_line = response_text.split("REASON:")[1].split("\n")[0].strip()
                reason = reason_line

            if "ALTERNATIVE:" in response_text:
                alt_line = response_text.split("ALTERNATIVE:")[1].split("\n")[0].strip()
                if alt_line.lower() != "none":
                    suggested_alternative = alt_line

            if "SEVERITY:" in response_text:
                sev_line = response_text.split("SEVERITY:")[1].split("\n")[0].strip().lower()
                if sev_line in ["low", "medium", "high", "critical"]:
                    severity = sev_line

            return ActionCheckResult(
                is_allowed=is_allowed,
                reason=reason,
                violations=["Policy violation"] if not is_allowed else [],
                severity=severity,
                suggested_alternative=suggested_alternative,
            )

        except Exception as e:
            logger.error(f"LLM semantic check failed: {str(e)}")
            # On error, default to allowing (fail open) but log the issue
            return ActionCheckResult(is_allowed=True, reason="Policy check incomplete - proceeding with caution")

    def _get_categories_for_policy(self, policy_level: str) -> list[str]:
        """
        Get pattern categories to check based on policy level.

        Args:
            policy_level: Content policy level

        Returns:
            List of categories to check
        """
        # Progressively fewer categories as the policy loosens; unrestricted
        # only checks for real credentials.
        categories_by_policy = {
            "defensive": ["credentials", "pii", "exploits", "sensitive"],
            "educational": ["credentials", "pii", "exploits"],
            "advanced": ["credentials", "pii"],
        }
        return categories_by_policy.get(policy_level, ["credentials"])

    def _generate_block_reason(self, matches: list[PatternMatch], policy_level: str) -> str:
        """
        Generate user-friendly block reason.

        Args:
            matches: Pattern matches found
            policy_level: Content policy level

        Returns:
            Human-readable reason
        """
        if not matches:
            return "Action blocked due to policy violation"

        # Get most severe match
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        most_severe = max(matches, key=lambda m: severity_order.get(m.severity, 0))

        category_messages = {
            "credentials": "This action contains what appears to be credentials or API keys.",
            "pii": "This action contains personally identifiable information (PII).",
            "exploits": "This action contains exploit code or dangerous commands.",
            "sensitive": "This action contains sensitive technical information.",
        }

        base_message = category_messages.get(most_severe.category, "This action violates the content policy.")

        policy_context = {
            "defensive": "In defensive mode, only security monitoring and incident response actions are allowed.",
            "educational": "In educational mode, actions must have clear learning objectives.",
            "advanced": "Even in advanced mode, certain content is restricted for safety.",
            "unrestricted": "This content is blocked even in unrestricted mode.",
        }

        return f"{base_message} {policy_context.get(policy_level, '')}"

    def _suggest_alternative(self, matches: list[PatternMatch], original_action: str) -> str | None:
        """
        Suggest a safer alternative action.

        Args:
            matches: Pattern matches found
            original_action: Original action text

        Returns:
            Suggested alternative or None
        """
        if not matches:
            return None

        # Get primary category
        primary_category = matches[0].category

        suggestions = {
            "credentials": "Try describing the action without including actual credentials. Use placeholders like '[API_KEY]' or '[PASSWORD]'.",
            "pii": "Describe the action using example data instead of real personal information.",
            "exploits": "Describe the security concept you're exploring without including executable code.",
            "sensitive": "Use generic examples rather than specific internal systems or addresses.",
        }

        return suggestions.get(primary_category)
