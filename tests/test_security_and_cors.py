#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for security headers and CORS configuration."""

import pytest
from fastapi.testclient import TestClient

from api.middleware.cors import allow_credentials, get_cors_origins
from config.settings import settings


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in resp.headers
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_cors_allows_configured_origin(client):
    origin = "http://localhost:8501"
    resp = client.get("/health", headers={"Origin": origin})
    assert resp.headers.get("access-control-allow-origin") == origin


def test_cors_rejects_unknown_origin(client):
    resp = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_get_cors_origins_parses_env(monkeypatch):
    monkeypatch.setattr(settings, "cors_origins", "https://a.com, https://b.com")
    assert get_cors_origins() == ["https://a.com", "https://b.com"]


def test_wildcard_origin_disables_credentials():
    assert allow_credentials(["*"]) is False
    assert allow_credentials(["https://a.com"]) is True
