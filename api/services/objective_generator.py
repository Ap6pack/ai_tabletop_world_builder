#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Objective Generator Service - Automatically generates training objectives from scenarios.
"""
import logging
from typing import List
from api.models import Organization, Objective, Vulnerability, ThreatActor, System

logger = logging.getLogger(__name__)


class ObjectiveGenerator:
    """
    Generates training objectives based on organization vulnerabilities, threats, and systems.
    """

    # Objective templates by type
    DETECTION_TEMPLATES = [
        "Identify indicators of compromise (IOCs) related to {threat_name}",
        "Detect suspicious network traffic patterns indicating {tactic}",
        "Identify all systems affected by {vulnerability_name}",
        "Locate evidence of {threat_name} activity in logs",
    ]

    CONTAINMENT_TEMPLATES = [
        "Isolate compromised {system_type} from the network",
        "Block malicious traffic associated with {threat_name}",
        "Prevent lateral movement to {critical_systems}",
        "Contain the spread of {attack_type} before it reaches critical systems",
    ]

    MITIGATION_TEMPLATES = [
        "Patch {vulnerability_name} on all affected systems",
        "Remove malicious artifacts left by {threat_name}",
        "Restore {system_name} to secure baseline configuration",
        "Apply security controls to prevent {attack_type}",
    ]

    INVESTIGATION_TEMPLATES = [
        "Determine the initial access vector used by {threat_name}",
        "Identify data exfiltration attempts from {system_type}",
        "Trace lateral movement paths through the network",
        "Determine scope of {threat_name} compromise",
    ]

    PROTECTION_TEMPLATES = [
        "Implement additional security controls on {critical_systems}",
        "Enable enhanced monitoring for {vulnerability_type} exploitation",
        "Deploy compensating controls for {vulnerability_name}",
        "Strengthen access controls on {system_type}",
    ]

    REPORTING_TEMPLATES = [
        "Document incident timeline and impact assessment",
        "Prepare executive summary of {threat_name} incident",
        "Create detailed technical report for forensics team",
        "Notify stakeholders about breach of {data_classification} data",
    ]

    def __init__(self):
        """Initialize the objective generator."""
        pass

    def generate_objectives_from_scenario(
        self,
        organization: Organization,
        scenario_type: str = "incident-response",
        difficulty: str = "intermediate",
        player_role: str = "soc-analyst"
    ) -> List[Objective]:
        """
        Generate objectives automatically from scenario data.

        Args:
            organization: The organization/scenario
            scenario_type: Type of training scenario
            difficulty: Difficulty level (beginner, intermediate, advanced, expert)
            player_role: Player's role (soc-analyst, incident-responder, etc.)

        Returns:
            List of structured objectives
        """
        objectives = []

        # Determine number of objectives based on difficulty
        objective_counts = {
            "beginner": 3,
            "intermediate": 5,
            "advanced": 6,
            "expert": 8
        }
        target_count = objective_counts.get(difficulty, 5)

        # Get key elements from organization
        vulnerabilities = self._extract_vulnerabilities(organization)
        threat_actors = organization.threat_actors
        critical_systems = self._extract_critical_systems(organization)

        # Generate detection objectives (always include at least one)
        if threat_actors:
            objectives.extend(
                self._generate_detection_objectives(
                    threat_actors[:2],  # Top 2 threats
                    critical_systems,
                    difficulty,
                    player_role
                )[:2]  # Max 2 detection objectives
            )

        # Generate containment objectives (incident response focus)
        if scenario_type == "incident-response" and threat_actors:
            objectives.extend(
                self._generate_containment_objectives(
                    threat_actors[0],  # Primary threat
                    critical_systems,
                    difficulty,
                    player_role
                )[:2]  # Max 2 containment objectives
            )

        # Generate mitigation objectives (vulnerability management focus)
        if vulnerabilities:
            objectives.extend(
                self._generate_mitigation_objectives(
                    vulnerabilities[:3],  # Top 3 vulnerabilities
                    difficulty,
                    player_role
                )[:2]  # Max 2 mitigation objectives
            )

        # Generate investigation objectives (threat hunting focus)
        if scenario_type == "threat-hunting" and threat_actors:
            objectives.extend(
                self._generate_investigation_objectives(
                    threat_actors[0],
                    critical_systems,
                    difficulty,
                    player_role
                )[:2]  # Max 2 investigation objectives
            )

        # Generate protection objectives (based on role)
        if player_role in ["security-engineer", "ciso"]:
            objectives.extend(
                self._generate_protection_objectives(
                    critical_systems,
                    vulnerabilities,
                    difficulty,
                    player_role
                )[:1]  # Max 1 protection objective
            )

        # Always include a reporting objective
        if player_role in ["incident-responder", "ciso"]:
            objectives.append(
                self._generate_reporting_objective(
                    threat_actors[0] if threat_actors else None,
                    organization,
                    difficulty,
                    player_role
                )
            )

        # Trim to target count
        objectives = objectives[:target_count]

        # Assign objective IDs
        for i, obj in enumerate(objectives, 1):
            obj.id = f"obj-{i:03d}"

        logger.info(f"Generated {len(objectives)} objectives for {difficulty} {scenario_type}")

        return objectives

    def _extract_vulnerabilities(self, organization: Organization) -> List[Vulnerability]:
        """Extract all vulnerabilities from organization systems."""
        vulnerabilities = []
        for dept in organization.departments:
            for system in dept.systems:
                vulnerabilities.extend(system.vulnerabilities)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        vulnerabilities.sort(key=lambda v: severity_order.get(v.severity, 5))

        return vulnerabilities

    def _extract_critical_systems(self, organization: Organization) -> List[System]:
        """Extract critical and high-priority systems."""
        critical_systems = []
        for dept in organization.departments:
            critical_systems.extend([s for s in dept.systems if s.criticality in ["critical", "high"]])

        return critical_systems

    def _generate_detection_objectives(
        self,
        threat_actors: List[ThreatActor],
        systems: List[System],
        difficulty: str,
        player_role: str
    ) -> List[Objective]:
        """Generate detection-focused objectives."""
        objectives = []

        for threat in threat_actors[:2]:
            obj = Objective(
                id="temp",
                description=f"Detect and identify indicators of {threat.name} activity in the environment",
                type="detect",
                success_criteria=f"Successfully identify at least 3 IOCs associated with {threat.name}",
                points=self._calculate_points("detect", difficulty),
                difficulty=self._map_difficulty(difficulty),
                related_threats=[threat.id],
                related_systems=[s.id for s in systems[:3]],
                hints=[
                    f"Check SIEM logs for patterns associated with {threat.ttps[0] if threat.ttps else 'suspicious activity'}",
                    f"Look for {threat.motivation} indicators in network traffic",
                    "Review recent alerts for anomalies"
                ]
            )

            if difficulty in ["advanced", "expert"]:
                obj.time_limit_minutes = 30

            objectives.append(obj)

        return objectives

    def _generate_containment_objectives(
        self,
        threat: ThreatActor,
        systems: List[System],
        difficulty: str,
        player_role: str
    ) -> List[Objective]:
        """Generate containment-focused objectives."""
        objectives = []

        # Isolate compromised systems
        if systems:
            obj = Objective(
                id="temp",
                description=f"Contain the {threat.name} attack by isolating affected systems",
                type="contain",
                success_criteria="Successfully isolate all compromised systems without disrupting critical services",
                points=self._calculate_points("contain", difficulty),
                difficulty=self._map_difficulty(difficulty),
                related_threats=[threat.id],
                related_systems=[s.id for s in systems[:2]],
                hints=[
                    "Use network segmentation to isolate affected systems",
                    "Coordinate with business units before isolation",
                    "Monitor for lateral movement attempts"
                ]
            )

            if difficulty in ["advanced", "expert"]:
                obj.time_limit_minutes = 45

            objectives.append(obj)

        # Block threat actor access
        obj = Objective(
            id="temp",
            description=f"Block {threat.name} command and control (C2) communications",
            type="contain",
            success_criteria="Successfully block all identified C2 channels",
            points=self._calculate_points("contain", difficulty),
            difficulty=self._map_difficulty(difficulty),
            related_threats=[threat.id],
            hints=[
                "Identify C2 IP addresses and domains",
                "Update firewall rules to block malicious traffic",
                "Monitor for C2 reconnection attempts"
            ]
        )

        if difficulty == "expert":
            obj.time_limit_minutes = 20

        objectives.append(obj)

        return objectives

    def _generate_mitigation_objectives(
        self,
        vulnerabilities: List[Vulnerability],
        difficulty: str,
        player_role: str
    ) -> List[Objective]:
        """Generate mitigation-focused objectives."""
        objectives = []

        for vuln in vulnerabilities[:2]:
            obj = Objective(
                id="temp",
                description=f"Mitigate {vuln.name} vulnerability on all affected systems",
                type="mitigate",
                success_criteria=f"Apply {vuln.remediation[:50]}... to all {len(vuln.affected_systems)} affected systems",
                points=self._calculate_points("mitigate", difficulty),
                difficulty=self._map_difficulty(difficulty),
                related_systems=vuln.affected_systems,
                hints=[
                    f"Priority: {vuln.severity.upper()} severity",
                    f"Remediation: {vuln.remediation[:80]}",
                    "Test patches in staging before production deployment"
                ]
            )

            # Time limits based on severity
            if vuln.severity == "critical" and difficulty in ["advanced", "expert"]:
                obj.time_limit_minutes = 60

            objectives.append(obj)

        return objectives

    def _generate_investigation_objectives(
        self,
        threat: ThreatActor,
        systems: List[System],
        difficulty: str,
        player_role: str
    ) -> List[Objective]:
        """Generate investigation-focused objectives."""
        objectives = []

        # Root cause analysis
        obj = Objective(
            id="temp",
            description=f"Investigate and determine the initial access vector used by {threat.name}",
            type="investigate",
            success_criteria="Identify the initial compromise method with supporting evidence",
            points=self._calculate_points("investigate", difficulty),
            difficulty=self._map_difficulty(difficulty),
            related_threats=[threat.id],
            hints=[
                f"Review {threat.ttps[0] if threat.ttps else 'attack'} patterns",
                "Check authentication logs for anomalies",
                "Analyze network traffic captures"
            ]
        )

        if difficulty == "expert":
            obj.time_limit_minutes = 90

        objectives.append(obj)

        # Data exfiltration check
        if systems:
            obj = Objective(
                id="temp",
                description="Determine if sensitive data was exfiltrated during the attack",
                type="investigate",
                success_criteria="Confirm data exfiltration status with evidence of what was accessed",
                points=self._calculate_points("investigate", difficulty),
                difficulty=self._map_difficulty(difficulty),
                related_systems=[s.id for s in systems if s.type in ["database", "application"]],
                hints=[
                    "Review data access logs",
                    "Check for large outbound data transfers",
                    "Analyze file access patterns"
                ]
            )

            objectives.append(obj)

        return objectives

    def _generate_protection_objectives(
        self,
        systems: List[System],
        vulnerabilities: List[Vulnerability],
        difficulty: str,
        player_role: str
    ) -> List[Objective]:
        """Generate protection-focused objectives."""
        objectives = []

        if systems:
            obj = Objective(
                id="temp",
                description="Implement enhanced security controls on critical systems",
                type="protect",
                success_criteria="Deploy additional monitoring and access controls on all critical assets",
                points=self._calculate_points("protect", difficulty),
                difficulty=self._map_difficulty(difficulty),
                related_systems=[s.id for s in systems[:3]],
                hints=[
                    "Enable enhanced logging and monitoring",
                    "Implement additional access restrictions",
                    "Deploy threat detection rules"
                ]
            )

            objectives.append(obj)

        return objectives

    def _generate_reporting_objective(
        self,
        threat: ThreatActor,
        organization: Organization,
        difficulty: str,
        player_role: str
    ) -> Objective:
        """Generate a reporting objective."""
        threat_name = threat.name if threat else "the security incident"

        obj = Objective(
            id="temp",
            description=f"Prepare comprehensive incident report for {threat_name}",
            type="report",
            success_criteria="Create detailed report including timeline, impact, and recommendations",
            points=self._calculate_points("report", difficulty),
            difficulty=self._map_difficulty(difficulty),
            hints=[
                "Include incident timeline from detection to resolution",
                "Document business impact and affected systems",
                "Provide actionable recommendations for prevention"
            ]
        )

        return obj

    def _calculate_points(self, objective_type: str, difficulty: str) -> int:
        """Calculate points for an objective based on type and difficulty."""
        base_points = {
            "detect": 20,
            "contain": 30,
            "mitigate": 25,
            "investigate": 35,
            "protect": 30,
            "report": 15
        }

        difficulty_multiplier = {
            "beginner": 0.8,
            "intermediate": 1.0,
            "advanced": 1.3,
            "expert": 1.5
        }

        base = base_points.get(objective_type, 25)
        multiplier = difficulty_multiplier.get(difficulty, 1.0)

        return int(base * multiplier)

    def _map_difficulty(self, scenario_difficulty: str) -> str:
        """Map scenario difficulty to objective difficulty."""
        mapping = {
            "beginner": "easy",
            "intermediate": "medium",
            "advanced": "hard",
            "expert": "hard"
        }
        return mapping.get(scenario_difficulty, "medium")
