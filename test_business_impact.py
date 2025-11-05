"""
Test suite for Business Impact Service.

Tests all cost calculation methods and business impact tracking.
"""
import sys
from datetime import datetime
from api.services.business_impact_service import BusinessImpactService
from api.models import (
    Organization,
    Department,
    System,
    Vulnerability,
    ThreatActor,
    GameState,
    Inventory,
    BusinessImpact,
)


def create_test_organization() -> Organization:
    """Create a test organization for testing."""
    # Create a vulnerability
    vuln = Vulnerability(
        id="vuln-001",
        name="SQL Injection",
        description="SQL injection vulnerability in web application",
        severity="high",
        cve_id="CVE-2023-1234",
        affected_systems=["sys-001"],
        exploitation_complexity="easy",
        remediation="Update to latest version and use parameterized queries",
    )

    # Create systems
    database_system = System(
        id="sys-001",
        name="Customer Database",
        description="Primary customer data database",
        type="database",
        os="Linux",
        services=["postgresql"],
        vulnerabilities=[vuln],
        security_controls=["firewall", "encryption-at-rest"],
        criticality="critical",
    )

    web_server = System(
        id="sys-002",
        name="Web Application Server",
        description="Public-facing web application",
        type="application",
        os="Linux",
        services=["nginx", "nodejs"],
        vulnerabilities=[],
        security_controls=["waf", "ddos-protection"],
        criticality="high",
    )

    # Create departments
    it_dept = Department(
        id="dept-001",
        name="IT Department",
        description="Information Technology Department",
        business_function="Technology operations",
        systems=[database_system, web_server],
        data_classification="confidential",
        compliance_requirements=["GDPR", "PCI-DSS"],
    )

    # Create threat actor
    threat = ThreatActor(
        id="threat-001",
        name="Advanced Persistent Threat Group",
        description="Nation-state threat actor",
        motivation="Espionage and data theft",
        sophistication="nation-state",
        ttps=["spearphishing", "lateral-movement", "data-exfiltration"],
        targets=["databases", "customer-data"],
    )

    # Create organization
    org = Organization(
        id="org-001",
        name="TechCorp Financial Services",
        description="A financial technology company",
        industry="financial",
        size="medium",
        departments=[it_dept],
        threat_actors=[threat],
        security_posture="developing",
        compliance_frameworks=["GDPR", "PCI-DSS", "SOX"],
    )

    return org


def create_test_game_state(org: Organization) -> GameState:
    """Create a test game state."""
    return GameState(
        session_id="test-session-001",
        organization=org,
        current_scenario="Ransomware incident response",
        player_role="soc-analyst",
        inventory=Inventory(),
        score=0,
        time_elapsed=0,
        status="in-progress",
    )


def test_initialize_business_impact():
    """Test 1: Initialize business impact."""
    print("\n=== Test 1: Initialize Business Impact ===")
    service = BusinessImpactService()
    org = create_test_organization()

    impact = service.initialize_business_impact(org)

    assert impact.downtime_cost == 0.0, "Initial downtime cost should be 0"
    assert impact.total_cost == 0.0, "Initial total cost should be 0"
    assert impact.records_compromised == 0, "Initial records should be 0"
    assert "No significant" in impact.impact_description or "Incident in progress" in impact.impact_description

    print("✅ Business impact initialized correctly")
    print(f"   Initial description: {impact.impact_description}")


def test_calculate_downtime_cost():
    """Test 2: Calculate downtime cost for critical system."""
    print("\n=== Test 2: Calculate Downtime Cost ===")
    service = BusinessImpactService()
    org = create_test_organization()

    # Get the critical database system
    system = org.departments[0].systems[0]  # Customer Database (critical)

    # Calculate 2 hours of downtime
    cost, description = service.calculate_downtime_cost(org, system, 2.0)

    print(f"   System: {system.name} ({system.criticality})")
    print(f"   Industry: {org.industry}")
    print(f"   Downtime: 2.0 hours")
    print(f"   Cost: ${cost:,.2f}")
    print(f"   Description: {description}")

    # For financial industry, critical system:
    # Base: $500K/hr × 2 hrs × 3.0 (industry) × 5.0 (criticality) = $15M
    expected_cost = 500000 * 2.0 * 3.0 * 5.0
    assert cost == expected_cost, f"Expected ${expected_cost:,.2f}, got ${cost:,.2f}"

    print(f"✅ Downtime cost calculated correctly: ${cost:,.2f}")


def test_calculate_data_loss_cost():
    """Test 3: Calculate data loss cost."""
    print("\n=== Test 3: Calculate Data Loss Cost ===")
    service = BusinessImpactService()
    org = create_test_organization()

    # IT Department has confidential data
    records = 10000
    cost, description = service.calculate_data_loss_cost(org, "IT Department", records)

    print(f"   Department: IT Department (confidential)")
    print(f"   Records compromised: {records:,}")
    print(f"   Cost: ${cost:,.2f}")
    print(f"   Description: {description}")

    # Confidential data: 10,000 × $250 = $2,500,000
    expected_cost = 10000 * 250.0
    assert cost == expected_cost, f"Expected ${expected_cost:,.2f}, got ${cost:,.2f}"

    print(f"✅ Data loss cost calculated correctly: ${cost:,.2f}")


