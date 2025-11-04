"""
Pydantic models for API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ============================================================================
# LLM Provider Models
# ============================================================================

class LLMRequest(BaseModel):
    """Request model for LLM completion."""
    prompt: str = Field(
        ...,
        description="The prompt to send to the LLM",
        examples=["Explain what a SIEM is in cybersecurity"]
    )
    provider: Optional[Literal["openai", "anthropic", "ollama"]] = Field(
        None,
        description="LLM provider to use. If not specified, uses default from settings.",
        examples=["openai"]
    )
    model: Optional[str] = Field(
        None,
        description="Model to use. If not specified, uses default for the provider. Examples: 'gpt-4', 'claude-3-5-sonnet-20241022', 'llama3'",
        examples=["gpt-4-turbo-preview"]
    )
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0). Higher values make output more random.",
        examples=[0.7]
    )
    max_tokens: Optional[int] = Field(
        None,
        ge=1,
        le=8000,
        description="Maximum tokens to generate",
        examples=[1000]
    )
    system_message: Optional[str] = Field(
        None,
        description="System message to set context for the LLM",
        examples=["You are a cybersecurity expert helping train security professionals."]
    )


class LLMResponse(BaseModel):
    """Response model from LLM completion."""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None


# ============================================================================
# Content Policy Models
# ============================================================================

class ContentPolicy(BaseModel):
    """Content policy configuration."""
    level: Literal["defensive", "educational", "advanced", "unrestricted"] = "educational"
    description: str = ""
    allowed_categories: List[str] = Field(default_factory=list)
    blocked_categories: List[str] = Field(default_factory=list)


class ContentCheckRequest(BaseModel):
    """Request to check content against policy."""
    content: str
    policy: ContentPolicy


class ContentCheckResponse(BaseModel):
    """Response from content safety check."""
    is_safe: bool
    policy_level: str
    violations: List[str] = Field(default_factory=list)
    message: Optional[str] = None


# ============================================================================
# Cybersecurity Scenario Models
# ============================================================================

class Vulnerability(BaseModel):
    """A security vulnerability or misconfiguration."""
    id: str
    name: str
    description: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    cve_id: Optional[str] = None
    affected_systems: List[str] = Field(default_factory=list)
    exploitation_complexity: Literal["easy", "moderate", "hard"]
    remediation: str


class ThreatActor(BaseModel):
    """A threat actor profile."""
    id: str
    name: str
    description: str
    motivation: str
    sophistication: Literal["nation-state", "organized-crime", "hacktivist", "script-kiddie"]
    ttps: List[str] = Field(default_factory=list)  # Tactics, Techniques, Procedures
    targets: List[str] = Field(default_factory=list)


class System(BaseModel):
    """An IT system or network component."""
    id: str
    name: str
    description: str
    type: Literal["server", "workstation", "network-device", "application", "database", "cloud-service"]
    os: Optional[str] = None
    services: List[str] = Field(default_factory=list)
    vulnerabilities: List[Vulnerability] = Field(default_factory=list)
    security_controls: List[str] = Field(default_factory=list)
    criticality: Literal["critical", "high", "medium", "low"]


class Department(BaseModel):
    """A business department with IT assets."""
    id: str
    name: str
    description: str
    business_function: str
    systems: List[System] = Field(default_factory=list)
    data_classification: Literal["public", "internal", "confidential", "restricted"]
    compliance_requirements: List[str] = Field(default_factory=list)


class Organization(BaseModel):
    """A complete organization with IT infrastructure."""
    id: str
    name: str
    description: str
    industry: str
    size: Literal["small", "medium", "large", "enterprise"]
    departments: List[Department] = Field(default_factory=list)
    threat_actors: List[ThreatActor] = Field(default_factory=list)
    security_posture: Literal["immature", "developing", "defined", "managed", "optimized"]
    compliance_frameworks: List[str] = Field(default_factory=list)


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
    time_limit_minutes: Optional[int] = None
    points: int = 25
    difficulty: Literal["easy", "medium", "hard"]
    related_systems: List[str] = Field(default_factory=list)
    related_threats: List[str] = Field(default_factory=list)
    hints: List[str] = Field(default_factory=list)
    status: Literal["pending", "in-progress", "completed", "failed"] = "pending"


class Inventory(BaseModel):
    """Player's available tools and resources."""
    tools: Dict[str, int] = Field(default_factory=dict)  # tool_name: quantity
    access_levels: List[str] = Field(default_factory=list)  # user, admin, root
    credentials: List[str] = Field(default_factory=list)


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
    affected_services: List[str] = Field(default_factory=list)
    notes: Optional[str] = None  # Additional context about the state


