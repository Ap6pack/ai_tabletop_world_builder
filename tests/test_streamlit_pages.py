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
