#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Compliance Scoring Service for evaluating game sessions against regulatory frameworks.

This service provides:
- Framework loading from JSON data files (NIST CSF 2.0, PCI DSS 4.0.1, HIPAA)
- Per-control scoring based on threat detection, mitigation, and player actions
- Weighted rollup to function-level and overall compliance scores
- Gap analysis identifying controls below threshold
- Multi-framework compliance report generation
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from api.models.schemas import GameState
from api.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# Pydantic Models for Compliance Scoring
# ============================================================================


class ComplianceControl(BaseModel):
    """A single compliance control with scoring data."""

    control_id: str
    name: str
    description: str = ""
    attack_techniques: list[str] = Field(default_factory=list)
    observable_actions: list[str] = Field(default_factory=list)
    weight: int = 1
    score: float = 0.0  # 0-100
    evidence: list[str] = Field(default_factory=list)


class ComplianceFunction(BaseModel):
    """A grouping of compliance controls (e.g., NIST CSF function)."""

    function_id: str
    name: str
    controls: list[ComplianceControl] = Field(default_factory=list)
    score: float = 0.0


class ComplianceScoreReport(BaseModel):
    """Full compliance score report for a framework."""

    framework_name: str
    framework_version: str = ""
    overall_score: float = 0.0
    functions: list[ComplianceFunction] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ComplianceGap(BaseModel):
    """A compliance gap identified during scoring."""

    control_id: str
    control_name: str
    framework: str
    gap_description: str
    remediation: str
    related_techniques: list[str] = Field(default_factory=list)


# ============================================================================
# Framework Data Key Constants
# ============================================================================

# Each framework JSON may use a different top-level key for its list of
# controls.  These constants map framework keys to the JSON field that holds
# the list of control objects and to the field name used for the control ID.

_FRAMEWORK_LIST_KEYS: dict[str, str] = {
    "nist_csf_2_0": "functions",
    "pci_dss_4_0_1": "requirements",
    "hipaa": "controls",
}

_FRAMEWORK_ID_FIELDS: dict[str, str] = {
    "nist_csf_2_0": "category_id",
    "pci_dss_4_0_1": "requirement_id",
    "hipaa": "control_id",
}


# ============================================================================
# Compliance Scoring Service
# ============================================================================


