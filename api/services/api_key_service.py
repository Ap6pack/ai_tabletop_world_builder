#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
API key service for generating, verifying, and managing API keys
used by external integrations. Backed by the application database.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from api.db import ApiKeyRow, init_db, session_scope
from api.utils.logger import setup_logger

logger = setup_logger(__name__)

VALID_SCOPES = ["read", "write", "admin"]


class APIKeyService:
    """Service for managing API key lifecycle."""

    def __init__(self, storage_dir: str = "data/api_keys") -> None:
        # storage_dir is retained for backward compatibility; storage is now
        # the application database.
        init_db()

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """SHA-256 hash of a raw API key."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def create_key(self, user_id: str, name: str, scopes: list[str] = None) -> dict:
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

        row = ApiKeyRow(
            id=key_id,
            user_id=user_id,
            name=name,
            hashed_key=self._hash_key(raw_key),
            prefix=raw_key[:10],
            scopes=scopes,
            created_at=datetime.now(UTC).isoformat(),
            revoked=False,
        )
        with session_scope() as db:
            db.add(row)
            db.flush()
            result = row.to_dict()

        logger.info("Created API key %s for user %s", key_id, user_id)
        return {**result, "raw_key": raw_key}

    def verify_key(self, raw_key: str) -> dict | None:
        """Verify a raw API key and return its metadata if valid."""
        hashed = self._hash_key(raw_key)
        with session_scope() as db:
            row = db.scalar(select(ApiKeyRow).where(ApiKeyRow.hashed_key == hashed))
            if row is None or row.revoked:
                return None
            return row.to_dict()

    def revoke_key(self, key_id: str) -> bool:
        """Mark an API key as revoked."""
        with session_scope() as db:
            row = db.get(ApiKeyRow, key_id)
            if row is None:
                return False
            row.revoked = True
            row.revoked_at = datetime.now(UTC).isoformat()
        logger.info("Revoked API key %s", key_id)
        return True

    def list_keys(self, user_id: str) -> list[dict]:
        """List a user's API keys with masked values."""
        with session_scope() as db:
            rows = db.scalars(select(ApiKeyRow).where(ApiKeyRow.user_id == user_id)).all()
            return [row.to_dict() for row in rows]

    def get_key(self, key_id: str) -> dict | None:
        """Get key metadata by ID (excludes the hashed key)."""
        with session_scope() as db:
            row = db.get(ApiKeyRow, key_id)
            if row is None:
                return None
            return row.to_dict()
