#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for the Streamlit UI using streamlit.testing's AppTest.

Every page is rendered against the real FastAPI app in-process: HTTP calls made
through ``requests`` are routed to a TestClient, so no servers or network are
needed. A page passes when it renders without raising.
"""

import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

# Imported up front: while a page runs, the UI's own `config` module shadows the API's.
from api.middleware.auth import auth_service
from config.settings import settings

APP_DIR = Path(__file__).resolve().parent.parent / "app"
PAGES = [APP_DIR / "Home.py", *sorted((APP_DIR / "pages").glob("*.py"))]


class _InProcessBackend:
    """Stand-in for requests.get/post/... that forwards to the FastAPI app."""

    def __init__(self, client: TestClient):
        self.client = client
        self.calls: list[tuple[str, str]] = []
        self.errors: list[tuple[str, str, int]] = []

    def request(self, method, url, params=None, json=None, data=None, headers=None, timeout=None, **_):
        parts = urlsplit(url)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        self.calls.append((method.upper(), parts.path))
        resp = self.client.request(method, path, params=params, json=json, data=data, headers=headers)
        if resp.status_code >= 400:
            self.errors.append((method.upper(), parts.path, resp.status_code))
        out = requests.models.Response()
        out.status_code = resp.status_code
        out._content = resp.content
        out.headers.update(resp.headers)
        out.url = url
        out.encoding = "utf-8"
        return out

    def verb(self, method):
        return lambda url, **kwargs: self.request(method, url, **kwargs)


# The UI has its own top-level modules (config, constants, utils) that share
# names with the API's packages; pages expect app/ first on sys.path.
_UI_MODULES = ("config", "constants", "utils")


@pytest.fixture
def ui_imports():
    """Run a page with the UI's own modules importable, then restore the API's."""
    saved = {name: mod for name, mod in sys.modules.items() if name.split(".")[0] in _UI_MODULES}
    for name in saved:
        del sys.modules[name]
    sys.path.insert(0, str(APP_DIR))
    try:
        yield
    finally:
        sys.path.remove(str(APP_DIR))
        for name in [n for n in sys.modules if n.split(".")[0] in _UI_MODULES]:
            del sys.modules[name]
        sys.modules.update(saved)


@pytest.fixture
def backend(monkeypatch):
    from main import app

    fake = _InProcessBackend(TestClient(app))
    monkeypatch.setattr(requests, "request", fake.request)
    for method in ("get", "post", "put", "delete", "patch"):
        monkeypatch.setattr(requests, method, fake.verb(method))
    return fake


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_renders_against_api(page, backend, ui_imports):
    at = AppTest.from_file(str(page), default_timeout=30)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    # Server errors mean the page and API disagree about a request.
    assert not [c for c in backend.errors if c[2] >= 500], backend.errors


def test_home_talks_to_the_api(backend, ui_imports):
    AppTest.from_file(str(APP_DIR / "Home.py"), default_timeout=30).run()
    assert ("GET", "/health") in backend.calls


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_renders_when_api_is_down(page, monkeypatch, ui_imports):
    def down(*args, **kwargs):
        raise requests.exceptions.ConnectionError("API unreachable")

    monkeypatch.setattr(requests, "request", down)
    for method in ("get", "post", "put", "delete", "patch"):
        monkeypatch.setattr(requests, method, down)

    at = AppTest.from_file(str(page), default_timeout=30)
    at.run()
    assert not at.exception, [e.message for e in at.exception]


# ---------------------------------------------------------------------------
# REQUIRE_AUTH=true
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setattr(settings, "require_auth", True)


@pytest.fixture
def login_tokens(auth_on):
    user = auth_service.register("uiuser", "ui@example.com", "password123")
    return {
        "auth_token": auth_service.create_access_token(user["id"], "uiuser"),
        "refresh_token": auth_service.create_refresh_token(user["id"]),
        "current_user": {k: v for k, v in user.items() if k != "hashed_password"},
    }


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_works_when_logged_in_with_auth_required(page, backend, ui_imports, login_tokens):
    at = AppTest.from_file(str(page), default_timeout=30)
    for key, value in login_tokens.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    # Every call carried the token: nothing was rejected as unauthenticated.
    assert not [c for c in backend.errors if c[2] == 401], backend.errors
    assert not [c for c in backend.errors if c[2] >= 500], backend.errors


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_asks_for_login_when_auth_required(page, backend, ui_imports, auth_on):
    at = AppTest.from_file(str(page), default_timeout=30)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    if any(status == 401 for *_, status in backend.errors):
        assert any("sign in" in w.value.lower() for w in at.warning), "401s must lead to a sign-in prompt"


def test_expired_access_token_is_refreshed(backend, ui_imports, login_tokens):
    at = AppTest.from_file(str(APP_DIR / "pages" / "4_Session_Manager.py"), default_timeout=30)
    at.session_state["auth_token"] = "expired-or-garbage"
    at.session_state["refresh_token"] = login_tokens["refresh_token"]
    at.run()
    assert not at.exception
    assert ("POST", "/auth/refresh") in backend.calls
    assert at.session_state["auth_token"] not in (None, "expired-or-garbage")
    assert not any("sign in" in w.value.lower() for w in at.warning)


def test_failed_refresh_clears_login_and_prompts(backend, ui_imports, auth_on):
    at = AppTest.from_file(str(APP_DIR / "pages" / "4_Session_Manager.py"), default_timeout=30)
    at.session_state["auth_token"] = "expired"
    at.session_state["refresh_token"] = "also-bad"
    at.run()
    assert not at.exception
    assert at.session_state["auth_token"] is None
    assert any("session has expired" in w.value.lower() for w in at.warning)


def test_exercise_join_flow_with_auth(backend, ui_imports, login_tokens, sample_organization):
    """A logged-in invitee can load an exercise's teams on the Play page before joining."""
    import asyncio

    from api.models.exercise_models import ExerciseConfig
    from api.services.exercise_orchestrator import ExerciseOrchestrator
    from api.services.scenario_orchestrator import ScenarioOrchestrator

    asyncio.run(ScenarioOrchestrator().save_scenario(sample_organization, "ui.json"))
    state = asyncio.run(
        ExerciseOrchestrator().create_exercise(ExerciseConfig(name="UI drill", scenario_filename="ui.json"))
    )

    at = AppTest.from_file(str(APP_DIR / "pages" / "11_Exercise_Play.py"), default_timeout=30)
    for key, value in login_tokens.items():
        at.session_state[key] = value
    at.session_state["exercise_id"] = state.exercise_id
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert ("GET", f"/exercise/{state.exercise_id}/teams") in backend.calls
    assert not backend.errors, backend.errors
    assert at.selectbox, "the team picker should be shown"
