#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Exercise role enforcement: identity comes from the login, never from the request."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from api.middleware.auth import auth_service
from api.services.scenario_orchestrator import ScenarioOrchestrator
from config.settings import settings


def _user(username: str) -> tuple[str, dict]:
    user = auth_service.register(username, f"{username}@example.com", "password123")
    token = auth_service.create_access_token(user["id"], username)
    return user["id"], {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "require_auth", True)
    from main import app

    return TestClient(app)


@pytest.fixture
def exercise(client, sample_organization):
    """Facilitator creates a blue/red/white exercise; blue and red players join."""
    fac_id, fac = _user("facil")
    _, blue = _user("bluey")
    _, red = _user("reddy")
    _, outsider = _user("outsider")
    scenario = asyncio.run(ScenarioOrchestrator().save_scenario(sample_organization, "ex.json", owner_id=fac_id))

    created = client.post(
        "/exercise/create",
        headers=fac,
        json={
            "name": "Drill",
            "scenario_filename": scenario,
            "teams": [
                {"name": "Blue", "team_type": "blue"},
                {"name": "Red", "team_type": "red"},
                {"name": "White", "team_type": "white"},
            ],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    teams = {t["type"]: t["team_id"] for t in body["teams"]}
    ex_id = body["exercise_id"]

    blue_seat = client.post(f"/exercise/{ex_id}/join", headers=blue, json={"team_id": teams["blue"]}).json()
    red_seat = client.post(f"/exercise/{ex_id}/join", headers=red, json={"team_id": teams["red"]}).json()
    assert blue_seat["display_name"] == "bluey"
    assert client.post(f"/exercise/{ex_id}/advance", headers=fac).status_code == 200  # start round 1
    return {
        "id": ex_id,
        "teams": teams,
        "fac": fac,
        "blue": blue,
        "red": red,
        "outsider": outsider,
        "blue_seat": blue_seat,
        "red_seat": red_seat,
    }


FACILITATOR_ONLY = [
    ("post", "advance", None),
    ("post", "pause", None),
    ("post", "end", None),
    ("post", "inject", {"title": "Breaking news", "content": "Leak reported"}),
]


@pytest.mark.parametrize(("method", "path", "body"), FACILITATOR_ONLY)
def test_players_cannot_use_facilitator_controls(client, exercise, method, path, body):
    for player in ("blue", "red"):
        # Passing the facilitator's team ID as the old query parameter no longer helps.
        resp = client.request(
            method,
            f"/exercise/{exercise['id']}/{path}",
            headers=exercise[player],
            params={"facilitator_id": exercise["teams"]["white"]},
            json=body,
        )
        assert resp.status_code == 403, (player, path)
    resp = client.request(method, f"/exercise/{exercise['id']}/{path}", headers=exercise["outsider"], json=body)
    assert resp.status_code == 404


def test_facilitator_controls_work(client, exercise):
    ex, fac = exercise["id"], exercise["fac"]
    assert client.post(f"/exercise/{ex}/advance", headers=fac).json()["current_round"] == 2
    assert client.post(f"/exercise/{ex}/inject", headers=fac, json={"title": "t", "content": "c"}).status_code == 200
    assert client.post(f"/exercise/{ex}/pause", headers=fac).json()["phase"] == "paused"
    assert client.post(f"/exercise/{ex}/end", headers=fac).json()["phase"] == "completed"


def test_players_act_only_as_their_own_seat(client, exercise):
    ex = exercise["id"]
    # Blue submits: the seat comes from the login.
    ok = client.post(f"/exercise/{ex}/action", headers=exercise["blue"], json={"action": "Check the SIEM"})
    assert ok.status_code == 200
    assert ok.json()["team_id"] == exercise["teams"]["blue"]

    # Red can't act for Blue's team or Blue's member.
    as_blue_team = client.post(
        f"/exercise/{ex}/action",
        headers=exercise["red"],
        json={"action": "Disable logging", "team_id": exercise["teams"]["blue"]},
    )
    assert as_blue_team.status_code == 403
    as_blue_member = client.post(
        f"/exercise/{ex}/action",
        headers=exercise["red"],
        json={"action": "x", "member_id": exercise["blue_seat"]["member_id"]},
    )
    assert as_blue_member.status_code == 403

    # Outsiders and the (seatless) facilitator can't submit team actions.
    assert client.post(f"/exercise/{ex}/action", headers=exercise["outsider"], json={"action": "x"}).status_code == 404
    assert client.post(f"/exercise/{ex}/action", headers=exercise["fac"], json={"action": "x"}).status_code == 403


def test_players_cannot_read_other_teams(client, exercise):
    ex = exercise["id"]
    client.post(f"/exercise/{ex}/action", headers=exercise["blue"], json={"action": "Isolate host BLUE-SECRET"})

    # Red asking for Blue's view is refused; red's own view hides Blue's actions.
    assert (
        client.get(f"/exercise/{ex}/state", headers=exercise["red"], params={"team_id": exercise["teams"]["blue"]})
    ).status_code == 403
    red_view = client.get(f"/exercise/{ex}/state", headers=exercise["red"])
    assert red_view.status_code == 200
    assert red_view.json()["team"]["team_id"] == exercise["teams"]["red"]
    assert "BLUE-SECRET" not in red_view.text
    assert "team_actions" not in red_view.json()  # not the full state

    red_poll = client.get(f"/exercise/{ex}/poll", headers=exercise["red"])
    assert "BLUE-SECRET" not in red_poll.text

    # Blue sees its own action; the facilitator sees everything.
    assert "BLUE-SECRET" in client.get(f"/exercise/{ex}/state", headers=exercise["blue"]).text
    full = client.get(f"/exercise/{ex}/state", headers=exercise["fac"]).json()
    assert "team_actions" in full
    assert "BLUE-SECRET" in client.get(f"/exercise/{ex}/poll", headers=exercise["fac"]).text

    # Outsiders get nothing.
    assert client.get(f"/exercise/{ex}/state", headers=exercise["outsider"]).status_code == 404
    assert client.get(f"/exercise/{ex}/poll", headers=exercise["outsider"]).status_code == 404


def test_one_seat_per_user(client, exercise):
    resp = client.post(
        f"/exercise/{exercise['id']}/join", headers=exercise["red"], json={"team_id": exercise["teams"]["blue"]}
    )
    assert resp.status_code == 400


def test_exercise_list_is_scoped(client, exercise):
    for who in ("fac", "blue", "red"):
        ids = [e["exercise_id"] for e in client.get("/exercise/list", headers=exercise[who]).json()["exercises"]]
        assert ids == [exercise["id"]], who
        assert "participant_ids" not in client.get("/exercise/list", headers=exercise[who]).json()["exercises"][0]
    assert client.get("/exercise/list", headers=exercise["outsider"]).json()["exercises"] == []


def test_players_cannot_open_the_exercise_game_session(client, exercise):
    full = client.get(f"/exercise/{exercise['id']}/state", headers=exercise["fac"]).json()
    session_id = full["game_state"]["session_id"]
    assert client.get(f"/game/state/{session_id}", headers=exercise["red"]).status_code == 404
    assert client.get(f"/game/state/{session_id}", headers=exercise["fac"]).status_code == 200


def test_cannot_create_exercise_from_someone_elses_scenario(client, exercise):
    resp = client.post(
        "/exercise/create", headers=exercise["outsider"], json={"name": "x", "scenario_filename": "ex.json"}
    )
    assert resp.status_code == 404


def test_team_list_is_the_invitation(client, exercise):
    ex = exercise["id"]
    invitee = client.get(f"/exercise/{ex}/teams", headers=exercise["outsider"]).json()
    assert {t["team_type"] for t in invitee["teams"]} == {"blue", "red", "white"}
    assert invitee["my_seat"] is None and invitee["is_facilitator"] is False
    assert "game_state" not in invitee

    blue = client.get(f"/exercise/{ex}/teams", headers=exercise["blue"]).json()
    assert blue["my_seat"]["member_id"] == exercise["blue_seat"]["member_id"]
    assert client.get(f"/exercise/{ex}/teams", headers=exercise["fac"]).json()["is_facilitator"] is True
    assert client.get("/exercise/nope/teams", headers=exercise["blue"]).status_code == 404
