#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Pydantic models for API requests and responses.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

# ============================================================================
# LLM Provider Models
# ============================================================================


class LLMRequest(BaseModel):
    """Request model for LLM completion."""

    prompt: str = Field(
        ..., description="The prompt to send to the LLM", examples=["Explain what a SIEM is in cybersecurity"]
    )
    provider: Literal["openai", "anthropic", "together", "ollama"] | None = Field(
        None, description="LLM provider to use. If not specified, uses default from settings.", examples=["openai"]
    )
    model: str | None = Field(
        None,
        description="Model to use. If not specified, uses default for the provider. Examples: 'gpt-4', 'claude-3-5-sonnet-20241022', 'llama3'",
        examples=["gpt-4-turbo-preview"],
    )
    temperature: float | None = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0). Higher values make output more random.",
        examples=[0.7],
    )
    max_tokens: int | None = Field(None, ge=1, le=8000, description="Maximum tokens to generate", examples=[1000])
    system_message: str | None = Field(
        None,
        description="System message to set context for the LLM",
        examples=["You are a cybersecurity expert helping train security professionals."],
    )


class LLMResponse(BaseModel):
    """Response model from LLM completion."""

    content: str
    provider: str
    model: str
    usage: dict[str, int] | None = None


# ============================================================================
# Content Policy Models
# ============================================================================


class ContentPolicy(BaseModel):
    """Content policy configuration."""

    level: Literal["defensive", "educational", "advanced", "unrestricted"] = "educational"
    description: str = ""
    allowed_categories: list[str] = Field(default_factory=list)
    blocked_categories: list[str] = Field(default_factory=list)


class ContentCheckRequest(BaseModel):
    """Request to check content against policy."""

    content: str
    policy: ContentPolicy


class ContentCheckResponse(BaseModel):
    """Response from content safety check."""

    is_safe: bool
    policy_level: str
    violations: list[str] = Field(default_factory=list)
    message: str | None = None


# ============================================================================
# Cybersecurity Scenario Models
# ============================================================================


class Vulnerability(BaseModel):
    """A security vulnerability or misconfiguration."""

    id: str
    name: str
    description: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    cve_id: str | None = None
    affected_systems: list[str] = Field(default_factory=list)
    exploitation_complexity: Literal["easy", "moderate", "hard"]
    remediation: str


class ThreatActor(BaseModel):
    """A threat actor profile."""

    id: str
    name: str
    description: str
    motivation: str
    sophistication: Literal["nation-state", "organized-crime", "hacktivist", "script-kiddie"]
    ttps: list[str] = Field(default_factory=list)  # Tactics, Techniques, Procedures
    attack_techniques: list[str] = Field(default_factory=list)  # MITRE ATT&CK technique IDs
    targets: list[str] = Field(default_factory=list)


class System(BaseModel):
    """An IT system or network component."""

    id: str
    name: str
    description: str
    type: Literal["server", "workstation", "network-device", "application", "database", "cloud-service"]
    os: str | None = None
    services: list[str] = Field(default_factory=list)
    vulnerabilities: list[Vulnerability] = Field(default_factory=list)
    security_controls: list[str] = Field(default_factory=list)
    criticality: Literal["critical", "high", "medium", "low"]


class Department(BaseModel):
    """A business department with IT assets."""

    id: str
    name: str
    description: str
    business_function: str
    systems: list[System] = Field(default_factory=list)
    data_classification: Literal["public", "internal", "confidential", "restricted"]
    compliance_requirements: list[str] = Field(default_factory=list)


class Organization(BaseModel):
    """A complete organization with IT infrastructure."""

    id: str
    name: str
    description: str
    industry: str
    size: Literal["small", "medium", "large", "enterprise"]
    departments: list[Department] = Field(default_factory=list)
    threat_actors: list[ThreatActor] = Field(default_factory=list)
    security_posture: Literal["immature", "developing", "defined", "managed", "optimized"]
    compliance_frameworks: list[str] = Field(default_factory=list)


# ============================================================================
# Phase 5B: Enhanced Game Mechanics Models (defined early for GameState)
# ============================================================================


class ImpactEvent(BaseModel):
    """A business impact event."""

    timestamp: datetime
    event_type: Literal["downtime", "data_loss", "compliance", "reputation"]
    system_id: str | None = None
    cost: float
    description: str
    severity: Literal["low", "medium", "high", "critical"]


