#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Test suite for Time Pressure Service.

Tests timer creation, escalation rules, and time-based mechanics.
"""

import sys
from datetime import UTC, datetime

from api.models import (
    GameState,
    Inventory,
    Objective,
    Organization,
    SystemState,
    ThreatActorState,
)
from api.services.time_pressure_service import TimePressureService


def create_test_game_state() -> GameState:
    """Create a minimal game state for testing."""
    org = Organization(
        id="test-org",
        name="Test Corp",
        description="Test organization",
        industry="technology",
        size="medium",
        departments=[],
        threat_actors=[],
        security_posture="developing",
        compliance_frameworks=[],
    )

    return GameState(
        session_id="test-session",
        organization=org,
        current_scenario="Test scenario",
        player_role="soc-analyst",
        inventory=Inventory(),
        score=0,
        time_elapsed=0,
        status="in-progress",
        game_started_at=datetime.now(UTC),
    )


def test_create_timer():
    """Test 1: Create a countdown timer."""
    print("\n=== Test 1: Create Timer ===")
    service = TimePressureService()

    timer = service.create_timer(
        name="Test Timer",
        description="A test countdown timer",
        duration_minutes=10,
        is_critical=True,
        on_expiry_event="Test event triggered",
    )

    assert timer.name == "Test Timer"
    assert timer.duration_seconds == 600  # 10 minutes
    assert timer.remaining_seconds == 600
    assert timer.is_critical is True
    assert not timer.is_expired

    print(f"✅ Timer created: {timer.name}")
    print(f"   Duration: {timer.duration_seconds}s ({timer.duration_seconds // 60}m)")
    print(f"   Remaining: {timer.remaining_seconds}s")
    print(f"   Critical: {timer.is_critical}")


def test_create_escalation_rule():
    """Test 2: Create an escalation rule."""
    print("\n=== Test 2: Create Escalation Rule ===")
    service = TimePressureService()

    rule = service.create_escalation_rule(
        trigger_time_minutes=15,
        action="threat_escalate",
        target_id="threat-001",
        severity_increase=20,
        description="Threat increases aggression",
    )

    assert rule.trigger_time_minutes == 15
    assert rule.action == "threat_escalate"
    assert rule.target_id == "threat-001"
    assert rule.severity_increase == 20
    assert rule.triggered is False

    print("✅ Escalation rule created")
    print(f"   Trigger time: {rule.trigger_time_minutes} minutes")
    print(f"   Action: {rule.action}")
    print(f"   Target: {rule.target_id}")
    print(f"   Triggered: {rule.triggered}")


def test_timer_expiry():
    """Test 3: Timer expiry detection."""
    print("\n=== Test 3: Timer Expiry ===")
    service = TimePressureService()

    # Create a timer that expires in 1 minute
    timer = service.create_timer(
        name="Short Timer",
        description="Expires quickly",
        duration_minutes=1,
    )

    print(f"   Initial state: expired={timer.is_expired}, remaining={timer.remaining_seconds}s")

    # Simulate 30 seconds passing
    timer.remaining_seconds = 30
    print(f"   After 30s: expired={timer.is_expired}, remaining={timer.remaining_seconds}s")
    assert not timer.is_expired

    # Simulate full expiry
    timer.remaining_seconds = 0
    print(f"   After 60s: expired={timer.is_expired}, remaining={timer.remaining_seconds}s")
    assert timer.is_expired

    print("✅ Timer expiry works correctly")


def test_update_timers():
    """Test 4: Update timers in game state."""
    print("\n=== Test 4: Update Timers ===")
    service = TimePressureService()
    game_state = create_test_game_state()

    # Create an objective with time limit
    objective = Objective(
        id="obj-001",
        description="Identify the attack vector",
        type="investigate",
        success_criteria="Find entry point",
        time_limit_minutes=15,
        points=50,
        difficulty="medium",
        status="in-progress",
    )
    game_state.objectives.append(objective)

    # Create timer for objective
    timer = service.create_objective_timer(objective)
    game_state.timers.append(timer)

    print(f"   Objective: {objective.description}")
    print(f"   Time limit: {objective.time_limit_minutes} minutes")
    print(f"   Timer created: {timer.name}")

    # Simulate some time passing (5 minutes)
    game_state.time_elapsed = 5
    game_state, messages = service.update_timers(game_state, 5)

    print(f"   After 5 minutes: {len(messages)} messages")
    assert len(messages) == 0, "No expiry yet"

    # Simulate timer expiring (time passes to 20 minutes - beyond the 15 min limit)
    game_state.time_elapsed = 20
    game_state, messages = service.update_timers(game_state, 20)

    print(f"   After 20 minutes: {len(messages)} messages")
    for msg in messages:
        print(f"      - {msg}")

    # The timer should detect expiry and generate messages
    assert len(messages) > 0, "Should have expiry messages"
    assert objective.status == "failed", "Objective should be failed"

    print("✅ Timer updates work correctly")


def test_threat_escalation():
    """Test 5: Threat escalation rule triggering."""
    print("\n=== Test 5: Threat Escalation ===")
    service = TimePressureService()
    game_state = create_test_game_state()

    # Add a threat state
    threat_state = ThreatActorState(
        threat_actor_id="threat-001",
        status="active",
        aggression_level=50,
        detection_level=20,
        last_update=datetime.now(UTC),
    )
    game_state.threat_states["threat-001"] = threat_state

    # Create escalation rule
    rule = service.create_escalation_rule(
        trigger_time_minutes=10,
        action="threat_escalate",
        target_id="threat-001",
        severity_increase=20,
        description="Threat increases aggression level",
    )
    game_state.escalation_rules.append(rule)

    print(f"   Initial aggression: {threat_state.aggression_level}%")
    print(f"   Escalation triggers at: {rule.trigger_time_minutes} minutes")

    # Before trigger time
    game_state.time_elapsed = 5
    game_state, messages = service.check_escalation_rules(game_state, 5)
    print(f"   At 5 minutes: aggression={threat_state.aggression_level}%, triggered={rule.triggered}")
    assert not rule.triggered, "Should not trigger yet"
    assert threat_state.aggression_level == 50, "Aggression unchanged"

    # After trigger time
    game_state.time_elapsed = 10
    game_state, messages = service.check_escalation_rules(game_state, 10)
    print(f"   At 10 minutes: aggression={threat_state.aggression_level}%, triggered={rule.triggered}")
    print(f"   Messages: {messages}")

    assert rule.triggered, "Should be triggered"
    assert threat_state.aggression_level == 70, "Aggression should increase"
    assert len(messages) > 0, "Should have escalation message"

    print("✅ Threat escalation works correctly")


def test_system_degradation():
    """Test 6: System degradation rule."""
    print("\n=== Test 6: System Degradation ===")
    service = TimePressureService()
    game_state = create_test_game_state()

    # Add a system state
    system_state = SystemState(
        system_id="sys-001",
        status="compromised",
        health=100,
        last_update=datetime.now(UTC),
    )
    game_state.system_states["sys-001"] = system_state

    # Create degradation rule
    rule = service.create_escalation_rule(
        trigger_time_minutes=5,
        action="system_degrade",
        target_id="sys-001",
        severity_increase=30,
        description="System health degrading",
    )
    game_state.escalation_rules.append(rule)

    print(f"   Initial health: {system_state.health}%")
    print(f"   Initial status: {system_state.status}")

    # Trigger degradation
    game_state.time_elapsed = 5
    game_state, messages = service.check_escalation_rules(game_state, 5)

    print(f"   After trigger: health={system_state.health}%, status={system_state.status}")
    print(f"   Messages: {messages}")

    assert system_state.health == 70, "Health should degrade"
    assert len(messages) > 0, "Should have degradation message"

    print("✅ System degradation works correctly")


def test_time_multiplier():
    """Test 7: Time-based score multipliers."""
    print("\n=== Test 7: Time-Based Multipliers ===")
    service = TimePressureService()

    objective = Objective(
        id="obj-001",
        description="Test objective",
        type="detect",
        success_criteria="Complete task",
        time_limit_minutes=20,
        points=100,
        difficulty="medium",
        status="pending",
    )

    # Fast completion (5 minutes = 25% of limit)
    multiplier_fast = service.calculate_time_multiplier(objective, 5)
    print(f"   Fast completion (5/20 min): {multiplier_fast}x")
    assert multiplier_fast == 2.0, "Fast medium should be 2.0x"

    # Normal completion (15 minutes = 75% of limit)
    multiplier_normal = service.calculate_time_multiplier(objective, 15)
    print(f"   Normal completion (15/20 min): {multiplier_normal}x")
    assert multiplier_normal == 1.0, "Normal should be 1.0x"

    # Slow completion (25 minutes = 125% of limit)
    multiplier_slow = service.calculate_time_multiplier(objective, 25)
    print(f"   Slow completion (25/20 min): {multiplier_slow}x")
    assert multiplier_slow == 0.3, "Slow medium should be 0.3x"

    # Hard difficulty fast completion
    hard_obj = Objective(
        id="obj-002",
        description="Hard objective",
        type="mitigate",
        success_criteria="Complete task",
        time_limit_minutes=30,
        points=200,
        difficulty="hard",
        status="pending",
    )
    multiplier_hard = service.calculate_time_multiplier(hard_obj, 10)
    print(f"   Hard fast completion (10/30 min): {multiplier_hard}x")
    assert multiplier_hard == 3.0, "Fast hard should be 3.0x"

    print("✅ Time multipliers calculated correctly")


def test_timer_status():
    """Test 8: Timer status reporting."""
    print("\n=== Test 8: Timer Status ===")
    service = TimePressureService()

    timer = service.create_timer(
        name="Status Test",
        description="Test status",
        duration_minutes=10,
    )

    # Active status (plenty of time)
    timer.remaining_seconds = 600  # 10 minutes
    status = service.get_timer_status(timer)
    print(f"   10:00 remaining - Status: {status['status']}, Urgency: {status['urgency']}")
    assert status["status"] == "active"
    assert status["urgency"] == "low"

    # Warning status (7 minutes)
    timer.remaining_seconds = 420
    status = service.get_timer_status(timer)
    print(f"   7:00 remaining - Status: {status['status']}, Urgency: {status['urgency']}")
    assert status["status"] == "warning"

    # Urgent status (3 minutes)
    timer.remaining_seconds = 180
    status = service.get_timer_status(timer)
    print(f"   3:00 remaining - Status: {status['status']}, Urgency: {status['urgency']}")
    assert status["status"] == "urgent"
    assert status["urgency"] == "high"

    # Expired
    timer.remaining_seconds = 0
    status = service.get_timer_status(timer)
    print(f"   0:00 remaining - Status: {status['status']}, Urgency: {status['urgency']}")
    assert status["status"] == "expired"
    assert status["urgency"] == "critical"

    print("✅ Timer status reporting works correctly")


def test_create_scenario_escalation_rules():
    """Test 9: Scenario-based escalation rules."""
    print("\n=== Test 9: Scenario Escalation Rules ===")
    service = TimePressureService()

    threat_ids = ["threat-001", "threat-002"]
    system_ids = ["sys-001", "sys-002", "sys-003"]

    # Intermediate difficulty
    rules = service.create_scenario_escalation_rules(
        scenario_type="incident-response",
        difficulty="intermediate",
        duration_minutes=60,
        threat_ids=threat_ids,
        system_ids=system_ids,
    )

    print(f"   Intermediate scenario (60 min): {len(rules)} rules")
    for rule in rules:
        print(f"      - T+{rule.trigger_time_minutes}m: {rule.action} - {rule.description}")

    assert len(rules) > 0, "Should create escalation rules"

    # Expert difficulty (should have more rules)
    expert_rules = service.create_scenario_escalation_rules(
        scenario_type="incident-response",
        difficulty="expert",
        duration_minutes=60,
        threat_ids=threat_ids,
        system_ids=system_ids,
    )

    print(f"\n   Expert scenario (60 min): {len(expert_rules)} rules")
    for rule in expert_rules:
        print(f"      - T+{rule.trigger_time_minutes}m: {rule.action} - {rule.description}")

    assert len(expert_rules) > len(rules), "Expert should have more rules"

    print("✅ Scenario escalation rules created correctly")


def test_active_timers_summary():
    """Test 10: Active timers summary."""
    print("\n=== Test 10: Active Timers Summary ===")
    service = TimePressureService()
    game_state = create_test_game_state()

    # Add multiple timers
    timer1 = service.create_timer("Timer 1", "First timer", 10, is_critical=True)
    timer1.remaining_seconds = 300  # 5 minutes

    timer2 = service.create_timer("Timer 2", "Second timer", 20)
    timer2.remaining_seconds = 600  # 10 minutes

    timer3 = service.create_timer("Timer 3", "Expired timer", 5)
    timer3.remaining_seconds = 0  # Expired

    game_state.timers = [timer1, timer2, timer3]

    summary = service.get_active_timers_summary(game_state)

    print(f"   Total timers: {summary['total_timers']}")
    print(f"   Active: {summary['active_count']}")
    print(f"   Expired: {summary['expired_count']}")
    print(f"   Critical: {summary['critical_count']}")

    if summary["most_urgent"]:
        print(f"   Most urgent: {summary['most_urgent'].name} ({summary['most_urgent'].remaining_seconds}s)")

    assert summary["total_timers"] == 3
    assert summary["active_count"] == 2
    assert summary["expired_count"] == 1
    assert summary["critical_count"] == 1
    assert summary["most_urgent"].name == "Timer 1"

    print("✅ Active timers summary works correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("TIME PRESSURE SERVICE TEST SUITE")
    print("=" * 70)

    tests = [
        test_create_timer,
        test_create_escalation_rule,
        test_timer_expiry,
        test_update_timers,
        test_threat_escalation,
        test_system_degradation,
        test_time_multiplier,
        test_timer_status,
        test_create_scenario_escalation_rules,
        test_active_timers_summary,
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
