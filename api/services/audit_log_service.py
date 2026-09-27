#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Audit log service for tracking policy checks, violations, and safety events.
Provides comprehensive logging for compliance and security investigation.
"""

import hashlib
import json
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select

from api.db import AuditChainHeadRow, AuditLogRow, session_scope
from api.models import AuditLog, ComplianceReport
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

# prev_hash of the first entry ever written.
GENESIS_HASH = "0" * 64
_CHAIN_HEAD_ID = 1
# Serializes appends within a process; the chain-head row lock (SELECT ... FOR
# UPDATE) serializes them across processes and instances on PostgreSQL.
_append_lock = threading.Lock()


def _to_naive_utc(value: datetime) -> datetime:
    """Normalize to naive UTC, the storage form of ``AuditLogRow.timestamp``."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


def _canonical(entry: dict[str, Any]) -> str:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), default=str)


def _chain_hash(prev_hash: str, entry: dict[str, Any]) -> str:
    return hashlib.sha256((prev_hash + _canonical(entry)).encode("utf-8")).hexdigest()


class AuditLogService:
    """Service for managing audit logs and compliance tracking.

    Entries live in the append-only ``audit_logs`` table, so they survive
    container restarts and are shared by every API instance. Each entry is
    chained to the previous one by hash; :meth:`verify_chain` detects edits and
    deletions in the middle of the log.
    """

    def __init__(self, log_dir: str | None = None):
        """
        Initialize audit log service.

        Args:
            log_dir: Ignored; kept for backward compatibility with the old
                file-based storage (audit logs now live in the database).
        """

    def _hash_content(self, content: str) -> str:
        """
        Create SHA256 hash of content for privacy.

        Args:
            content: Content to hash

        Returns:
            SHA256 hash hex string
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def log_policy_check(
        self,
        content: str,
        policy_level: str,
        result: str,
        violations: list[str] | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
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
            metadata=metadata or {},
        )

        self._write_log_entry(log_entry)

        logger.info(
            f"Policy check logged: {result}",
            extra={
                "log_id": log_entry.id,
                "policy_level": policy_level,
                "result": result,
                "violations": len(violations or []),
            },
        )

        return log_entry

    def log_violation(
        self,
        content: str,
        violation_type: str,
        severity: str,
        policy_level: str,
        action_taken: str,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
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

        log_severity = {"low": "info", "medium": "warning", "high": "error", "critical": "critical"}.get(
            severity, "warning"
        )

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
            metadata=metadata or {},
        )

        self._write_log_entry(log_entry)

        logger.warning(
            f"Violation logged: {violation_type} ({severity})",
            extra={
                "log_id": log_entry.id,
                "violation_type": violation_type,
                "severity": severity,
                "action_taken": action_taken,
            },
        )

        return log_entry

    def log_filter(
        self,
        content: str,
        filter_type: str,
        matched_patterns: list[str],
        policy_level: str,
        result: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
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
            metadata=metadata or {},
        )

        self._write_log_entry(log_entry)

        logger.info(
            f"Filter logged: {filter_type} - {result}",
            extra={
                "log_id": log_entry.id,
                "filter_type": filter_type,
                "patterns": len(matched_patterns),
                "result": result,
            },
        )

        return log_entry

    def log_sanitization(
        self,
        content: str,
        sanitized_content: str,
        violations: list[str],
        policy_level: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
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
            metadata={**(metadata or {}), "sanitized_hash": sanitized_hash},
        )

        self._write_log_entry(log_entry)

        logger.info(
            f"Sanitization logged: {len(violations)} violations redacted",
            extra={"log_id": log_entry.id, "violations": len(violations)},
        )

        return log_entry

    def _write_log_entry(self, log_entry: AuditLog) -> None:
        """Append a log entry to the hash chain."""
        entry = log_entry.model_dump(mode="json")
        with _append_lock, session_scope() as db:
            head = db.execute(
                select(AuditChainHeadRow).where(AuditChainHeadRow.id == _CHAIN_HEAD_ID).with_for_update()
            ).scalar_one_or_none()
            if head is None:
                head = AuditChainHeadRow(id=_CHAIN_HEAD_ID, last_hash=GENESIS_HASH)
                db.add(head)
                db.flush()
            entry_hash = _chain_hash(head.last_hash, entry)
            db.add(
                AuditLogRow(
                    id=log_entry.id,
                    timestamp=_to_naive_utc(log_entry.timestamp),
                    event_type=log_entry.event_type,
                    severity=log_entry.severity,
                    session_id=log_entry.session_id,
                    user_id=log_entry.user_id,
                    data=entry,
                    prev_hash=head.last_hash,
                    entry_hash=entry_hash,
                )
            )
            head.last_hash = entry_hash

    def get_logs(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        event_type: str | None = None,
        severity: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Retrieve audit logs with filters, oldest first.

        Args:
            start_date: Filter logs at or after this time (naive values are UTC)
            end_date: Filter logs at or before this time (naive values are UTC)
            event_type: Filter by event type
            severity: Filter by severity
            session_id: Filter by session ID
            user_id: Filter by user ID
            limit: Maximum number of logs to return

        Returns:
            List of matching AuditLog entries
        """
        stmt = select(AuditLogRow.data).order_by(AuditLogRow.seq).limit(limit)
        if start_date:
            stmt = stmt.where(AuditLogRow.timestamp >= _to_naive_utc(start_date))
        if end_date:
            stmt = stmt.where(AuditLogRow.timestamp <= _to_naive_utc(end_date))
        if event_type:
            stmt = stmt.where(AuditLogRow.event_type == event_type)
        if severity:
            stmt = stmt.where(AuditLogRow.severity == severity)
        if session_id:
            stmt = stmt.where(AuditLogRow.session_id == session_id)
        if user_id:
            stmt = stmt.where(AuditLogRow.user_id == user_id)
        with session_scope() as db:
            return [AuditLog(**data) for data in db.scalars(stmt).all()]

    def get_stats(self) -> dict[str, Any]:
        """Entry count and time range of the stored audit log."""
        with session_scope() as db:
            total, oldest, newest = db.execute(
                select(func.count(AuditLogRow.seq), func.min(AuditLogRow.timestamp), func.max(AuditLogRow.timestamp))
            ).one()
        return {
            "total_entries": total,
            "oldest_log_date": oldest.replace(tzinfo=UTC).isoformat() if oldest else None,
            "newest_log_date": newest.replace(tzinfo=UTC).isoformat() if newest else None,
        }

    def verify_chain(self) -> dict[str, Any]:
        """Check that no stored entry was modified, inserted, or removed mid-chain.

        Entries purged by :meth:`cleanup_old_logs` are expected: verification
        anchors on the oldest remaining entry's ``prev_hash``.
        """
        with session_scope() as db:
            head = db.get(AuditChainHeadRow, _CHAIN_HEAD_ID)
            expected_prev = None
            checked = 0
            for row in db.scalars(select(AuditLogRow).order_by(AuditLogRow.seq)).yield_per(500):
                if expected_prev is not None and row.prev_hash != expected_prev:
                    return {
                        "valid": False,
                        "entries_checked": checked,
                        "invalid_entry_id": row.id,
                        "reason": "entry does not follow the previous entry (inserted or removed rows)",
                    }
                if _chain_hash(row.prev_hash, row.data) != row.entry_hash:
                    return {
                        "valid": False,
                        "entries_checked": checked,
                        "invalid_entry_id": row.id,
                        "reason": "entry content does not match its hash (modified)",
                    }
                expected_prev = row.entry_hash
                checked += 1
            head_hash = head.last_hash if head else GENESIS_HASH
            if (expected_prev or GENESIS_HASH) != head_hash:
                return {
                    "valid": False,
                    "entries_checked": checked,
                    "invalid_entry_id": None,
                    "reason": "newest entries are missing (chain head does not match)",
                }
        return {"valid": True, "entries_checked": checked, "invalid_entry_id": None, "reason": None}

    def generate_compliance_report(self, start_date: datetime, end_date: datetime) -> ComplianceReport:
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
            limit=10000,  # High limit for reporting
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
        top_violations = sorted(violations_by_type.items(), key=lambda x: x[1], reverse=True)[:10]

        top_violation_patterns = [{"pattern": pattern, "count": count} for pattern, count in top_violations]

        report = ComplianceReport(
            period_start=start_date,
            period_end=end_date,
            total_checks=total_checks,
            total_violations=total_violations,
            violation_rate=round(violation_rate, 2),
            violations_by_type=violations_by_type,
            violations_by_severity=violations_by_severity,
            policy_level_distribution=policy_level_distribution,
            top_violation_patterns=top_violation_patterns,
        )

        logger.info(
            f"Compliance report generated: {total_checks} checks, {total_violations} violations",
            extra={
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "violation_rate": violation_rate,
            },
        )

        return report

    def cleanup_old_logs(self, retention_days: int = 90) -> int:
        """
        Delete audit entries older than the retention period.

        Args:
            retention_days: Number of days to retain logs

        Returns:
            Number of entries deleted
        """
        cutoff = _to_naive_utc(datetime.now(UTC) - timedelta(days=retention_days))
        with _append_lock, session_scope() as db:
            deleted = db.execute(delete(AuditLogRow).where(AuditLogRow.timestamp < cutoff)).rowcount or 0
        logger.info(f"Audit log cleanup complete: {deleted} entries deleted")
        return deleted
