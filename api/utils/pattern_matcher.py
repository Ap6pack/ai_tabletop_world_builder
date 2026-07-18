#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Pattern matcher utility for content filtering.
Provides regex patterns and matching functions for detecting sensitive content.
"""

import re
from dataclasses import dataclass


@dataclass
class PatternMatch:
    """Represents a pattern match in content."""

    category: str
    pattern_name: str
    matched_text: str
    start_pos: int
    end_pos: int
    severity: str  # low, medium, high, critical


class PatternMatcher:
    """Centralized pattern matching for content filtering."""

    # Credential patterns
    CREDENTIAL_PATTERNS = {
        "aws_access_key": (r"AKIA[0-9A-Z]{16}", "high"),
        "aws_secret_key": (r"aws_secret_access_key\s*[:=]\s*[A-Za-z0-9/+=]{40}", "critical"),
        "github_token": (r"gh[ps]_[A-Za-z0-9]{36}", "high"),
        "github_pat": (r"github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59}", "high"),
        "openai_key": (r"sk-[A-Za-z0-9]{20,}", "high"),  # More flexible matching
        "anthropic_key": (r"sk-ant-[A-Za-z0-9\-]{95}", "high"),
        "generic_api_key": (r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9]{20,}['\"]?", "medium"),
        "password": (r"password\s*(?:to|[:=])\s*['\"]?[A-Za-z0-9!@#$%^&*]{6,}['\"]?", "high"),  # More flexible
        "jwt_token": (r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "medium"),
        "private_key_header": (r"-----BEGIN\s+(RSA\s+)?PRIVATE KEY-----", "critical"),
        "db_connection": (r"(mysql|postgresql|mongodb)://[^\s]+", "high"),
        "bearer_token": (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "medium"),
    }

    # PII patterns
    PII_PATTERNS = {
        "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "high"),
        "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "low"),
        "phone_us": (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "medium"),
        "credit_card": (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "high"),
        "ip_address": (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "low"),
        "mac_address": (r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b", "low"),
    }

    # Exploit code patterns
    EXPLOIT_PATTERNS = {
        "shell_exec": (r"(exec|system|popen|subprocess\.call)\s*\(", "high"),
        "sql_injection": (r"(union\s+select|or\s+1\s*=\s*1|drop\s+table)", "high"),
        "xss_payload": (r"<script[^>]*>.*?</script>", "medium"),
        "command_injection": (r"[;&|]\s*(cat|ls|pwd|whoami|wget|curl)\s+", "high"),
        "path_traversal": (r"\.\./\.\./", "medium"),
        "eval_function": (r"eval\s*\(", "high"),
        "rm_recursive": (r"rm\s+-rf\s+/", "critical"),
        "format_disk": (r"format\s+[a-z]:", "critical"),
        "drop_database": (r"drop\s+database", "critical"),
        "reverse_shell": (r"(nc|netcat|bash|sh)\s+-[a-z]*e\s+/bin/(bash|sh)", "critical"),
        "shellcode": (r"\\x[0-9a-fA-F]{2}(\\x[0-9a-fA-F]{2}){10,}", "high"),
    }

    # Sensitive information patterns
    SENSITIVE_PATTERNS = {
        "internal_ip": (r"\b(10|172\.(1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b", "medium"),
        "localhost": (r"localhost:\d+", "low"),
        "aws_arn": (r"arn:aws:[a-z0-9-]+:[a-z0-9-]*:\d+:[^\s]+", "medium"),
        "azure_resource": (r"/subscriptions/[a-f0-9-]{36}/resourceGroups/", "medium"),
    }

    @classmethod
    def find_matches(cls, content: str, categories: list[str] | None = None) -> list[PatternMatch]:
        """
        Find all pattern matches in content.

        Args:
            content: Content to search
            categories: Categories to search (credentials, pii, exploits, sensitive)
                       If None, searches all categories

        Returns:
            List of PatternMatch objects
        """
        matches = []

        # Select pattern sets based on categories
        pattern_sets = {}
        if categories is None or "credentials" in categories:
            pattern_sets["credentials"] = cls.CREDENTIAL_PATTERNS
        if categories is None or "pii" in categories:
            pattern_sets["pii"] = cls.PII_PATTERNS
        if categories is None or "exploits" in categories:
            pattern_sets["exploits"] = cls.EXPLOIT_PATTERNS
        if categories is None or "sensitive" in categories:
            pattern_sets["sensitive"] = cls.SENSITIVE_PATTERNS

        # Search for matches
        for category, patterns in pattern_sets.items():
            for pattern_name, (pattern, severity) in patterns.items():
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    matches.append(
                        PatternMatch(
                            category=category,
                            pattern_name=pattern_name,
                            matched_text=match.group(),
                            start_pos=match.start(),
                            end_pos=match.end(),
                            severity=severity,
                        )
                    )

        return matches

    @classmethod
    def has_matches(cls, content: str, categories: list[str] | None = None, min_severity: str = "low") -> bool:
        """
        Check if content has any matches.

        Args:
            content: Content to check
            categories: Categories to check
            min_severity: Minimum severity level to consider

        Returns:
            True if matches found
        """
        severity_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_levels.get(min_severity, 0)

        matches = cls.find_matches(content, categories)
        return any(severity_levels.get(match.severity, 0) >= min_level for match in matches)

    @classmethod
    def redact_content(cls, content: str, matches: list[PatternMatch], redaction_style: str = "mask") -> str:
        """
        Redact matched content.

        Args:
            content: Original content
            matches: Pattern matches to redact
            redaction_style: Style of redaction (mask, remove, replace)

        Returns:
            Redacted content
        """
        if not matches:
            return content

        # Sort matches by position (descending) to maintain correct positions during replacement
        sorted_matches = sorted(matches, key=lambda m: m.start_pos, reverse=True)

        redacted = content
        for match in sorted_matches:
            if redaction_style == "mask":
                replacement = f"[REDACTED-{match.category.upper()}]"
            elif redaction_style == "remove":
                replacement = ""
            else:  # replace
                replacement = "*" * (match.end_pos - match.start_pos)

            redacted = redacted[: match.start_pos] + replacement + redacted[match.end_pos :]

        return redacted

    @classmethod
    def get_match_summary(cls, matches: list[PatternMatch]) -> dict[str, any]:
        """
        Get summary statistics of matches.

        Args:
            matches: Pattern matches

        Returns:
            Summary dict with counts by category and severity
        """
        summary = {"total": len(matches), "by_category": {}, "by_severity": {}, "highest_severity": "low"}

        severity_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        max_severity = 0

        for match in matches:
            # Count by category
            summary["by_category"][match.category] = summary["by_category"].get(match.category, 0) + 1

            # Count by severity
            summary["by_severity"][match.severity] = summary["by_severity"].get(match.severity, 0) + 1

            # Track highest severity
            severity_level = severity_levels.get(match.severity, 0)
            if severity_level > max_severity:
                max_severity = severity_level
                summary["highest_severity"] = match.severity

        return summary
