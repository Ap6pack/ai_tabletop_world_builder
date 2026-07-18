#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Test script for audit log service.
Tests comprehensive logging of policy checks, violations, and compliance reporting.
"""

import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, ".")

from api.services.audit_log_service import AuditLogService


def test_audit_log():
    """Test audit logging with various scenarios."""

    # Use temporary directory for tests
    test_log_dir = "./data/audit_logs_test"
    service = AuditLogService(log_dir=test_log_dir)

    print("=" * 80)
    print("AUDIT LOG SERVICE TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    try:
        # Test 1: Log policy check (allowed)
        print("Test 1: Log policy check (allowed)")
        log_entry = service.log_policy_check(
            content="Check the SIEM logs for suspicious activity",
            policy_level="educational",
            result="allowed",
            violations=[],
            session_id="sess-001",
        )
        if log_entry.event_type == "policy_check" and log_entry.result == "allowed":
            print("✅ PASS - Policy check logged")
            print(f"   Log ID: {log_entry.id}")
            print(f"   Content hash: {log_entry.content_hash[:16]}...")
            passed += 1
        else:
            print("❌ FAIL - Policy check log incorrect")
            failed += 1
        print()

        # Test 2: Log policy check (blocked)
        print("Test 2: Log policy check (blocked)")
        log_entry = service.log_policy_check(
            content="Use password P@ssw0rd123 to access the system",
            policy_level="educational",
            result="blocked",
            violations=["credentials: password"],
            session_id="sess-001",
        )
        if log_entry.event_type == "policy_check" and log_entry.result == "blocked":
            print("✅ PASS - Blocked action logged")
            print(f"   Violations: {log_entry.violations}")
            passed += 1
        else:
            print("❌ FAIL - Blocked action log incorrect")
            failed += 1
        print()

        # Test 3: Log violation
        print("Test 3: Log violation")
        log_entry = service.log_violation(
            content="Execute rm -rf / to clean up",
            violation_type="exploit_code",
            severity="critical",
            policy_level="educational",
            action_taken="Action blocked and user notified",
            session_id="sess-001",
            user_id="user-123",
        )
        if log_entry.event_type == "violation" and log_entry.severity == "critical":
            print("✅ PASS - Violation logged")
            print(f"   Severity: {log_entry.severity}")
            print(f"   Action taken: {log_entry.action_taken}")
            passed += 1
        else:
            print("❌ FAIL - Violation log incorrect")
            failed += 1
        print()

        # Test 4: Log filter event
        print("Test 4: Log filter event")
        log_entry = service.log_filter(
            content="API key sk-1234567890 found in text",
            filter_type="credential_detection",
            matched_patterns=["api_key", "openai_key"],
            policy_level="educational",
            result="sanitized",
            session_id="sess-001",
        )
        if log_entry.event_type == "filter" and log_entry.result == "sanitized":
            print("✅ PASS - Filter event logged")
            print(f"   Matched patterns: {log_entry.violations}")
            passed += 1
        else:
            print("❌ FAIL - Filter event log incorrect")
            failed += 1
        print()

        # Test 5: Log sanitization
        print("Test 5: Log sanitization")
        original = "Password is P@ssw0rd123 and API key is sk-test"
        sanitized = "Password is [REDACTED] and API key is [REDACTED]"
        log_entry = service.log_sanitization(
            content=original,
            sanitized_content=sanitized,
            violations=["password", "api_key"],
            policy_level="educational",
            session_id="sess-002",
        )
        if log_entry.event_type == "sanitization":
            print("✅ PASS - Sanitization logged")
            print(f"   Violations sanitized: {len(log_entry.violations)}")
            passed += 1
        else:
            print("❌ FAIL - Sanitization log incorrect")
            failed += 1
        print()

        # Test 6: Retrieve logs
        print("Test 6: Retrieve logs with filters")
        logs = service.get_logs(session_id="sess-001", limit=10)
        if len(logs) >= 3:  # Should have at least 3 logs from sess-001
            print(f"✅ PASS - Retrieved {len(logs)} logs")
            for i, log in enumerate(logs[:3], 1):
                print(f"   Log {i}: {log.event_type} - {log.result}")
            passed += 1
        else:
            print(f"❌ FAIL - Expected at least 3 logs, got {len(logs)}")
            failed += 1
        print()

        # Test 7: Retrieve logs by event type
        print("Test 7: Filter logs by event type")
        violation_logs = service.get_logs(event_type="violation", limit=10)
        if len(violation_logs) >= 1:
            print(f"✅ PASS - Retrieved {len(violation_logs)} violation logs")
            passed += 1
        else:
            print("❌ FAIL - No violation logs found")
            failed += 1
        print()

        # Test 8: Retrieve logs by severity
        print("Test 8: Filter logs by severity")
        critical_logs = service.get_logs(severity="critical", limit=10)
        if len(critical_logs) >= 1:
            print(f"✅ PASS - Retrieved {len(critical_logs)} critical logs")
            passed += 1
        else:
            print("❌ FAIL - No critical logs found")
            failed += 1
        print()

        # Test 9: Generate compliance report
        print("Test 9: Generate compliance report")
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=1)
        report = service.generate_compliance_report(start_date, end_date)

        if report.total_checks > 0:
            print("✅ PASS - Compliance report generated")
            print(f"   Total checks: {report.total_checks}")
            print(f"   Total violations: {report.total_violations}")
            print(f"   Violation rate: {report.violation_rate}%")
            print(f"   Policy levels: {list(report.policy_level_distribution.keys())}")
            if report.top_violation_patterns:
                print(
                    f"   Top violation: {report.top_violation_patterns[0]['pattern']} ({report.top_violation_patterns[0]['count']} times)"
                )
            passed += 1
        else:
            print("❌ FAIL - Report has no data")
            failed += 1
        print()

        # Test 10: Content hashing (privacy)
        print("Test 10: Verify content hashing for privacy")
        # Two logs with same content should have same hash
        log1 = service.log_policy_check(
            content="Test content for hashing", policy_level="educational", result="allowed"
        )
        log2 = service.log_policy_check(
            content="Test content for hashing", policy_level="educational", result="allowed"
        )
        if log1.content_hash == log2.content_hash:
            print("✅ PASS - Content hashing consistent")
            print(f"   Hash: {log1.content_hash[:32]}...")
            passed += 1
        else:
            print("❌ FAIL - Content hashing inconsistent")
            failed += 1
        print()

        # Test 11: Log file creation and format
        print("Test 11: Verify log file creation and format")
        log_file = service.current_log_file
        if log_file.exists():
            with open(log_file) as f:
                lines = f.readlines()
                if len(lines) > 0:
                    # Try to parse first line as JSON
                    import json

                    try:
                        log_data = json.loads(lines[0])
                        if "id" in log_data and "timestamp" in log_data:
                            print("✅ PASS - Log file format valid (JSONL)")
                            print(f"   Log file: {log_file.name}")
                            print(f"   Entries: {len(lines)}")
                            passed += 1
                        else:
                            print("❌ FAIL - Log entry missing required fields")
                            failed += 1
                    except json.JSONDecodeError:
                        print("❌ FAIL - Invalid JSON in log file")
                        failed += 1
                else:
                    print("❌ FAIL - Log file is empty")
                    failed += 1
        else:
            print("❌ FAIL - Log file not created")
            failed += 1
        print()

        # Test 12: Log retention/cleanup
        print("Test 12: Test log cleanup (dry run)")
        # Don't actually delete anything in test, just verify the method works
        deleted = service.cleanup_old_logs(retention_days=365)  # High number won't delete test logs
        print("✅ PASS - Cleanup method executed")
        print(f"   Files deleted: {deleted}")
        passed += 1
        print()

    finally:
        # Cleanup test directory
        print("-" * 80)
        print("Cleaning up test directory...")
        if Path(test_log_dir).exists():
            shutil.rmtree(test_log_dir)
            print(f"✓ Removed {test_log_dir}")
        print()

    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 80)

    assert failed == 0, f"{failed} test(s) failed"


if __name__ == "__main__":
    try:
        test_audit_log()
        sys.exit(0)
    except (AssertionError, Exception):
        sys.exit(1)
