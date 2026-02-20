"""
Training Path Service for identifying skill gaps and recommending training paths.

Analyzes player performance across multiple war game sessions to identify
weak areas, recommend targeted scenarios, build training plans, and track
improvement over time.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from api.models import GameState, DecisionEvaluation
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

SKILL_AREAS = [
    "detection", "containment", "mitigation", "communication",
    "investigation", "resource_management", "time_management",
]
DEFAULT_TARGET_LEVEL = 80

SCENARIO_MAPPING = {
    "detection": ["threat-hunting", "incident-response"],
    "containment": ["incident-response"],
    "mitigation": ["vulnerability-management", "incident-response"],
    "communication": ["incident-response", "compliance-audit"],
    "investigation": ["threat-hunting", "incident-response"],
    "resource_management": ["incident-response", "compliance-audit"],
    "time_management": ["incident-response", "threat-hunting"],
}

CATEGORY_KEYWORDS = {
    "detection": ["scan", "check logs", "monitor", "detect", "observe",
                   "review logs", "check alerts", "inspect", "hunt"],
    "containment": ["isolate", "block", "quarantine", "disable",
                     "disconnect", "shut down", "firewall", "contain"],
    "mitigation": ["patch", "restore", "fix", "update", "remediate",
                    "repair", "rebuild", "recover", "rollback"],
    "communication": ["alert", "notify", "report", "escalate", "inform",
                       "brief", "communicate", "call", "email", "warn"],
    "investigation": ["investigate", "analyze", "forensic", "correlate",
                       "trace", "examine", "root cause", "assess"],
}

OBJ_TYPE_MAP = {
    "detection": "detect", "containment": "contain",
    "mitigation": "mitigate", "communication": "report",
    "investigation": "investigate",
}


class TrainingPathService:
    """Identifies skill gaps and recommends targeted training paths."""

    def __init__(self) -> None:
        pass

    def analyze_skill_gaps(self, session_states: List[GameState]) -> List[Dict]:
        """Analyze multiple sessions to find weak areas, returning a priority-sorted
        list of dicts with skill_area, current_level, target_level, gap, priority,
        and recommended_scenarios."""
        if not session_states:
            logger.warning("No session states provided for skill gap analysis")
            return []
        logger.info(f"Analyzing skill gaps across {len(session_states)} sessions")
        gaps: List[Dict] = []
        for area in SKILL_AREAS:
            scores = [self._calculate_area_score(gs, area) for gs in session_states]
            level = int(sum(scores) / len(scores))
            gap = max(0, DEFAULT_TARGET_LEVEL - level)
            priority = "high" if gap >= 40 else ("medium" if gap >= 20 else "low")
            gaps.append({"skill_area": area, "current_level": level,
                         "target_level": DEFAULT_TARGET_LEVEL, "gap": gap,
                         "priority": priority,
                         "recommended_scenarios": SCENARIO_MAPPING.get(area, ["incident-response"])})
        gaps.sort(key=lambda g: g["gap"], reverse=True)
        logger.info(f"Skill gap analysis complete: "
                    f"{sum(1 for g in gaps if g['priority'] == 'high')} high-priority gaps")
        return gaps

    def recommend_next_scenario(
        self, skill_gaps: List[Dict], available_scenarios: Optional[List[str]] = None,
    ) -> Dict:
        """Recommend the next scenario based on skill gaps. Returns dict with
        scenario_type, difficulty, focus_areas, and reasoning."""
        if not skill_gaps:
            return {"scenario_type": "incident-response", "difficulty": "medium",
                    "focus_areas": ["detection", "containment"],
                    "reasoning": "No skill gap data available; defaulting to "
                                 "general incident response training."}
        high = [g for g in skill_gaps if g["priority"] == "high"]
        targets = high if high else skill_gaps[:3]
        focus_areas = [g["skill_area"] for g in targets[:3]]
        counts: Dict[str, int] = {}
        for gap in targets:
            for s in gap.get("recommended_scenarios", []):
                if available_scenarios is None or s in available_scenarios:
                    counts[s] = counts.get(s, 0) + 1
        scenario_type = max(counts, key=counts.get) if counts else "incident-response"
        avg_lvl = sum(g["current_level"] for g in targets) / len(targets)
        difficulty = "easy" if avg_lvl < 35 else ("medium" if avg_lvl < 65 else "hard")
        parts = [f"Targeting {', '.join(focus_areas)} based on identified gaps"]
        if high:
            parts.append(f"{len(high)} high-priority gap(s) require focused practice")
        parts.append(f"Current average level in focus areas: {int(avg_lvl)}/100")
        return {"scenario_type": scenario_type, "difficulty": difficulty,
                "focus_areas": focus_areas, "reasoning": ". ".join(parts) + "."}

    def build_training_plan(self, session_states: List[GameState]) -> Dict:
        """Build a multi-session training plan with current_level, target_level,
        skill_profile, recommended_sessions, estimated_sessions_to_target,
        and focus_priorities."""
        logger.info(f"Building training plan from {len(session_states)} sessions")
        gaps = self.analyze_skill_gaps(session_states)
        skill_profile = {g["skill_area"]: g["current_level"] for g in gaps}
        current_level = int(sum(skill_profile.values()) / len(skill_profile)) if skill_profile else 50
        focus_priorities = [g["skill_area"] for g in gaps if g["gap"] > 0]
        remaining = [g for g in gaps if g["gap"] > 0]
        n_sessions = min(5, max(3, len([g for g in gaps if g["priority"] != "low"])))
        recommended_sessions: List[Dict] = []
        for i in range(n_sessions):
            if remaining:
                rec = self.recommend_next_scenario(remaining[:3])
                rec["session_number"] = i + 1
                recommended_sessions.append(rec)
                remaining = remaining[1:] + remaining[:1]
        needed = max(0, DEFAULT_TARGET_LEVEL - current_level)
        estimated = max(len(recommended_sessions), (needed + 4) // 5) if needed > 0 else 0
        logger.info(f"Training plan: current={current_level}, estimated_sessions={estimated}")
        return {"current_level": current_level, "target_level": DEFAULT_TARGET_LEVEL,
                "skill_profile": skill_profile, "recommended_sessions": recommended_sessions,
                "estimated_sessions_to_target": estimated, "focus_priorities": focus_priorities}

    def track_progress(self, session_states: List[GameState]) -> Dict:
        """Track improvement across sessions. Returns sessions_completed,
        score_trend, skill_improvements, and milestones."""
        if not session_states:
            return {"sessions_completed": 0, "score_trend": [],
                    "skill_improvements": {}, "milestones": []}
        logger.info(f"Tracking progress across {len(session_states)} sessions")
        skill_improvements: Dict[str, Dict] = {}
        for area in SKILL_AREAS:
            scores = [self._calculate_area_score(gs, area) for gs in session_states]
            first, latest = int(scores[0]), int(scores[-1])
            skill_improvements[area] = {"first": first, "latest": latest,
                                        "change": latest - first}
        milestones = self._detect_milestones(session_states)
        result = {"sessions_completed": len(session_states),
                  "score_trend": [gs.score for gs in session_states],
                  "skill_improvements": skill_improvements, "milestones": milestones}
        logger.info(f"Progress: {len(session_states)} sessions, {len(milestones)} milestones")
        return result

    def _calculate_area_score(self, game_state: GameState, area: str) -> float:
        """Calculate 0-100 score for a specific skill area from a single session."""
        if area == "resource_management":
            return self._score_resource_management(game_state)
        if area == "time_management":
            return self._score_time_management(game_state)
        keywords = CATEGORY_KEYWORDS.get(area, [])
        if not keywords:
            return 50.0
        timeline = game_state.incident_timeline
        scores: List[float] = []
        for i, event in enumerate(timeline):
            if event.actor != "player" or event.event_type != "action":
                continue
            if not any(kw in event.description.lower() for kw in keywords):
                continue
            score = 50.0
            for sub in timeline[i + 1: i + 4]:
                if sub.event_type == "consequence":
                    score += 15.0 if sub.severity in ("low", "info") else (
                        -15.0 if sub.severity in ("critical", "high") else 0.0)
                if sub.event_type == "escalation":
                    score -= 10.0
            scores.append(max(0.0, min(100.0, score)))
        if not scores:
            obj_type = OBJ_TYPE_MAP.get(area)
            if obj_type:
                matching = [o for o in game_state.objectives if o.type == obj_type]
                if matching:
                    return sum(1 for o in matching if o.status == "completed") / len(matching) * 100
            return 50.0
        return sum(scores) / len(scores)

    def _score_resource_management(self, game_state: GameState) -> float:
        """Score resource management based on resource pool usage efficiency."""
        if not game_state.resource_pool:
            return 50.0
        pool = game_state.resource_pool
        ap_ratio = pool.action_points / max(pool.max_action_points, 1)
        budget_ratio = pool.budget_remaining / max(pool.budget_total, 1)
        score = (100.0 - abs(ap_ratio - 0.3) * 100) * 0.6 + (100.0 - abs(budget_ratio - 0.3) * 100) * 0.4
        return max(0.0, min(100.0, score))

    def _score_time_management(self, game_state: GameState) -> float:
        """Score time management based on objective timing."""
        timed = [o for o in game_state.objectives if o.time_limit_minutes is not None]
        if not timed:
            total = len(game_state.objectives)
            if total == 0:
                return 50.0
            ratio = sum(1 for o in game_state.objectives if o.status == "completed") / total
            penalty = min(20.0, max(0.0, (game_state.time_elapsed / max(total, 1) - 10) * 2))
            return max(0.0, min(100.0, ratio * 80 + 20 - penalty))
        return sum(1 for o in timed if o.status == "completed") / len(timed) * 100

    def _detect_milestones(self, session_states: List[GameState]) -> List[str]:
        """Check for achievements based on session history."""
        if not session_states:
            return []
        milestones: List[str] = ["First session completed"]
        if len(session_states) >= 5:
            milestones.append("Five sessions completed")
        if len(session_states) >= 10:
            milestones.append("Ten sessions completed")
        for gs in session_states:
            possible = sum(o.points for o in gs.objectives) or 100
            if gs.score >= possible * 0.9:
                milestones.append("First A grade")
                break
        for gs in session_states:
            if gs.objectives and all(o.status == "completed" for o in gs.objectives):
                milestones.append("Perfect session: all objectives completed")
                break
        latest = session_states[-1]
        for area in SKILL_AREAS:
            if self._calculate_area_score(latest, area) >= 85:
                milestones.append(f"{area.replace('_', ' ').title()} mastery")
        if len(session_states) >= 3:
            scores = [gs.score for gs in session_states]
            streak = 0
            for i in range(1, len(scores)):
                streak = streak + 1 if scores[i] > scores[i - 1] else 0
                if streak >= 3:
                    milestones.append("Improvement streak: 3+ sessions")
                    break
        return milestones
