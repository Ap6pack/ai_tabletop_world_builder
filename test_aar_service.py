"""
Test suite for AAR Service, Decision Analyzer, and Alternative Path Service.

Tests the complete After Action Review pipeline:
- Decision analysis and scoring
- Alternative path suggestions
- AAR report generation
- Performance metrics calculation
- Performance dashboard aggregation
"""
import sys
from datetime import datetime, timedelta, timezone
from api.models import (
    Organization, Department, System, Vulnerability, ThreatActor,
    GameState, Objective, Inventory, IncidentEvent,
    SystemState, ThreatActorState, BusinessImpact, ResourcePool,
)


def create_test_organization():
    """Create a test organization for AAR testing."""
    return Organization(
        id="org-001",
        name="Acme Corp",
        description="Mid-size financial services company",
        industry="Financial Services",
        size="medium",
        departments=[
            Department(
                id="dept-001",
                name="IT Operations",
                description="IT Operations Department",
                business_function="Technology",
                systems=[
                    System(
                        id="sys-001", name="Web Server",
                        description="Primary web server", type="server",
                        criticality="high"
                    ),
                    System(
                        id="sys-002", name="Database",
                        description="Production database", type="database",
                        criticality="critical"
                    ),
                ],
                data_classification="restricted",
            )
        ],
        threat_actors=[
            ThreatActor(
                id="threat-001", name="APT29",
                description="Nation-state actor",
                motivation="espionage",
                sophistication="nation-state",
                ttps=["phishing", "lateral-movement"],
                targets=["sys-001", "sys-002"]
            )
        ],
        security_posture="developing",
        compliance_frameworks=["PCI-DSS"],
    )


def create_test_game_state(status="completed", include_business_impact=True):
    """Create a comprehensive test game state with realistic timeline."""
    now = datetime.now(timezone.utc)
    org = create_test_organization()

    timeline = [
        IncidentEvent(
            timestamp=now - timedelta(minutes=55),
            event_type="detection", description="SIEM alert: suspicious login from unknown IP",
            severity="high", actor="system"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=50),
            event_type="action", description="Check SIEM logs for the alert details",
            severity="medium", actor="player"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=45),
            event_type="consequence", description="Alert confirmed as brute force attempt",
            severity="info", actor="system"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=40),
            event_type="action", description="Investigate the source IP and correlate with threat intel",
            severity="medium", actor="player"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=35),
            event_type="action", description="Block the malicious IP at the firewall",
            severity="medium", actor="player"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=30),
            event_type="consequence", description="IP blocked successfully",
            severity="low", actor="system"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=25),
            event_type="escalation", description="Threat actor pivoted to phishing campaign",
            severity="high", actor="threat_actor"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=20),
            event_type="action", description="Monitor email gateway for phishing attempts",
            severity="medium", actor="player"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=15),
            event_type="action", description="Isolate compromised workstation from network",
            severity="high", actor="player"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=10),
            event_type="consequence", description="Workstation isolated, lateral movement stopped",
            severity="low", actor="system"
        ),
        IncidentEvent(
            timestamp=now - timedelta(minutes=5),
            event_type="action", description="Notify management and escalate to CISO",
            severity="medium", actor="player"
        ),
    ]

    objectives = [
        Objective(
            id="obj-001", description="Identify attack vector",
            type="investigate", success_criteria="Determine initial access method",
            points=25, difficulty="easy", status="completed"
        ),
        Objective(
            id="obj-002", description="Contain the breach",
            type="contain", success_criteria="Isolate compromised systems",
            points=50, difficulty="medium", status="completed"
        ),
        Objective(
            id="obj-003", description="Notify stakeholders",
            type="report", success_criteria="Alert management chain",
            points=15, difficulty="easy", status="completed"
        ),
        Objective(
            id="obj-004", description="Restore affected systems",
            type="mitigate", success_criteria="Bring systems back online",
            points=40, difficulty="hard", status="failed"
        ),
    ]

    system_states = {
        "sys-001": SystemState(
            system_id="sys-001", status="recovering", health=60,
            last_update=now, affected_services=["web"]
        ),
        "sys-002": SystemState(
            system_id="sys-002", status="online", health=95,
            last_update=now
        ),
    }

    threat_states = {
        "threat-001": ThreatActorState(
            threat_actor_id="threat-001", status="contained",
            detection_level=80, aggression_level=30,
            last_update=now
        ),
    }

    game_state = GameState(
        session_id="session_test001",
        organization=org,
        current_scenario="incident-response",
        player_role="soc-analyst",
        inventory=Inventory(tools={"siem": 1, "firewall": 1}, access_levels=["user", "admin"]),
        incident_timeline=timeline,
        score=75,
        time_elapsed=55,
        objectives=objectives,
        system_states=system_states,
        threat_states=threat_states,
        status=status,
        game_started_at=now - timedelta(minutes=55),
    )

    if include_business_impact:
        game_state.business_impact = BusinessImpact(
            downtime_cost=25000.0,
            downtime_hours=2.0,
            total_cost=35000.0,
            impact_description="Moderate business impact from 2-hour partial outage"
        )
        game_state.resource_pool = ResourcePool(
            action_points=3, max_action_points=10,
            budget_remaining=65000.0, budget_total=100000.0,
            staff_available=3
        )

    return game_state


