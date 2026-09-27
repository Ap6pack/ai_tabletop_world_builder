#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for webhook registration, SSRF protection, and delivery."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import api.services.webhook_service as ws
from api.services.webhook_service import UnsafeWebhookURLError, WebhookService, validate_webhook_url

# Hostname -> addresses returned by the patched resolver.
DNS = {
    "hooks.example.com": ["93.184.216.34"],
    "internal.example.com": ["10.0.0.5"],
    "mixed.example.com": ["93.184.216.34", "192.168.1.10"],
    "rebind.example.com": ["93.184.216.34"],
}


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    def resolve(host, port):
        if host in DNS:
            return list(DNS[host])
        try:
            import ipaddress

            ipaddress.ip_address(host.strip("[]"))
            return [host.strip("[]")]
        except ValueError:
            raise OSError("unknown host") from None

    monkeypatch.setattr(ws, "_resolve_host", resolve)
    return DNS


@pytest.fixture
def service():
    return WebhookService()


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/hook",
        "https://localhost.invalid/hook",
        "https://169.254.169.254/latest/meta-data/",
        "https://10.1.2.3/hook",
        "https://172.16.0.1/hook",
        "https://192.168.0.1/hook",
        "https://[::1]/hook",
        "https://[fe80::1]/hook",
        "https://[fd00::1]/hook",
        "https://[::ffff:127.0.0.1]/hook",
        "https://0.0.0.0/hook",
        "https://internal.example.com/hook",
        "https://mixed.example.com/hook",
        "http://hooks.example.com/hook",
        "ftp://hooks.example.com/hook",
        "https://user:pw@hooks.example.com/hook",
        "https:///nohost",
        "not a url",
    ],
)
def test_unsafe_urls_rejected(url):
    with pytest.raises(UnsafeWebhookURLError):
        validate_webhook_url(url)


def test_public_https_url_accepted():
    validate_webhook_url("https://hooks.example.com/hook")
    validate_webhook_url("https://93.184.216.34:8443/hook")


def test_register_rejects_private_address(service):
    with pytest.raises(ValueError, match="public address"):
        service.register_webhook("https://169.254.169.254/", ["game.started"])
    assert service.list_webhooks() == []


def test_update_rejects_private_address(service):
    hook = service.register_webhook("https://hooks.example.com/hook", ["game.started"])
    with pytest.raises(ValueError):
        service.update_webhook(hook["id"], {"url": "https://127.0.0.1/"})
    assert service.get_webhook(hook["id"])["url"] == "https://hooks.example.com/hook"


def test_delivery_rechecks_address(service, fake_dns, monkeypatch):
    """A host re-pointed at an internal address after registration is refused at send time."""
    hook = service.register_webhook("https://rebind.example.com/hook", ["game.started"])
    fake_dns["rebind.example.com"] = ["127.0.0.1"]
    post = MagicMock()
    monkeypatch.setattr(ws.requests, "post", post)

    service.deliver_event_now("game.started", {"id": 1})

    post.assert_not_called()
    log = service.get_delivery_log(hook["id"])
    assert log[-1]["success"] is False
    assert "public address" in log[-1]["error"]


def test_delivery_signs_and_disables_redirects(service, monkeypatch):
    hook = service.register_webhook("https://hooks.example.com/hook", ["game.ended"], secret="s3cret")
    post = MagicMock(return_value=MagicMock(status_code=204))
    monkeypatch.setattr(ws.requests, "post", post)

    service.deliver_event_now("game.ended", {"id": 1})
    service.deliver_event_now("game.started", {"id": 2})  # not subscribed

    assert post.call_count == 1
    kwargs = post.call_args.kwargs
    assert kwargs["allow_redirects"] is False
    assert kwargs["headers"]["X-Signature-256"] == service._compute_signature(kwargs["data"], "s3cret")
    assert service.get_delivery_log(hook["id"])[-1]["success"] is True


def test_deliver_event_runs_in_background(service, monkeypatch):
    submitted = []
    monkeypatch.setattr(ws._delivery_executor, "submit", lambda fn, *args: submitted.append((fn, args)))
    service.deliver_event("game.started", {"id": 1})
    assert submitted == [(service.deliver_event_now, ("game.started", {"id": 1}))]


def test_api_refuses_private_webhook():
    from main import app

    client = TestClient(app)
    resp = client.post("/integrations/webhooks", json={"url": "https://127.0.0.1/x", "events": ["game.started"]})
    assert resp.status_code == 400
    ok = client.post("/integrations/webhooks", json={"url": "https://hooks.example.com/x", "events": ["game.started"]})
    assert ok.status_code == 201
    bad_update = client.put(f"/integrations/webhooks/{ok.json()['id']}", json={"url": "https://10.0.0.1/"})
    assert bad_update.status_code == 400
