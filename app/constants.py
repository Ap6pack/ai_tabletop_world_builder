#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Shared constants for the Streamlit frontend.
These ensure consistency between UI labels and backend API values.
"""

# Player role mapping: UI label -> API value
PLAYER_ROLES = {
    "SOC Analyst": "soc-analyst",
    "Incident Responder": "incident-responder",
    "Security Engineer": "security-engineer",
    "CISO": "ciso",
    "Mixed Team": "mixed",
}

# Reverse mapping for display: API value -> UI label
PLAYER_ROLES_DISPLAY = {v: k for k, v in PLAYER_ROLES.items()}

# Scenario types
SCENARIO_TYPES = {
    "Incident Response": "incident-response",
    "Threat Hunting": "threat-hunting",
    "Vulnerability Management": "vulnerability-management",
    "Compliance Audit": "compliance-audit",
}

SCENARIO_TYPES_DISPLAY = {v: k for k, v in SCENARIO_TYPES.items()}

# Difficulty levels
DIFFICULTY_LEVELS = {"Beginner": "beginner", "Intermediate": "intermediate", "Advanced": "advanced", "Expert": "expert"}

DIFFICULTY_LEVELS_DISPLAY = {v: k for k, v in DIFFICULTY_LEVELS.items()}

# Organization sizes
ORG_SIZES = {
    "Small (< 100 employees)": "small",
    "Medium (100-1000)": "medium",
    "Large (1000-5000)": "large",
    "Enterprise (5000+)": "enterprise",
}

ORG_SIZES_DISPLAY = {v: k for k, v in ORG_SIZES.items()}

# Complexity levels
COMPLEXITY_LEVELS = {"Basic": "basic", "Moderate": "moderate", "Complex": "complex"}

COMPLEXITY_LEVELS_DISPLAY = {v: k for k, v in COMPLEXITY_LEVELS.items()}
