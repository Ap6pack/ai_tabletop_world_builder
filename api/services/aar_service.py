#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
After Action Review (AAR) Service for generating post-session analysis reports.

Orchestrates the DecisionAnalyzer and AlternativePathService to produce a
complete AAR report with metrics, grades, and training recommendations.
"""

from datetime import UTC, datetime
from typing import Any

from api.models import (
    AARReport,
    AlternativePath,
    DecisionEvaluation,
    GameState,
    PerformanceDashboard,
    PerformanceMetric,
)
from api.services.alternative_path_service import AlternativePathService
from api.services.decision_analyzer import DecisionAnalyzer
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class AARService:
    """
    Service for generating After Action Review reports and performance dashboards.

    Orchestrates the DecisionAnalyzer and AlternativePathService to produce
    a complete AAR report with grades, metrics, strengths, weaknesses, and
    actionable recommendations.
    """

    GRADE_THRESHOLDS = {"A": 90, "B": 75, "C": 60, "D": 40}
    SCORE_WEIGHT = 0.60
    METRIC_WEIGHT = 0.40
    MAX_EXPECTED_SCORE = 500

    METRIC_BENCHMARKS = {
        "response_time": 5.0,
        "containment_speed": 15.0,
        "objectives_completed_pct": 80.0,
        "financial_efficiency": 70.0,
        "detection_rate": 75.0,
        "resource_efficiency": 50.0,
    }

    LOWER_IS_BETTER = {"response_time", "containment_speed"}

    def __init__(self):
        """Initialize the AAR service with its dependent analyzers."""
        self.decision_analyzer = DecisionAnalyzer()
        self.alternative_path_service = AlternativePathService()

    def generate_aar(self, game_state: GameState, include_alternatives: bool = True) -> AARReport:
        """Generate a complete After Action Review report for a game session."""
        logger.info(f"Generating AAR for session {game_state.session_id}")

        evaluations = self.decision_analyzer.analyze_timeline(game_state)
        logger.info(f"Analyzed {len(evaluations)} decisions")

        alternatives: list[AlternativePath] = []
        if include_alternatives:
            alternatives = self.alternative_path_service.suggest_alternatives(game_state)
            logger.info(f"Generated {len(alternatives)} alternative paths")

        metrics = self.calculate_metrics(game_state)
        score_breakdown = self.build_score_breakdown(game_state)
        overall_grade = self.calculate_grade(game_state.score, metrics)
        strengths = self.identify_strengths(evaluations, metrics)
        weaknesses = self.identify_weaknesses(evaluations, metrics)
        recommendations = self.generate_recommendations(weaknesses, game_state)
        summary = self.generate_summary(game_state, overall_grade)

        metrics_dict: dict[str, Any] = {
            name: {"value": m.value, "unit": m.unit, "benchmark": m.benchmark, "percentile": m.percentile}
            for name, m in metrics.items()
        }

        report = AARReport(
            session_id=game_state.session_id,
            generated_at=datetime.now(UTC),
            summary=summary,
            timeline_analysis=evaluations,
            alternative_paths=alternatives,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            overall_grade=overall_grade,
            score_breakdown=score_breakdown,
            metrics=metrics_dict,
            ai_feedback="",
        )
        logger.info(f"AAR generated: grade={overall_grade}, strengths={len(strengths)}, weaknesses={len(weaknesses)}")
        return report

    def calculate_metrics(self, game_state: GameState) -> dict[str, PerformanceMetric]:
        """Calculate performance metrics (response_time, containment_speed, etc.) from game state."""
        metrics: dict[str, PerformanceMetric] = {}
        timeline = game_state.incident_timeline

        # response_time: average gap between threat events and player responses
        threat_times = [e.timestamp for e in timeline if e.actor == "threat_actor"]
        response_times = [e.timestamp for e in timeline if e.actor == "player"]
        avg_response = 0.0
        if threat_times and response_times:
            gaps = []
            for t_ts in threat_times:
                after = [r for r in response_times if r >= t_ts]
                if after:
                    gaps.append((min(after) - t_ts).total_seconds() / 60.0)
            avg_response = sum(gaps) / len(gaps) if gaps else 0.0
        metrics["response_time"] = self._build_metric("response_time", avg_response, "minutes")

        # containment_speed: first detection to first containment action
        first_detection = first_containment = None
        containment_kw = {"isolate", "contain", "block", "quarantine", "disable"}
        for event in timeline:
            if event.event_type == "detection" and first_detection is None:
                first_detection = event.timestamp
            if (
                event.actor == "player"
                and first_containment is None
                and any(kw in event.description.lower() for kw in containment_kw)
            ):
                first_containment = event.timestamp
        cont_min = 0.0
        if first_detection and first_containment and first_containment >= first_detection:
            cont_min = (first_containment - first_detection).total_seconds() / 60.0
        metrics["containment_speed"] = self._build_metric("containment_speed", cont_min, "minutes")

        # objectives_completed_pct
        total_obj = len(game_state.objectives)
        done = sum(1 for o in game_state.objectives if o.status == "completed")
        done += len(game_state.objectives_completed)
        pct = (done / total_obj * 100.0) if total_obj > 0 else 0.0
        metrics["objectives_completed_pct"] = self._build_metric("objectives_completed_pct", pct, "percent")

        # financial_efficiency: remaining budget vs total cost
        if game_state.business_impact is not None:
            budget = game_state.resource_pool.budget_total if game_state.resource_pool else 100000.0
            eff = max(0.0, (budget - game_state.business_impact.total_cost) / budget * 100.0) if budget > 0 else 0.0
            metrics["financial_efficiency"] = self._build_metric("financial_efficiency", eff, "percent")

        # detection_rate: player detections vs total threats
        det_actions = sum(1 for e in timeline if e.event_type == "detection" and e.actor == "player")
        tot_threats = sum(1 for e in timeline if e.actor == "threat_actor")
        det_pct = (det_actions / tot_threats * 100.0) if tot_threats > 0 else 0.0
        metrics["detection_rate"] = self._build_metric("detection_rate", det_pct, "percent")

        # resource_efficiency: remaining resources vs total
        if game_state.resource_pool is not None:
            pool = game_state.resource_pool
            res_pct = (pool.budget_remaining / pool.budget_total * 100.0) if pool.budget_total > 0 else 0.0
            metrics["resource_efficiency"] = self._build_metric("resource_efficiency", res_pct, "percent")

        return metrics

    def calculate_grade(self, score: int, metrics: dict[str, PerformanceMetric]) -> str:
        """Calculate letter grade: 60% game score (normalized to 100), 40% metric quality."""
        normalized = min(100.0, score / max(1, self.MAX_EXPECTED_SCORE) * 100.0)
        percentiles = [m.percentile for m in metrics.values() if m.percentile is not None]
        avg_quality = sum(percentiles) / len(percentiles) if percentiles else 50.0
        combined = normalized * self.SCORE_WEIGHT + avg_quality * self.METRIC_WEIGHT

        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if combined >= threshold:
                return grade
        return "F"

    def identify_strengths(
        self, evaluations: list[DecisionEvaluation], metrics: dict[str, PerformanceMetric]
    ) -> list[str]:
        """Identify what the player did well (quality_score > 70, metrics above benchmark)."""
        strengths: list[str] = []

        strong = [e for e in evaluations if e.quality_score > 70]
        if strong:
            cats: dict[str, list[DecisionEvaluation]] = {}
            for d in strong:
                cats.setdefault(d.category, []).append(d)
            for cat, decs in cats.items():
                avg = sum(d.quality_score for d in decs) / len(decs)
                strengths.append(f"Strong {cat} skills: {len(decs)} effective decision(s) with avg score {avg:.0f}/100")

        for name, m in metrics.items():
            if m.percentile is not None and m.percentile >= 70:
                label = name.replace("_", " ").title()
                strengths.append(
                    f"Excellent {label}: {m.value}{self._unit_suffix(m.unit)} "
                    f"(benchmark: {m.benchmark}{self._unit_suffix(m.unit)}, {m.percentile}th pctl)"
                )

        pos = sum(1 for e in evaluations if e.impact == "positive")
        if pos and evaluations and (pos / len(evaluations) * 100) >= 50:
            strengths.append(
                f"High positive impact: {pos}/{len(evaluations)} decisions ({pos / len(evaluations) * 100:.0f}%)"
            )

        return strengths or ["Session completed -- continue building experience"]

    def identify_weaknesses(
        self, evaluations: list[DecisionEvaluation], metrics: dict[str, PerformanceMetric]
    ) -> list[str]:
        """Identify areas needing improvement (quality_score < 40, metrics below benchmark)."""
        weaknesses: list[str] = []

        weak = [e for e in evaluations if e.quality_score < 40]
        if weak:
            cats: dict[str, list[DecisionEvaluation]] = {}
            for d in weak:
                cats.setdefault(d.category, []).append(d)
            for cat, decs in cats.items():
                avg = sum(d.quality_score for d in decs) / len(decs)
                weaknesses.append(
                    f"Needs improvement in {cat}: {len(decs)} suboptimal decision(s), avg score {avg:.0f}/100"
                )

        for name, m in metrics.items():
            if m.percentile is not None and m.percentile < 40:
                label = name.replace("_", " ").title()
                weaknesses.append(
                    f"Below target for {label}: {m.value}{self._unit_suffix(m.unit)} "
                    f"(benchmark: {m.benchmark}{self._unit_suffix(m.unit)}, {m.percentile}th pctl)"
                )

        neg = sum(1 for e in evaluations if e.impact == "negative")
        if neg and evaluations and (neg / len(evaluations) * 100) >= 30:
            weaknesses.append(
                f"High negative impact: {neg}/{len(evaluations)} decisions ({neg / len(evaluations) * 100:.0f}%)"
            )

        return weaknesses

    def generate_recommendations(self, weaknesses: list[str], game_state: GameState) -> list[str]:
        """Turn weaknesses into actionable training recommendations."""
        rec_map = {
            "detection": "Practice threat detection: log analysis, SIEM alert triage, and IOC identification",
            "containment": "Review containment procedures: network isolation, quarantine, and access revocation drills",
            "mitigation": "Study mitigation strategies: patch management, vulnerability remediation, system hardening",
            "communication": "Improve incident communication: stakeholder briefings, status updates, escalation procedures",
            "investigation": "Strengthen investigation: forensic analysis, evidence collection, root cause analysis",
            "response time": "Work on response speed: rapid triage and prioritization of security alerts",
            "containment speed": "Reduce time-to-containment: develop and rehearse containment playbooks",
            "objectives": "Focus on objective completion: review objectives at start, track progress systematically",
            "financial": "Improve cost management: consider financial impact before executing response actions",
            "resource": "Optimize resource utilization: plan action sequences to conserve points and budget",
            "negative impact": "Review decision-making under pressure: study NIST/SANS incident response frameworks",
        }
        recommendations: list[str] = []
        for weakness in weaknesses:
            wl = weakness.lower()
            for keyword, rec in rec_map.items():
                if keyword in wl and rec not in recommendations:
                    recommendations.append(rec)

        if game_state.status == "failed":
            recommendations.append("Consider starting with a lower difficulty to build foundational skills")

        failed = [o for o in game_state.objectives if o.status == "failed"]
        for obj_type in set(o.type for o in failed):
            recommendations.append(f"Review {obj_type} techniques: multiple {obj_type} objectives were not achieved")

        return recommendations or ["Good performance overall. Try a higher difficulty or different scenario type."]

    def build_score_breakdown(self, game_state: GameState) -> dict[str, int]:
        """Break down total score by category: detection, containment, objective, penalty points."""
        bd = {"detection_points": 0, "containment_points": 0, "objective_points": 0, "penalty_points": 0}

        for event in game_state.incident_timeline:
            if event.event_type == "detection" and event.actor == "player":
                bd["detection_points"] += (
                    15 if event.severity in ("critical", "high") else (10 if event.severity == "medium" else 5)
                )
            if event.event_type == "consequence" and event.severity in ("critical", "high"):
                bd["penalty_points"] -= 10

        for ts in game_state.threat_states.values():
            if ts.status == "contained":
                bd["containment_points"] += 25
            elif ts.status == "eliminated":
                bd["containment_points"] += 40

        for obj in game_state.objectives:
            if obj.status == "completed":
                bd["objective_points"] += obj.points
            elif obj.status == "failed":
                bd["penalty_points"] -= obj.points // 2

        return bd

    def generate_summary(self, game_state: GameState, grade: str) -> str:
        """Generate a 2-3 sentence summary of the session."""
        total_obj = len(game_state.objectives)
        completed = sum(1 for o in game_state.objectives if o.status == "completed")
        contained = sum(1 for t in game_state.threat_states.values() if t.status in ("contained", "eliminated"))
        total_threats = len(game_state.threat_states)

        outcome_map = {"completed": "successfully completed", "failed": "ended unsuccessfully"}
        outcome = outcome_map.get(game_state.status, "is still in progress")

        summary = f"Session {outcome} with an overall grade of {grade} and a score of {game_state.score} points. "
        if total_obj > 0:
            summary += f"The player completed {completed} of {total_obj} objectives "
        if total_threats > 0:
            summary += f"and contained {contained} of {total_threats} threat(s) "
        summary += f"over {game_state.time_elapsed} minutes of gameplay."
        return summary

    def build_dashboard(self, session_states: list[GameState]) -> PerformanceDashboard:
        """Aggregate metrics across multiple sessions into a performance dashboard."""
        logger.info(f"Building dashboard from {len(session_states)} sessions")
        if not session_states:
            return PerformanceDashboard()

        scores = [gs.score for gs in session_states]
        play_times = [gs.time_elapsed for gs in session_states]
        average_score = sum(scores) / len(scores)

        # Collect per-session metric values
        all_metrics: dict[str, list[float]] = {}
        for gs in session_states:
            for name, m in self.calculate_metrics(gs).items():
                all_metrics.setdefault(name, []).append(m.value)

        # Build aggregated metrics and trends
        aggregated: list[PerformanceMetric] = []
        trends: dict[str, list[float]] = {}
        for name, values in all_metrics.items():
            avg = sum(values) / len(values)
            bm = self.METRIC_BENCHMARKS.get(name)
            aggregated.append(self._build_metric(name, avg, "minutes" if name in self.LOWER_IS_BETTER else "percent"))
            trends[name] = [round(v, 2) for v in values]
        trends["score"] = [float(s) for s in scores]

        # Identify skill gaps: metrics below benchmark in 60%+ of sessions
        skill_gaps: list[str] = []
        for name, values in all_metrics.items():
            bm = self.METRIC_BENCHMARKS.get(name)
            if bm is not None and len(values) >= 2:
                below = sum(1 for v in values if (v > bm if name in self.LOWER_IS_BETTER else v < bm))
                if below >= len(values) * 0.6:
                    skill_gaps.append(
                        f"{name.replace('_', ' ').title()}: below benchmark in {below}/{len(values)} sessions"
                    )

        # Cross-session recommendations
        recommendations: list[str] = []
        if skill_gaps:
            recommendations.append("Focus training on: " + ", ".join(g.split(":")[0] for g in skill_gaps))
        if len(scores) >= 3:
            recent = sum(scores[-3:]) / 3
            if recent > average_score * 1.1:
                recommendations.append("Performance trending upward. Consider increasing difficulty.")
            elif recent < average_score * 0.9:
                recommendations.append("Recent performance declining. Review fundamentals at a lower difficulty.")
        if not recommendations:
            recommendations.append("Continue regular practice sessions to maintain and improve skills.")

        dashboard = PerformanceDashboard(
            sessions_completed=len(session_states),
            average_score=round(average_score, 1),
            best_score=max(scores),
            total_play_time_minutes=sum(play_times),
            metrics=aggregated,
            trends=trends,
            skill_gaps=skill_gaps,
            recommendations=recommendations,
        )
        logger.info(f"Dashboard built: {len(session_states)} sessions, avg={average_score:.1f}, gaps={len(skill_gaps)}")
        return dashboard

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _build_metric(self, name: str, value: float, unit: str) -> PerformanceMetric:
        """Build a PerformanceMetric with benchmark and percentile from class constants."""
        bm = self.METRIC_BENCHMARKS.get(name)
        return PerformanceMetric(
            metric_type=name,
            value=round(value, 2),
            unit=unit,
            benchmark=bm,
            percentile=self._calculate_percentile(value, bm or 50.0, name in self.LOWER_IS_BETTER),
        )

    def _calculate_percentile(self, value: float, benchmark: float, lower_is_better: bool = False) -> int:
        """Estimate percentile from value vs benchmark (benchmark = 50th percentile)."""
        if benchmark <= 0:
            return 50
        ratio = (benchmark / value if value > 0 else 2.0) if lower_is_better else value / benchmark
        return int(min(99, max(1, ratio * 50)))

    @staticmethod
    def _unit_suffix(unit: str) -> str:
        """Return display suffix for a metric unit (e.g., ' min', '%')."""
        if unit == "minutes":
            return " min"
        if unit == "percent":
            return "%"
        return f" {unit}" if unit else ""