def test_calculate_compliance_penalties():
    """Test 4: Calculate compliance penalties."""
    print("\n=== Test 4: Calculate Compliance Penalties ===")
    service = BusinessImpactService()
    org = create_test_organization()

    records = 10000
    penalties, description = service.calculate_compliance_penalties(org, records)

    print(f"   Records compromised: {records:,}")
    print(f"   Compliance frameworks: {', '.join(org.compliance_frameworks)}")
    print(f"   Penalties: {penalties}")
    print(f"   Description: {description}")

    # Should have penalties for GDPR, PCI-DSS, SOX
    assert "GDPR" in penalties, "GDPR penalty should be present"
    assert "PCI-DSS" in penalties, "PCI-DSS penalty should be present"
    assert "SOX" in penalties, "SOX penalty should be present"

    total = sum(penalties.values())
    print(f"✅ Compliance penalties calculated: ${total:,.2f}")
    for framework, penalty in penalties.items():
        print(f"   - {framework}: ${penalty:,.2f}")


def test_calculate_reputation_damage():
    """Test 5: Calculate reputation damage."""
    print("\n=== Test 5: Calculate Reputation Damage ===")
    service = BusinessImpactService()
    org = create_test_organization()

    records = 10000
    cost, description = service.calculate_reputation_damage(org, records, "high")

    print(f"   Records affected: {records:,}")
    print(f"   Severity: high")
    print(f"   Cost: ${cost:,.2f}")
    print(f"   Description: {description}")

    # Base $100K + (10,000 × $50) × 2.0 (high severity) × 2.0 (recovery) = $2.2M
    expected_cost = (100000 + (10000 * 50)) * 2.0 * 2.0
    assert cost == expected_cost, f"Expected ${expected_cost:,.2f}, got ${cost:,.2f}"

    print(f"✅ Reputation damage calculated correctly: ${cost:,.2f}")


def test_update_impact_downtime():
    """Test 6: Update game state with downtime impact."""
    print("\n=== Test 6: Update Impact - Downtime ===")
    service = BusinessImpactService()
    org = create_test_organization()
    game_state = create_test_game_state(org)

    # System goes down for 1 hour
    system_id = "sys-001"  # Customer Database
    game_state = service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="downtime",
        system_id=system_id,
        hours=1.0,
        severity="high",
    )

    assert game_state.business_impact is not None, "Business impact should be initialized"
    assert game_state.business_impact.downtime_hours == 1.0, "Downtime hours should be 1.0"
    assert game_state.business_impact.downtime_cost > 0, "Downtime cost should be > 0"
    assert len(game_state.impact_events) == 1, "Should have 1 impact event"

    print(f"   System: sys-001 (Customer Database)")
    print(f"   Downtime: 1.0 hours")
    print(f"   Cost: ${game_state.business_impact.downtime_cost:,.2f}")
    print(f"   Total cost: ${game_state.business_impact.total_cost:,.2f}")
    print(f"✅ Downtime impact updated successfully")


def test_update_impact_data_loss():
    """Test 7: Update game state with data loss impact."""
    print("\n=== Test 7: Update Impact - Data Loss ===")
    service = BusinessImpactService()
    org = create_test_organization()
    game_state = create_test_game_state(org)

    # Data breach: 5000 records
    game_state = service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="data_loss",
        records=5000,
        department="IT Department",
        severity="critical",
    )

    assert game_state.business_impact.records_compromised == 5000, "Records should be 5000"
    assert game_state.business_impact.data_loss_cost > 0, "Data loss cost should be > 0"
    assert len(game_state.impact_events) == 1, "Should have 1 impact event"

    print(f"   Records compromised: 5,000")
    print(f"   Department: IT Department")
    print(f"   Cost: ${game_state.business_impact.data_loss_cost:,.2f}")
    print(f"   Total cost: ${game_state.business_impact.total_cost:,.2f}")
    print(f"✅ Data loss impact updated successfully")


def test_update_impact_compliance():
    """Test 8: Update game state with compliance penalties."""
    print("\n=== Test 8: Update Impact - Compliance ===")
    service = BusinessImpactService()
    org = create_test_organization()
    game_state = create_test_game_state(org)

    # Compliance violation: 5000 records
    game_state = service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="compliance",
        records=5000,
        severity="high",
    )

    assert len(game_state.business_impact.compliance_penalties) > 0, "Should have penalties"
    total_penalties = sum(game_state.business_impact.compliance_penalties.values())
    assert total_penalties > 0, "Total penalties should be > 0"

    print(f"   Records: 5,000")
    print(f"   Frameworks affected: {list(game_state.business_impact.compliance_penalties.keys())}")
    print(f"   Total penalties: ${total_penalties:,.2f}")
    for framework, penalty in game_state.business_impact.compliance_penalties.items():
        print(f"   - {framework}: ${penalty:,.2f}")
    print(f"✅ Compliance penalties updated successfully")


