#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the database-backed, hash-chained audit log."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from api.db import AuditLogRow, session_scope
from api.services.audit_log_service import GENESIS_HASH, AuditLogService


def _populate(service: AuditLogService, count: int = 3) -> None:
    for i in range(count):
        service.log_policy_check(f"content {i}", "educational", "allowed", session_id=f"s{i}")


def test_entries_are_chained():
    service = AuditLogService()
    _populate(service)
    with session_scope() as db:
        rows = db.scalars(select(AuditLogRow).order_by(AuditLogRow.seq)).all()
        assert rows[0].prev_hash == GENESIS_HASH
        for prev, row in zip(rows, rows[1:], strict=False):
            assert row.prev_hash == prev.entry_hash
    assert service.verify_chain()["valid"] is True


def test_shared_between_service_instances():
    """Two instances (e.g. two API workers) write to and read from one log."""
    a, b = AuditLogService(), AuditLogService()
    a.log_policy_check("from a", "educational", "allowed")
    b.log_violation("from b", "malware", "high", "educational", "blocked")
    assert len(a.get_logs()) == 2
    assert b.verify_chain()["entries_checked"] == 2


def test_modified_entry_is_detected():
    service = AuditLogService()
    _populate(service)
    with session_scope() as db:
        row = db.scalars(select(AuditLogRow).order_by(AuditLogRow.seq).offset(1)).first()
        tampered = dict(row.data, result="blocked")
        db.execute(update(AuditLogRow).where(AuditLogRow.seq == row.seq).values(data=tampered))
        target = row.id
    result = service.verify_chain()
    assert result["valid"] is False
    assert result["invalid_entry_id"] == target
    assert "modified" in result["reason"]


def test_removed_middle_entry_is_detected():
    service = AuditLogService()
    _populate(service)
    with session_scope() as db:
        row = db.scalars(select(AuditLogRow).order_by(AuditLogRow.seq).offset(1)).first()
        db.delete(row)
    assert service.verify_chain()["valid"] is False


def test_removed_newest_entry_is_detected():
    service = AuditLogService()
    _populate(service)
    with session_scope() as db:
        row = db.scalars(select(AuditLogRow).order_by(AuditLogRow.seq.desc())).first()
        db.delete(row)
    result = service.verify_chain()
    assert result["valid"] is False
    assert "newest" in result["reason"]


def test_retention_cleanup_keeps_chain_valid():
    service = AuditLogService()
    _populate(service, 4)
    old = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=400)
    with session_scope() as db:
        oldest = db.scalars(select(AuditLogRow).order_by(AuditLogRow.seq).limit(2)).all()
        for row in oldest:
            row.timestamp = old
    assert service.cleanup_old_logs(retention_days=90) == 2
    assert len(service.get_logs()) == 2
    assert service.verify_chain() == {"valid": True, "entries_checked": 2, "invalid_entry_id": None, "reason": None}


def test_date_filters_accept_naive_and_aware():
    service = AuditLogService()
    _populate(service, 2)
    now = datetime.now(UTC)
    assert len(service.get_logs(start_date=now - timedelta(minutes=1))) == 2
    assert len(service.get_logs(start_date=(now - timedelta(minutes=1)).replace(tzinfo=None))) == 2
    assert service.get_logs(end_date=now - timedelta(days=1)) == []


def test_stats():
    service = AuditLogService()
    assert service.get_stats() == {"total_entries": 0, "oldest_log_date": None, "newest_log_date": None}
    _populate(service, 2)
    assert service.get_stats()["total_entries"] == 2
