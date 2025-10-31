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
    objectives_completed: List[str] = Field(default_factory=list)
    objectives_failed: List[str] = Field(default_factory=list)
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