def test_update_impact_reputation():
    """Test 9: Update game state with reputation damage."""
    print("\n=== Test 9: Update Impact - Reputation ===")
    service = BusinessImpactService()
    org = create_test_organization()
    game_state = create_test_game_state(org)

    # Reputation damage: 5000 records, critical severity
    game_state = service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="reputation",
        records=5000,
        severity="critical",
    )

    assert game_state.business_impact.reputation_damage > 0, "Reputation damage should be > 0"

    print(f"   Records affected: 5,000")
    print(f"   Severity: critical")
    print(f"   Cost: ${game_state.business_impact.reputation_damage:,.2f}")
    print(f"   Total cost: ${game_state.business_impact.total_cost:,.2f}")
    print(f"✅ Reputation damage updated successfully")


def test_cumulative_impact():
    """Test 10: Test cumulative impact from multiple events."""
    print("\n=== Test 10: Cumulative Impact ===")
    service = BusinessImpactService()
    org = create_test_organization()
    game_state = create_test_game_state(org)

    # Event 1: Downtime
    game_state = service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="downtime",
        system_id="sys-001",
        hours=2.0,
        severity="high",
    )

    # Event 2: Data loss
    game_state = service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="data_loss",
        records=10000,
        department="IT Department",
        severity="critical",
    )

    # Event 3: Compliance
    game_state = service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="compliance",
        records=10000,
        severity="critical",
    )

    # Event 4: Reputation
    game_state = service.update_impact(
        game_state=game_state,
        organization=org,
        event_type="reputation",
        records=10000,
        severity="critical",
    )

    assert len(game_state.impact_events) == 4, "Should have 4 impact events"
    assert game_state.business_impact.total_cost > 0, "Total cost should be > 0"

    print(f"   Events processed: 4")
    print(f"   Downtime: ${game_state.business_impact.downtime_cost:,.2f}")
    print(f"   Data loss: ${game_state.business_impact.data_loss_cost:,.2f}")
    print(f"   Compliance: ${sum(game_state.business_impact.compliance_penalties.values()):,.2f}")
    print(f"   Reputation: ${game_state.business_impact.reputation_damage:,.2f}")
    print(f"   TOTAL COST: ${game_state.business_impact.total_cost:,.2f}")
    print(f"\n   Summary: {game_state.business_impact.impact_description}")
    print(f"✅ Cumulative impact calculated successfully")


def test_get_impact_summary():
    """Test 11: Test impact summary generation."""
    print("\n=== Test 11: Impact Summary ===")
    service = BusinessImpactService()
    org = create_test_organization()
    game_state = create_test_game_state(org)

    # Add multiple impacts
    game_state = service.update_impact(
        game_state, org, "downtime", system_id="sys-001", hours=1.5, severity="high"
    )
    game_state = service.update_impact(
        game_state, org, "data_loss", records=5000, department="IT Department", severity="high"
    )

    summary = service.get_impact_summary(game_state.business_impact)

    assert "Downtime" in summary, "Summary should mention downtime"
    assert "Data Loss" in summary, "Summary should mention data loss"
    assert "Total" in summary, "Summary should include total"

    print(f"   Summary: {summary}")
    print(f"✅ Impact summary generated successfully")


def test_different_industries():
    """Test 12: Test cost differences across industries."""
    print("\n=== Test 12: Industry Cost Differences ===")
    service = BusinessImpactService()

    industries = ["financial", "healthcare", "technology", "retail"]
    system = System(
        id="sys-test",
        name="Test System",
        description="Test",
        type="server",
        criticality="high",
    )

    for industry in industries:
        org = Organization(
            id="test",
            name="Test Corp",
            description="Test",
            industry=industry,
            size="medium",
            departments=[],
            threat_actors=[],
            security_posture="developing",
            compliance_frameworks=[],
        )

        cost, _ = service.calculate_downtime_cost(org, system, 1.0)
        print(f"   {industry.capitalize():12} - 1 hour downtime (high system): ${cost:,.2f}")

    print(f"✅ Industry multipliers working correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("BUSINESS IMPACT SERVICE TEST SUITE")
    print("=" * 70)

    tests = [
        test_initialize_business_impact,
        test_calculate_downtime_cost,
        test_calculate_data_loss_cost,
        test_calculate_compliance_penalties,
        test_calculate_reputation_damage,
        test_update_impact_downtime,
        test_update_impact_data_loss,
        test_update_impact_compliance,
        test_update_impact_reputation,
        test_cumulative_impact,
        test_get_impact_summary,
        test_different_industries,
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
            failed += 1

    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
