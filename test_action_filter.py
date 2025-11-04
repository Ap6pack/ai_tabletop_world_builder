#!/usr/bin/env python3
"""
Test script for action filter service.
Tests pre-action content checking with various policy levels and action types.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from api.services.action_filter_service import ActionFilterService


async def test_action_filter():
    """Test action filtering with various scenarios."""

    service = ActionFilterService()

    test_cases = [
        {
            "name": "Safe action - investigate logs",
            "action": "I want to investigate the SIEM logs for suspicious activity",
            "policy": "defensive",
            "should_allow": True
        },
        {
            "name": "Contains password - educational mode",
            "action": "Set the admin password to P@ssw0rd123 for testing",
            "policy": "educational",
            "should_allow": False
        },
        {
            "name": "Contains API key",
            "action": "Use API key sk-1234567890abcdefghijklmnopqrstuvwxyz1234567 to access the service",
            "policy": "educational",
            "should_allow": False
        },
        {
            "name": "Dangerous command - rm -rf",
            "action": "Run rm -rf / to clean up the system",
            "policy": "educational",
            "should_allow": False
        },
        {
            "name": "SQL injection pattern",
            "action": "Try input: ' OR 1=1-- to test for SQL injection",
            "policy": "educational",
            "should_allow": False
        },
        {
            "name": "Internal IP address",
            "action": "Check the internal server at 192.168.1.100 for issues",
            "policy": "defensive",
            "should_allow": True  # Internal IPs are low severity
        },
        {
            "name": "Safe educational action",
            "action": "Explain how a ransomware attack typically progresses through a network",
            "policy": "educational",
            "should_allow": True
        },
        {
            "name": "Advanced technique in advanced mode",
            "action": "Demonstrate a privilege escalation technique using sudo misconfiguration",
            "policy": "advanced",
            "should_allow": True  # Would need LLM check
        }
    ]

    print("=" * 80)
    print("ACTION FILTER SERVICE TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"Policy: {test['policy']}")
        print(f"Action: {test['action'][:60]}...")
        print()

        # Test with quick check only (fast)
        result = await service.check_action(
            action=test['action'],
            policy_level=test['policy'],
            enable_quick_check=True,
            enable_llm_check=False  # Disable LLM for testing
        )

        print(f"Result: {'ALLOWED' if result.is_allowed else 'BLOCKED'}")
        if not result.is_allowed:
            print(f"Reason: {result.reason}")
            if result.violations:
                print(f"Violations: {', '.join(result.violations)}")
            if result.suggested_alternative:
                print(f"Suggestion: {result.suggested_alternative}")
            print(f"Severity: {result.severity}")
            print(f"Pattern Matches: {len(result.matched_patterns)}")

        # Check if result matches expectation
        if result.is_allowed == test['should_allow']:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL (expected " + ("ALLOWED" if test['should_allow'] else "BLOCKED") + ")")
            failed += 1

        print("-" * 80)
        print()

    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_action_filter())
    sys.exit(0 if success else 1)
