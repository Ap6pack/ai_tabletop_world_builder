#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Phase 5B Integration Test Suite.

Tests all three Phase 5B features working together:
- Feature 1: Business Impact Calculations
- Feature 2: Time Pressure Mechanics
- Feature 3: Resource Constraints

This test simulates a complete game flow with all Phase 5B mechanics.
"""

import sys
from datetime import UTC, datetime

from api.models import (
    Department,
    Objective,
    Organization,
    System,
    SystemState,
    ThreatActor,
    ThreatActorState,
    Vulnerability,
)
from api.services.business_impact_service import BusinessImpactService
from api.services.resource_manager import ResourceManager
from api.services.time_pressure_service import TimePressureService


def create_test_organization():
    """Create a test organization for integration testing."""
    # Create systems
    web_server = System(
        id="sys-001",
        name="Web Server",
        description="Primary web application server",
        type="server",
        criticality="high",
    )

    database = System(
        id="sys-002",
        name="Database Server",
        description="Production database with customer data",
        type="database",
        criticality="critical",
    )

    # Create department
    it_dept = Department(
        id="dept-001",
        name="IT Operations",
        description="Information Technology and Operations Department",
        business_function="Technology and Infrastructure",
        data_classification="restricted",
        systems=[web_server, database],
    )

    # Create vulnerability
    Vulnerability(
        id="vuln-001",
        cve_id="CVE-2024-1234",
        name="SQL Injection",
        description="SQL injection vulnerability in database query handling",
        severity="high",
        affected_systems=["sys-002"],
        exploitation_complexity="moderate",
        remediation="Apply parameterized queries and input validation",
    )

    # Create threat actor
    threat = ThreatActor(
        id="threat-001",
        name="APT29",
        description="Nation-state threat actor targeting financial institutions",
        motivation="espionage",
        sophistication="nation-state",
        ttps=["phishing", "lateral-movement"],
        targets=["sys-001", "sys-002"],
    )

    # Create organization
    org = Organization(
        id="org-001",
        name="Acme Corp",
        description="Mid-size financial services company",
        industry="Financial Services",
        size="medium",
        departments=[it_dept],
        threat_actors=[threat],
        security_posture="developing",
        compliance_frameworks=["PCI-DSS", "SOX"],
    )

    return org


def test_phase_5b_game_start():
    """Test 1: Game initialization with all Phase 5B features."""
    print("\n=== Test 1: Phase 5B Game Start ===")

    org = create_test_organization()

    # Initialize all three services
    business_impact_service = BusinessImpactService()
    time_pressure_service = TimePressureService()
    resource_manager = ResourceManager()

    # Initialize business impact
    business_impact = business_impact_service.initialize_business_impact(org)
    print("✅ Business impact initialized")
    print(f"   Industry: {org.industry}")
    print(f"   Total cost: ${business_impact.total_cost:,.2f}")

    # Initialize resource pool
    resource_pool = resource_manager.initialize_resource_pool("intermediate")
    print("✅ Resource pool initialized")
    print(f"   Action points: {resource_pool.action_points}/{resource_pool.max_action_points}")
    print(f"   Budget: ${resource_pool.budget_remaining:,.0f}")
    print(f"   Staff: {resource_pool.staff_available}")

    # Create objectives with time limits
    objectives = [
        Objective(
            id="obj-001",
            description="Identify attack vector",
            type="investigate",
            difficulty="easy",
            points=25,
            status="pending",
            time_limit_minutes=15,
            success_criteria="Determine how attackers gained access",
        ),
        Objective(
            id="obj-002",
            description="Contain the breach",
            type="contain",
            difficulty="medium",
            points=50,
            status="pending",
            time_limit_minutes=30,
            success_criteria="Isolate compromised systems",
        ),
    ]

    # Create timers for objectives
    timers = []
    for obj in objectives:
        timer = time_pressure_service.create_objective_timer(obj)
        if timer:
            timers.append(timer)

    print(f"✅ Timers created: {len(timers)}")
    for timer in timers:
        print(f"   ⏱️ {timer.name}: {timer.duration_seconds // 60} minutes")

    # Create escalation rules
    threat_ids = [t.id for t in org.threat_actors]
    system_ids = []
    for dept in org.departments:
        for system in dept.systems:
            system_ids.append(system.id)

    escalation_rules = time_pressure_service.create_scenario_escalation_rules(
        scenario_type="incident-response",
        difficulty="intermediate",
        duration_minutes=60,
        threat_ids=threat_ids,
        system_ids=system_ids,
    )

    print(f"✅ Escalation rules created: {len(escalation_rules)}")
    for rule in escalation_rules[:3]:
        print(f"   ⚠️ {rule.action} at {rule.trigger_time_minutes} minutes")

    assert business_impact is not None
    assert resource_pool.action_points == 10
    assert len(timers) == 2
    assert len(escalation_rules) > 0

    print("✅ Test 1 passed: All Phase 5B features initialized correctly")

    # Return value removed to avoid PytestReturnNotNoneWarning


def test_resource_constrained_action():
    """Test 2: Player action with resource constraints."""
    print("\n=== Test 2: Resource-Constrained Action ===")

    resource_manager = ResourceManager()
    resource_pool = resource_manager.initialize_resource_pool("intermediate")

    print("Initial resources:")
    print(f"   AP: {resource_pool.action_points}")
    print(f"   Budget: ${resource_pool.budget_remaining:,.0f}")

    # Try an expensive action
    action = "patch the vulnerability in the database server"
    action_cost = resource_manager.get_action_cost(action)

    print(f"\nAction: '{action}'")
    print(f"   Cost: {action_cost.points} AP, ${action_cost.budget:,.0f}, {action_cost.requires_staff} staff")

    # Check if affordable
    can_afford, reason = resource_manager.can_afford_action(resource_pool, action_cost)
    print(f"   Affordable: {can_afford}")

    assert can_afford is True

    # Spend resources
    resource_pool = resource_manager.spend_resources(resource_pool, action_cost, tool_name="patch_tool")

    print("\nAfter action:")
    print(f"   AP: {resource_pool.action_points}")
    print(f"   Budget: ${resource_pool.budget_remaining:,.0f}")
    print(f"   Tools on cooldown: {len(resource_pool.tools_on_cooldown)}")

    assert resource_pool.action_points == 6  # 10 - 4
    assert resource_pool.budget_remaining == 95000.0  # 100000 - 5000
    assert "patch_tool" in resource_pool.tools_on_cooldown

    # Try to use the same tool again (should fail)
    can_afford, reason = resource_manager.can_afford_action(resource_pool, action_cost, tool_name="patch_tool")
    print(f"\nTrying to use patch_tool again: {can_afford}")
    print(f"   Reason: {reason}")

    assert can_afford is False
    assert "cooldown" in reason.lower()

    print("✅ Test 2 passed: Resource constraints work correctly")

    # Return value removed to avoid PytestReturnNotNoneWarning


def test_time_pressure_and_escalation():
    """Test 3: Time pressure mechanics and automatic escalation."""
    print("\n=== Test 3: Time Pressure & Escalation ===")

    org = create_test_organization()
    time_pressure_service = TimePressureService()

    # Create a game state with timers and escalation rules
    from api.models import Inventory
    from api.models.schemas import GameState as GameStateSchema

    game_state = GameStateSchema(
        session_id="test-session",
        organization=org,
        current_scenario="incident-response",
        player_role="soc-analyst",
        inventory=Inventory(),
        status="in-progress",
        objectives=[],
        incident_timeline=[],
        score=0,
        time_elapsed=0,
        timers=[],
        escalation_rules=[],
    )

    # Add a timer
    timer = time_pressure_service.create_timer(
        name="Contain breach",
        description="Isolate compromised systems",
        duration_minutes=10,
        is_critical=True,
        on_expiry_event="Breach spreads to additional systems",
    )
    game_state.timers.append(timer)

    # Add escalation rules
    escalation_rules = time_pressure_service.create_scenario_escalation_rules(
        scenario_type="incident-response",
        difficulty="intermediate",
        duration_minutes=60,
        threat_ids=["threat-001"],
        system_ids=["sys-001", "sys-002"],
    )
    game_state.escalation_rules.extend(escalation_rules)

    # Initialize threat states
    game_state.threat_states = {
        "threat-001": ThreatActorState(
            threat_actor_id="threat-001",
            status="active",
            current_tactics=["reconnaissance"],
            systems_compromised=["sys-001"],
            detection_level=20,
            aggression_level=50,
            last_action="Initial access via phishing",
            last_update=datetime.now(UTC),
            notes="Lateral movement suspected",
        )
    }

    # Initialize system states
    game_state.system_states = {
        "sys-001": SystemState(
            system_id="sys-001",
            status="compromised",
            health=80,
            last_update=datetime.now(UTC),
            notes="Compromised by threat-001 via phishing",
        ),
        "sys-002": SystemState(
            system_id="sys-002",
            status="online",
            health=100,
            last_update=datetime.now(UTC),
        ),
    }

    print("Initial state:")
    print(f"   Timers: {len(game_state.timers)}")
    print(f"   Escalation rules: {len(game_state.escalation_rules)}")
    print(f"   Threat aggression: {game_state.threat_states['threat-001'].aggression_level}%")
    print(
        f"   System health: sys-001={game_state.system_states['sys-001'].health}%, sys-002={game_state.system_states['sys-002'].health}%"
    )

    # Simulate time passing (20 minutes)
    game_state.time_elapsed = 20

    # Update timers
    game_state, timer_messages = time_pressure_service.update_timers(game_state, 20)
    print("\nAfter 20 minutes:")
    print(f"   Timer messages: {len(timer_messages)}")
    for msg in timer_messages:
        print(f"      {msg}")

    # Check escalations
    game_state, escalation_messages = time_pressure_service.check_escalation_rules(game_state, 20)
    print(f"   Escalation messages: {len(escalation_messages)}")
    for msg in escalation_messages:
        print(f"      {msg}")

    # Verify timer expired
    assert game_state.timers[0].is_expired

    # Verify at least one escalation triggered
    triggered_rules = [r for r in game_state.escalation_rules if r.triggered]
    print(f"   Triggered rules: {len(triggered_rules)}")
    assert len(triggered_rules) > 0

    print("✅ Test 3 passed: Time pressure and escalation work correctly")


def test_business_impact_tracking():
    """Test 4: Business impact calculation during incident."""
    print("\n=== Test 4: Business Impact Tracking ===")

    org = create_test_organization()
    business_impact_service = BusinessImpactService()

    # Initialize business impact
    from api.models import Inventory
    from api.models.schemas import GameState as GameStateSchema

    game_state = GameStateSchema(
        session_id="test-session",
        organization=org,
        current_scenario="incident-response",
        player_role="soc-analyst",
        inventory=Inventory(),
        status="in-progress",
        objectives=[],
        incident_timeline=[],
        score=0,
        time_elapsed=0,
    )

    game_state.business_impact = business_impact_service.initialize_business_impact(org)

    print("Initial impact:")
    print(f"   Total cost: ${game_state.business_impact.total_cost:,.2f}")

    # System downtime
    game_state = business_impact_service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="downtime",
        system_id="sys-002",  # Critical database
        hours=2.0,
        severity="high",
    )

    downtime_cost = game_state.business_impact.total_cost
    print("\nAfter 2 hours database downtime:")
    print(f"   Total cost: ${downtime_cost:,.2f}")
    print(f"   Events: {len(game_state.impact_events)}")

    assert downtime_cost > 0

    # Data loss
    game_state = business_impact_service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="data_loss",
        records=10000,
        department="IT Operations",
        severity="critical",
    )

    data_loss_cost = game_state.business_impact.total_cost
    print("\nAfter 10,000 records compromised:")
    print(f"   Total cost: ${data_loss_cost:,.2f}")
    print(f"   Cost increase: ${data_loss_cost - downtime_cost:,.2f}")

    assert data_loss_cost > downtime_cost

    # Compliance violation (records must be passed for penalty calculation)
    game_state = business_impact_service.update_impact(
        game_state=game_state, organization=org, event_type="compliance", records=10000, severity="critical"
    )

    compliance_cost = game_state.business_impact.total_cost
    print("\nAfter compliance violation:")
    print(f"   Total cost: ${compliance_cost:,.2f}")
    print(f"   Total events: {len(game_state.impact_events)}")

    # Generate report
    report = business_impact_service.generate_impact_report(game_state.business_impact)
    print("\n📊 Impact Report:")
    print("   By category:")
    for category, cost in report["by_category"].items():
        if cost > 0:
            print(f"      {category}: ${cost:,.2f}")

    assert compliance_cost > data_loss_cost
    assert len(game_state.impact_events) == 3

    print("✅ Test 4 passed: Business impact tracking works correctly")


def test_integrated_game_flow():
    """Test 5: Complete game flow with all Phase 5B features."""
    print("\n=== Test 5: Integrated Game Flow ===")

    org = create_test_organization()

    # Initialize all services
    business_impact_service = BusinessImpactService()
    time_pressure_service = TimePressureService()
    resource_manager = ResourceManager()

    # Create game state
    from api.models import Inventory
    from api.models.schemas import GameState as GameStateSchema

    game_state = GameStateSchema(
        session_id="integration-test",
        organization=org,
        current_scenario="incident-response",
        player_role="soc-analyst",
        inventory=Inventory(),
        status="in-progress",
        objectives=[],
        incident_timeline=[],
        score=0,
        time_elapsed=0,
    )

    # Initialize all Phase 5B features
    game_state.business_impact = business_impact_service.initialize_business_impact(org)
    game_state.resource_pool = resource_manager.initialize_resource_pool("intermediate")

    # Add objectives with timers
    objectives = [
        Objective(
            id="obj-001",
            description="Investigate suspicious activity",
            type="investigate",
            difficulty="easy",
            points=25,
            status="pending",
            time_limit_minutes=10,
            success_criteria="Identify attack type",
        )
    ]
    game_state.objectives = objectives

    # Create timer
    timer = time_pressure_service.create_objective_timer(objectives[0])
    game_state.timers.append(timer)

    # Create escalation rules
    threat_ids = ["threat-001"]
    system_ids = ["sys-001", "sys-002"]
    escalation_rules = time_pressure_service.create_scenario_escalation_rules(
        scenario_type="incident-response",
        difficulty="intermediate",
        duration_minutes=30,
        threat_ids=threat_ids,
        system_ids=system_ids,
    )
    game_state.escalation_rules.extend(escalation_rules)

    print("Game initialized:")
    print(
        f"   Resources: {game_state.resource_pool.action_points} AP, ${game_state.resource_pool.budget_remaining:,.0f}"
    )
    print(f"   Timers: {len(game_state.timers)}")
    print(f"   Escalations: {len(game_state.escalation_rules)}")
    print(f"   Business impact: ${game_state.business_impact.total_cost:,.2f}")

    # === Turn 1: Investigation ===
    print("\n--- Turn 1: Investigation ---")
    action = "investigate the database logs"
    action_cost = resource_manager.get_action_cost(action)

    can_afford, _ = resource_manager.can_afford_action(game_state.resource_pool, action_cost)
    assert can_afford

    game_state.resource_pool = resource_manager.spend_resources(game_state.resource_pool, action_cost)
    game_state.time_elapsed = 5

    print(f"   Action: {action}")
    print(f"   Cost: {action_cost.points} AP, ${action_cost.budget:,.0f}")
    print(f"   Remaining: {game_state.resource_pool.action_points} AP")

    # === Turn 2: Containment ===
    print("\n--- Turn 2: Containment ---")
    action = "isolate the compromised database server"
    action_cost = resource_manager.get_action_cost(action)

    can_afford, _ = resource_manager.can_afford_action(game_state.resource_pool, action_cost)
    assert can_afford

    game_state.resource_pool = resource_manager.spend_resources(game_state.resource_pool, action_cost)
    game_state.time_elapsed = 12

    # Update timers (should expire)
    game_state, timer_messages = time_pressure_service.update_timers(game_state, game_state.time_elapsed)

    print(f"   Action: {action}")
    print(f"   Cost: {action_cost.points} AP, ${action_cost.budget:,.0f}")
    print(f"   Remaining: {game_state.resource_pool.action_points} AP")
    print(f"   Timer expired: {game_state.timers[0].is_expired}")

    # Check escalations
    game_state, escalation_messages = time_pressure_service.check_escalation_rules(game_state, game_state.time_elapsed)

    if escalation_messages:
        print(f"   Escalations triggered: {len(escalation_messages)}")

    # Add business impact (system was down)
    game_state = business_impact_service.update_impact(
        game_state=game_state, organization=org, event_type="downtime", system_id="sys-002", hours=0.5, severity="high"
    )

    print(f"   Business impact: ${game_state.business_impact.total_cost:,.2f}")

    # === Turn 3: Restore action ===
    print("\n--- Turn 3: Restoration ---")
    action = "restore the database from backup"
    action_cost = resource_manager.get_action_cost(action)

    can_afford, reason = resource_manager.can_afford_action(game_state.resource_pool, action_cost)

    if not can_afford:
        print(f"   ❌ Cannot afford: {reason}")
        print(f"   Need: {action_cost.points} AP, have: {game_state.resource_pool.action_points} AP")

        # Regenerate action points
        game_state.resource_pool, points_added = resource_manager.regenerate_action_points(
            game_state.resource_pool, game_state.time_elapsed
        )
        print(f"   Regenerated: {points_added} AP")
        print(f"   Now have: {game_state.resource_pool.action_points} AP")

        # Re-check affordability after regeneration
        can_afford, reason = resource_manager.can_afford_action(game_state.resource_pool, action_cost)

    if can_afford:
        game_state.resource_pool = resource_manager.spend_resources(game_state.resource_pool, action_cost)
        print(f"   Action: {action}")
        print(f"   Cost: {action_cost.points} AP, ${action_cost.budget:,.0f}")
        print(
            f"   Remaining: {game_state.resource_pool.action_points} AP, ${game_state.resource_pool.budget_remaining:,.0f}"
        )

    # Final state
    print("\n📊 Final Game State:")
    print(f"   Time elapsed: {game_state.time_elapsed} minutes")
    print(
        f"   Resources remaining: {game_state.resource_pool.action_points} AP, ${game_state.resource_pool.budget_remaining:,.0f}"
    )
    print(f"   Timers expired: {sum(1 for t in game_state.timers if t.is_expired)}")
    print(f"   Escalations triggered: {sum(1 for r in game_state.escalation_rules if r.triggered)}")
    print(f"   Total business impact: ${game_state.business_impact.total_cost:,.2f}")

    # Assertions
    assert game_state.resource_pool.action_points < 10  # Some AP spent
    assert game_state.resource_pool.budget_remaining < 100000  # Some budget spent
    assert game_state.timers[0].is_expired  # Timer expired
    assert game_state.business_impact.total_cost > 0  # Impact tracked

    print("✅ Test 5 passed: Integrated game flow works correctly")


def run_all_tests():
    """Run all Phase 5B integration tests."""
    print("=" * 70)
    print("PHASE 5B INTEGRATION TEST SUITE")
    print("=" * 70)

    tests = [
        test_phase_5b_game_start,
        test_resource_constrained_action,
        test_time_pressure_and_escalation,
        test_business_impact_tracking,
        test_integrated_game_flow,
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

    if passed == len(tests):
        print("\n🎉 ALL PHASE 5B INTEGRATION TESTS PASSED!")
        print("\n✅ Phase 5B Complete:")
        print("   - Feature 1: Business Impact Calculations ✅")
        print("   - Feature 2: Time Pressure Mechanics ✅")
        print("   - Feature 3: Resource Constraints ✅")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
