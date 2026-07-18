#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Test suite for Resource Manager Service.

Tests resource management, action costs, and cooldowns.
"""

import sys
from datetime import UTC, datetime, timedelta

from api.models import ActionCost, ResourcePool
from api.services.resource_manager import ResourceManager


def test_initialize_resource_pool():
    """Test 1: Initialize resource pool."""
    print("\n=== Test 1: Initialize Resource Pool ===")
    manager = ResourceManager()

    # Intermediate difficulty
    pool = manager.initialize_resource_pool("intermediate")

    assert pool.action_points == 10
    assert pool.max_action_points == 10
    assert pool.budget_remaining == 100000.0
    assert pool.staff_available == 5

    print("✅ Resource pool initialized (intermediate)")
    print(f"   Action points: {pool.action_points}/{pool.max_action_points}")
    print(f"   Budget: ${pool.budget_remaining:,.0f}")
    print(f"   Staff: {pool.staff_available}")
    print(f"   Regen rate: {pool.points_per_minute} pts/min")


def test_difficulty_scaling():
    """Test 2: Resource scaling by difficulty."""
    print("\n=== Test 2: Difficulty Scaling ===")
    manager = ResourceManager()

    difficulties = ["beginner", "intermediate", "advanced", "expert"]
    for diff in difficulties:
        pool = manager.initialize_resource_pool(diff)
        print(
            f"   {diff.capitalize():12} - AP: {pool.action_points}, Budget: ${pool.budget_remaining:,.0f}, Staff: {pool.staff_available}"
        )

    beginner_pool = manager.initialize_resource_pool("beginner")
    expert_pool = manager.initialize_resource_pool("expert")

    assert beginner_pool.action_points > expert_pool.action_points
    assert beginner_pool.budget_remaining > expert_pool.budget_remaining

    print("✅ Difficulty scaling works correctly")


def test_get_action_cost():
    """Test 3: Get action cost by description."""
    print("\n=== Test 3: Get Action Cost ===")
    manager = ResourceManager()

    # Investigation action
    cost1 = manager.get_action_cost("investigate the logs")
    print(f"   'investigate the logs' - {cost1.points} pts, ${cost1.budget:,.0f}, {cost1.requires_staff} staff")
    assert cost1.points == 1

    # Containment action
    cost2 = manager.get_action_cost("isolate the compromised server")
    print(
        f"   'isolate the compromised server' - {cost2.points} pts, ${cost2.budget:,.0f}, {cost2.requires_staff} staff"
    )
    assert cost2.points == 3

    # Mitigation action
    cost3 = manager.get_action_cost("patch the vulnerability")
    print(f"   'patch the vulnerability' - {cost3.points} pts, ${cost3.budget:,.0f}, {cost3.requires_staff} staff")
    assert cost3.points == 4
    assert cost3.budget == 5000.0

    print("✅ Action cost detection works correctly")


def test_can_afford_action():
    """Test 4: Check if action is affordable."""
    print("\n=== Test 4: Can Afford Action ===")
    manager = ResourceManager()
    pool = manager.initialize_resource_pool("intermediate")

    # Cheap action (should be affordable)
    cheap_cost = ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1)
    can_afford, reason = manager.can_afford_action(pool, cheap_cost)
    print(f"   Cheap action (1 pt): {can_afford} - {reason}")
    assert can_afford is True

    # Expensive action (too many points)
    expensive_cost = ActionCost(points=20, budget=0, cooldown_seconds=0, requires_staff=1)
    can_afford, reason = manager.can_afford_action(pool, expensive_cost)
    print(f"   Expensive action (20 pts): {can_afford} - {reason}")
    assert can_afford is False
    assert "action points" in reason.lower()

    # High budget action
    budget_cost = ActionCost(points=1, budget=200000, cooldown_seconds=0, requires_staff=1)
    can_afford, reason = manager.can_afford_action(pool, budget_cost)
    print(f"   High budget ($200K): {can_afford} - {reason}")
    assert can_afford is False
    assert "budget" in reason.lower()

    # Too many staff
    staff_cost = ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=10)
    can_afford, reason = manager.can_afford_action(pool, staff_cost)
    print(f"   High staff (10): {can_afford} - {reason}")
    assert can_afford is False
    assert "staff" in reason.lower()

    print("✅ Affordability checking works correctly")


def test_spend_resources():
    """Test 5: Spend resources."""
    print("\n=== Test 5: Spend Resources ===")
    manager = ResourceManager()
    pool = manager.initialize_resource_pool("intermediate")

    print(f"   Initial: {pool.action_points} pts, ${pool.budget_remaining:,.0f}")

    # Spend resources
    cost = ActionCost(points=3, budget=5000, cooldown_seconds=0, requires_staff=2)
    pool = manager.spend_resources(pool, cost)

    print(f"   After spending: {pool.action_points} pts, ${pool.budget_remaining:,.0f}")

    assert pool.action_points == 7  # 10 - 3
    assert pool.budget_remaining == 95000.0  # 100000 - 5000

    print("✅ Resource spending works correctly")


def test_cooldown_management():
    """Test 6: Tool cooldown management."""
    print("\n=== Test 6: Cooldown Management ===")
    manager = ResourceManager()
    pool = manager.initialize_resource_pool("intermediate")

    # Set a tool on cooldown
    cost = ActionCost(points=1, budget=0, cooldown_seconds=300, requires_staff=1)
    pool = manager.spend_resources(pool, cost, tool_name="scanner")

    print(f"   Tools on cooldown: {list(pool.tools_on_cooldown.keys())}")
    assert "scanner" in pool.tools_on_cooldown

    # Try to use the tool again (should fail)
    can_afford, reason = manager.can_afford_action(pool, cost, tool_name="scanner")
    print(f"   Can use scanner again: {can_afford} - {reason}")
    assert can_afford is False
    assert "cooldown" in reason.lower()

    # Manually set cooldown to expired
    pool.tools_on_cooldown["scanner"] = datetime.now(UTC) - timedelta(seconds=1)

    # Clear expired cooldowns
    pool = manager.clear_expired_cooldowns(pool)
    print(f"   After clearing expired: {list(pool.tools_on_cooldown.keys())}")
    assert "scanner" not in pool.tools_on_cooldown

    print("✅ Cooldown management works correctly")


def test_regenerate_action_points():
    """Test 7: Action point regeneration."""
    print("\n=== Test 7: Action Point Regeneration ===")
    manager = ResourceManager()
    pool = manager.initialize_resource_pool("intermediate")

    # Spend some points
    pool.action_points = 5
    initial_points = pool.action_points
    print(f"   Initial points: {initial_points}")

    # Simulate time passing (manually set last regeneration to 10 minutes ago)
    pool.last_regeneration = datetime.now(UTC) - timedelta(minutes=10)

    # Regenerate (at 0.5 pts/min, 10 minutes = 5 points)
    pool, points_added = manager.regenerate_action_points(pool, 10)

    print(f"   After 10 minutes: {pool.action_points} pts (+{points_added})")
    assert points_added == 5
    assert pool.action_points == 10  # Capped at max

    print("✅ Action point regeneration works correctly")


def test_get_resource_status():
    """Test 8: Get resource status."""
    print("\n=== Test 8: Resource Status ===")
    manager = ResourceManager()
    pool = manager.initialize_resource_pool("intermediate")

    # Spend some resources
    pool.action_points = 3  # Low
    pool.budget_remaining = 20000  # Low

    status = manager.get_resource_status(pool)

    print(
        f"   Action Points: {status['action_points']['current']}/{status['action_points']['max']} ({status['action_points']['percentage']:.0f}%) - {status['action_points']['status']}"
    )
    print(
        f"   Budget: ${status['budget']['remaining']:,.0f}/${status['budget']['total']:,.0f} ({status['budget']['percentage']:.0f}%) - {status['budget']['status']}"
    )
    print(f"   Staff: {status['staff']['available']} - {status['staff']['status']}")

    assert status["action_points"]["status"] == "low"  # 30% is low
    assert status["budget"]["status"] == "critical"  # 20% is critical

    print("✅ Resource status reporting works correctly")


def test_adjust_budget():
    """Test 9: Budget adjustments."""
    print("\n=== Test 9: Budget Adjustments ===")
    manager = ResourceManager()
    pool = manager.initialize_resource_pool("intermediate")

    initial = pool.budget_remaining
    print(f"   Initial budget: ${initial:,.0f}")

    # Add budget
    pool = manager.adjust_budget(pool, 50000, "Emergency funding")
    print(f"   After +$50K: ${pool.budget_remaining:,.0f}")
    assert pool.budget_remaining == 150000.0

    # Subtract budget
    pool = manager.adjust_budget(pool, -75000, "Vendor payment")
    print(f"   After -$75K: ${pool.budget_remaining:,.0f}")
    assert pool.budget_remaining == 75000.0

    # Cannot go negative
    pool = manager.adjust_budget(pool, -100000, "Large expense")
    print(f"   After -$100K (capped): ${pool.budget_remaining:,.0f}")
    assert pool.budget_remaining == 0

    print("✅ Budget adjustments work correctly")


def test_adjust_staff():
    """Test 10: Staff adjustments."""
    print("\n=== Test 10: Staff Adjustments ===")
    manager = ResourceManager()
    pool = manager.initialize_resource_pool("intermediate")

    initial = pool.staff_available
    print(f"   Initial staff: {initial}")

    # Add staff
    pool = manager.adjust_staff(pool, 2, "Backup team arrives")
    print(f"   After +2: {pool.staff_available}")
    assert pool.staff_available == 7

    # Remove staff
    pool = manager.adjust_staff(pool, -3, "Staff on other incident")
    print(f"   After -3: {pool.staff_available}")
    assert pool.staff_available == 4

    print("✅ Staff adjustments work correctly")


def test_get_affordable_actions():
    """Test 11: Get affordable actions."""
    print("\n=== Test 11: Affordable Actions ===")
    manager = ResourceManager()

    # Low resources scenario
    pool = ResourcePool(
        action_points=2,
        max_action_points=10,
        points_per_minute=0.5,
        budget_remaining=1000,
        budget_total=100000,
        staff_available=2,
        tools_on_cooldown={},
        last_regeneration=datetime.now(UTC),
    )

    affordable = manager.get_affordable_actions(pool)

    print(f"   With 2 AP, $1K budget, 2 staff: {len(affordable)} affordable actions")
    for action in affordable[:5]:  # Show first 5
        print(f"      - {action['action']}: {action['cost']['points']} pts, ${action['cost']['budget']:,.0f}")

    # Should only afford cheap actions
    action_names = [a["action"] for a in affordable]
    assert "investigate" in action_names
    assert "patch" not in action_names  # Too expensive

    print("✅ Affordable actions list works correctly")


def test_estimate_action_duration():
    """Test 12: Estimate action duration."""
    print("\n=== Test 12: Action Duration Estimation ===")
    manager = ResourceManager()

    # Simple action
    simple_cost = ActionCost(points=1, budget=0, cooldown_seconds=0, requires_staff=1)
    duration1 = manager.estimate_action_duration(simple_cost)
    print(f"   Simple action (1 pt, 1 staff): {duration1} minutes")

    # Complex action
    complex_cost = ActionCost(points=5, budget=10000, cooldown_seconds=3600, requires_staff=3)
    duration2 = manager.estimate_action_duration(complex_cost)
    print(f"   Complex action (5 pts, 3 staff): {duration2} minutes")

    assert duration2 > duration1  # Complex actions take longer

    print("✅ Action duration estimation works correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("RESOURCE MANAGER TEST SUITE")
    print("=" * 70)

    tests = [
        test_initialize_resource_pool,
        test_difficulty_scaling,
        test_get_action_cost,
        test_can_afford_action,
        test_spend_resources,
        test_cooldown_management,
        test_regenerate_action_points,
        test_get_resource_status,
        test_adjust_budget,
        test_adjust_staff,
        test_get_affordable_actions,
        test_estimate_action_duration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