class ExecutiveMetrics(BaseModel):
    """Executive-level business impact metrics."""

    stock_price_impact_pct: float = 0.0
    customer_churn_rate: float = 0.0
    regulatory_risk_level: Literal["low", "medium", "high", "critical"] = "low"
    media_exposure_level: Literal["none", "local", "national", "international"] = "none"
    estimated_recovery_time_days: int = 0
    board_notification_required: bool = False
    sec_disclosure_required: bool = False
    notification_obligations: list[str] = Field(default_factory=list)


class BusinessImpact(BaseModel):
    """Business impact tracking for an incident."""

    downtime_cost: float = 0.0  # Cumulative downtime cost
    downtime_hours: float = 0.0  # Total downtime hours
    data_loss_cost: float = 0.0  # Data breach costs
    records_compromised: int = 0  # Number of records
    compliance_penalties: dict[str, float] = Field(default_factory=dict)  # Framework: penalty
    reputation_damage: float = 0.0  # Brand/customer impact
    total_cost: float = 0.0  # Cumulative total
    impact_description: str = "No significant impact yet"
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    executive_metrics: ExecutiveMetrics | None = None


class Timer(BaseModel):
    """A countdown timer for an objective or event."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    duration_seconds: int
    remaining_seconds: int
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_critical: bool = False
    on_expiry_event: str  # Description of what happens
    related_objective_id: str | None = None

    @property
    def expires_at(self) -> datetime:
        """Calculate expiration time."""
        return self.started_at + timedelta(seconds=self.duration_seconds)

    @property
    def is_expired(self) -> bool:
        """Check if timer has expired."""
        return self.remaining_seconds <= 0


class EscalationRule(BaseModel):
    """A rule for automatic threat escalation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger_time_minutes: int
    action: Literal["threat_escalate", "system_degrade", "spread", "alert"]
    target_id: str | None = None  # System ID or threat ID
    severity_increase: int = 10
    description: str
    triggered: bool = False


class ResourcePool(BaseModel):
    """Resource management for the player."""

    action_points: int = 10
    max_action_points: int = 10
    points_per_minute: float = 0.5
    budget_remaining: float = 100000.0  # Starting budget
    budget_total: float = 100000.0
    staff_available: int = 5
    tools_on_cooldown: dict[str, datetime] = Field(default_factory=dict)  # tool: available_at
    last_regeneration: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ActionCost(BaseModel):
    """Cost of performing an action."""

    points: int
    budget: float
    cooldown_seconds: int
    requires_staff: int = 1


class CampaignStage(BaseModel):
    """A stage in a multi-stage threat campaign."""

    stage_number: int
    name: str
    description: str
    duration_minutes: int
    systems_targeted: list[str] = Field(default_factory=list)
    ttps_used: list[str] = Field(default_factory=list)
    detection_difficulty: Literal["easy", "medium", "hard"]
    completed: bool = False
    started_at: datetime | None = None


class ThreatCampaign(BaseModel):
    """A multi-stage threat actor campaign."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    threat_actor_id: str
    current_stage: int = 0
    total_stages: int
    stages: list[CampaignStage]
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed: bool = False
    success: bool = False  # Did threat achieve objective?
    intelligence_gathered: list[str] = Field(default_factory=list)  # What player knows


# ============================================================================
# War Game Session Models
# ============================================================================


class Tool(BaseModel):
    """A security tool available to the player."""

    name: str
    category: Literal["siem", "ids-ips", "forensics", "vulnerability-scanner", "edr", "firewall", "other"]
    description: str
    requires_access_level: Literal["user", "admin", "root"]


class Objective(BaseModel):
    """A training objective with success criteria."""

    id: str
    description: str
    type: Literal["detect", "contain", "mitigate", "investigate", "protect", "report"]
    success_criteria: str
    time_limit_minutes: int | None = None
    points: int = 25
    difficulty: Literal["easy", "medium", "hard"]
    related_systems: list[str] = Field(default_factory=list)
    related_threats: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    status: Literal["pending", "in-progress", "completed", "failed"] = "pending"


class Inventory(BaseModel):
    """Player's available tools and resources."""

    tools: dict[str, int] = Field(default_factory=dict)  # tool_name: quantity
    access_levels: list[str] = Field(default_factory=list)  # user, admin, root
    credentials: list[str] = Field(default_factory=list)


