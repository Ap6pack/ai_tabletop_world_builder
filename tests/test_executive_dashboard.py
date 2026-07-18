#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Executive Dashboard metrics service."""

import pytest

from api.models.schemas import (
    BusinessImpact,
    Department,
    ExecutiveMetrics,
    GameState,
    Inventory,
    Organization,
)
from api.services.executive_dashboard_service import ExecutiveDashboardService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_org(industry="Technology", **overrides):
    """Factory for minimal Organization instances."""
    defaults = dict(
        id="org-1",
        name="Test Corp",
        description="Test",
        industry=industry,
        size="medium",
        departments=[
            Department(
                id="d1",
                name="IT",
                description="IT",
                business_function="Tech",
                systems=[],
                data_classification="internal",
                compliance_requirements=[],
            )
        ],
        threat_actors=[],
        security_posture="developing",
        compliance_frameworks=[],
    )
    defaults.update(overrides)
    return Organization(**defaults)


def make_game_state(business_impact=None, industry="Technology", **overrides):
    """Factory for minimal GameState instances."""
    org = make_org(industry=industry)
    defaults = dict(
        session_id="test-session",
        organization=org,
        current_scenario="test",
        player_role="mixed",
        inventory=Inventory(),
        status="in-progress",
        business_impact=business_impact,
    )
    defaults.update(overrides)
    return GameState(**defaults)


def make_impact(**overrides):
    """Factory for BusinessImpact with safe defaults."""
    defaults = dict(
        total_cost=0.0,
        downtime_cost=0.0,
        data_loss_cost=0.0,
        records_compromised=0,
        downtime_hours=0.0,
        reputation_damage=0.0,
        compliance_penalties={},
    )
    defaults.update(overrides)
    return BusinessImpact(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def svc():
    return ExecutiveDashboardService()


# ---------------------------------------------------------------------------
# Stock impact
# ---------------------------------------------------------------------------


def test_calculate_stock_impact_financial(svc):
    """Financial sector has higher base stock impact (5.5%)."""
    impact = make_impact(total_cost=1_000_000, records_compromised=500)
    org = make_org(industry="Financial")
    result = svc.calculate_stock_impact(impact, org)
    # Should be negative and at least the financial base of 5.5
    assert result < 0
    assert abs(result) >= 5.5


def test_calculate_stock_impact_low(svc):
    """Small breach in retail yields a modest stock dip."""
    impact = make_impact(total_cost=10_000, records_compromised=10)
    org = make_org(industry="Retail")
    result = svc.calculate_stock_impact(impact, org)
    assert result < 0
    # Retail base is 3.0, no multiplier or add-on triggers
    assert abs(result) == pytest.approx(3.0, abs=0.01)


# ---------------------------------------------------------------------------
# Customer churn
# ---------------------------------------------------------------------------


def test_customer_churn_healthcare(svc):
    """Healthcare base churn rate is 6.7%."""
    impact = make_impact(records_compromised=50)
    org = make_org(industry="Healthcare")
    result = svc.calculate_customer_churn(impact, org)
    assert result == pytest.approx(6.7, abs=0.01)


def test_customer_churn_scales_with_records(svc):
    """More records compromised raises churn above the base."""
    low = make_impact(records_compromised=100)
    high = make_impact(records_compromised=2_000_000)
    org = make_org(industry="Technology")
    churn_low = svc.calculate_customer_churn(low, org)
    churn_high = svc.calculate_customer_churn(high, org)
    assert churn_high > churn_low


# ---------------------------------------------------------------------------
# Regulatory risk
# ---------------------------------------------------------------------------


def test_regulatory_risk_low(svc):
    """No records, no penalties -> low risk."""
    impact = make_impact()
    gs = make_game_state(business_impact=impact)
    assert svc.assess_regulatory_risk(gs) == "low"


def test_regulatory_risk_critical(svc):
    """High records + multiple compliance penalties -> critical."""
    impact = make_impact(
        records_compromised=200_000,
        compliance_penalties={"GDPR": 500_000, "HIPAA": 800_000},
    )
    gs = make_game_state(business_impact=impact)
    assert svc.assess_regulatory_risk(gs) == "critical"


# ---------------------------------------------------------------------------
# Media exposure
# ---------------------------------------------------------------------------


def test_media_exposure_none(svc):
    """Small breach should have no media exposure."""
    impact = make_impact(total_cost=1_000, records_compromised=5)
    org = make_org()
    assert svc.assess_media_exposure(impact, org) == "none"


def test_media_exposure_international(svc):
    """Large cost or records -> international exposure."""
    impact = make_impact(total_cost=50_000_000, records_compromised=500_000)
    org = make_org()
    assert svc.assess_media_exposure(impact, org) == "international"


# ---------------------------------------------------------------------------
# Aggregate metrics
# ---------------------------------------------------------------------------


def test_calculate_executive_metrics(svc):
    """Full metrics calculation produces a populated ExecutiveMetrics."""
    impact = make_impact(
        total_cost=5_000_000,
        downtime_cost=1_000_000,
        data_loss_cost=2_000_000,
        records_compromised=50_000,
        downtime_hours=48,
        reputation_damage=500_000,
        compliance_penalties={"GDPR": 200_000},
    )
    gs = make_game_state(business_impact=impact)
    metrics = svc.calculate_executive_metrics(gs)

    assert isinstance(metrics, ExecutiveMetrics)
    assert metrics.stock_price_impact_pct < 0
    assert metrics.customer_churn_rate > 0
    assert metrics.regulatory_risk_level in ("low", "medium", "high", "critical")
    assert metrics.media_exposure_level in ("none", "local", "national", "international")
    assert metrics.estimated_recovery_time_days > 0


# ---------------------------------------------------------------------------
# Board report
# ---------------------------------------------------------------------------


def test_generate_board_report(svc):
    """Board report contains all required top-level sections."""
    impact = make_impact(
        total_cost=2_000_000,
        records_compromised=10_000,
        downtime_hours=24,
        compliance_penalties={"PCI-DSS": 100_000},
    )
    gs = make_game_state(business_impact=impact)
    report = svc.generate_board_report(gs)

    expected_keys = {
        "report_generated_at",
        "organization",
        "industry",
        "incident_summary",
        "financial_impact",
        "customer_impact",
        "regulatory_status",
        "recovery_timeline",
        "recommendations",
    }
    assert expected_keys.issubset(report.keys())
    assert len(report["recommendations"]) >= 3
