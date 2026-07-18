#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for fixed-window rate limiting."""

import pytest
from fastapi.testclient import TestClient

from config.settings import settings

PROBE_PATH = "/mitre/techniques"


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def test_requests_within_limit_succeed(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_requests", 5)
    for _ in range(5):
        assert client.get(PROBE_PATH).status_code == 200


def test_request_over_limit_is_throttled(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_requests", 3)
    for _ in range(3):
        assert client.get(PROBE_PATH).status_code == 200
    resp = client.get(PROBE_PATH)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_rate_limit_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    # Well over the configured limit, but disabled, so all succeed.
    for _ in range(5):
        assert client.get(PROBE_PATH).status_code == 200


def test_limiter_key_prefers_user_over_ip():
    from unittest.mock import MagicMock

    from api.middleware import rate_limit as rl

    request = MagicMock()
    request.headers = {"Authorization": "Bearer sometoken"}
    request.client.host = "1.2.3.4"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(rl.auth_service, "verify_token", lambda _t: {"sub": "user-123"})
        assert rl._client_key(request) == "user:user-123"

    # No/invalid token falls back to client IP.
    request.headers = {}
    assert rl._client_key(request) == "ip:1.2.3.4"
