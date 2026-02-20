"""
Test suite for Adaptive Difficulty Service and Training Path Service.

Tests the adaptive AI subsystem:
- Player skill calculation and difficulty adjustment
- Minimum action thresholds for adjustments
- Difficulty configuration retrieval
- Skill gap analysis across multiple sessions
- Scenario recommendations based on gaps
- Training plan generation and progress tracking
"""
import sys
from datetime import datetime, timedelta, timezone
from api.models import (
    Organization, Department, System, ThreatActor,
    GameState, Objective, Inventory, IncidentEvent,
    SystemState, ThreatActorState, BusinessImpact, ResourcePool,
)


def create_test_game_state(status="completed", include_business_impact=True):
    """Create a comprehensive test game state with realistic timeline."""
    now = datetime.now(timezone.utc)
    org = Organization(
        id="org-001", name="Acme Corp",
        description="Mid-size financial services company",
        industry="Financial Services", size="medium",
        departments=[
            Department(
                id="dept-001", name="IT Operations",
                description="IT Operations Department",
                business_function="Technology",
                systems=[
                    System(id="sys-001", name="Web Server",
                           description="Primary web server", type="server",
                           criticality="high"),
                    System(id="sys-002", name="Database",
                           description="Production database", type="database",
                           criticality="critical"),
                ],
                data_classification="restricted",
            )
        ],
        threat_actors=[
            ThreatActor(
                id="threat-001", name="APT29",
                description="Nation-state actor", motivation="espionage",
                sophistication="nation-state",
                ttps=["phishing", "lateral-movement"],
                targets=["sys-001", "sys-002"],
            )
        ],
        security_posture="developing",
        compliance_frameworks=["PCI-DSS"],
    )

    timeline = [
        IncidentEvent(timestamp=now - timedelta(minutes=55),
                      event_type="detection", description="SIEM alert: suspicious login",
                      severity="high", actor="system"),
        IncidentEvent(timestamp=now - timedelta(minutes=50),
                      event_type="action", description="Check SIEM logs for alert details",
                      severity="medium", actor="player"),
        IncidentEvent(timestamp=now - timedelta(minutes=45),
                      event_type="consequence", description="Alert confirmed as brute force",
                      severity="info", actor="system"),
        IncidentEvent(timestamp=now - timedelta(minutes=40),
                      event_type="action", description="Investigate source IP and correlate",
                      severity="medium", actor="player"),
        IncidentEvent(timestamp=now - timedelta(minutes=35),
                      event_type="action", description="Block the malicious IP at firewall",
                      severity="medium", actor="player"),
        IncidentEvent(timestamp=now - timedelta(minutes=30),
                      event_type="consequence", description="IP blocked successfully",
                      severity="low", actor="system"),
        IncidentEvent(timestamp=now - timedelta(minutes=25),
                      event_type="escalation", description="Threat actor pivoted to phishing",
                      severity="high", actor="threat_actor"),
        IncidentEvent(timestamp=now - timedelta(minutes=20),
                      event_type="action", description="Monitor email gateway for phishing",
                      severity="medium", actor="player"),
        IncidentEvent(timestamp=now - timedelta(minutes=15),
                      event_type="action", description="Isolate compromised workstation",
                      severity="high", actor="player"),
        IncidentEvent(timestamp=now - timedelta(minutes=10),
                      event_type="consequence", description="Workstation isolated, movement stopped",
                      severity="low", actor="system"),
        IncidentEvent(timestamp=now - timedelta(minutes=5),
                      event_type="action", description="Notify management and escalate to CISO",
                      severity="medium", actor="player"),
    ]

    objectives = [
        Objective(id="obj-001", description="Identify attack vector",
                  type="investigate", success_criteria="Determine initial access",
                  points=25, difficulty="easy", status="completed"),
        Objective(id="obj-002", description="Contain the breach",
                  type="contain", success_criteria="Isolate compromised systems",
                  points=50, difficulty="medium", status="completed"),
        Objective(id="obj-003", description="Notify stakeholders",
                  type="report", success_criteria="Alert management chain",
                  points=15, difficulty="easy", status="completed"),
        Objective(id="obj-004", description="Restore affected systems",
                  type="mitigate", success_criteria="Bring systems back online",
                  points=40, difficulty="hard", status="failed"),
    ]

    game_state = GameState(
        session_id="session_test001", organization=org,
        current_scenario="incident-response", player_role="soc-analyst",
        inventory=Inventory(tools={"siem": 1, "firewall": 1},
                            access_levels=["user", "admin"]),
        incident_timeline=timeline, score=75, time_elapsed=55,
        objectives=objectives,
        system_states={
            "sys-001": SystemState(system_id="sys-001", status="recovering",
                                   health=60, last_update=now,
                                   affected_services=["web"]),
            "sys-002": SystemState(system_id="sys-002", status="online",
                                   health=95, last_update=now),
        },
        threat_states={
            "threat-001": ThreatActorState(
                threat_actor_id="threat-001", status="contained",
                detection_level=80, aggression_level=30, last_update=now),
        },
        status=status,
        game_started_at=now - timedelta(minutes=55),
    )

    if include_business_impact:
        game_state.business_impact = BusinessImpact(
            downtime_cost=25000.0, downtime_hours=2.0, total_cost=35000.0,
            impact_description="Moderate business impact from 2-hour partial outage",
        )
        game_state.resource_pool = ResourcePool(
            action_points=3, max_action_points=10,
            budget_remaining=65000.0, budget_total=100000.0,
            staff_available=3,
        )
    return game_state


