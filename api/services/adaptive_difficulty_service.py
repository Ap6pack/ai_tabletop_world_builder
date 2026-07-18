#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Adaptive Difficulty Service for dynamically adjusting game difficulty.

Monitors player performance during war game sessions and adjusts difficulty
parameters in real time to maintain an appropriate challenge level.
"""

from datetime import UTC, datetime

from api.models import DecisionEvaluation, GameState
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

MIN_ACTIONS_FOR_ADJUSTMENT = 3
MIN_MINUTES_BETWEEN_ADJUSTMENTS = 5
SKILL_THRESHOLD_EASY = 35
SKILL_THRESHOLD_HARD = 70

CATEGORY_KEYWORDS = {
    "detection": [
        "scan",
        "check logs",
        "monitor",
        "detect",
        "observe",
        "review logs",
        "check alerts",
        "inspect",
        "hunt",
    ],
    "containment": ["isolate", "block", "quarantine", "disable", "disconnect", "shut down", "firewall", "contain"],
    "mitigation": ["patch", "restore", "fix", "update", "remediate", "repair", "rebuild", "recover", "rollback"],
    "communication": [
        "alert",
        "notify",
        "report",
        "escalate",
        "inform",
        "brief",
        "communicate",
        "call",
        "email",
        "warn",
    ],
    "investigation": ["investigate", "analyze", "forensic", "correlate", "trace", "examine", "root cause", "assess"],
}

DIFFICULTY_CONFIGS = {
    "easy": {
        "action_point_bonus": 2,
        "timer_multiplier": 1.3,
        "threat_aggression_cap": 50,
        "hints_enabled": True,
        "resource_multiplier": 1.2,
    },
    "medium": {
        "action_point_bonus": 0,
        "timer_multiplier": 1.0,
        "threat_aggression_cap": 80,
        "hints_enabled": True,
        "resource_multiplier": 1.0,
    },
    "hard": {
        "action_point_bonus": -2,
        "timer_multiplier": 0.7,
        "threat_aggression_cap": 100,
        "hints_enabled": False,
        "resource_multiplier": 0.8,
    },
}


def _score_action_at(timeline: list, idx: int) -> float:
    """Score a player action based on subsequent consequence events."""
    score = 50.0
    for event in timeline[idx + 1 : idx + 4]:
        if event.event_type == "consequence":
            if event.severity in ("low", "info"):
                score += 15.0
            elif event.severity in ("critical", "high"):
                score -= 15.0
        if event.event_type == "escalation":
            score -= 10.0
    return max(0.0, min(100.0, score))


class AdaptiveDifficultyService:
    """Dynamically adjusts game difficulty based on player skill level."""

    def __init__(self) -> None:
        self._last_adjustment_time: datetime | None = None

    def calculate_player_skill(
        self,
        game_state: GameState,
        evaluations: list[DecisionEvaluation] | None = None,
    ) -> dict:
        """Analyze performance to produce a skill profile with overall_skill,
        category_skills, trend, and recommended_difficulty."""
        logger.info(f"Calculating player skill for session {game_state.session_id}")
        total_possible = sum(obj.points for obj in game_state.objectives) or 100
        score_ratio = min(game_state.score / total_possible, 1.0) * 100
        total_obj = len(game_state.objectives)
        obj_ratio = (
            (sum(1 for o in game_state.objectives if o.status == "completed") / total_obj * 100) if total_obj else 50.0
        )
        if evaluations:
            dq = sum(e.quality_score for e in evaluations) / len(evaluations)
        else:
            dq = self._calculate_recent_performance(game_state)
        overall = max(0, min(100, int(score_ratio * 0.3 + obj_ratio * 0.3 + dq * 0.4)))
        category_skills = self._build_category_skills(game_state, evaluations)
        trend = self._detect_trend(game_state)
        if overall < SKILL_THRESHOLD_EASY:
            rec = "easy"
        elif overall >= SKILL_THRESHOLD_HARD:
            rec = "hard"
        else:
            rec = "medium"
        logger.info(f"Skill profile: overall={overall}, trend={trend}, rec={rec}")
        return {
            "overall_skill": overall,
            "category_skills": category_skills,
            "trend": trend,
            "recommended_difficulty": rec,
        }

    def adjust_difficulty(self, game_state: GameState, current_difficulty: str) -> dict:
        """Return difficulty adjustments including new_difficulty, modifiers,
        hint_availability, and explanation."""
        logger.info(f"Evaluating adjustment for session {game_state.session_id}")
        skill = self.calculate_player_skill(game_state)
        overall, trend = skill["overall_skill"], skill["trend"]
        order = ["easy", "medium", "hard"]
        cur_idx = order.index(current_difficulty)
        rec_idx = order.index(skill["recommended_difficulty"])
        new_difficulty = order[cur_idx + max(-1, min(1, rec_idx - cur_idx))]
        gap = overall - 50
        parts = []
        if new_difficulty != current_difficulty:
            parts.append(f"Difficulty changed from {current_difficulty} to {new_difficulty}")
        if trend == "declining":
            parts.append("Player performance is declining")
        elif trend == "improving":
            parts.append("Player performance is improving")
        parts.append(f"Overall skill level: {overall}/100")
        self._last_adjustment_time = datetime.now(UTC)
        return {
            "new_difficulty": new_difficulty,
            "threat_aggression_modifier": round(max(-20.0, min(20.0, gap * 0.4)), 1),
            "timer_modifier": round(max(0.5, min(1.5, 1.0 - gap * 0.01)), 2),
            "hint_availability": overall < 40 or trend == "declining",
            "resource_modifier": round(max(0.8, min(1.2, 1.0 - gap * 0.004)), 2),
            "explanation": ". ".join(parts) + ".",
        }

    def should_adjust(self, game_state: GameState) -> bool:
        """Check if minimum 3 player actions taken and 5+ minutes elapsed."""
        actions = sum(1 for e in game_state.incident_timeline if e.actor == "player" and e.event_type == "action")
        if actions < MIN_ACTIONS_FOR_ADJUSTMENT:
            return False
        if self._last_adjustment_time is not None:
            elapsed = (datetime.now(UTC) - self._last_adjustment_time).total_seconds() / 60
            if elapsed < MIN_MINUTES_BETWEEN_ADJUSTMENTS:
                return False
        return game_state.time_elapsed >= MIN_MINUTES_BETWEEN_ADJUSTMENTS

    def get_difficulty_config(self, difficulty: str) -> dict:
        """Return static config for easy/medium/hard difficulty levels."""
        return DIFFICULTY_CONFIGS.get(difficulty, DIFFICULTY_CONFIGS["medium"])

    def _calculate_recent_performance(self, game_state: GameState) -> float:
        """Average quality of last 5 player actions based on consequences."""
        timeline = game_state.incident_timeline
        indices = [i for i, e in enumerate(timeline) if e.actor == "player" and e.event_type == "action"]
        if not indices:
            return 50.0
        scores = [_score_action_at(timeline, idx) for idx in indices[-5:]]
        return sum(scores) / len(scores)

    def _detect_trend(self, game_state: GameState) -> str:
        """Compare first-half vs second-half performance."""
        indices = [
            i for i, e in enumerate(game_state.incident_timeline) if e.actor == "player" and e.event_type == "action"
        ]
        if len(indices) < 4:
            return "stable"
        mid = len(indices) // 2
        timeline = game_state.incident_timeline

        def avg(idx_list: list[int]) -> float:
            s = [_score_action_at(timeline, i) for i in idx_list]
            return sum(s) / len(s) if s else 50.0

        diff = avg(indices[mid:]) - avg(indices[:mid])
        if diff > 10:
            return "improving"
        return "declining" if diff < -10 else "stable"

    def _build_category_skills(
        self,
        game_state: GameState,
        evaluations: list[DecisionEvaluation] | None = None,
    ) -> dict[str, int]:
        """Build per-category skill scores from evaluations or timeline."""
        cats = list(CATEGORY_KEYWORDS.keys())
        scores: dict[str, list[int]] = {c: [] for c in cats}
        if evaluations:
            for ev in evaluations:
                if ev.category in scores:
                    scores[ev.category].append(ev.quality_score)
        else:
            for event in game_state.incident_timeline:
                if event.actor == "player" and event.event_type == "action":
                    lower = event.description.lower()
                    for cat, kws in CATEGORY_KEYWORDS.items():
                        if any(kw in lower for kw in kws):
                            scores[cat].append(50)
                            break
        return {c: int(sum(v) / len(v)) if v else 50 for c, v in scores.items()}