class IncidentEvent(BaseModel):
    """A single event in the incident timeline."""

    timestamp: datetime
    event_type: Literal["detection", "action", "consequence", "escalation"]
    description: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    actor: str  # "system", "player", "threat_actor"


class SystemState(BaseModel):
    """Current state of a system during gameplay."""

    system_id: str
    status: Literal["online", "offline", "compromised", "recovering", "patched"]
    health: int = Field(100, ge=0, le=100)  # 0-100 health percentage
    last_update: datetime
    affected_services: list[str] = Field(default_factory=list)
    notes: str | None = None  # Additional context about the state


class ThreatActorState(BaseModel):
    """Current state of a threat actor during gameplay."""

    threat_actor_id: str
    status: Literal["active", "contained", "eliminated", "dormant"]
    current_tactics: list[str] = Field(default_factory=list)  # Currently employed TTPs
    active_techniques: list[str] = Field(default_factory=list)  # Active MITRE ATT&CK IDs
    detected_techniques: list[str] = Field(default_factory=list)  # ATT&CK IDs player detected
    mitigated_techniques: list[str] = Field(default_factory=list)  # ATT&CK IDs player mitigated
    systems_compromised: list[str] = Field(default_factory=list)  # Compromised system IDs
    detection_level: int = Field(0, ge=0, le=100)  # How aware they are of being detected
    aggression_level: int = Field(50, ge=0, le=100)  # How aggressively they're acting
    last_action: str | None = None  # Description of last action taken
    last_update: datetime
    notes: str | None = None  # Additional context


class GameState(BaseModel):
    """Current state of a war gaming session."""

    session_id: str
    organization: Organization
    current_scenario: str
    player_role: Literal["soc-analyst", "incident-responder", "security-engineer", "ciso", "mixed"]
    inventory: Inventory
    incident_timeline: list[IncidentEvent] = Field(default_factory=list)
    score: int = 0
    time_elapsed: int = 0  # minutes
    objectives: list[Objective] = Field(default_factory=list)  # Active objectives
    objectives_completed: list[str] = Field(default_factory=list)  # Legacy support
    objectives_failed: list[str] = Field(default_factory=list)  # Legacy support
    system_states: dict[str, SystemState] = Field(default_factory=dict)  # system_id: state
    threat_states: dict[str, ThreatActorState] = Field(default_factory=dict)  # threat_id: state
    status: Literal["in-progress", "completed", "failed"]
    # Phase 5B: Enhanced Game Mechanics
    business_impact: BusinessImpact | None = None  # Business impact tracking
    impact_events: list[ImpactEvent] = Field(default_factory=list)  # Impact event history
    timers: list[Timer] = Field(default_factory=list)  # Active countdown timers
    escalation_rules: list[EscalationRule] = Field(default_factory=list)  # Auto-escalation rules
    resource_pool: ResourcePool | None = None  # Resource management
    active_campaigns: list[ThreatCampaign] = Field(default_factory=list)  # Multi-stage campaigns
    game_started_at: datetime | None = None  # When game actually started


class PlayerAction(BaseModel):
    """A player action in the war game."""

    action: str
    game_state: GameState
    content_policy: ContentPolicy | None = None


class GameResponse(BaseModel):
    """Response to a player action."""

    narrative: str
    game_state: GameState
    inventory_changes: dict[str, int] | None = None
    new_events: list[IncidentEvent] = Field(default_factory=list)
    hints: list[str] | None = None


# ============================================================================
# Scenario Generation Models
# ============================================================================


class GenerateOrganizationRequest(BaseModel):
    """Request to generate an organization."""

    industry: str | None = None
    size: Literal["small", "medium", "large", "enterprise"] | None = None
    complexity: Literal["basic", "moderate", "complex"] = "moderate"
    focus_areas: list[str] | None = None  # e.g., ["ransomware", "insider-threat"]


class GenerateScenarioRequest(BaseModel):
    """Request to generate a complete training scenario."""

    organization_id: str | None = None
    scenario_type: Literal["incident-response", "threat-hunting", "vulnerability-management", "compliance-audit"]
    difficulty: Literal["beginner", "intermediate", "advanced", "expert"]
    duration_minutes: int = Field(60, ge=15, le=480)
    player_role: Literal["soc-analyst", "incident-responder", "security-engineer", "ciso", "mixed"]
    learning_objectives: list[str] | None = None


