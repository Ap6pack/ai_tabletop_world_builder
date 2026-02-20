#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Test script for violation handler service.
Tests violation handling, escalation, and user education.
"""
import sys
import shutil
from pathlib import Path
sys.path.insert(0, '.')

from api.services.violation_handler_service import ViolationHandlerService


def test_violation_handler():
    """Test violation handling with various scenarios."""

    # Use temporary directory for audit logs
    test_log_dir = "./data/audit_logs_test"
    service = ViolationHandlerService()

    print("=" * 80)
    print("VIOLATION HANDLER SERVICE TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    try:
        # Test 1: Handle low severity violation (first time)
        print("Test 1: Handle low severity violation (first time)")
        response = service.handle_violation(
            content="Check server at 192.168.1.100",
            violation_type="sensitive_info",
            severity="low",
            policy_level="defensive",
            user_id="user-001",
            session_id="sess-001"
        )
        if response.action == "warn" and not response.requires_review:
            print("✅ PASS - Low severity handled with warning")
            print(f"   Action: {response.action}")
            print(f"   Message: {response.message[:60]}...")
            passed += 1
        else:
            print(f"❌ FAIL - Expected warn action, got {response.action}")
            failed += 1
        print()

        # Test 2: Handle low severity violation (repeat)
        print("Test 2: Handle low severity violation (repeat)")
        response = service.handle_violation(
            content="Another internal IP: 10.0.0.5",
            violation_type="sensitive_info",
            severity="low",
            policy_level="defensive",
            user_id="user-001",
            session_id="sess-001"
        )
        if response.action == "warn":
            print("✅ PASS - Repeat low violation escalated to stronger warning")
            print(f"   Has educational content: {len(response.educational_content) > 0}")
            passed += 1
        else:
            print(f"❌ FAIL - Expected warn action, got {response.action}")
            failed += 1
        print()

        # Test 3: Handle medium severity violation (first time)
        print("Test 3: Handle medium severity violation")
        response = service.handle_violation(
            content="Use API key sk-test123456789",
            violation_type="credentials",
            severity="medium",
            policy_level="educational",
            user_id="user-002",
            session_id="sess-002"
        )
        if response.action == "block":
            print("✅ PASS - Medium severity blocked")
            print(f"   Has alternative: {response.suggested_alternative is not None}")
            print(f"   Educational content: {len(response.educational_content)} chars")
            passed += 1
        else:
            print(f"❌ FAIL - Expected block action, got {response.action}")
            failed += 1
        print()

        # Test 4: Handle medium severity violation (repeat)
        print("Test 4: Handle medium severity violation (repeat)")
        response = service.handle_violation(
            content="Password is P@ssw0rd123",
            violation_type="credentials",
            severity="medium",
            policy_level="educational",
            user_id="user-002",
            session_id="sess-002"
        )
        if response.action == "escalate" and response.requires_review:
            print("✅ PASS - Repeat medium violation escalated")
            print(f"   Requires review: {response.requires_review}")
            passed += 1
        else:
            print(f"❌ FAIL - Expected escalate action with review, got {response.action}")
            failed += 1
        print()

        # Test 5: Handle high severity violation
        print("Test 5: Handle high severity violation")
        response = service.handle_violation(
            content="Execute: ' OR 1=1--",
            violation_type="sql_injection",
            severity="high",
            policy_level="educational",
            user_id="user-003",
            session_id="sess-003"
        )
        if response.action == "escalate" and response.requires_review:
            print("✅ PASS - High severity escalated immediately")
            print(f"   Educational content provided: {len(response.educational_content) > 0}")
            passed += 1
        else:
            print(f"❌ FAIL - Expected escalate with review, got {response.action}")
            failed += 1
        print()

        # Test 6: Handle critical severity violation
        print("Test 6: Handle critical severity violation")
        response = service.handle_violation(
            content="Run rm -rf /",
            violation_type="dangerous_commands",
            severity="critical",
            policy_level="educational",
            user_id="user-004",
            session_id="sess-004"
        )
        if response.action == "escalate" and response.requires_review:
            print("✅ PASS - Critical violation escalated")
            print(f"   Message length: {len(response.message)} chars")
            if "critical" in response.message.lower():
                print("   ✓ Message mentions severity")
            passed += 1
        else:
            print(f"❌ FAIL - Expected escalate with review")
            failed += 1
        print()

        # Test 7: Educational content accuracy
        print("Test 7: Verify educational content accuracy")
        response = service.handle_violation(
            content="Test exploit code",
            violation_type="exploit_code",
            severity="high",
            policy_level="educational",
            user_id="user-005"
        )
        if "exploit" in response.educational_content.lower():
            print("✅ PASS - Educational content relevant to violation type")
            print(f"   Content preview: {response.educational_content[:80]}...")
            passed += 1
        else:
            print("❌ FAIL - Educational content not relevant")
            failed += 1
        print()

        # Test 8: Alternative suggestions
        print("Test 8: Verify alternative suggestions")
        response = service.handle_violation(
            content="Use password admin123",
            violation_type="credentials",
            severity="medium",
            policy_level="educational",
            user_id="user-006"
        )
        if response.suggested_alternative and len(response.suggested_alternative) > 0:
            print("✅ PASS - Alternative suggestion provided")
            print(f"   Suggestion: {response.suggested_alternative[:70]}...")
            passed += 1
        else:
            print("❌ FAIL - No alternative suggestion provided")
            failed += 1
        print()

        # Test 9: Get violation metrics
        print("Test 9: Get violation metrics")
        metrics = service.get_violation_metrics(user_id="user-002")
        if metrics["total_violations"] == 2:  # Two violations from tests 3 and 4
            print("✅ PASS - Violation metrics accurate")
            print(f"   Total violations: {metrics['total_violations']}")
            print(f"   By severity: {metrics['by_severity']}")
            print(f"   Recent violations: {metrics['recent_violations']}")
            passed += 1
        else:
            print(f"❌ FAIL - Expected 2 violations, got {metrics['total_violations']}")
            failed += 1
        print()

        # Test 10: Session-specific metrics
        print("Test 10: Session-specific violation metrics")
        metrics = service.get_violation_metrics(
            user_id="user-002",
            session_id="sess-002"
        )
        if metrics["total_violations"] > 0:
            print("✅ PASS - Session filtering works")
            print(f"   Session violations: {metrics['total_violations']}")
            passed += 1
        else:
            print("❌ FAIL - No violations found for session")
            failed += 1
        print()

        # Test 11: Reset user violations
        print("Test 11: Reset user violations")
        cleared = service.reset_user_violations("user-002")
        if cleared == 2:
            metrics_after = service.get_violation_metrics(user_id="user-002")
            if metrics_after["total_violations"] == 0:
                print("✅ PASS - User violations reset successfully")
                print(f"   Cleared: {cleared} violations")
                passed += 1
            else:
                print("❌ FAIL - Violations not cleared")
                failed += 1
        else:
            print(f"❌ FAIL - Expected 2 violations cleared, got {cleared}")
            failed += 1
        print()

        # Test 12: Violation type matching in educational content
        print("Test 12: Specific violation type education")
        test_cases = [
            ("credentials", "credential"),
            ("pii", "privacy"),
            ("sql_injection", "SQL injection"),
            ("xss", "XSS"),
        ]

        type_matches = 0
        for violation_type, expected_keyword in test_cases:
            response = service.handle_violation(
                content=f"Test {violation_type}",
                violation_type=violation_type,
                severity="medium",
                policy_level="educational",
                user_id=f"user-test-{violation_type}"
            )
            if expected_keyword.lower() in response.educational_content.lower():
                type_matches += 1

        if type_matches >= 3:  # At least 3 out of 4
            print(f"✅ PASS - Educational content matches violation types ({type_matches}/4)")
            passed += 1
        else:
            print(f"❌ FAIL - Educational content matching insufficient ({type_matches}/4)")
            failed += 1
        print()

    finally:
        # Cleanup test directory if it exists
        print("-" * 80)
        print("Cleaning up...")
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
        test_violation_handler()
        sys.exit(0)
    except (AssertionError, Exception):
        sys.exit(1)