class ThreatActorState(BaseModel):
    """Current state of a threat actor during gameplay."""
    threat_actor_id: str
    status: Literal["active", "contained", "eliminated", "dormant"]
    current_tactics: List[str] = Field(default_factory=list)  # Currently employed TTPs
    systems_compromised: List[str] = Field(default_factory=list)  # Compromised system IDs
    detection_level: int = Field(0, ge=0, le=100)  # How aware they are of being detected
    aggression_level: int = Field(50, ge=0, le=100)  # How aggressively they're acting
    last_action: Optional[str] = None  # Description of last action taken
    last_update: datetime
    notes: Optional[str] = None  # Additional context


class GameState(BaseModel):
    """Current state of a war gaming session."""
    session_id: str
    organization: Organization
    current_scenario: str
    player_role: Literal["soc-analyst", "incident-responder", "security-engineer", "ciso", "mixed"]
    inventory: Inventory
    incident_timeline: List[IncidentEvent] = Field(default_factory=list)
    score: int = 0
    time_elapsed: int = 0  # minutes
    objectives: List[Objective] = Field(default_factory=list)  # Active objectives
    objectives_completed: List[str] = Field(default_factory=list)  # Legacy support
    objectives_failed: List[str] = Field(default_factory=list)  # Legacy support
    system_states: Dict[str, SystemState] = Field(default_factory=dict)  # system_id: state
    threat_states: Dict[str, ThreatActorState] = Field(default_factory=dict)  # threat_id: state
    status: Literal["in-progress", "completed", "failed"]


class PlayerAction(BaseModel):
    """A player action in the war game."""
    action: str
    game_state: GameState
    content_policy: Optional[ContentPolicy] = None


class GameResponse(BaseModel):
    """Response to a player action."""
    narrative: str
    game_state: GameState
    inventory_changes: Optional[Dict[str, int]] = None
    new_events: List[IncidentEvent] = Field(default_factory=list)
    hints: Optional[List[str]] = None


# ============================================================================
# Scenario Generation Models
# ============================================================================

class GenerateOrganizationRequest(BaseModel):
    """Request to generate an organization."""
    industry: Optional[str] = None
    size: Optional[Literal["small", "medium", "large", "enterprise"]] = None
    complexity: Literal["basic", "moderate", "complex"] = "moderate"
    focus_areas: Optional[List[str]] = None  # e.g., ["ransomware", "insider-threat"]


class GenerateScenarioRequest(BaseModel):
    """Request to generate a complete training scenario."""
    organization_id: Optional[str] = None
    scenario_type: Literal["incident-response", "threat-hunting", "vulnerability-management", "compliance-audit"]
    difficulty: Literal["beginner", "intermediate", "advanced", "expert"]
    duration_minutes: int = Field(60, ge=15, le=480)
    player_role: Literal["soc-analyst", "incident-responder", "security-engineer", "ciso", "mixed"]
    learning_objectives: Optional[List[str]] = None


# Phase 4: Enhanced Safety & Policies Models

class ActionCheckResult(BaseModel):
    """Result of action content check."""
    is_allowed: bool
    reason: Optional[str] = None
    violations: List[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    suggested_alternative: Optional[str] = None
    pattern_matches: int = 0


class ValidationResult(BaseModel):
    """Result of content validation."""
    is_safe: bool
    can_sanitize: bool = False
    violations: List[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "low"
    reason: Optional[str] = None
    sanitized_content: Optional[str] = None


class AuditLog(BaseModel):
    """Audit log entry for policy checks and violations."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: Literal["policy_check", "violation", "filter", "sanitization"]
    severity: Literal["info", "warning", "error", "critical"]
    policy_level: str
    content_hash: str  # SHA256 hash for privacy
    result: str  # "allowed", "blocked", "sanitized"
    violations: List[str] = Field(default_factory=list)
    action_taken: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyViolation(BaseModel):
    """Policy violation record."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: Literal["low", "medium", "high", "critical"]
    violation_type: str
    content_hash: str
    policy_level: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    action_taken: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ViolationResponse(BaseModel):
    """Response to a policy violation."""
    action: Literal["allow", "warn", "block", "escalate"]
    message: str
    educational_content: Optional[str] = None
    suggested_alternative: Optional[str] = None
    requires_review: bool = False


class ComplianceReport(BaseModel):
    """Compliance report for a time period."""
    period_start: datetime
    period_end: datetime
    total_checks: int
    total_violations: int
    violation_rate: float
    violations_by_type: Dict[str, int] = Field(default_factory=dict)
    violations_by_severity: Dict[str, int] = Field(default_factory=dict)
    policy_level_distribution: Dict[str, int] = Field(default_factory=dict)
    top_violation_patterns: List[Dict[str, Any]] = Field(default_factory=list)


class FilterConfig(BaseModel):
    """Content filter configuration."""
    enable_credential_detection: bool = True
    enable_pii_detection: bool = True
    enable_exploit_detection: bool = True
    enable_sensitive_detection: bool = True
    redaction_style: Literal["remove", "mask", "replace"] = "mask"
    custom_patterns: Dict[str, List[str]] = Field(default_factory=dict)
    allowlist: List[str] = Field(default_factory=list)