# Phase 4: Enhanced Safety & Policies Models


class ActionCheckResult(BaseModel):
    """Result of action content check."""

    is_allowed: bool
    reason: str | None = None
    violations: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    suggested_alternative: str | None = None
    pattern_matches: int = 0


class ValidationResult(BaseModel):
    """Result of content validation."""

    is_safe: bool
    can_sanitize: bool = False
    violations: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "low"
    reason: str | None = None
    sanitized_content: str | None = None


class AuditLog(BaseModel):
    """Audit log entry for policy checks and violations."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: Literal["policy_check", "violation", "filter", "sanitization"]
    severity: Literal["info", "warning", "error", "critical"]
    policy_level: str
    content_hash: str  # SHA256 hash for privacy
    result: str  # "allowed", "blocked", "sanitized"
    violations: list[str] = Field(default_factory=list)
    action_taken: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyViolation(BaseModel):
    """Policy violation record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    severity: Literal["low", "medium", "high", "critical"]
    violation_type: str
    content_hash: str
    policy_level: str
    user_id: str | None = None
    session_id: str | None = None
    action_taken: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ViolationResponse(BaseModel):
    """Response to a policy violation."""

    action: Literal["allow", "warn", "block", "escalate"]
    message: str
    educational_content: str | None = None
    suggested_alternative: str | None = None
    requires_review: bool = False


class ComplianceReport(BaseModel):
    """Compliance report for a time period."""

    period_start: datetime
    period_end: datetime
    total_checks: int
    total_violations: int
    violation_rate: float
    violations_by_type: dict[str, int] = Field(default_factory=dict)
    violations_by_severity: dict[str, int] = Field(default_factory=dict)
    policy_level_distribution: dict[str, int] = Field(default_factory=dict)
    top_violation_patterns: list[dict[str, Any]] = Field(default_factory=list)


class FilterConfig(BaseModel):
    """Content filter configuration."""

    enable_credential_detection: bool = True
    enable_pii_detection: bool = True
    enable_exploit_detection: bool = True
    enable_sensitive_detection: bool = True
    redaction_style: Literal["remove", "mask", "replace"] = "mask"
    custom_patterns: dict[str, list[str]] = Field(default_factory=dict)
    allowlist: list[str] = Field(default_factory=list)


# ============================================================================
# Phase 6: Analytics & After Action Review Models
# ============================================================================


class DecisionEvaluation(BaseModel):
    """Evaluation of a single player decision during a game session."""

    action: str
    timestamp: datetime
    context: str = ""
    quality_score: int = Field(50, ge=0, le=100)
    impact: Literal["positive", "neutral", "negative"] = "neutral"
    reasoning: str = ""
    better_alternative: str | None = None
    category: Literal["detection", "containment", "mitigation", "communication", "investigation", "other"] = "other"


class AlternativePath(BaseModel):
    """A suggested alternative action path at a key decision point."""

    decision_point: str
    original_action: str
    suggested_action: str
    expected_outcome: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class PerformanceMetric(BaseModel):
    """A single measurable performance metric."""

    metric_type: str
    value: float
    unit: str = ""
    benchmark: float | None = None
    percentile: int | None = None


class AARReport(BaseModel):
    """After Action Review report for a completed game session."""

    session_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    summary: str = ""
    timeline_analysis: list[DecisionEvaluation] = Field(default_factory=list)
    alternative_paths: list[AlternativePath] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    overall_grade: str = "C"
    score_breakdown: dict[str, int] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    ai_feedback: str = ""


class PerformanceDashboard(BaseModel):
    """Aggregated performance data across sessions."""

    sessions_completed: int = 0
    average_score: float = 0.0
    best_score: int = 0
    total_play_time_minutes: int = 0
    metrics: list[PerformanceMetric] = Field(default_factory=list)
    trends: dict[str, list[float]] = Field(default_factory=dict)
    skill_gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AARRequest(BaseModel):
    """Request to generate an After Action Review."""

    session_id: str
    include_alternatives: bool = True
    include_ai_feedback: bool = True
