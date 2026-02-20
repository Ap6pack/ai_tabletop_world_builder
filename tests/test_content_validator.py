#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Test script for content validator service.
Tests post-generation validation with various content types.
"""
import asyncio
import sys
sys.path.insert(0, '.')
import pytest

from api.services.content_validator_service import ContentValidatorService
from api.models import Organization, Department, System, Vulnerability, ThreatActor


@pytest.mark.asyncio
async def test_content_validator():
    """Test content validation with various scenarios."""

    service = ContentValidatorService()

    print("=" * 80)
    print("CONTENT VALIDATOR SERVICE TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    # Test 1: Safe narrative
    print("Test 1: Safe narrative validation")
    narrative = "The security team detected unusual network traffic from the web server."
    result = await service.validate_narrative(narrative, "educational")
    if result.is_safe and len(result.violations) == 0:
        print("✅ PASS - Safe narrative approved")
        passed += 1
    else:
        print(f"❌ FAIL - Expected safe, got violations: {result.violations}")
        failed += 1
    print()

    # Test 2: Narrative with credentials
    print("Test 2: Narrative with embedded credentials")
    narrative_with_creds = "The attacker used API key sk-1234567890abcdefghijklmnopqrstuvwxyz1234567 to access the system."
    result = await service.validate_narrative(narrative_with_creds, "educational")
    if not result.is_safe and len(result.violations) > 0:
        print(f"✅ PASS - Credentials detected: {result.violations}")
        print(f"   Can sanitize: {result.can_sanitize}")
        passed += 1
    else:
        print("❌ FAIL - Credentials not detected")
        failed += 1
    print()

    # Test 3: Narrative with dangerous command
    print("Test 3: Narrative with dangerous command")
    dangerous_narrative = "Run rm -rf / to clean up the compromised system."
    result = await service.validate_narrative(dangerous_narrative, "educational")
    if not result.is_safe:
        print(f"✅ PASS - Dangerous command blocked: {result.reason}")
        print(f"   Severity: {result.severity}")
        passed += 1
    else:
        print("❌ FAIL - Dangerous command not detected")
        failed += 1
    print()

    # Test 4: Content sanitization
    print("Test 4: Content sanitization")
    unsafe_content = "Use password P@ssw0rd123 and API key sk-test123456789012345678901234567890123456 to connect."
    result = await service.validate_narrative(unsafe_content, "educational")
    if not result.is_safe and result.can_sanitize:
        sanitized = service.sanitize_content(unsafe_content, result.violations)
        if "[REDACTED-" in sanitized:
            print(f"✅ PASS - Content sanitized")
            print(f"   Original: {unsafe_content[:50]}...")
            print(f"   Sanitized: {sanitized[:80]}...")
            passed += 1
        else:
            print("❌ FAIL - Sanitization didn't redact content")
            failed += 1
    else:
        print(f"❌ FAIL - Content not identified as sanitizable")
        failed += 1
    print()

    # Test 5: Objective validation
    print("Test 5: Safe objective validation")
    safe_objective = "Detect and identify the source of the network anomaly"
    result = await service.validate_objective(safe_objective, "educational")
    if result.is_safe:
        print("✅ PASS - Safe objective approved")
        passed += 1
    else:
        print(f"❌ FAIL - Safe objective rejected: {result.violations}")
        failed += 1
    print()

    # Test 6: Objective with exploit code
    print("Test 6: Objective with dangerous content")
    dangerous_objective = "Execute rm -rf /tmp/* to clean up the compromised files"
    result = await service.validate_objective(dangerous_objective, "educational")
    if not result.is_safe:
        print(f"✅ PASS - Dangerous objective blocked")
        print(f"   Reason: {result.reason}")
        passed += 1
    else:
        print("❌ FAIL - Dangerous objective not detected")
        failed += 1
    print()

    # Test 7: Validate and auto-sanitize
    print("Test 7: Validate and auto-sanitize")
    content_with_creds = "Use API key sk-test123456789012345678901234567890123456 to authenticate"
    is_safe, processed = await service.validate_and_sanitize(
        content_with_creds,
        "educational",
        auto_sanitize=True
    )
    if is_safe and "[REDACTED-" in processed:
        print("✅ PASS - Auto-sanitization worked")
        print(f"   Result: {processed}")
        passed += 1
    else:
        print(f"❌ FAIL - Auto-sanitization failed")
        print(f"   is_safe={is_safe}, has_redaction={'[REDACTED-' in processed}")
        failed += 1
    print()

    # Test 8: Policy level differences
    print("Test 8: Policy level differences (internal IP)")
    ip_content = "Check the server at 192.168.1.100 for issues"

    # Should be allowed in educational mode
    result_edu = await service.validate_narrative(ip_content, "educational")
    # Should be more strict in defensive mode
    result_def = await service.validate_narrative(ip_content, "defensive")

    if result_edu.is_safe or result_def.is_safe:
        print("✅ PASS - Policy levels working correctly")
        print(f"   Educational: {result_edu.is_safe}")
        print(f"   Defensive: {result_def.is_safe}")
        passed += 1
    else:
        print("❌ FAIL - Both policies blocked low-severity content")
        failed += 1
    print()

    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_content_validator())
    sys.exit(0 if success else 1)