def test_adaptive_difficulty():
    """Tests 1-6: AdaptiveDifficultyService tests."""
    from api.services.adaptive_difficulty_service import AdaptiveDifficultyService

    print("\n" + "=" * 70)
    print("ADAPTIVE DIFFICULTY SERVICE TESTS")
    print("=" * 70)

    svc = AdaptiveDifficultyService()
    game_state = create_test_game_state()

    # Test 1: Calculate player skill
    print("\nTest 1: Calculate player skill")
    skill = svc.calculate_player_skill(game_state)
    assert "overall_skill" in skill, "Missing overall_skill key"
    assert "category_skills" in skill, "Missing category_skills key"
    assert "trend" in skill, "Missing trend key"
    assert "recommended_difficulty" in skill, "Missing recommended_difficulty key"
    assert 0 <= skill["overall_skill"] <= 100, f"overall_skill {skill['overall_skill']} out of range"
    assert isinstance(skill["category_skills"], dict)
    print(f"  PASS - Skill profile: overall={skill['overall_skill']}, "
          f"trend={skill['trend']}, rec={skill['recommended_difficulty']}")

    # Test 2: Adjust difficulty from medium
    print("\nTest 2: Adjust difficulty from medium")
    adj = svc.adjust_difficulty(game_state, "medium")
    for key in ("new_difficulty", "threat_aggression_modifier", "timer_modifier",
                "hint_availability", "resource_modifier", "explanation"):
        assert key in adj, f"Missing key: {key}"
    assert adj["new_difficulty"] in ("easy", "medium", "hard")
    assert isinstance(adj["hint_availability"], bool)
    assert isinstance(adj["explanation"], str) and len(adj["explanation"]) > 0
    print(f"  PASS - Adjustment: {adj['new_difficulty']}, hints={adj['hint_availability']}")

    # Test 3: should_adjust returns False with < 3 player actions
    print("\nTest 3: should_adjust with < 3 player actions")
    sparse_state = create_test_game_state()
    sparse_state.incident_timeline = [
        IncidentEvent(timestamp=datetime.now(timezone.utc), event_type="action",
                      description="Check logs", severity="medium", actor="player"),
    ]
    sparse_state.time_elapsed = 10
    svc_fresh = AdaptiveDifficultyService()
    assert svc_fresh.should_adjust(sparse_state) is False, "Should be False with < 3 actions"
    print("  PASS - Correctly returns False for insufficient actions")

    # Test 4: should_adjust returns True with 3+ actions and enough time
    print("\nTest 4: should_adjust with 3+ actions and elapsed time")
    assert svc_fresh.should_adjust(game_state) is True, "Should be True with 6 actions and 55 min"
    print("  PASS - Correctly returns True for sufficient actions and time")

    # Test 5: get_difficulty_config for each level
    print("\nTest 5: Difficulty config for easy/medium/hard")
    expected_keys = {"action_point_bonus", "timer_multiplier", "threat_aggression_cap",
                     "hints_enabled", "resource_multiplier"}
    for level in ("easy", "medium", "hard"):
        config = svc.get_difficulty_config(level)
        assert set(config.keys()) == expected_keys, f"{level} config missing keys"
    print("  PASS - All difficulty configs have correct keys")

    # Test 6: category_skills has all 5 categories
    print("\nTest 6: Skill categories completeness")
    expected_cats = {"detection", "containment", "mitigation", "communication", "investigation"}
    assert set(skill["category_skills"].keys()) == expected_cats, (
        f"Expected {expected_cats}, got {set(skill['category_skills'].keys())}")
    for cat, val in skill["category_skills"].items():
        assert 0 <= val <= 100, f"Category {cat} score {val} out of range"
    print(f"  PASS - All 5 categories present: {list(skill['category_skills'].keys())}")

    print("\n  All Adaptive Difficulty tests PASSED")


