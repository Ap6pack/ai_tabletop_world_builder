#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Multi-team exercise data models."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

# Import shared models
from api.models.schemas import GameState, Objective


class InjectType(StrEnum):
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
    target_teams: list[str] = Field(default_factory=list)  # Empty = all teams
    severity: Literal["info", "low", "medium", "high", "critical"] = "medium"
    requires_response: bool = False
    response_time_limit_minutes: int | None = None
    attack_technique_id: str | None = None  # MITRE ATT&CK ID
    business_impact: dict[str, Any] | None = None
    delivered: bool = False
    delivered_at: datetime | None = None
    responses: dict[str, str] = Field(default_factory=dict)  # team_id: response


class TeamMember(BaseModel):
    """A participant in a multi-team exercise."""

    member_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    display_name: str
    role: str  # "SOC Analyst", "CISO", "Legal Counsel", etc.
    team_id: str
    is_facilitator: bool = False
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExerciseTeam(BaseModel):
    """A team in a multi-team exercise."""

    team_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    team_type: Literal["blue", "red", "white", "executive", "custom"]
    members: list[TeamMember] = Field(default_factory=list)
    objectives: list[Objective] = Field(default_factory=list)
    score: int = 0
    communication_log: list[dict[str, Any]] = Field(default_factory=list)


class TeamAction(BaseModel):
    """An action submitted by a team member."""

    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str
    member_id: str
    action: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    round_number: int = 0
    attack_techniques_used: list[str] = Field(default_factory=list)  # ATT&CK IDs
    result: str | None = None
    processed: bool = False


class ExerciseEvent(BaseModel):
    """An event in the exercise log."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: Literal["team_action", "inject", "facilitator", "system", "round_change"]
    source_team_id: str | None = None
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
    teams: list[dict[str, Any]] = Field(default_factory=list)  # [{name, team_type, roles}]
    max_rounds: int | None = None
    round_time_limit_minutes: int | None = None
    enable_injects: bool = True
    enable_scoring: bool = True


class ExerciseState(BaseModel):
    """Complete state of a multi-team exercise."""

    exercise_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    facilitator_id: str = ""
    teams: list[ExerciseTeam] = Field(default_factory=list)
    game_state: GameState | None = None  # Shared world state
    team_actions: dict[str, list[TeamAction]] = Field(default_factory=dict)  # team_id: actions
    phase: Literal["setup", "active", "paused", "debrief", "completed"] = "setup"
    current_round: int = 0
    max_rounds: int | None = None
    round_time_limit_minutes: int | None = None
    round_started_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    exercise_log: list[ExerciseEvent] = Field(default_factory=list)
    injects: list[Inject] = Field(default_factory=list)
    pending_injects: list[Inject] = Field(default_factory=list)  # Queued for future delivery
    version: int = 0  # Incremented on every state change (for polling)
    config: ExerciseConfig | None = None


class TeamGameView(BaseModel):
    """Filtered view of exercise state for a specific team."""

    exercise_id: str
    team: ExerciseTeam
    game_state: GameState | None = None  # May be filtered based on team visibility
    visible_events: list[ExerciseEvent] = Field(default_factory=list)
    active_injects: list[Inject] = Field(default_factory=list)
    current_round: int = 0
    phase: str = "setup"
    version: int = 0


class TeamActionResult(BaseModel):
    """Result of processing a team action."""

    action_id: str
    team_id: str
    narrative: str = ""
    game_state_updated: bool = False
    events_generated: list[ExerciseEvent] = Field(default_factory=list)
    score_change: int = 0
