#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Webhook service for registering and delivering event notifications
to external systems via HTTP callbacks. Backed by the application database.
"""

import hashlib
import hmac
import ipaddress
import json
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from urllib.parse import urlsplit

import requests
from sqlalchemy import select

from api.db import WebhookDeliveryRow, WebhookRow, init_db, session_scope
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

VALID_EVENTS = [
    "game.started",
    "game.ended",
    "aar.generated",
    "scenario.created",
    "user.registered",
]

# Number of most-recent delivery attempts retained per webhook.
DELIVERY_LOG_LIMIT = 100

# Deliveries run off the request path so a slow receiver can't stall the API.
_delivery_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="webhook")


class UnsafeWebhookURLError(ValueError):
    """Raised when a webhook URL is not a public https endpoint."""


def _resolve_host(host: str, port: int) -> list[str]:
    """Return every IP address ``host`` resolves to (patched in tests)."""
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


def _is_public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def validate_webhook_url(url: str) -> None:
    """Reject webhook URLs that could reach internal services (SSRF).

    Only ``https`` URLs are allowed, and every address the host resolves to
    must be publicly routable: loopback, private (RFC 1918 / ULA), link-local
    (including cloud metadata at 169.254.169.254), and other reserved ranges
    are refused. Called at registration and again right before each delivery,
    so a DNS record changed after registration is caught too.
    """
    try:
        parts = urlsplit(url)
        port = parts.port or 443
    except ValueError as exc:
        raise UnsafeWebhookURLError(f"Invalid webhook URL: {exc}") from exc
    if parts.scheme != "https":
        raise UnsafeWebhookURLError("Webhook URL must use https")
    if not parts.hostname:
        raise UnsafeWebhookURLError("Webhook URL must include a host")
    if parts.username or parts.password:
        raise UnsafeWebhookURLError("Webhook URL must not contain credentials")
    try:
        addresses = _resolve_host(parts.hostname, port)
    except (OSError, UnicodeError) as exc:
        raise UnsafeWebhookURLError(f"Webhook host could not be resolved: {parts.hostname}") from exc
    if not addresses:
        raise UnsafeWebhookURLError(f"Webhook host could not be resolved: {parts.hostname}")
    for address in addresses:
        if not _is_public_ip(address):
            raise UnsafeWebhookURLError("Webhook URL must point to a public address")


class WebhookService:
    """Service for managing webhook registrations and event delivery."""

    def __init__(self, storage_dir: str = "data/webhooks") -> None:
        # storage_dir is retained for backward compatibility; storage is now
        # the application database.
        init_db()

    def register_webhook(self, url: str, events: list[str], user_id: str = "system", secret: str = None) -> dict:
        """Register a new webhook endpoint."""
        invalid = [e for e in events if e not in VALID_EVENTS]
        if invalid:
            raise ValueError(f"Invalid event types: {invalid}")
        validate_webhook_url(url)

        row = WebhookRow(
            id=str(uuid.uuid4()),
            url=url,
            events=events,
            user_id=user_id,
            active=True,
            secret=secret,
            created_at=datetime.now(UTC).isoformat(),
        )
        with session_scope() as db:
            db.add(row)
            db.flush()
            result = row.to_dict()
        logger.info("Registered webhook %s for events %s", result["id"], events)
        return result

    def unregister_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook registration and its delivery log."""
        with session_scope() as db:
            row = db.get(WebhookRow, webhook_id)
            if row is None:
                return False
            db.delete(row)
            for delivery in db.scalars(
                select(WebhookDeliveryRow).where(WebhookDeliveryRow.webhook_id == webhook_id)
            ).all():
                db.delete(delivery)
        logger.info("Unregistered webhook %s", webhook_id)
        return True

    def list_webhooks(self, user_id: str = None) -> list[dict]:
        """List all webhooks, optionally filtered by user."""
        stmt = select(WebhookRow)
        if user_id is not None:
            stmt = stmt.where(WebhookRow.user_id == user_id)
        with session_scope() as db:
            return [row.to_dict() for row in db.scalars(stmt).all()]

    def get_webhook(self, webhook_id: str) -> dict | None:
        """Get a single webhook by ID."""
        with session_scope() as db:
            row = db.get(WebhookRow, webhook_id)
            return row.to_dict() if row is not None else None

    def update_webhook(self, webhook_id: str, updates: dict) -> dict | None:
        """Update a webhook's configuration."""
        protected = {"id", "created_at", "user_id"}
        if "url" in updates:
            validate_webhook_url(updates["url"])
        if "events" in updates:
            invalid = [e for e in updates["events"] if e not in VALID_EVENTS]
            if invalid:
                raise ValueError(f"Invalid event types: {invalid}")
        with session_scope() as db:
            row = db.get(WebhookRow, webhook_id)
            if row is None:
                return None
            for key, value in updates.items():
                if key not in protected and hasattr(row, key):
                    setattr(row, key, value)
            db.flush()
            result = row.to_dict()
        logger.info("Updated webhook %s", webhook_id)
        return result

    def deliver_event(self, event_type: str, payload: dict) -> None:
        """Queue an event for background delivery to all matching active webhooks."""
        _delivery_executor.submit(self.deliver_event_now, event_type, payload)

    def deliver_event_now(self, event_type: str, payload: dict) -> None:
        """Deliver an event synchronously (runs on the background executor)."""
        for webhook in self.list_webhooks():
            if not webhook.get("active", False):
                continue
            if event_type not in webhook.get("events", []):
                continue
            self._send(webhook, event_type, payload)

    def _send(self, webhook: dict, event_type: str, payload: dict) -> None:
        """Send a single delivery attempt."""
        body = json.dumps({"event": event_type, "payload": payload, "timestamp": datetime.now(UTC).isoformat()})
        headers = {"Content-Type": "application/json", "X-Event-Type": event_type}
        if webhook.get("secret"):
            headers["X-Signature-256"] = self._compute_signature(body, webhook["secret"])

        record = {"event": event_type, "timestamp": datetime.now(UTC).isoformat(), "url": webhook["url"]}
        try:
            # Re-check at delivery time: the host's DNS may have changed since
            # registration. Redirects are not followed, so a public endpoint
            # can't bounce the request to an internal one.
            validate_webhook_url(webhook["url"])
            resp = requests.post(webhook["url"], data=body, headers=headers, timeout=5, allow_redirects=False)
            record["status_code"] = resp.status_code
            record["success"] = 200 <= resp.status_code < 300
            logger.info("Webhook %s delivered %s: %s", webhook["id"], event_type, resp.status_code)
        except Exception as exc:
            record["success"] = False
            record["error"] = str(exc)
            logger.error("Webhook %s delivery failed for %s: %s", webhook["id"], event_type, exc)

        self._append_delivery(webhook["id"], record)

    def get_delivery_log(self, webhook_id: str) -> list[dict]:
        """Return recent delivery attempts for a webhook (oldest to newest)."""
        with session_scope() as db:
            rows = db.scalars(
                select(WebhookDeliveryRow)
                .where(WebhookDeliveryRow.webhook_id == webhook_id)
                .order_by(WebhookDeliveryRow.id)
            ).all()
            return [row.record for row in rows]

    def _append_delivery(self, webhook_id: str, record: dict) -> None:
        """Append a delivery record, keeping the last ``DELIVERY_LOG_LIMIT`` entries."""
        with session_scope() as db:
            db.add(WebhookDeliveryRow(webhook_id=webhook_id, record=record))
            db.flush()
            ids = db.scalars(
                select(WebhookDeliveryRow.id)
                .where(WebhookDeliveryRow.webhook_id == webhook_id)
                .order_by(WebhookDeliveryRow.id)
            ).all()
            excess = len(ids) - DELIVERY_LOG_LIMIT
            for old_id in ids[:excess] if excess > 0 else []:
                db.delete(db.get(WebhookDeliveryRow, old_id))

    def _compute_signature(self, payload_str: str, secret: str) -> str:
        """Compute HMAC-SHA256 signature for a payload."""
        return hmac.new(secret.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