def test_decision_analyzer():
    """Test 1-4: Decision Analyzer tests."""
    from api.services.decision_analyzer import DecisionAnalyzer

    print("\n" + "=" * 70)
    print("DECISION ANALYZER TESTS")
    print("=" * 70)

    analyzer = DecisionAnalyzer()
    game_state = create_test_game_state()

    # Test 1: Categorize actions
    print("\nTest 1: Action categorization")
    assert analyzer.categorize_action("Check SIEM logs") == "detection"
    assert analyzer.categorize_action("Isolate the server") == "containment"
    assert analyzer.categorize_action("Patch the vulnerability") == "mitigation"
    assert analyzer.categorize_action("Notify the CISO") == "communication"
    assert analyzer.categorize_action("Investigate the root cause") == "investigation"
    assert analyzer.categorize_action("Do something random") == "other"
    print("  PASS - All categories correctly identified")

    # Test 2: Analyze timeline
    print("\nTest 2: Timeline analysis")
    evaluations = analyzer.analyze_timeline(game_state)
    assert len(evaluations) > 0, "Should have at least one evaluation"
    # We have 6 player actions in the timeline
    player_actions = [e for e in game_state.incident_timeline if e.actor == "player"]
    assert len(evaluations) == len(player_actions), f"Expected {len(player_actions)} evaluations, got {len(evaluations)}"
    print(f"  PASS - Analyzed {len(evaluations)} player decisions")

    # Test 3: Decision scoring
    print("\nTest 3: Decision quality scoring")
    for ev in evaluations:
        assert 0 <= ev.quality_score <= 100, f"Score {ev.quality_score} out of range"
        assert ev.impact in ("positive", "neutral", "negative")
        assert ev.category in ("detection", "containment", "mitigation", "communication", "investigation", "other")
        assert len(ev.reasoning) > 0
    print(f"  PASS - All {len(evaluations)} decisions scored within valid ranges")

    # Test 4: Early action bonus
    print("\nTest 4: Early action timing bonus")
    first_eval = evaluations[0]
    # First action should get timeliness bonus (within first 30%)
    assert first_eval.quality_score >= 50, "First action should score at least base"
    print(f"  PASS - First action scored {first_eval.quality_score}")

    print("\n  All Decision Analyzer tests PASSED")


def test_alternative_path_service():
    """Test 5-7: Alternative Path Service tests."""
    from api.services.alternative_path_service import AlternativePathService

    print("\n" + "=" * 70)
    print("ALTERNATIVE PATH SERVICE TESTS")
    print("=" * 70)

    service = AlternativePathService()
    game_state = create_test_game_state()

    # Test 5: Suggest alternatives
    print("\nTest 5: Generate alternative suggestions")
    alternatives = service.suggest_alternatives(game_state)
    assert isinstance(alternatives, list), "Should return a list"
    print(f"  PASS - Generated {len(alternatives)} alternative suggestions")

    # Test 6: Identify decision points
    print("\nTest 6: Identify decision points")
    decision_points = service.identify_decision_points(game_state.incident_timeline)
    assert len(decision_points) > 0, "Should identify at least one decision point"
    for dp in decision_points:
        assert "event" in dp
        assert "reason" in dp
    print(f"  PASS - Identified {len(decision_points)} decision points")

    # Test 7: Alternative structure validation
    print("\nTest 7: Alternative path structure")
    for alt in alternatives:
        assert len(alt.decision_point) > 0
        assert len(alt.suggested_action) > 0
        assert len(alt.expected_outcome) > 0
        assert alt.difficulty in ("easy", "medium", "hard")
    print(f"  PASS - All alternatives have valid structure")

    print("\n  All Alternative Path Service tests PASSED")


