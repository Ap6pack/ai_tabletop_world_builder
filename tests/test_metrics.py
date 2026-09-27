#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Prometheus /metrics endpoint and instrumentation."""

import pytest
from fastapi.testclient import TestClient

from config.settings import settings


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def test_metrics_endpoint_exposes_http_metrics(client):
    client.get("/health")
    client.get("/game/state/does-not-exist")
    body = client.get("/metrics").text
    assert 'http_requests_total{method="GET",path="/health",status_code="200"}' in body
    # Labelled by route template, not the raw path.
    assert 'path="/game/state/{session_id}"' in body
    assert "does-not-exist" not in body
    assert "http_request_duration_seconds_bucket" in body
    assert "http_active_requests" in body
    assert "http_errors_total" in body


def test_metrics_token(client, monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "scrape-secret")
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer scrape-secret"}).status_code == 200


async def test_llm_calls_are_counted():
    from prometheus_client import REGISTRY

    from api.providers.base import BaseLLMProvider

    class FakeProvider(BaseLLMProvider):
        async def complete(self, prompt, system_message=None, temperature=0.7, max_tokens=None, **kwargs):
            return {"content": "x", "model": "m"}

        def get_model_name(self):
            return "fake-model"

        def get_provider_name(self):
            return "fake"

    labels = {"provider": "fake", "model": "fake-model", "outcome": "success"}
    before = REGISTRY.get_sample_value("llm_calls_total", labels) or 0
    await FakeProvider().complete("hi")
    assert REGISTRY.get_sample_value("llm_calls_total", labels) == before + 1