class ComplianceScoringService:
    """Service that scores game sessions against compliance frameworks.

    Loads compliance framework definitions from JSON files located in
    ``data/compliance_frameworks/`` and evaluates a ``GameState`` to produce
    per-control scores, function-level rollups, gap analysis, and
    multi-framework compliance reports.
    """

    # Points awarded for each scoring category
    POINTS_TECHNIQUE_ACTIVE = 40
    POINTS_TECHNIQUE_DETECTED = 30
    POINTS_TECHNIQUE_MITIGATED = 30
    POINTS_PER_ACTION_MATCH = 10
    MAX_ACTION_BONUS = 30
    MAX_CONTROL_SCORE = 100

    def __init__(self) -> None:
        self._frameworks: dict[str, dict] = {}
        self._load_frameworks()

    # ------------------------------------------------------------------ #
    # Framework Loading
    # ------------------------------------------------------------------ #

    def _load_frameworks(self) -> None:
        """Load all JSON files from the compliance frameworks data directory."""
        frameworks_dir = Path(__file__).resolve().parent.parent.parent / "data" / "compliance_frameworks"

        if not frameworks_dir.exists():
            logger.warning("Compliance frameworks directory not found: %s", frameworks_dir)
            return

        json_files = list(frameworks_dir.glob("*.json"))
        if not json_files:
            logger.warning("No JSON framework files found in %s", frameworks_dir)
            return

        for json_file in json_files:
            try:
                with open(json_file, encoding="utf-8") as fh:
                    data = json.load(fh)
                framework_key = json_file.stem  # e.g. "nist_csf_2_0"
                self._frameworks[framework_key] = data
                logger.info(
                    "Loaded compliance framework: %s (%s)",
                    data.get("framework_name", framework_key),
                    data.get("framework_version", "unknown"),
                )
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to load framework file %s: %s", json_file, exc)

        logger.info("Loaded %d compliance frameworks", len(self._frameworks))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_available_frameworks(self) -> list[str]:
        """Return the list of loaded framework keys."""
        return list(self._frameworks.keys())

    def score_session(self, game_state: GameState, framework: str) -> ComplianceScoreReport:
        """Score a game session against the specified compliance framework.

        Scoring process:
        1. Collect active, detected, and mitigated ATT&CK technique IDs from
           all ``ThreatActorState`` entries in the game state.
        2. Collect player action descriptions from the incident timeline
           (events where ``actor == "player"``).
        3. For each control in the framework:
           a. +40 if any of its ``attack_techniques`` appear in active techniques
           b. +30 if any appear in detected techniques
           c. +30 if any appear in mitigated techniques
           d. +10 per matching ``observable_actions`` keyword found in player
              actions (capped at +30, total score capped at 100)
        4. Roll up to function-level weighted averages and an overall score.
        """
        if framework not in self._frameworks:
            logger.warning(
                "Framework '%s' not found. Available: %s",
                framework,
                list(self._frameworks.keys()),
            )
            return ComplianceScoreReport(
                framework_name=framework,
                gaps=[f"Framework '{framework}' not loaded"],
            )

        fw_data = self._frameworks[framework]

        # -- Step 1: gather technique sets from threat states ---------------
        active_techniques, detected_techniques, mitigated_techniques = self._extract_technique_sets(game_state)

        # -- Step 2: gather player action text ------------------------------
        player_action_texts = self._extract_player_actions(game_state)

        # -- Step 3 & 4: build scored functions / controls ------------------
        functions = self._build_scored_functions(
            framework,
            fw_data,
            active_techniques,
            detected_techniques,
            mitigated_techniques,
            player_action_texts,
        )

        # -- Step 5: compute overall score ----------------------------------
        overall_score = self._compute_overall_score(functions)

        # -- Collect gaps & recommendations ---------------------------------
        gaps: list[str] = []
        recommendations: list[str] = []
        for func in functions:
            for ctrl in func.controls:
                if ctrl.score < 50:
                    gaps.append(f"{ctrl.control_id} ({ctrl.name}): score {ctrl.score:.0f}/100")
                    technique_hint = ", ".join(ctrl.attack_techniques[:3]) if ctrl.attack_techniques else "N/A"
                    recommendations.append(
                        f"Improve coverage for {ctrl.control_id} - "
                        f"{ctrl.name}. Focus on detecting/mitigating: "
                        f"{technique_hint}"
                    )

        report = ComplianceScoreReport(
            framework_name=fw_data.get("framework_name", framework),
            framework_version=fw_data.get("framework_version", ""),
            overall_score=overall_score,
            functions=functions,
            gaps=gaps,
            recommendations=recommendations,
        )

        logger.info(
            "Scored session %s against %s: overall %.1f",
            game_state.session_id,
            framework,
            overall_score,
        )
        return report

    def get_gap_analysis(self, game_state: GameState, framework: str) -> list[ComplianceGap]:
        """Return controls with a score below 50."""
        report = self.score_session(game_state, framework)
        gap_list: list[ComplianceGap] = []

        for func in report.functions:
            for ctrl in func.controls:
                if ctrl.score < 50:
                    gap_list.append(
                        ComplianceGap(
                            control_id=ctrl.control_id,
                            control_name=ctrl.name,
                            framework=report.framework_name,
                            gap_description=(
                                f"Control scored {ctrl.score:.0f}/100. "
                                f"Insufficient detection or mitigation "
                                f"of mapped techniques."
                            ),
                            remediation=(
                                f"Ensure the following ATT&CK techniques "
                                f"are detected and mitigated: "
                                f"{', '.join(ctrl.attack_techniques[:5])}. "
                                f"Demonstrate actions such as: "
                                f"{', '.join(ctrl.observable_actions[:3])}."
                            ),
                            related_techniques=ctrl.attack_techniques,
                        )
                    )

        logger.info(
            "Gap analysis for session %s / %s: %d gaps found",
            game_state.session_id,
            framework,
            len(gap_list),
        )
        return gap_list

    def generate_compliance_report(self, game_state: GameState, frameworks: list[str]) -> dict:
        """Generate a multi-framework compliance report.

        Returns a dictionary with per-framework score reports and an
        aggregate summary.
        """
        framework_reports: dict[str, ComplianceScoreReport] = {}
        all_gaps: list[ComplianceGap] = []
        total_score = 0.0
        scored_count = 0

        for fw_key in frameworks:
            report = self.score_session(game_state, fw_key)
            framework_reports[fw_key] = report
            total_score += report.overall_score
            scored_count += 1
            all_gaps.extend(self.get_gap_analysis(game_state, fw_key))

        aggregate_score = total_score / scored_count if scored_count > 0 else 0.0

        # Determine overall posture label
        if aggregate_score >= 80:
            posture = "Strong"
        elif aggregate_score >= 60:
            posture = "Moderate"
        elif aggregate_score >= 40:
            posture = "Developing"
        else:
            posture = "Weak"

        # Deduplicate recommendations across frameworks
        seen_recs: set[str] = set()
        unique_recommendations: list[str] = []
        for report in framework_reports.values():
            for rec in report.recommendations:
                if rec not in seen_recs:
                    seen_recs.add(rec)
                    unique_recommendations.append(rec)

        result = {
            "session_id": game_state.session_id,
            "frameworks_evaluated": list(framework_reports.keys()),
            "aggregate_score": round(aggregate_score, 1),
            "compliance_posture": posture,
            "framework_scores": {
                key: {
                    "framework_name": rpt.framework_name,
                    "framework_version": rpt.framework_version,
                    "overall_score": round(rpt.overall_score, 1),
                    "function_scores": {fn.function_id: round(fn.score, 1) for fn in rpt.functions},
                    "gap_count": len(rpt.gaps),
                }
                for key, rpt in framework_reports.items()
            },
            "total_gaps": len(all_gaps),
            "critical_gaps": [
                {
                    "control_id": g.control_id,
                    "control_name": g.control_name,
                    "framework": g.framework,
                    "gap_description": g.gap_description,
                    "remediation": g.remediation,
                }
                for g in all_gaps
            ],
            "recommendations": unique_recommendations[:20],
        }

        logger.info(
            "Generated multi-framework report for session %s: %d frameworks, aggregate %.1f",
            game_state.session_id,
            scored_count,
            aggregate_score,
        )
        return result

    # ------------------------------------------------------------------ #
    # Internal Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_technique_sets(
        game_state: GameState,
    ) -> tuple[set[str], set[str], set[str]]:
        """Extract active, detected, and mitigated technique ID sets."""
        active: set[str] = set()
        detected: set[str] = set()
        mitigated: set[str] = set()

        for threat_state in game_state.threat_states.values():
            active.update(threat_state.active_techniques)
            detected.update(threat_state.detected_techniques)
            mitigated.update(threat_state.mitigated_techniques)

        return active, detected, mitigated

    @staticmethod
    def _extract_player_actions(game_state: GameState) -> list[str]:
        """Collect lowercased descriptions of player actions from the timeline."""
        actions: list[str] = []
        for event in game_state.incident_timeline:
            if event.actor == "player":
                actions.append(event.description.lower())
        return actions

    def _build_scored_functions(
        self,
        framework_key: str,
        fw_data: dict,
        active_techniques: set[str],
        detected_techniques: set[str],
        mitigated_techniques: set[str],
        player_action_texts: list[str],
    ) -> list[ComplianceFunction]:
        """Parse framework data and score each control.

        Handles the structural differences between frameworks:
        - NIST CSF 2.0: functions -> categories (nested)
        - PCI DSS 4.0.1: requirements (flat list, single function)
        - HIPAA: controls (flat list, single function)
        """
        functions: list[ComplianceFunction] = []

        if framework_key == "nist_csf_2_0":
            functions = self._build_nist_functions(
                fw_data,
                active_techniques,
                detected_techniques,
                mitigated_techniques,
                player_action_texts,
            )
        elif framework_key == "pci_dss_4_0_1":
            functions = self._build_flat_framework_functions(
                fw_data,
                list_key="requirements",
                id_field="requirement_id",
                function_id="PCI",
                function_name="PCI DSS 4.0.1 Requirements",
                active_techniques=active_techniques,
                detected_techniques=detected_techniques,
                mitigated_techniques=mitigated_techniques,
                player_action_texts=player_action_texts,
            )
        elif framework_key == "hipaa":
            functions = self._build_flat_framework_functions(
                fw_data,
                list_key="controls",
                id_field="control_id",
                function_id="HIPAA",
                function_name="HIPAA Security Rule Controls",
                active_techniques=active_techniques,
                detected_techniques=detected_techniques,
                mitigated_techniques=mitigated_techniques,
                player_action_texts=player_action_texts,
            )
        else:
            # Generic fallback: try common keys
            for key in ("requirements", "controls", "categories"):
                if key in fw_data:
                    id_field = _FRAMEWORK_ID_FIELDS.get(framework_key, "control_id")
                    functions = self._build_flat_framework_functions(
                        fw_data,
                        list_key=key,
                        id_field=id_field,
                        function_id=framework_key.upper(),
                        function_name=fw_data.get("framework_name", framework_key),
                        active_techniques=active_techniques,
                        detected_techniques=detected_techniques,
                        mitigated_techniques=mitigated_techniques,
                        player_action_texts=player_action_texts,
                    )
                    break

        return functions

    def _build_nist_functions(
        self,
        fw_data: dict,
        active_techniques: set[str],
        detected_techniques: set[str],
        mitigated_techniques: set[str],
        player_action_texts: list[str],
    ) -> list[ComplianceFunction]:
        """Build scored functions for the NIST CSF 2.0 nested structure."""
        functions: list[ComplianceFunction] = []

        for func_data in fw_data.get("functions", []):
            scored_controls: list[ComplianceControl] = []

            for cat in func_data.get("categories", []):
                control = self._score_control(
                    control_id=cat.get("category_id", ""),
                    name=cat.get("name", ""),
                    description=cat.get("description", ""),
                    attack_techniques=cat.get("attack_techniques", []),
                    observable_actions=cat.get("observable_actions", []),
                    weight=cat.get("weight", 1),
                    active_techniques=active_techniques,
                    detected_techniques=detected_techniques,
                    mitigated_techniques=mitigated_techniques,
                    player_action_texts=player_action_texts,
                )
                scored_controls.append(control)

            func_score = self._weighted_average(scored_controls)
            functions.append(
                ComplianceFunction(
                    function_id=func_data.get("function_id", ""),
                    name=func_data.get("name", ""),
                    controls=scored_controls,
                    score=func_score,
                )
            )

        return functions

    def _build_flat_framework_functions(
        self,
        fw_data: dict,
        list_key: str,
        id_field: str,
        function_id: str,
        function_name: str,
        active_techniques: set[str],
        detected_techniques: set[str],
        mitigated_techniques: set[str],
        player_action_texts: list[str],
    ) -> list[ComplianceFunction]:
        """Build scored functions for flat-list frameworks (PCI, HIPAA)."""
        scored_controls: list[ComplianceControl] = []

        for item in fw_data.get(list_key, []):
            control = self._score_control(
                control_id=item.get(id_field, ""),
                name=item.get("name", ""),
                description=item.get("description", ""),
                attack_techniques=item.get("attack_techniques", []),
                observable_actions=item.get("observable_actions", []),
                weight=item.get("weight", 1),
                active_techniques=active_techniques,
                detected_techniques=detected_techniques,
                mitigated_techniques=mitigated_techniques,
                player_action_texts=player_action_texts,
            )
            scored_controls.append(control)

        func_score = self._weighted_average(scored_controls)
        return [
            ComplianceFunction(
                function_id=function_id,
                name=function_name,
                controls=scored_controls,
                score=func_score,
            )
        ]

    def _score_control(
        self,
        control_id: str,
        name: str,
        description: str,
        attack_techniques: list[str],
        observable_actions: list[str],
        weight: int,
        active_techniques: set[str],
        detected_techniques: set[str],
        mitigated_techniques: set[str],
        player_action_texts: list[str],
    ) -> ComplianceControl:
        """Score an individual control based on the game state.

        Scoring rubric:
        - +40 if any mapped ATT&CK technique was actively exercised
        - +30 if any mapped technique was detected by the player
        - +30 if any mapped technique was mitigated by the player
        - +10 per observable_action keyword matched in player actions (max +30)
        - Total capped at 100
        """
        score = 0.0
        evidence: list[str] = []
        ctrl_techniques = set(attack_techniques)

        # Technique-based scoring
        active_overlap = ctrl_techniques & active_techniques
        if active_overlap:
            score += self.POINTS_TECHNIQUE_ACTIVE
            evidence.append(f"Techniques actively exercised: {', '.join(sorted(active_overlap))}")

        detected_overlap = ctrl_techniques & detected_techniques
        if detected_overlap:
            score += self.POINTS_TECHNIQUE_DETECTED
            evidence.append(f"Techniques detected: {', '.join(sorted(detected_overlap))}")

        mitigated_overlap = ctrl_techniques & mitigated_techniques
        if mitigated_overlap:
            score += self.POINTS_TECHNIQUE_MITIGATED
            evidence.append(f"Techniques mitigated: {', '.join(sorted(mitigated_overlap))}")

        # Observable action keyword matching
        action_bonus = 0.0
        matched_actions: list[str] = []
        for keyword in observable_actions:
            keyword_lower = keyword.lower()
            for action_text in player_action_texts:
                if keyword_lower in action_text:
                    action_bonus += self.POINTS_PER_ACTION_MATCH
                    matched_actions.append(keyword)
                    break  # Only count each keyword once

            if action_bonus >= self.MAX_ACTION_BONUS:
                break

        action_bonus = min(action_bonus, self.MAX_ACTION_BONUS)
        if matched_actions:
            evidence.append(f"Observed player actions: {', '.join(matched_actions)}")

        score = min(score + action_bonus, self.MAX_CONTROL_SCORE)

        return ComplianceControl(
            control_id=control_id,
            name=name,
            description=description,
            attack_techniques=attack_techniques,
            observable_actions=observable_actions,
            weight=weight,
            score=round(score, 1),
            evidence=evidence,
        )

    @staticmethod
    def _weighted_average(controls: list[ComplianceControl]) -> float:
        """Compute weighted average score across a list of controls."""
        if not controls:
            return 0.0

        total_weight = sum(c.weight for c in controls)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(c.score * c.weight for c in controls)
        return round(weighted_sum / total_weight, 1)

    @staticmethod
    def _compute_overall_score(
        functions: list[ComplianceFunction],
    ) -> float:
        """Compute the overall framework score from function scores.

        Each function contributes equally to the overall score.
        """
        if not functions:
            return 0.0

        total = sum(f.score for f in functions)
        return round(total / len(functions), 1)
