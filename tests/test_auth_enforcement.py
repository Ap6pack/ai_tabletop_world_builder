#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Tests for authentication enforcement on product and admin endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.middleware.auth import auth_service
from config.settings import settings

# A product endpoint that requires no request body.
PRODUCT_PATH = "/mitre/techniques"
# An admin-gated, non-destructive endpoint.
ADMIN_PATH = "/settings/export"


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


@pytest.fixture
def enable_auth(monkeypatch):
    """Turn on auth enforcement for the duration of a test."""
    monkeypatch.setattr(settings, "require_auth", True)


def _make_user_token(username: str, role: str = "user") -> str:
    """Register a user (optionally promoted to admin) and return an access token."""
    user = auth_service.register(username, f"{username}@example.com", "password123")
    if role != "user":
        auth_service.update_user(user["id"], {"role": role})
    return auth_service.create_access_token(user["id"], username, role=role)


# ---------------------------------------------------------------------------
# Auth disabled (dev default): endpoints stay open
# ---------------------------------------------------------------------------


def test_product_endpoint_open_when_auth_disabled(client):
    assert settings.require_auth is False
    assert client.get(PRODUCT_PATH).status_code == 200


# ---------------------------------------------------------------------------
# Auth enabled: product endpoints require a valid token
# ---------------------------------------------------------------------------


def test_product_endpoint_rejects_missing_token(client, enable_auth):
    assert client.get(PRODUCT_PATH).status_code == 401


def test_product_endpoint_rejects_invalid_token(client, enable_auth):
    resp = client.get(PRODUCT_PATH, headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_product_endpoint_accepts_valid_token(client, enable_auth):
    token = _make_user_token("alice")
    resp = client.get(PRODUCT_PATH, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auth endpoints stay open even when auth is enabled
# ---------------------------------------------------------------------------


def test_auth_register_open_when_auth_enabled(client, enable_auth):
    resp = client.post(
        "/auth/register",
        json={"username": "newbie", "email": "newbie@example.com", "password": "password123"},
    )
    assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Admin endpoints require the admin role when auth is enabled
# ---------------------------------------------------------------------------


def test_admin_endpoint_forbidden_for_regular_user(client, enable_auth):
    token = _make_user_token("bob")
    resp = client.post(ADMIN_PATH, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_endpoint_allows_admin(client, enable_auth):
    token = _make_user_token("root", role="admin")
    resp = client.post(ADMIN_PATH, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_admin_endpoint_open_when_auth_disabled(client):
    # With auth disabled (dev), admin endpoints are reachable (no user context).
    assert settings.require_auth is False
    assert client.post(ADMIN_PATH).status_code == 200
