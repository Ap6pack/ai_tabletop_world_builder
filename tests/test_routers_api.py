#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""API tests for the auth, library, LLM, MITRE and content-policy routers."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from config.settings import settings


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# /auth
# ---------------------------------------------------------------------------


def _register(client, username="alice", password="password123"):
    return client.post(
        "/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password}
    )


def _login(client, username="alice", password="password123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def test_register_and_login(client):
    resp = _register(client)
    assert resp.status_code == 201
    assert resp.json()["username"] == "alice"
    assert "hashed_password" not in resp.json()

    tokens = _login(client).json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]


def test_register_validation_and_duplicates(client):
    assert _register(client, "ab").status_code == 422
    assert _register(client, password="short").status_code == 422
    assert _register(client).status_code == 201
    assert _register(client).status_code == 400


def test_login_rejects_bad_password(client):
    _register(client)
    assert _login(client, password="wrong-password").status_code == 401
    assert _login(client, username="nobody").status_code == 401


def test_refresh_flow(client):
    _register(client)
    tokens = _login(client).json()
    resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    # An access token is not a refresh token.
    assert client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": "garbage"}).status_code == 401


@pytest.fixture
def authed(client, monkeypatch):
    monkeypatch.setattr(settings, "require_auth", True)
    _register(client)
    token = _login(client).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_profile_read_and_update(client, authed):
    me = client.get("/auth/me", headers=authed)
    assert me.status_code == 200
    assert me.json()["role"] == "user"

    resp = client.put("/auth/me", headers=authed, json={"display_name": "Alice A."})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Alice A."
    assert client.put("/auth/me", headers=authed, json={}).status_code == 400


def test_profile_cannot_escalate_role(client, authed):
    resp = client.put("/auth/me", headers=authed, json={"role": "admin", "display_name": "x"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "user"


def test_change_password(client, authed):
    bad = client.post(
        "/auth/change-password", headers=authed, json={"old_password": "nope-nope", "new_password": "newpassword1"}
    )
    assert bad.status_code == 400
    ok = client.post(
        "/auth/change-password",
        headers=authed,
        json={"old_password": "password123", "new_password": "newpassword1"},
    )
    assert ok.status_code == 200
    assert _login(client, password="newpassword1").status_code == 200


def test_me_requires_login(client):
    assert client.get("/auth/me").status_code == 401


# ---------------------------------------------------------------------------
# /library
# ---------------------------------------------------------------------------


def test_library_templates_and_listing(client):
    templates = client.get("/library/templates").json()
    assert templates["total"] >= 1
    listing = client.get("/library/scenarios").json()
    assert listing["total"] == len(listing["scenarios"])


def test_library_add_get_rate_fork_share(client):
    added = client.post("/library/scenarios", json={"name": "Phish Friday", "tags": ["phishing"]}).json()["scenario"]
    sid = added["id"]

    assert client.get(f"/library/scenarios/{sid}").json()["name"] == "Phish Friday"
    assert client.post(f"/library/scenarios/{sid}/rate", json={"rating": 4}).status_code == 200
    assert client.post(f"/library/scenarios/{sid}/rate", json={"rating": 9}).status_code == 422

    fork = client.post(f"/library/scenarios/{sid}/fork", json={"user_id": "bob"})
    assert fork.status_code == 200
    assert fork.json()["scenario"]["id"] != sid

    assert client.post(f"/library/scenarios/{sid}/share", json={"visibility": "private"}).status_code == 200
    assert client.post(f"/library/scenarios/{sid}/share", json={"visibility": "everyone"}).status_code == 400

    results = client.get("/library/search", params={"q": "phish"}).json()
    assert any(r["id"] == sid for r in results["results"])


def test_library_missing_scenario(client):
    assert client.get("/library/scenarios/missing").status_code == 404
    assert client.post("/library/scenarios/missing/rate", json={"rating": 3}).status_code == 404
    assert client.post("/library/scenarios/missing/fork").status_code == 404
    assert client.post("/library/scenarios/missing/share", json={"visibility": "public"}).status_code == 404
    assert client.get("/library/search", params={"q": ""}).status_code == 422


# ---------------------------------------------------------------------------
# /llm
# ---------------------------------------------------------------------------


def test_llm_complete_uses_provider(client, _no_real_llm):
    _no_real_llm.complete = AsyncMock(return_value={"content": "A SIEM aggregates logs.", "model": "fake"})
    resp = client.post("/llm/complete", json={"prompt": "What is a SIEM?"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "A SIEM aggregates logs."


def test_llm_complete_errors(client, _no_real_llm, monkeypatch):
    _no_real_llm.complete = AsyncMock(side_effect=RuntimeError("upstream down"))
    assert client.post("/llm/complete", json={"prompt": "x"}).status_code == 500

    def bad_config(*args, **kwargs):
        raise ValueError("no key")

    monkeypatch.setattr("api.providers.factory.LLMProviderFactory.create_provider", bad_config)
    assert client.post("/llm/complete", json={"prompt": "x"}).status_code == 400


def test_llm_providers(client, monkeypatch):
    monkeypatch.setattr(
        "api.providers.factory.LLMProviderFactory.get_available_providers",
        AsyncMock(return_value={"openai": False, "ollama": True}),
    )
    assert client.get("/llm/providers").json() == {"openai": False, "ollama": True}


# ---------------------------------------------------------------------------
# /mitre
# ---------------------------------------------------------------------------


def test_mitre_techniques_and_tactics(client):
    all_techniques = client.get("/mitre/techniques", params={"limit": 5}).json()
    assert all_techniques["total"] == 5
    tech_id = all_techniques["techniques"][0]["technique_id"]
    assert client.get(f"/mitre/techniques/{tech_id}").json()["technique_id"] == tech_id
    assert client.get("/mitre/techniques/T0000").status_code == 404

    tactics = client.get("/mitre/tactics").json()["tactics"]
    assert tactics
    first_tactic = tactics[0] if isinstance(tactics, list) else next(iter(tactics))
    tactic_name = first_tactic if isinstance(first_tactic, str) else first_tactic.get("name", "")
    assert client.get("/mitre/techniques", params={"tactic": tactic_name}).status_code == 200
    assert client.get("/mitre/techniques", params={"search": "phishing"}).json()["total"] >= 1


def test_mitre_map_and_coverage(client, sample_game_state):
    mapped = client.post("/mitre/map", params={"ttp": "spear phishing email"}).json()
    assert mapped["techniques"]
    assert client.get("/mitre/coverage/missing").status_code == 404


# ---------------------------------------------------------------------------
# /content-policy
# ---------------------------------------------------------------------------


def test_content_policy_list_and_check(client, _no_real_llm):
    policies = client.get("/content-policy/policies").json()
    assert "educational" in policies
    _no_real_llm.complete = AsyncMock(return_value={"content": "STATUS: SAFE\nVIOLATIONS: none", "model": "f"})
    resp = client.post(
        "/content-policy/check", json={"content": "Check the firewall logs", "policy": policies["educational"]}
    )
    assert resp.status_code == 200
    assert resp.json()["is_safe"] is True
