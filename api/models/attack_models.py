#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
MITRE ATT&CK data models for technique mapping and coverage analysis.
"""

from pydantic import BaseModel, Field


class ATTCKTechnique(BaseModel):
    """
    Represents a single MITRE ATT&CK technique or sub-technique.

    Attributes:
        technique_id: The ATT&CK technique identifier (e.g., T1566, T1566.001).
        name: Human-readable technique name.
        tactic: The tactic shortname this technique belongs to (e.g., initial-access).
        tactic_id: The tactic identifier (e.g., TA0001).
        description: Brief description of the technique.
        platforms: List of platforms where this technique applies.
        data_sources: List of data sources useful for detecting this technique.
        detection: Guidance on how to detect usage of this technique.
        mitigations: List of recommended mitigations.
        is_subtechnique: Whether this is a sub-technique (e.g., T1566.001).
        parent_technique_id: The parent technique ID if this is a sub-technique.
    """

    technique_id: str = Field(
        ...,
        description="MITRE ATT&CK technique ID (e.g., T1566)",
        examples=["T1566", "T1566.001"],
    )
    name: str = Field(
        ...,
        description="Technique name",
        examples=["Phishing", "Spearphishing Attachment"],
    )
    tactic: str = Field(
        ...,
        description="Tactic shortname",
        examples=["initial-access", "execution"],
    )
    tactic_id: str = Field(
        ...,
        description="Tactic ID",
        examples=["TA0001"],
    )
    description: str = Field(
        ...,
        description="Brief description of the technique",
    )
    platforms: list[str] = Field(
        default_factory=list,
        description="Applicable platforms",
        examples=[["Windows", "Linux", "macOS"]],
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="Data sources useful for detection",
    )
    detection: str = Field(
        default="",
        description="Detection guidance",
    )
    mitigations: list[str] = Field(
        default_factory=list,
        description="Recommended mitigations",
    )
    is_subtechnique: bool = Field(
        default=False,
        description="Whether this is a sub-technique",
    )
    parent_technique_id: str | None = Field(
        default=None,
        description="Parent technique ID for sub-techniques",
    )


class ATTCKTactic(BaseModel):
    """
    Represents a MITRE ATT&CK tactic (kill chain phase).

    Attributes:
        tactic_id: The tactic identifier (e.g., TA0001).
        name: Human-readable tactic name (e.g., Initial Access).
        shortname: Tactic shortname used in lookups (e.g., initial-access).
    """

    tactic_id: str = Field(
        ...,
        description="Tactic ID (e.g., TA0001)",
        examples=["TA0001"],
    )
    name: str = Field(
        ...,
        description="Tactic name",
        examples=["Initial Access"],
    )
    shortname: str = Field(
        ...,
        description="Tactic shortname",
        examples=["initial-access"],
    )


class ATTCKCoverageReport(BaseModel):
    """
    Coverage report showing which ATT&CK techniques were exercised,
    detected, and mitigated during a game session.

    Attributes:
        techniques_exercised: ATT&CK IDs that were active during the session.
        techniques_detected: ATT&CK IDs that the player successfully detected.
        techniques_mitigated: ATT&CK IDs that the player successfully mitigated.
        coverage_by_tactic: Per-tactic breakdown of total/detected/mitigated counts.
        coverage_percentage: Overall detection coverage as a percentage.
        gaps: ATT&CK IDs that were exercised but not detected.
    """

    techniques_exercised: list[str] = Field(
        default_factory=list,
        description="ATT&CK technique IDs that were exercised",
    )
    techniques_detected: list[str] = Field(
        default_factory=list,
        description="ATT&CK technique IDs that were detected",
    )
    techniques_mitigated: list[str] = Field(
        default_factory=list,
        description="ATT&CK technique IDs that were mitigated",
    )
    coverage_by_tactic: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Per-tactic coverage breakdown: {tactic: {total, detected, mitigated}}",
    )
    coverage_percentage: float = Field(
        default=0.0,
        description="Overall detection coverage percentage",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="ATT&CK technique IDs exercised but not detected",
    )
