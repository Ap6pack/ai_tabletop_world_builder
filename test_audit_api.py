#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Test script for audit API endpoints.

Requires a running API server at localhost:8000. Automatically skipped
during `pytest` when the server is not reachable.
"""
import requests
import json
import pytest
from datetime import datetime, timedelta

API_BASE = "http://127.0.0.1:8000"


def _api_reachable() -> bool:
    try:
        requests.get(f"{API_BASE}/health", timeout=2)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


@pytest.mark.skipif(not _api_reachable(), reason="API server not running")
def test_audit_endpoints():
    """Test all audit API endpoints."""
    print("=" * 80)
    print("AUDIT API ENDPOINTS TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    # Test 1: Create some audit logs first (via test_audit_log.py)
    print("Test 1: Creating test audit logs...")
    import subprocess
    result = subprocess.run(["python", "test_audit_log.py"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ PASS - Test logs created successfully")
        passed += 1
    else:
        print(f"❌ FAIL - Failed to create test logs: {result.stderr}")
        failed += 1
    print()

    # Test 2: Get audit stats
    print("Test 2: GET /audit/stats")
    try:
        response = requests.get(f"{API_BASE}/audit/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ PASS - Audit stats retrieved")
            print(f"   Total log files: {stats['total_log_files']}")
            print(f"   Disk usage: {stats['disk_usage_mb']} MB")
            print(f"   Date range: {stats.get('oldest_log_date', 'N/A')} to {stats.get('newest_log_date', 'N/A')}")
            passed += 1
        else:
            print(f"❌ FAIL - Status code: {response.status_code}")
            print(f"   Error: {response.text}")
            failed += 1
    except Exception as e:
        print(f"❌ FAIL - Exception: {str(e)}")
        failed += 1
    print()

    # Test 3: Get audit logs (no filters)
    print("Test 3: GET /audit/logs (no filters)")
    try:
        response = requests.get(f"{API_BASE}/audit/logs?limit=10", timeout=5)
        if response.status_code == 200:
            logs = response.json()
            print(f"✅ PASS - Retrieved {len(logs)} logs")
            if logs:
                first_log = logs[0]
                print(f"   First log: {first_log['event_type']} - {first_log['severity']}")
            passed += 1
        else:
            print(f"❌ FAIL - Status code: {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"❌ FAIL - Exception: {str(e)}")
        failed += 1
    print()

    # Test 4: Get audit logs (filtered by event_type)
    print("Test 4: GET /audit/logs (filter by event_type=violation)")
    try:
        response = requests.get(
            f"{API_BASE}/audit/logs",
            params={"event_type": "violation", "limit": 10},
            timeout=5
        )
        if response.status_code == 200:
            logs = response.json()
            print(f"✅ PASS - Retrieved {len(logs)} violation logs")
            passed += 1
        else:
            print(f"❌ FAIL - Status code: {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"❌ FAIL - Exception: {str(e)}")
        failed += 1
    print()

    # Test 5: Get audit logs (filtered by severity)
    print("Test 5: GET /audit/logs (filter by severity=critical)")
    try:
        response = requests.get(
            f"{API_BASE}/audit/logs",
            params={"severity": "critical", "limit": 10},
            timeout=5
        )
        if response.status_code == 200:
            logs = response.json()
            print(f"✅ PASS - Retrieved {len(logs)} critical logs")
            passed += 1
        else:
            print(f"❌ FAIL - Status code: {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"❌ FAIL - Exception: {str(e)}")
        failed += 1
    print()

    # Test 6: Generate compliance report
    print("Test 6: GET /audit/compliance-report")
    try:
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        response = requests.get(
            f"{API_BASE}/audit/compliance-report",
            params={
                "start_date": yesterday.date().isoformat(),
                "end_date": today.date().isoformat()
            },
            timeout=5
        )
        if response.status_code == 200:
            report = response.json()
            print(f"✅ PASS - Compliance report generated")
            print(f"   Total checks: {report.get('total_checks', 0)}")
            print(f"   Total violations: {report.get('total_violations', 0)}")
            print(f"   Violation rate: {report.get('violation_rate', 0)}%")
            passed += 1
        else:
            print(f"❌ FAIL - Status code: {response.status_code}")
            print(f"   Error: {response.text}")
            failed += 1
    except Exception as e:
        print(f"❌ FAIL - Exception: {str(e)}")
        failed += 1
    print()

    # Test 7: Test invalid date format
    print("Test 7: GET /audit/compliance-report (invalid date)")
    try:
        response = requests.get(
            f"{API_BASE}/audit/compliance-report",
            params={
                "start_date": "invalid-date",
                "end_date": "2025-11-04"
            },
            timeout=5
        )
        if response.status_code == 400:
            print(f"✅ PASS - Correctly rejected invalid date (400)")
            passed += 1
        else:
            print(f"❌ FAIL - Expected 400, got {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"❌ FAIL - Exception: {str(e)}")
        failed += 1
    print()

    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 80)

    assert failed == 0, f"{failed} test(s) failed"


if __name__ == "__main__":
    import sys
    try:
        test_audit_endpoints()
        sys.exit(0)
    except (AssertionError, Exception):
        sys.exit(1)