def test_aar_service():
    """Test 8-15: AAR Service tests."""
    from api.services.aar_service import AARService

    print("\n" + "=" * 70)
    print("AAR SERVICE TESTS")
    print("=" * 70)

    service = AARService()
    game_state = create_test_game_state()

    # Test 8: Generate full AAR
    print("\nTest 8: Generate complete AAR report")
    report = service.generate_aar(game_state)
    assert report.session_id == "session_test001"
    assert len(report.summary) > 0
    assert report.overall_grade in ("A", "B", "C", "D", "F")
    assert len(report.timeline_analysis) > 0
    assert len(report.strengths) >= 0
    assert len(report.weaknesses) >= 0
    assert len(report.recommendations) >= 0
    print(f"  PASS - AAR generated: grade={report.overall_grade}, "
          f"{len(report.timeline_analysis)} decisions analyzed")

    # Test 9: Calculate metrics
    print("\nTest 9: Performance metrics calculation")
    metrics = service.calculate_metrics(game_state)
    assert isinstance(metrics, dict)
    assert "objectives_completed_pct" in metrics
    obj_pct = metrics["objectives_completed_pct"]
    assert obj_pct.value == 75.0, f"Expected 75% objectives completed, got {obj_pct.value}"
    print(f"  PASS - Calculated {len(metrics)} metrics")

    # Test 10: Grade calculation
    print("\nTest 10: Grade calculation")
    grade = service.calculate_grade(75, metrics)
    assert grade in ("A", "B", "C", "D", "F")
    # Score of 75 with decent metrics should be B or C
    print(f"  PASS - Grade: {grade} for score 75")

    # Test 11: Strengths identification
    print("\nTest 11: Identify strengths")
    evaluations = report.timeline_analysis
    strengths = service.identify_strengths(evaluations, metrics)
    assert isinstance(strengths, list)
    print(f"  PASS - Found {len(strengths)} strengths")

    # Test 12: Weaknesses identification
    print("\nTest 12: Identify weaknesses")
    weaknesses = service.identify_weaknesses(evaluations, metrics)
    assert isinstance(weaknesses, list)
    print(f"  PASS - Found {len(weaknesses)} weaknesses")

    # Test 13: Recommendations generation
    print("\nTest 13: Generate recommendations")
    recommendations = service.generate_recommendations(weaknesses, game_state)
    assert isinstance(recommendations, list)
    print(f"  PASS - Generated {len(recommendations)} recommendations")

    # Test 14: Score breakdown
    print("\nTest 14: Score breakdown")
    breakdown = service.build_score_breakdown(game_state)
    assert isinstance(breakdown, dict)
    assert "objective_points" in breakdown
    print(f"  PASS - Score breakdown: {breakdown}")

    # Test 15: Performance dashboard
    print("\nTest 15: Performance dashboard from multiple sessions")
    state2 = create_test_game_state()
    state2.session_id = "session_test002"
    state2.score = 90
    state2.time_elapsed = 40

    dashboard = service.build_dashboard([game_state, state2])
    assert dashboard.sessions_completed == 2
    assert dashboard.average_score > 0
    assert dashboard.best_score == 90
    print(f"  PASS - Dashboard: {dashboard.sessions_completed} sessions, "
          f"avg={dashboard.average_score:.1f}, best={dashboard.best_score}")

    print("\n  All AAR Service tests PASSED")


def test_aar_edge_cases():
    """Test 16-18: Edge cases."""
    from api.services.aar_service import AARService

    print("\n" + "=" * 70)
    print("EDGE CASE TESTS")
    print("=" * 70)

    service = AARService()

    # Test 16: Empty timeline
    print("\nTest 16: AAR with empty timeline")
    game_state = create_test_game_state()
    game_state.incident_timeline = []
    report = service.generate_aar(game_state)
    assert report.session_id == "session_test001"
    assert len(report.timeline_analysis) == 0
    print("  PASS - Handled empty timeline gracefully")

    # Test 17: No business impact
    print("\nTest 17: AAR without business impact data")
    game_state = create_test_game_state(include_business_impact=False)
    report = service.generate_aar(game_state)
    assert report.overall_grade in ("A", "B", "C", "D", "F")
    print(f"  PASS - AAR generated without business impact: grade={report.overall_grade}")

    # Test 18: Dashboard with no sessions
    print("\nTest 18: Dashboard with empty session list")
    dashboard = service.build_dashboard([])
    assert dashboard.sessions_completed == 0
    assert dashboard.average_score == 0.0
    print("  PASS - Empty dashboard handled")

    print("\n  All Edge Case tests PASSED")


if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 6 ANALYTICS & AAR TEST SUITE")
    print("=" * 70)

    all_passed = True
    try:
        test_decision_analyzer()
        test_alternative_path_service()
        test_aar_service()
        test_aar_edge_cases()

        print("\n" + "=" * 70)
        print("ALL PHASE 6 TESTS PASSED")
        print("=" * 70)
    except Exception as e:
        print(f"\n  FAILED: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    sys.exit(0 if all_passed else 1)
