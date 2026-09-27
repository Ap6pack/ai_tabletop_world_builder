#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the audit API endpoints (admin-only)."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api.middleware.auth import auth_service
from api.services.audit_log_service import AuditLogService
from config.settings import settings

AUDIT_REQUESTS = [
    ("get", "/audit/logs"),
    ("get", "/audit/stats"),
    ("get", "/audit/compliance-report?start_date=2026-01-01&end_date=2026-01-02"),
    ("post", "/audit/cleanup"),
    ("get", "/audit/verify"),
]


@pytest.fixture
def audit_service(monkeypatch):
    """Point the audit router at an isolated, pre-populated audit log."""
    import api.routers.audit as audit_router

    service = AuditLogService()
    service.log_policy_check("check the SIEM", "educational", "allowed", session_id="s1", user_id="u1")
    service.log_violation("rm -rf /", "destructive_command", "critical", "educational", "blocked", session_id="s1")
    monkeypatch.setattr(audit_router, "audit_service", service)
    return service


@pytest.fixture
def client(audit_service):
    from main import app

    return TestClient(app)


@pytest.fixture
def enable_auth(monkeypatch):
    monkeypatch.setattr(settings, "require_auth", True)


def _auth_header(username: str, role: str = "user") -> dict:
    user = auth_service.register(username, f"{username}@example.com", "password123")
    if role != "user":
        auth_service.update_user(user["id"], {"role": role})
    token = auth_service.create_access_token(user["id"], username, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(("method", "path"), AUDIT_REQUESTS)
def test_audit_endpoints_forbidden_for_non_admin(client, enable_auth, method, path):
    resp = client.request(method, path, headers=_auth_header("player"))
    assert resp.status_code == 403


@pytest.mark.parametrize(("method", "path"), AUDIT_REQUESTS)
def test_audit_endpoints_require_login(client, enable_auth, method, path):
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize(("method", "path"), AUDIT_REQUESTS)
def test_audit_endpoints_allow_admin(client, enable_auth, method, path):
    resp = client.request(method, path, headers=_auth_header("root", role="admin"))
    assert resp.status_code == 200


def test_get_logs_returns_entries(client):
    logs = client.get("/audit/logs", params={"limit": 10}).json()
    assert {log["event_type"] for log in logs} == {"policy_check", "violation"}


def test_get_logs_filters(client):
    violations = client.get("/audit/logs", params={"event_type": "violation"}).json()
    assert len(violations) == 1
    assert violations[0]["severity"] == "critical"
    by_user = client.get("/audit/logs", params={"user_id": "u1"}).json()
    assert len(by_user) == 1


def test_get_logs_rejects_invalid_date(client):
    assert client.get("/audit/logs", params={"start_date": "not-a-date"}).status_code == 400


def test_compliance_report(client):
    today = datetime.now()
    resp = client.get(
        "/audit/compliance-report",
        params={
            "start_date": (today - timedelta(days=1)).date().isoformat(),
            "end_date": (today + timedelta(days=1)).date().isoformat(),
        },
    )
    assert resp.status_code == 200
    report = resp.json()
    assert report["total_checks"] >= 1
    assert report["total_violations"] >= 1


def test_compliance_report_rejects_bad_dates(client):
    assert client.get("/audit/compliance-report", params={"start_date": "x", "end_date": "y"}).status_code == 400
    resp = client.get("/audit/compliance-report", params={"start_date": "2026-02-01", "end_date": "2026-01-01"})
    assert resp.status_code == 400


def test_stats(client):
    stats = client.get("/audit/stats").json()
    assert stats["total_entries"] == 2
    assert stats["oldest_log_date"] <= stats["newest_log_date"]


def test_verify_reports_valid_chain(client):
    result = client.get("/audit/verify").json()
    assert result == {"valid": True, "entries_checked": 2, "invalid_entry_id": None, "reason": None}


def test_cleanup_validates_retention(client):
    assert client.post("/audit/cleanup", params={"retention_days": 1}).status_code == 422
    resp = client.post("/audit/cleanup", params={"retention_days": 30})
    assert resp.status_code == 200
    assert resp.json()["retention_days"] == 30
