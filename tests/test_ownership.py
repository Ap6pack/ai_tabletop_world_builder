#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Two-user isolation tests: user B can't see or touch user A's records."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from api.middleware.auth import auth_service
from api.services.scenario_orchestrator import ScenarioOrchestrator
from config.settings import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "require_auth", True)
    from main import app

    return TestClient(app)


def _user(username: str, role: str = "user") -> tuple[str, dict]:
    user = auth_service.register(username, f"{username}@example.com", "password123")
    if role != "user":
        auth_service.update_user(user["id"], {"role": role})
    token = auth_service.create_access_token(user["id"], username, role=role)
    return user["id"], {"Authorization": f"Bearer {token}"}


@pytest.fixture
def users():
    alice_id, alice = _user("alice")
    _, bob = _user("bob")
    _, admin = _user("root", role="admin")
    return {"alice_id": alice_id, "alice": alice, "bob": bob, "admin": admin}


@pytest.fixture
def alice_scenario(users, sample_organization):
    return asyncio.run(
        ScenarioOrchestrator().save_scenario(sample_organization, "alice_org.json", owner_id=users["alice_id"])
    )


@pytest.fixture
def alice_session(client, users, alice_scenario):
    resp = client.post(
        "/game/start",
        headers=users["alice"],
        json={"scenario_filename": alice_scenario, "player_role": "soc-analyst"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["game_state"]["session_id"]


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def test_scenarios_are_private_to_their_owner(client, users, alice_scenario):
    assert [s["filename"] for s in client.get("/scenarios/list", headers=users["alice"]).json()] == [alice_scenario]
    assert client.get("/scenarios/list", headers=users["bob"]).json() == []
    assert client.get(f"/scenarios/{alice_scenario}", headers=users["bob"]).status_code == 404
    assert client.delete(f"/scenarios/{alice_scenario}", headers=users["bob"]).status_code == 404
    # Bob can't start a game from Alice's scenario either.
    resp = client.post(
        "/game/start", headers=users["bob"], json={"scenario_filename": alice_scenario, "player_role": "ciso"}
    )
    assert resp.status_code == 404

    assert client.get(f"/scenarios/{alice_scenario}", headers=users["alice"]).status_code == 200
    assert client.get(f"/scenarios/{alice_scenario}", headers=users["admin"]).status_code == 200
    assert client.delete(f"/scenarios/{alice_scenario}", headers=users["alice"]).status_code == 200


def test_generated_scenario_is_owned_by_caller(client, users, monkeypatch, sample_organization):
    async def fake_generate(self, **kwargs):
        return sample_organization.model_copy(deep=True)

    monkeypatch.setattr(ScenarioOrchestrator, "generate_complete_scenario", fake_generate)
    resp = client.post("/scenarios/generate", headers=users["bob"], json={"industry": "Technology"})
    assert resp.status_code == 200
    assert len(client.get("/scenarios/list", headers=users["bob"]).json()) == 1
    assert client.get("/scenarios/list", headers=users["alice"]).json() == []


# ---------------------------------------------------------------------------
# Game sessions
# ---------------------------------------------------------------------------


def test_sessions_are_private_to_their_owner(client, users, alice_session):
    sid = alice_session
    bob = users["bob"]

    assert client.get("/game/sessions", headers=bob).json()["sessions"] == []
    assert [s["session_id"] for s in client.get("/game/sessions", headers=users["alice"]).json()["sessions"]] == [sid]

    assert client.get(f"/game/state/{sid}", headers=bob).status_code == 404
    assert client.post("/game/action", headers=bob, json={"session_id": sid, "action": "wipe"}).status_code == 404
    assert client.post("/game/hint", headers=bob, params={"session_id": sid}).status_code == 404
    assert client.post("/game/objective", headers=bob, params={"session_id": sid, "objective": "x"}).status_code == 404
    assert client.post("/game/end", headers=bob, json={"session_id": sid}).status_code == 404
    assert client.delete(f"/game/sessions/{sid}", headers=bob).status_code == 404

    # Analytics, exports and ATT&CK coverage are scoped the same way.
    for path in (
        f"/analytics/metrics/{sid}",
        f"/analytics/export/json/{sid}",
        f"/analytics/export/csv/{sid}",
        f"/analytics/export/pdf/{sid}",
        f"/analytics/aar/{sid}",
        f"/mitre/coverage/{sid}",
    ):
        assert client.get(path, headers=bob).status_code == 404, path
    assert client.post(f"/analytics/aar/{sid}", headers=bob).status_code == 404

    # Alice still has full access, and so does an admin.
    assert client.get(f"/game/state/{sid}", headers=users["alice"]).json()["owner_id"] == users["alice_id"]
    assert client.get(f"/game/state/{sid}", headers=users["admin"]).status_code == 200
    assert client.get(f"/analytics/export/json/{sid}", headers=users["alice"]).status_code == 200


def test_dashboard_and_trends_only_include_own_sessions(client, users, alice_session):
    client.post("/game/end", headers=users["alice"], json={"session_id": alice_session})
    assert client.get("/analytics/dashboard", headers=users["alice"]).json()["sessions_completed"] == 1
    assert client.get("/analytics/dashboard", headers=users["bob"]).json()["sessions_completed"] == 0
    assert client.get("/analytics/trends", headers=users["alice"]).json()["count"] == 1
    assert client.get("/analytics/trends", headers=users["bob"]).json()["count"] == 0


def test_owner_can_delete_own_session(client, users, alice_session):
    assert client.delete(f"/game/sessions/{alice_session}", headers=users["alice"]).status_code == 200
    assert client.get(f"/game/state/{alice_session}", headers=users["alice"]).status_code == 404


def test_unowned_legacy_records_are_admin_only(client, users, sample_organization):
    """Records created before ownership existed (owner_id NULL) are hidden from regular users."""
    filename = asyncio.run(ScenarioOrchestrator().save_scenario(sample_organization, "legacy.json"))
    assert client.get(f"/scenarios/{filename}", headers=users["alice"]).status_code == 404
    assert client.get(f"/scenarios/{filename}", headers=users["admin"]).status_code == 200


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------


@pytest.fixture
def public_dns(monkeypatch):
    import api.services.webhook_service as ws

    monkeypatch.setattr(ws, "_resolve_host", lambda host, port: ["93.184.216.34"])


def test_webhooks_are_private(client, users, public_dns):
    created = client.post(
        "/integrations/webhooks",
        headers=users["alice"],
        json={"url": "https://hooks.example.com/a", "events": ["game.started"], "secret": "s3cret"},
    ).json()
    hook_id = created["id"]
    assert created["user_id"] == users["alice_id"]
    assert "secret" not in created and created["secret_configured"] is True

    assert client.get("/integrations/webhooks", headers=users["bob"]).json() == []
    assert client.get(f"/integrations/webhooks/{hook_id}", headers=users["bob"]).status_code == 404
    assert (
        client.put(f"/integrations/webhooks/{hook_id}", headers=users["bob"], json={"active": False}).status_code == 404
    )
    assert client.get(f"/integrations/webhooks/{hook_id}/deliveries", headers=users["bob"]).status_code == 404
    assert client.delete(f"/integrations/webhooks/{hook_id}", headers=users["bob"]).status_code == 404
    # Bob can't register a webhook on Alice's behalf.
    resp = client.post(
        "/integrations/webhooks",
        headers=users["bob"],
        json={"url": "https://hooks.example.com/b", "events": ["game.started"], "user_id": users["alice_id"]},
    )
    assert resp.status_code == 403

    assert len(client.get("/integrations/webhooks", headers=users["alice"]).json()) == 1
    assert client.delete(f"/integrations/webhooks/{hook_id}", headers=users["alice"]).status_code == 200


def test_api_keys_are_private(client, users):
    key = client.post("/integrations/api-keys", headers=users["alice"], json={"name": "ci"}).json()
    assert key["user_id"] == users["alice_id"]

    assert client.get("/integrations/api-keys", headers=users["bob"]).json() == []
    resp = client.get("/integrations/api-keys", headers=users["bob"], params={"user_id": users["alice_id"]})
    assert resp.status_code == 403
    assert client.delete(f"/integrations/api-keys/{key['id']}", headers=users["bob"]).status_code == 404
    resp = client.post("/integrations/api-keys", headers=users["bob"], json={"name": "x", "user_id": users["alice_id"]})
    assert resp.status_code == 403

    assert [k["id"] for k in client.get("/integrations/api-keys", headers=users["alice"]).json()] == [key["id"]]
    admin_view = client.get("/integrations/api-keys", headers=users["admin"], params={"user_id": users["alice_id"]})
    assert len(admin_view.json()) == 1
    assert client.delete(f"/integrations/api-keys/{key['id']}", headers=users["alice"]).status_code == 200


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


def test_library_visibility_and_share_rights(client, users):
    added = client.post("/library/scenarios", headers=users["alice"], json={"name": "Alice's drill"}).json()
    sid = added["scenario"]["id"]
    assert added["scenario"]["author"] == "alice"
    assert added["scenario"]["is_mine"] is True
    assert "ratings" not in added["scenario"] and "owner_id" not in added["scenario"]

    # Bob can't change the visibility of Alice's scenario.
    resp = client.post(f"/library/scenarios/{sid}/share", headers=users["bob"], json={"visibility": "private"})
    assert resp.status_code == 403

    # Once private, it disappears for Bob everywhere.
    ok = client.post(f"/library/scenarios/{sid}/share", headers=users["alice"], json={"visibility": "private"})
    assert ok.status_code == 200
    assert client.get(f"/library/scenarios/{sid}", headers=users["bob"]).status_code == 404
    assert sid not in [s["id"] for s in client.get("/library/scenarios", headers=users["bob"]).json()["scenarios"]]
    assert client.get("/library/search", headers=users["bob"], params={"q": "drill"}).json()["total"] == 0
    assert client.post(f"/library/scenarios/{sid}/rate", headers=users["bob"], json={"rating": 1}).status_code == 404
    assert client.post(f"/library/scenarios/{sid}/fork", headers=users["bob"]).status_code == 404
    assert client.get(f"/library/scenarios/{sid}", headers=users["alice"]).status_code == 200


def test_library_ratings_are_one_per_user(client, users):
    sid = client.post("/library/scenarios", headers=users["alice"], json={"name": "Rated"}).json()["scenario"]["id"]
    client.post(f"/library/scenarios/{sid}/rate", headers=users["bob"], json={"rating": 1, "user_id": "sock-1"})
    result = client.post(
        f"/library/scenarios/{sid}/rate", headers=users["bob"], json={"rating": 5, "user_id": "sock-2"}
    )
    # The user_id in the body is ignored with auth on, so Bob's second vote replaces his first.
    assert result.json()["rating_count"] == 1
    assert result.json()["rating"] == 5


def test_library_fork_is_private_to_forker(client, users):
    sid = client.post("/library/scenarios", headers=users["alice"], json={"name": "Shared"}).json()["scenario"]["id"]
    fork = client.post(f"/library/scenarios/{sid}/fork", headers=users["bob"]).json()["scenario"]
    assert fork["author"] == "bob" and fork["visibility"] == "private"
    assert client.get(f"/library/scenarios/{fork['id']}", headers=users["alice"]).status_code == 404
    assert client.get(f"/library/scenarios/{fork['id']}", headers=users["bob"]).status_code == 200
