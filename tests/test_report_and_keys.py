#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the PDF/CSV report generator and the API key service."""

import csv
import io
from datetime import UTC, datetime

import pytest

from api.services.api_key_service import APIKeyService
from api.services.report_generator import ReportGenerator

FULL_AAR = {
    "session_id": "sess-1",
    "generated_at": datetime(2026, 9, 27, 12, 0, tzinfo=UTC),
    "overall_grade": "B",
    "summary": "Solid containment with a slow start.",
    "score_breakdown": {"detection": 30, "containment_speed": 25},
    "timeline_analysis": [
        {"action": "Checked the SIEM " * 10, "category": "detection", "quality_score": 80, "impact": "positive"},
        {"action": "Isolated host", "category": "containment", "quality_score": 90, "impact": "positive"},
    ],
    "strengths": ["Fast isolation of the compromised host after initial triage was completed"],
    "weaknesses": ["Late escalation", "No stakeholder comms"],
    "recommendations": ["Practice escalation paths", "Pre-draft comms templates"],
    "metrics": {
        "mean_time_to_detect": {"value": 12, "benchmark": 15, "percentile": 70},
        "mean_time_to_contain": {"value": 40, "benchmark": None, "percentile": None},
        "ignored": "not a dict",
    },
}


def test_pdf_contains_all_sections():
    pdf = ReportGenerator().generate_pdf(FULL_AAR)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1500


def test_pdf_minimal_report():
    pdf = ReportGenerator().generate_pdf({"session_id": "s", "overall_grade": "F"})
    assert pdf.startswith(b"%PDF")


@pytest.mark.parametrize("grade", ["A", "B", "C", "D", "F", "N/A", "Z"])
def test_grade_colors_are_rgb(grade):
    color = ReportGenerator._grade_color(grade)
    assert len(color) == 3 and all(0 <= c <= 255 for c in color)


def test_csv_export():
    game_state = {
        "session_id": "s",
        "incident_timeline": [
            {
                "timestamp": datetime(2026, 1, 1, 9, 0),
                "event_type": "detection",
                "description": "Alert, with comma",
                "severity": "high",
                "actor": "system",
            },
            {
                "timestamp": "2026-01-01T09:05:00",
                "event_type": "action",
                "description": "Isolate",
                "severity": "info",
                "actor": "player",
            },
        ],
    }
    rows = list(csv.DictReader(io.StringIO(ReportGenerator().generate_csv(game_state))))
    assert [r["event_type"] for r in rows] == ["detection", "action"]
    assert rows[0]["description"] == "Alert, with comma"
    assert rows[0]["timestamp"] == "2026-01-01T09:00:00"


def test_csv_empty_timeline():
    assert ReportGenerator().generate_csv({}).strip() == "timestamp,event_type,description,severity,actor"


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------


def test_api_key_lifecycle():
    service = APIKeyService()
    created = service.create_key("user-1", "ci", scopes=["read"])
    raw = created["raw_key"]
    assert raw.startswith("wg_") and created["prefix"] == raw[:10]

    assert service.verify_key(raw)["id"] == created["id"]
    assert service.verify_key("wg_wrong") is None
    listed = service.list_keys("user-1")
    assert [k["id"] for k in listed] == [created["id"]]
    assert "hashed_key" not in listed[0] and "raw_key" not in listed[0]
    assert service.list_keys("someone-else") == []
    assert service.get_key(created["id"])["name"] == "ci"

    assert service.revoke_key(created["id"]) is True
    assert service.verify_key(raw) is None
    assert service.get_key(created["id"])["revoked"] is True
    assert service.revoke_key("missing") is False
    assert service.get_key("missing") is None


def test_api_key_rejects_unknown_scopes():
    with pytest.raises(ValueError, match="Invalid scopes"):
        APIKeyService().create_key("u", "k", scopes=["root"])


def test_api_key_default_scope():
    assert APIKeyService().create_key("u", "k")["scopes"] == ["read"]
