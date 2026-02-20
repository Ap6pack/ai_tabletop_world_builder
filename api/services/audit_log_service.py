"""
Audit log service for tracking policy checks, violations, and safety events.
Provides comprehensive logging for compliance and security investigation.
"""
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from api.models import AuditLog, ComplianceReport
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class AuditLogService:
    """Service for managing audit logs and compliance tracking."""

    def __init__(self, log_dir: str = "./data/audit_logs"):
        """
        Initialize audit log service.

        Args:
            log_dir: Directory for storing audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file = self._get_current_log_file()

    def _get_current_log_file(self) -> Path:
        """
        Get the current log file path (daily rotation).

        Returns:
            Path to current log file
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{today}.jsonl"

    def _hash_content(self, content: str) -> str:
        """
        Create SHA256 hash of content for privacy.

        Args:
            content: Content to hash

        Returns:
            SHA256 hash hex string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def log_policy_check(
        self,
        content: str,
        policy_level: str,
        result: str,
        violations: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log a policy check event.

        Args:
            content: Content that was checked (will be hashed)
            policy_level: Policy level used
            result: Result (allowed, blocked, sanitized)
            violations: List of violations found
            session_id: Optional game session ID
            user_id: Optional user ID
            metadata: Optional additional metadata

        Returns:
            Created AuditLog entry
        """
        content_hash = self._hash_content(content)

        log_entry = AuditLog(
            event_type="policy_check",
            severity="info" if result == "allowed" else "warning",
            policy_level=policy_level,
            content_hash=content_hash,
            result=result,
            violations=violations or [],
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )

        self._write_log_entry(log_entry)

        logger.info(
            f"Policy check logged: {result}",
            extra={
                "log_id": log_entry.id,
                "policy_level": policy_level,
                "result": result,
                "violations": len(violations or [])
            }
        )

        return log_entry

    def log_violation(
        self,
        content: str,
        violation_type: str,
        severity: str,
        policy_level: str,
        action_taken: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log a policy violation event.

        Args:
            content: Content that violated policy (will be hashed)
            violation_type: Type of violation
            severity: Severity level (low/medium/high/critical)
            policy_level: Policy level in effect
            action_taken: Action taken in response
            session_id: Optional game session ID
            user_id: Optional user ID
            metadata: Optional additional metadata

        Returns:
            Created AuditLog entry
        """
        content_hash = self._hash_content(content)

        log_severity = {
            "low": "info",
            "medium": "warning",
            "high": "error",
            "critical": "critical"
        }.get(severity, "warning")

        log_entry = AuditLog(
            event_type="violation",
            severity=log_severity,
            policy_level=policy_level,
            content_hash=content_hash,
            result="blocked",
            violations=[violation_type],
            action_taken=action_taken,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )

        self._write_log_entry(log_entry)

        logger.warning(
            f"Violation logged: {violation_type} ({severity})",
            extra={
                "log_id": log_entry.id,
                "violation_type": violation_type,
                "severity": severity,
                "action_taken": action_taken
            }
        )

        return log_entry

    def log_filter(
        self,
        content: str,
        filter_type: str,
        matched_patterns: List[str],
        policy_level: str,
        result: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log a content filter event.

        Args:
            content: Content that was filtered (will be hashed)
            filter_type: Type of filter applied
            matched_patterns: Patterns that matched
            policy_level: Policy level in effect
            result: Result (allowed, blocked, sanitized)
            session_id: Optional game session ID
            metadata: Optional additional metadata

        Returns:
            Created AuditLog entry
        """
        content_hash = self._hash_content(content)

        log_entry = AuditLog(
            event_type="filter",
            severity="info" if result == "allowed" else "warning",
            policy_level=policy_level,
            content_hash=content_hash,
            result=result,
            violations=matched_patterns,
            action_taken=f"Content {result}",
            session_id=session_id,
            metadata=metadata or {}
        )

        self._write_log_entry(log_entry)

        logger.info(
            f"Filter logged: {filter_type} - {result}",
            extra={
                "log_id": log_entry.id,
                "filter_type": filter_type,
                "patterns": len(matched_patterns),
                "result": result
            }
        )

        return log_entry

    def log_sanitization(
        self,
        content: str,
        sanitized_content: str,
        violations: List[str],
        policy_level: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log a content sanitization event.

        Args:
            content: Original content (will be hashed)
            sanitized_content: Sanitized content (will be hashed)
            violations: Violations that were sanitized
            policy_level: Policy level in effect
            session_id: Optional game session ID
            metadata: Optional additional metadata

        Returns:
            Created AuditLog entry
        """
        content_hash = self._hash_content(content)
        sanitized_hash = self._hash_content(sanitized_content)

        log_entry = AuditLog(
            event_type="sanitization",
            severity="info",
            policy_level=policy_level,
            content_hash=content_hash,
            result="sanitized",
            violations=violations,
            action_taken="Content sanitized",
            session_id=session_id,
            metadata={
                **(metadata or {}),
                "sanitized_hash": sanitized_hash
            }
        )

        self._write_log_entry(log_entry)

        logger.info(
            f"Sanitization logged: {len(violations)} violations redacted",
            extra={
                "log_id": log_entry.id,
                "violations": len(violations)
            }
        )

        return log_entry

    def _write_log_entry(self, log_entry: AuditLog) -> None:
        """
        Write a log entry to the current log file.

        Args:
            log_entry: AuditLog to write
        """
        # Convert to JSON-serializable dict
        log_dict = log_entry.model_dump()
        log_dict['timestamp'] = log_dict['timestamp'].isoformat()

        # Append to JSONL file
        with open(self.current_log_file, 'a') as f:
            f.write(json.dumps(log_dict) + '\n')

    def get_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Retrieve audit logs with filters.

        Args:
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            event_type: Filter by event type
            severity: Filter by severity
            session_id: Filter by session ID
            user_id: Filter by user ID
            limit: Maximum number of logs to return

        Returns:
            List of matching AuditLog entries
        """
        logs = []

        # Determine which log files to read
        log_files = self._get_log_files_in_range(start_date, end_date)

        for log_file in log_files:
            if not log_file.exists():
                continue

            with open(log_file, 'r') as f:
                for line in f:
                    if len(logs) >= limit:
                        break

                    try:
                        log_dict = json.loads(line)
                        log_dict['timestamp'] = datetime.fromisoformat(log_dict['timestamp'])

                        # Apply filters
                        if start_date and log_dict['timestamp'] < start_date:
                            continue
                        if end_date and log_dict['timestamp'] > end_date:
                            continue
                        if event_type and log_dict['event_type'] != event_type:
                            continue
                        if severity and log_dict['severity'] != severity:
                            continue
                        if session_id and log_dict.get('session_id') != session_id:
                            continue
                        if user_id and log_dict.get('user_id') != user_id:
                            continue

                        logs.append(AuditLog(**log_dict))

                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(f"Failed to parse log entry: {e}")
                        continue

            if len(logs) >= limit:
                break

        return logs[:limit]

    def _get_log_files_in_range(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[Path]:
        """
        Get log files that might contain entries in the date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of log file paths
        """
        if not start_date and not end_date:
            # Return all log files
            return sorted(self.log_dir.glob("audit_*.jsonl"))

        # Generate list of dates in range
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)  # Default: last 30 days
        if not end_date:
            end_date = datetime.now(timezone.utc)

        log_files = []
        current_date = start_date.date()
        end = end_date.date()

        while current_date <= end:
            log_file = self.log_dir / f"audit_{current_date.isoformat()}.jsonl"
            if log_file.exists():
                log_files.append(log_file)
            current_date += timedelta(days=1)

        return log_files

    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> ComplianceReport:
        """
        Generate a compliance report for a time period.

        Args:
            start_date: Start of reporting period
            end_date: End of reporting period

        Returns:
            ComplianceReport with statistics
        """
        logs = self.get_logs(
            start_date=start_date,
            end_date=end_date,
            limit=10000  # High limit for reporting
        )

        total_checks = 0
        total_violations = 0
        violations_by_type = {}
        violations_by_severity = {}
        policy_level_distribution = {}

        for log in logs:
            if log.event_type == "policy_check":
                total_checks += 1

            if log.event_type == "violation":
                total_violations += 1

            # Count violations by type
            for violation in log.violations:
                violations_by_type[violation] = violations_by_type.get(violation, 0) + 1

            # Count by severity
            if log.event_type in ["violation", "filter"]:
                violations_by_severity[log.severity] = violations_by_severity.get(log.severity, 0) + 1

            # Track policy level usage
            policy_level_distribution[log.policy_level] = policy_level_distribution.get(log.policy_level, 0) + 1

        # Calculate violation rate
        violation_rate = (total_violations / total_checks * 100) if total_checks > 0 else 0.0

        # Get top violation patterns
        top_violations = sorted(
            violations_by_type.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        top_violation_patterns = [
            {"pattern": pattern, "count": count}
            for pattern, count in top_violations
        ]

        report = ComplianceReport(
            period_start=start_date,
            period_end=end_date,
            total_checks=total_checks,
            total_violations=total_violations,
            violation_rate=round(violation_rate, 2),
            violations_by_type=violations_by_type,
            violations_by_severity=violations_by_severity,
            policy_level_distribution=policy_level_distribution,
            top_violation_patterns=top_violation_patterns
        )

        logger.info(
            f"Compliance report generated: {total_checks} checks, {total_violations} violations",
            extra={
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "violation_rate": violation_rate
            }
        )

        return report

    def cleanup_old_logs(self, retention_days: int = 90) -> int:
        """
        Clean up audit logs older than retention period.

        Args:
            retention_days: Number of days to retain logs

        Returns:
            Number of log files deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted_count = 0

        for log_file in self.log_dir.glob("audit_*.jsonl"):
            try:
                # Parse date from filename
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)

                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old audit log: {log_file.name}")

            except (ValueError, OSError) as e:
                logger.error(f"Failed to process log file {log_file.name}: {e}")
                continue

        logger.info(f"Audit log cleanup complete: {deleted_count} files deleted")
        return deleted_count