def test_training_path():
    """Tests 7-12: TrainingPathService tests."""
    from api.services.training_path_service import TrainingPathService

    print("\n" + "=" * 70)
    print("TRAINING PATH SERVICE TESTS")
    print("=" * 70)

    svc = TrainingPathService()
    gs1 = create_test_game_state()
    gs2 = create_test_game_state()
    gs2.session_id = "session_test002"
    gs2.score = 90
    gs2.time_elapsed = 40
    sessions = [gs1, gs2]

    # Test 7: Analyze skill gaps
    print("\nTest 7: Analyze skill gaps across sessions")
    gaps = svc.analyze_skill_gaps(sessions)
    assert isinstance(gaps, list) and len(gaps) > 0, "Should return non-empty list"
    for gap in gaps:
        for key in ("skill_area", "current_level", "target_level", "gap",
                     "priority", "recommended_scenarios"):
            assert key in gap, f"Missing key: {key}"
        assert gap["priority"] in ("high", "medium", "low")
        assert isinstance(gap["recommended_scenarios"], list)
        assert gap["gap"] >= 0
    print(f"  PASS - Found {len(gaps)} skill areas, "
          f"{sum(1 for g in gaps if g['priority'] == 'high')} high-priority")

    # Test 8: Recommend next scenario
    print("\nTest 8: Recommend next scenario")
    rec = svc.recommend_next_scenario(gaps)
    for key in ("scenario_type", "difficulty", "focus_areas", "reasoning"):
        assert key in rec, f"Missing key: {key}"
    assert rec["difficulty"] in ("easy", "medium", "hard")
    assert isinstance(rec["focus_areas"], list) and len(rec["focus_areas"]) > 0
    assert len(rec["reasoning"]) > 0
    print(f"  PASS - Recommended: {rec['scenario_type']} ({rec['difficulty']}), "
          f"focus={rec['focus_areas']}")

    # Test 9: Build training plan
    print("\nTest 9: Build training plan")
    plan = svc.build_training_plan(sessions)
    for key in ("current_level", "target_level", "recommended_sessions",
                "estimated_sessions_to_target", "focus_priorities", "skill_profile"):
        assert key in plan, f"Missing key: {key}"
    assert isinstance(plan["recommended_sessions"], list) and len(plan["recommended_sessions"]) > 0
    assert plan["target_level"] == 80
    assert isinstance(plan["skill_profile"], dict)
    print(f"  PASS - Plan: current={plan['current_level']}, target={plan['target_level']}, "
          f"sessions={len(plan['recommended_sessions'])}")

    # Test 10: Track progress
    print("\nTest 10: Track progress")
    progress = svc.track_progress(sessions)
    for key in ("sessions_completed", "score_trend", "skill_improvements", "milestones"):
        assert key in progress, f"Missing key: {key}"
    assert progress["sessions_completed"] == 2
    assert isinstance(progress["score_trend"], list) and len(progress["score_trend"]) == 2
    assert isinstance(progress["milestones"], list) and len(progress["milestones"]) > 0
    print(f"  PASS - Progress: {progress['sessions_completed']} sessions, "
          f"{len(progress['milestones'])} milestones, scores={progress['score_trend']}")

    # Test 11: Empty sessions handled gracefully
    print("\nTest 11: Empty session lists")
    from api.services.adaptive_difficulty_service import AdaptiveDifficultyService
    empty_gaps = svc.analyze_skill_gaps([])
    assert empty_gaps == [], "analyze_skill_gaps([]) should return []"
    empty_progress = svc.track_progress([])
    assert empty_progress["sessions_completed"] == 0
    assert empty_progress["score_trend"] == []
    empty_rec = svc.recommend_next_scenario([])
    assert empty_rec["scenario_type"] == "incident-response", "Default scenario on empty gaps"
    print("  PASS - Both services handle empty sessions gracefully")

    # Test 12: Single session
    print("\nTest 12: Single session handling")
    ad_svc = AdaptiveDifficultyService()
    single = [gs1]
    single_gaps = svc.analyze_skill_gaps(single)
    assert len(single_gaps) > 0, "Should produce gaps from one session"
    single_plan = svc.build_training_plan(single)
    assert single_plan["current_level"] >= 0
    single_skill = ad_svc.calculate_player_skill(gs1)
    assert 0 <= single_skill["overall_skill"] <= 100
    single_progress = svc.track_progress(single)
    assert single_progress["sessions_completed"] == 1
    print(f"  PASS - Single session: gaps={len(single_gaps)}, "
          f"skill={single_skill['overall_skill']}, milestones={len(single_progress['milestones'])}")

    print("\n  All Training Path tests PASSED")


if __name__ == "__main__":
    print("=" * 70)
    print("ADAPTIVE AI TEST SUITE")
    print("=" * 70)

    all_passed = True
    try:
        test_adaptive_difficulty()
        test_training_path()

        print("\n" + "=" * 70)
        print("ALL ADAPTIVE AI TESTS PASSED")
        print("=" * 70)
    except Exception as e:
        print(f"\n  FAILED: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    sys.exit(0 if all_passed else 1)
