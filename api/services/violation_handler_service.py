"""
Violation handler service for managing policy violations.
Provides automated responses, escalation, and user education.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from api.models import PolicyViolation, ViolationResponse
from api.services.audit_log_service import AuditLogService
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class ViolationHandlerService:
    """Service for handling policy violations with appropriate responses."""

    def __init__(self, audit_log_service: Optional[AuditLogService] = None):
        """
        Initialize violation handler service.

        Args:
            audit_log_service: Optional audit log service for logging
        """
        self.audit_log_service = audit_log_service or AuditLogService()
        self.violation_history: Dict[str, List[PolicyViolation]] = defaultdict(list)

    def handle_violation(
        self,
        content: str,
        violation_type: str,
        severity: str,
        policy_level: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ViolationResponse:
        """
        Handle a policy violation with appropriate response.

        Args:
            content: Content that violated policy
            violation_type: Type of violation
            severity: Severity level (low/medium/high/critical)
            policy_level: Policy level in effect
            session_id: Optional session ID
            user_id: Optional user ID
            metadata: Optional additional metadata

        Returns:
            ViolationResponse with action and messaging
        """
        logger.info(
            f"Handling {severity} violation: {violation_type}",
            extra={"session_id": session_id, "user_id": user_id}
        )

        # Create violation record
        violation = PolicyViolation(
            severity=severity,
            violation_type=violation_type,
            content_hash=self.audit_log_service._hash_content(content),
            policy_level=policy_level,
            user_id=user_id,
            session_id=session_id,
            action_taken="pending",
            metadata=metadata or {}
        )

        # Check violation history for escalation
        if user_id:
            self.violation_history[user_id].append(violation)

        # Determine response based on severity and history
        response = self._determine_response(violation, user_id)

        # Update violation record with action taken
        violation.action_taken = response.action

        # Log violation to audit trail
        self.audit_log_service.log_violation(
            content=content,
            violation_type=violation_type,
            severity=severity,
            policy_level=policy_level,
            action_taken=response.action,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata
        )

        logger.info(
            f"Violation handled: {response.action}",
            extra={
                "violation_id": violation.id,
                "action": response.action,
                "requires_review": response.requires_review
            }
        )

        return response

    def _determine_response(
        self,
        violation: PolicyViolation,
        user_id: Optional[str]
    ) -> ViolationResponse:
        """
        Determine appropriate response to violation.

        Args:
            violation: PolicyViolation record
            user_id: Optional user ID

        Returns:
            ViolationResponse
        """
        severity = violation.severity
        violation_type = violation.violation_type

        # Check for repeat violations (escalation)
        repeat_violations = self._get_recent_violations(user_id) if user_id else []
        is_repeat = len(repeat_violations) > 1

        # Severity-based response logic
        if severity == "low":
            return self._handle_low_severity(violation, is_repeat)
        elif severity == "medium":
            return self._handle_medium_severity(violation, is_repeat)
        elif severity == "high":
            return self._handle_high_severity(violation, is_repeat)
        else:  # critical
            return self._handle_critical_severity(violation, is_repeat)

    def _handle_low_severity(
        self,
        violation: PolicyViolation,
        is_repeat: bool
    ) -> ViolationResponse:
        """Handle low severity violations."""
        if is_repeat:
            # Second low violation - give warning
            return ViolationResponse(
                action="warn",
                message="Your action was blocked due to policy restrictions. This is your second violation. Please review the content policy guidelines.",
                educational_content=self._get_educational_content(violation.violation_type),
                suggested_alternative=self._get_alternative_suggestion(violation.violation_type),
                requires_review=False
            )
        else:
            # First low violation - informational
            return ViolationResponse(
                action="warn",
                message="Your action was flagged for review but allowed. Please be mindful of content policy restrictions.",
                educational_content=self._get_educational_content(violation.violation_type),
                requires_review=False
            )

    def _handle_medium_severity(
        self,
        violation: PolicyViolation,
        is_repeat: bool
    ) -> ViolationResponse:
        """Handle medium severity violations."""
        if is_repeat:
            # Repeat medium violation - escalate
            return ViolationResponse(
                action="escalate",
                message="Your action has been blocked due to repeated policy violations. This incident will be reviewed by administrators.",
                educational_content=self._get_educational_content(violation.violation_type),
                suggested_alternative=self._get_alternative_suggestion(violation.violation_type),
                requires_review=True
            )
        else:
            # First medium violation - block with education
            return ViolationResponse(
                action="block",
                message="Your action was blocked due to policy restrictions. Please review the guidelines and try a different approach.",
                educational_content=self._get_educational_content(violation.violation_type),
                suggested_alternative=self._get_alternative_suggestion(violation.violation_type),
                requires_review=False
            )

    def _handle_high_severity(
        self,
        violation: PolicyViolation,
        is_repeat: bool
    ) -> ViolationResponse:
        """Handle high severity violations."""
        return ViolationResponse(
            action="escalate",
            message="Your action has been blocked due to a serious policy violation. This incident has been logged and will be reviewed.",
            educational_content=self._get_educational_content(violation.violation_type),
            suggested_alternative=self._get_alternative_suggestion(violation.violation_type),
            requires_review=True
        )

    def _handle_critical_severity(
        self,
        violation: PolicyViolation,
        is_repeat: bool
    ) -> ViolationResponse:
        """Handle critical severity violations."""
        return ViolationResponse(
            action="escalate",
            message="Your action has been blocked due to a critical security policy violation. This incident has been logged and flagged for immediate review. Continued violations may result in restricted access.",
            educational_content=self._get_educational_content(violation.violation_type),
            requires_review=True
        )

    def _get_educational_content(self, violation_type: str) -> str:
        """
        Get educational content for violation type.

        Args:
            violation_type: Type of violation

        Returns:
            Educational message
        """
        educational_messages = {
            "credentials": "Security best practice: Never share actual credentials, API keys, or passwords in training exercises. Use placeholder values like '[API_KEY]' or '[PASSWORD]' instead. This protects real credentials and maintains security hygiene.",

            "pii": "Privacy reminder: Avoid including real personal information (PII) such as actual names, email addresses, phone numbers, or social security numbers. Use fictional examples to maintain privacy standards and comply with data protection regulations.",

            "exploit_code": "Training guideline: While learning about security vulnerabilities is important, avoid including actual exploit code or malicious commands. Instead, describe the concepts and techniques in educational terms. This keeps the training safe and compliant.",

            "sql_injection": "SQL injection awareness: Discuss SQL injection concepts without including actual malicious SQL queries. Focus on detection, prevention, and remediation techniques rather than exploitation methods.",

            "xss": "XSS education: Cross-site scripting (XSS) should be discussed conceptually. Avoid including actual XSS payloads. Focus on understanding attack vectors, detection methods, and secure coding practices.",

            "shellcode": "Shellcode policy: Discussion of shellcode and exploit payloads should remain conceptual. Focus on defense mechanisms, detection techniques, and system hardening rather than actual exploitation code.",

            "dangerous_commands": "Safe practices: Avoid demonstrating destructive commands that could cause system damage. Focus on detection, monitoring, and incident response procedures instead.",
        }

        # Try to match violation type to educational content
        for key, message in educational_messages.items():
            if key in violation_type.lower():
                return message

        # Default educational content
        return "Content policy reminder: Please ensure your actions comply with the current policy level. Focus on educational value and safe security practices. When in doubt, describe concepts rather than demonstrating potentially harmful techniques."

    def _get_alternative_suggestion(self, violation_type: str) -> str:
        """
        Get suggested alternative approach.

        Args:
            violation_type: Type of violation

        Returns:
            Alternative suggestion
        """
        suggestions = {
            "credentials": "Instead of using actual credentials, try: 'Check if the authentication system properly validates credentials' or 'Test the login mechanism with a test account'.",

            "pii": "Instead of real information, try: 'Investigate user records with anonymized data' or 'Search for patterns in the dataset without exposing individual identities'.",

            "exploit_code": "Instead of actual exploit code, try: 'Research the vulnerability type and its characteristics' or 'Review security advisories about this issue'.",

            "sql_injection": "Instead of SQL injection payloads, try: 'Test input validation on the login form' or 'Review database query parameterization'.",

            "xss": "Instead of XSS payloads, try: 'Check input sanitization in the web application' or 'Review Content Security Policy headers'.",

            "dangerous_commands": "Instead of destructive commands, try: 'Analyze system logs for suspicious activity' or 'Review access controls and permissions'.",
        }

        # Try to match violation type to suggestion
        for key, suggestion in suggestions.items():
            if key in violation_type.lower():
                return suggestion

        # Default suggestion
        return "Try rephrasing your action to focus on security analysis, detection, or response rather than actual exploitation or execution of potentially harmful commands."

    def _get_recent_violations(
        self,
        user_id: str,
        time_window_hours: int = 24
    ) -> List[PolicyViolation]:
        """
        Get recent violations for a user.

        Args:
            user_id: User ID
            time_window_hours: Time window in hours

        Returns:
            List of recent violations
        """
        if user_id not in self.violation_history:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        recent_violations = [
            v for v in self.violation_history[user_id]
            if v.timestamp > cutoff_time
        ]

        return recent_violations

    def get_violation_metrics(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get violation metrics for a user or session.

        Args:
            user_id: Optional user ID
            session_id: Optional session ID

        Returns:
            Dictionary of metrics
        """
        violations = []

        if user_id and user_id in self.violation_history:
            violations = self.violation_history[user_id]

        if session_id:
            # Filter by session
            violations = [v for v in violations if v.session_id == session_id]

        if not violations:
            return {
                "total_violations": 0,
                "by_severity": {},
                "by_type": {},
                "recent_violations": 0
            }

        # Calculate metrics
        by_severity = defaultdict(int)
        by_type = defaultdict(int)

        for violation in violations:
            by_severity[violation.severity] += 1
            by_type[violation.violation_type] += 1

        recent = self._get_recent_violations(user_id) if user_id else []

        return {
            "total_violations": len(violations),
            "by_severity": dict(by_severity),
            "by_type": dict(by_type),
            "recent_violations": len(recent),
            "last_violation": violations[-1].timestamp.isoformat() if violations else None
        }

    def reset_user_violations(self, user_id: str) -> int:
        """
        Reset violation history for a user.

        Args:
            user_id: User ID

        Returns:
            Number of violations cleared
        """
        if user_id in self.violation_history:
            count = len(self.violation_history[user_id])
            del self.violation_history[user_id]
            logger.info(f"Reset {count} violations for user {user_id}")
            return count
        return 0
