"""
API key service for generating, verifying, and managing API keys
used by external integrations.
"""
import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from api.utils.logger import setup_logger

logger = setup_logger(__name__)

VALID_SCOPES = ["read", "write", "admin"]


class APIKeyService:
    """Service for managing API key lifecycle."""

    def __init__(self, storage_dir: str = "data/api_keys") -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _path(self, key_id: str) -> str:
        return os.path.join(self.storage_dir, f"{key_id}.json")

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """SHA-256 hash of a raw API key."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def create_key(
        self, user_id: str, name: str, scopes: List[str] = None
    ) -> Dict:
        """
        Generate a new API key.

        Returns the key metadata including the raw key (shown only once).
        """
        scopes = scopes or ["read"]
        invalid = [s for s in scopes if s not in VALID_SCOPES]
        if invalid:
            raise ValueError(f"Invalid scopes: {invalid}")

        raw_key = "wg_" + secrets.token_hex(32)
        key_id = str(uuid.uuid4())

        key_data = {
            "id": key_id,
            "user_id": user_id,
            "name": name,
            "hashed_key": self._hash_key(raw_key),
            "prefix": raw_key[:10],
            "scopes": scopes,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "revoked": False,
        }
        with open(self._path(key_id), "w") as f:
            json.dump(key_data, f, indent=2)

        logger.info("Created API key %s for user %s", key_id, user_id)
        return {**key_data, "raw_key": raw_key}

    def verify_key(self, raw_key: str) -> Optional[Dict]:
        """Verify a raw API key and return its metadata if valid."""
        hashed = self._hash_key(raw_key)
        for fname in os.listdir(self.storage_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.storage_dir, fname), "r") as f:
                    data = json.load(f)
                if data.get("hashed_key") == hashed and not data.get("revoked"):
                    safe = {k: v for k, v in data.items() if k != "hashed_key"}
                    return safe
            except (json.JSONDecodeError, IOError):
                continue
        return None

    def revoke_key(self, key_id: str) -> bool:
        """Mark an API key as revoked."""
        key_data = self._load(key_id)
        if key_data is None:
            return False
        key_data["revoked"] = True
        key_data["revoked_at"] = datetime.now(timezone.utc).isoformat()
        with open(self._path(key_id), "w") as f:
            json.dump(key_data, f, indent=2)
        logger.info("Revoked API key %s", key_id)
        return True

    def list_keys(self, user_id: str) -> List[Dict]:
        """List a user's API keys with masked values."""
        keys: List[Dict] = []
        for fname in os.listdir(self.storage_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.storage_dir, fname), "r") as f:
                    data = json.load(f)
                if data.get("user_id") == user_id:
                    safe = {k: v for k, v in data.items() if k != "hashed_key"}
                    keys.append(safe)
            except (json.JSONDecodeError, IOError):
                continue
        return keys

    def get_key(self, key_id: str) -> Optional[Dict]:
        """Get key metadata by ID (excludes the hashed key)."""
        data = self._load(key_id)
        if data is None:
            return None
        return {k: v for k, v in data.items() if k != "hashed_key"}

    def _load(self, key_id: str) -> Optional[Dict]:
        """Load raw key data from disk."""
        path = self._path(key_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            logger.error("Failed to load API key %s: %s", key_id, exc)
            return None
