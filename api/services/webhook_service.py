"""
Webhook service for registering and delivering event notifications
to external systems via HTTP callbacks.
"""
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from api.utils.logger import setup_logger

logger = setup_logger(__name__)

VALID_EVENTS = [
    "game.started", "game.ended", "aar.generated",
    "scenario.created", "user.registered",
]


class WebhookService:
    """Service for managing webhook registrations and event delivery."""

    def __init__(self, storage_dir: str = "data/webhooks") -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _path(self, webhook_id: str) -> str:
        return os.path.join(self.storage_dir, f"{webhook_id}.json")

    def _log_path(self, webhook_id: str) -> str:
        return os.path.join(self.storage_dir, f"{webhook_id}_deliveries.json")

    def register_webhook(
        self, url: str, events: List[str], user_id: str = "system", secret: str = None
    ) -> Dict:
        """Register a new webhook endpoint."""
        invalid = [e for e in events if e not in VALID_EVENTS]
        if invalid:
            raise ValueError(f"Invalid event types: {invalid}")

        webhook = {
            "id": str(uuid.uuid4()),
            "url": url,
            "events": events,
            "user_id": user_id,
            "active": True,
            "secret": secret,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._path(webhook["id"]), "w") as f:
            json.dump(webhook, f, indent=2)
        logger.info("Registered webhook %s for events %s", webhook["id"], events)
        return webhook

    def unregister_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook registration."""
        path = self._path(webhook_id)
        if not os.path.exists(path):
            return False
        os.remove(path)
        log_path = self._log_path(webhook_id)
        if os.path.exists(log_path):
            os.remove(log_path)
        logger.info("Unregistered webhook %s", webhook_id)
        return True

    def list_webhooks(self, user_id: str = None) -> List[Dict]:
        """List all webhooks, optionally filtered by user."""
        webhooks: List[Dict] = []
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json") and not fname.endswith("_deliveries.json"):
                try:
                    with open(os.path.join(self.storage_dir, fname), "r") as f:
                        data = json.load(f)
                    if user_id is None or data.get("user_id") == user_id:
                        webhooks.append(data)
                except (json.JSONDecodeError, IOError):
                    continue
        return webhooks

    def get_webhook(self, webhook_id: str) -> Optional[Dict]:
        """Get a single webhook by ID."""
        path = self._path(webhook_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def update_webhook(self, webhook_id: str, updates: Dict) -> Optional[Dict]:
        """Update a webhook's configuration."""
        webhook = self.get_webhook(webhook_id)
        if webhook is None:
            return None
        protected = {"id", "created_at", "user_id"}
        for key, value in updates.items():
            if key not in protected:
                webhook[key] = value
        with open(self._path(webhook_id), "w") as f:
            json.dump(webhook, f, indent=2)
        logger.info("Updated webhook %s", webhook_id)
        return webhook

    def deliver_event(self, event_type: str, payload: Dict) -> None:
        """Deliver an event to all matching active webhooks."""
        for webhook in self.list_webhooks():
            if not webhook.get("active", False):
                continue
            if event_type not in webhook.get("events", []):
                continue
            self._send(webhook, event_type, payload)

    def _send(self, webhook: Dict, event_type: str, payload: Dict) -> None:
        """Send a single delivery attempt."""
        body = json.dumps({"event": event_type, "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat()})
        headers = {"Content-Type": "application/json", "X-Event-Type": event_type}
        if webhook.get("secret"):
            headers["X-Signature-256"] = self._compute_signature(body, webhook["secret"])

        record = {"event": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), "url": webhook["url"]}
        try:
            resp = requests.post(webhook["url"], data=body, headers=headers, timeout=5)
            record["status_code"] = resp.status_code
            record["success"] = 200 <= resp.status_code < 300
            logger.info("Webhook %s delivered %s: %s", webhook["id"], event_type, resp.status_code)
        except Exception as exc:
            record["success"] = False
            record["error"] = str(exc)
            logger.error("Webhook %s delivery failed for %s: %s", webhook["id"], event_type, exc)

        self._append_delivery(webhook["id"], record)

    def get_delivery_log(self, webhook_id: str) -> List[Dict]:
        """Return recent delivery attempts for a webhook."""
        path = self._log_path(webhook_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _append_delivery(self, webhook_id: str, record: Dict) -> None:
        """Append a delivery record, keeping the last 100 entries."""
        entries = self.get_delivery_log(webhook_id)
        entries.append(record)
        entries = entries[-100:]
        with open(self._log_path(webhook_id), "w") as f:
            json.dump(entries, f, indent=2)

    def _compute_signature(self, payload_str: str, secret: str) -> str:
        """Compute HMAC-SHA256 signature for a payload."""
        return hmac.new(
            secret.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256
        ).hexdigest()
