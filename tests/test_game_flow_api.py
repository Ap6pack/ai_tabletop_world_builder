#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""End-to-end API tests for the scenarios, game, analytics and exercise routers."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.services.game_master_service import GameMasterService
from api.services.scenario_orchestrator import ScenarioOrchestrator


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


@pytest.fixture
def scenario(sample_organization):
    return asyncio.run(ScenarioOrchestrator().save_scenario(sample_organization, "flow.json"))


@pytest.fixture
def session_id(client, scenario, monkeypatch):
    monkeypatch.setattr(GameMasterService, "start_game", AsyncMock(return_value="An alert fires."))
    resp = client.post("/game/start", json={"scenario_filename": scenario, "player_role": "soc-analyst"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["narrative"] == "An alert fires."
    return resp.json()["game_state"]["session_id"]


# ---------------------------------------------------------------------------
# /scenarios
# ---------------------------------------------------------------------------


def test_industries(client):
    industries = client.get("/scenarios/industries").json()
    assert industries
    assert client.get(f"/scenarios/industries/{industries[0]}").status_code == 200
    assert client.get("/scenarios/industries/Underwater Basket Weaving").status_code == 404


def test_scenario_crud(client, scenario):
    listing = client.get("/scenarios/list").json()
    assert [s["filename"] for s in listing] == [scenario]
    assert client.get(f"/scenarios/{scenario}").json()["name"] == "TestCorp International"
    assert client.delete(f"/scenarios/{scenario}").status_code == 200
    assert client.get(f"/scenarios/{scenario}").status_code == 404
    assert client.delete(f"/scenarios/{scenario}").status_code == 404


def test_generate_scenario_records_duration(client, monkeypatch, sample_organization):
    async def fake_generate(self, **kwargs):
        return sample_organization.model_copy(deep=True)

    monkeypatch.setattr(ScenarioOrchestrator, "generate_complete_scenario", fake_generate)
    resp = client.post("/scenarios/generate", json={"industry": "Technology", "duration_minutes": 90})
    assert resp.status_code == 200
    assert resp.json()["metadata"]["duration_minutes"] == 90


def test_generate_scenario_errors(client, monkeypatch):
    async def bad_input(self, **kwargs):
        raise ValueError("unknown industry")

    monkeypatch.setattr(ScenarioOrchestrator, "generate_complete_scenario", bad_input)
    assert client.post("/scenarios/generate", json={"industry": "?"}).status_code == 400

    async def boom(self, **kwargs):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(ScenarioOrchestrator, "generate_complete_scenario", boom)
    assert client.post("/scenarios/generate", json={"industry": "Technology"}).status_code == 500
    assert client.post("/scenarios/generate", json={"industry": "Tech", "duration_minutes": 5}).status_code == 422


# ---------------------------------------------------------------------------
# /game
# ---------------------------------------------------------------------------


def test_start_requires_existing_scenario(client):
    resp = client.post("/game/start", json={"scenario_filename": "missing.json", "player_role": "ciso"})
    assert resp.status_code == 404


def test_full_game_flow(client, session_id, monkeypatch):
    monkeypatch.setattr(
        GameMasterService,
        "process_action",
        AsyncMock(
            return_value={
                "narrative": "You find a suspicious login.",
                "new_events": [],
                "inventory_changes": {},
                "score_change": {"points": 10, "reason": "good triage"},
                "hints": ["look at the firewall"],
            }
        ),
    )
    monkeypatch.setattr(GameMasterService, "generate_hint", AsyncMock(return_value="Check the proxy logs."))

    action = client.post("/game/action", json={"session_id": session_id, "action": "Check SIEM logins"})
    assert action.status_code == 200
    assert action.json()["narrative"].startswith("You find a suspicious login.")
    assert action.json()["game_state"]["score"] == 10

    assert client.post("/game/hint", params={"session_id": session_id}).json() == {"hint": "Check the proxy logs."}
    state = client.get(f"/game/state/{session_id}").json()
    objective = state["objectives"][0]["description"] if state["objectives"] else "Contain the threat"
    resp = client.post("/game/objective", params={"session_id": session_id, "objective": objective})
    assert resp.status_code == 200

    sessions = client.get("/game/sessions", params={"status": "in-progress"}).json()["sessions"]
    assert [s["session_id"] for s in sessions] == [session_id]

    # AAR and PDF need a finished session.
    assert client.post(f"/analytics/aar/{session_id}").status_code == 400
    assert client.get(f"/analytics/export/pdf/{session_id}").status_code == 400
    assert client.get(f"/analytics/aar/{session_id}").status_code == 400

    ended = client.post("/game/end", json={"session_id": session_id, "status": "completed"})
    assert ended.json()["status"] == "completed"

    # Actions on a finished session are refused.
    assert client.post("/game/action", json={"session_id": session_id, "action": "x"}).status_code == 404


def test_missing_session_everywhere(client):
    assert client.get("/game/state/nope").status_code == 404
    assert client.post("/game/action", json={"session_id": "nope", "action": "x"}).status_code == 404
    assert client.post("/game/end", json={"session_id": "nope"}).status_code == 404
    assert client.delete("/game/sessions/nope").status_code == 404
    for path in ("aar/nope", "metrics/nope", "export/json/nope", "export/csv/nope", "export/pdf/nope"):
        assert client.get(f"/analytics/{path}").status_code == 404


# ---------------------------------------------------------------------------
# /analytics
# ---------------------------------------------------------------------------


@pytest.fixture
def finished_session(client, session_id):
    client.post("/game/end", json={"session_id": session_id})
    return session_id


def test_aar_and_exports(client, finished_session):
    sid = finished_session
    aar = client.post(f"/analytics/aar/{sid}")
    assert aar.status_code == 200
    assert aar.json()["session_id"] == sid
    assert client.get(f"/analytics/aar/{sid}").json()["overall_grade"] == aar.json()["overall_grade"]

    metrics = client.get(f"/analytics/metrics/{sid}").json()
    assert metrics["session_id"] == sid and metrics["metrics"]

    exported = client.get(f"/analytics/export/json/{sid}")
    assert exported.status_code == 200
    csv_export = client.get(f"/analytics/export/csv/{sid}").json()
    assert csv_export["columns"][0] == "timestamp"
    assert csv_export["total_events"] == len(csv_export["rows"])

    pdf = client.get(f"/analytics/export/pdf/{sid}")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


@pytest.mark.parametrize("metric", ["score", "time_elapsed", "objectives_completed", "total_cost", "unknown"])
def test_trends(client, finished_session, metric):
    trends = client.get("/analytics/trends", params={"metric": metric}).json()
    assert trends["metric"] == metric
    assert trends["count"] == 1
    assert "value" in trends["data_points"][0]


def test_dashboard(client, finished_session):
    dashboard = client.get("/analytics/dashboard").json()
    assert dashboard["sessions_completed"] == 1
    assert client.get("/analytics/dashboard", params={"status": "in-progress"}).json()["sessions_completed"] == 0


def test_delete_session(client, session_id):
    assert client.delete(f"/game/sessions/{session_id}").status_code == 200
    assert client.get(f"/game/state/{session_id}").status_code == 404


# ---------------------------------------------------------------------------
# /exercise (auth disabled: single trusted user, seats given in the request)
# ---------------------------------------------------------------------------


def test_exercise_flow_without_auth(client, scenario):
    created = client.post("/exercise/create", json={"name": "Drill", "scenario_filename": scenario}).json()
    ex = created["exercise_id"]
    blue = next(t["team_id"] for t in created["teams"] if t["type"] == "blue")

    assert client.post(f"/exercise/{ex}/join", json={"team_id": blue}).status_code == 422  # no name, no login
    seat = client.post(f"/exercise/{ex}/join", json={"team_id": blue, "display_name": "Ana"}).json()
    assert client.post(f"/exercise/{ex}/join", json={"team_id": "nope", "display_name": "Bo"}).status_code == 400

    assert client.post(f"/exercise/{ex}/advance").json()["phase"] == "active"
    assert client.post(f"/exercise/{ex}/action", json={"action": "scan"}).status_code == 422
    acted = client.post(
        f"/exercise/{ex}/action", json={"action": "scan", "team_id": blue, "member_id": seat["member_id"]}
    )
    assert acted.status_code == 200

    assert "team_actions" in client.get(f"/exercise/{ex}/state").json()
    assert client.get(f"/exercise/{ex}/state", params={"team_id": blue}).json()["team"]["team_id"] == blue
    assert client.get(f"/exercise/{ex}/state", params={"team_id": "nope"}).status_code == 404
    poll = client.get(f"/exercise/{ex}/poll").json()
    assert poll["changed"] in (True, False)
    assert client.get(f"/exercise/{ex}/poll", params={"since_version": 10_000}).json()["changed"] is False

    assert client.get("/exercise/list").json()["exercises"][0]["exercise_id"] == ex
    assert client.post(f"/exercise/{ex}/end").json()["phase"] == "completed"


def test_exercise_missing(client):
    for method, path in [("get", "state"), ("get", "poll"), ("post", "advance"), ("post", "pause"), ("post", "end")]:
        assert client.request(method, f"/exercise/nope/{path}").status_code == 404
    assert client.post("/exercise/nope/join", json={"team_id": "t", "display_name": "x"}).status_code == 404
    assert client.post("/exercise/create", json={"name": "x", "scenario_filename": "missing.json"}).status_code == 404
