"""Multi-team exercise data models."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid

# Import shared models
from api.models.schemas import GameState, Objective, IncidentEvent


class InjectType(str, Enum):
    """Types of crisis injects."""
    NEWS_ARTICLE = "news_article"
    SOCIAL_MEDIA = "social_media"
    REGULATOR_CALL = "regulator_call"
    CEO_DEMAND = "ceo_demand"
    VENDOR_ALERT = "vendor_alert"
    MEDIA_INQUIRY = "media_inquiry"
    CUSTOMER_COMPLAINT = "customer_complaint"
    LAW_ENFORCEMENT = "law_enforcement"
    INSIDER_THREAT = "insider_threat"
    TECHNICAL_FAILURE = "technical_failure"


class InjectTrigger(BaseModel):
    """Defines when an inject should fire."""
    trigger_type: Literal["time", "round", "event", "manual", "condition"]
    trigger_value: Any = None  # Minutes, round number, or None for manual


class Inject(BaseModel):
    """A crisis inject event."""
    inject_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    inject_type: InjectType
    title: str
    content: str
    trigger: InjectTrigger
    target_teams: List[str] = Field(default_factory=list)  # Empty = all teams
    severity: Literal["info", "low", "medium", "high", "critical"] = "medium"
    requires_response: bool = False
    response_time_limit_minutes: Optional[int] = None
    attack_technique_id: Optional[str] = None  # MITRE ATT&CK ID
    business_impact: Optional[Dict[str, Any]] = None
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    responses: Dict[str, str] = Field(default_factory=dict)  # team_id: response


class TeamMember(BaseModel):
    """A participant in a multi-team exercise."""
    member_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    display_name: str
    role: str  # "SOC Analyst", "CISO", "Legal Counsel", etc.
    team_id: str
    is_facilitator: bool = False
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExerciseTeam(BaseModel):
    """A team in a multi-team exercise."""
    team_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    team_type: Literal["blue", "red", "white", "executive", "custom"]
    members: List[TeamMember] = Field(default_factory=list)
    objectives: List[Objective] = Field(default_factory=list)
    score: int = 0
    communication_log: List[Dict[str, Any]] = Field(default_factory=list)


class TeamAction(BaseModel):
    """An action submitted by a team member."""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str
    member_id: str
    action: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    round_number: int = 0
    attack_techniques_used: List[str] = Field(default_factory=list)  # ATT&CK IDs
    result: Optional[str] = None
    processed: bool = False


class ExerciseEvent(BaseModel):
    """An event in the exercise log."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: Literal["team_action", "inject", "facilitator", "system", "round_change"]
    source_team_id: Optional[str] = None
    description: str
    visibility: Literal["all", "team_only", "facilitator_only"] = "all"
    round_number: int = 0


class ExerciseConfig(BaseModel):
    """Configuration for creating a new exercise."""
    name: str
    description: str = ""
    scenario_filename: str
    scenario_type: str = "incident-response"
    difficulty: str = "intermediate"
    teams: List[Dict[str, Any]] = Field(default_factory=list)  # [{name, team_type, roles}]
    max_rounds: Optional[int] = None
    round_time_limit_minutes: Optional[int] = None
    enable_injects: bool = True
    enable_scoring: bool = True


class ExerciseState(BaseModel):
    """Complete state of a multi-team exercise."""
    exercise_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    facilitator_id: str = ""
    teams: List[ExerciseTeam] = Field(default_factory=list)
    game_state: Optional[GameState] = None  # Shared world state
    team_actions: Dict[str, List[TeamAction]] = Field(default_factory=dict)  # team_id: actions
    phase: Literal["setup", "active", "paused", "debrief", "completed"] = "setup"
    current_round: int = 0
    max_rounds: Optional[int] = None
    round_time_limit_minutes: Optional[int] = None
    round_started_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    exercise_log: List[ExerciseEvent] = Field(default_factory=list)
    injects: List[Inject] = Field(default_factory=list)
    pending_injects: List[Inject] = Field(default_factory=list)  # Queued for future delivery
    version: int = 0  # Incremented on every state change (for polling)
    config: Optional[ExerciseConfig] = None


class TeamGameView(BaseModel):
    """Filtered view of exercise state for a specific team."""
    exercise_id: str
    team: ExerciseTeam
    game_state: Optional[GameState] = None  # May be filtered based on team visibility
    visible_events: List[ExerciseEvent] = Field(default_factory=list)
    active_injects: List[Inject] = Field(default_factory=list)
    current_round: int = 0
    phase: str = "setup"
    version: int = 0


class TeamActionResult(BaseModel):
    """Result of processing a team action."""
    action_id: str
    team_id: str
    narrative: str = ""
    game_state_updated: bool = False
    events_generated: List[ExerciseEvent] = Field(default_factory=list)
    score_change: int = 0
