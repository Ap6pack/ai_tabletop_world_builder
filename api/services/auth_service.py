#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Authentication service for user management with Argon2id password hashing
and JWT token generation/verification. Backed by the application database.
"""

import re
import uuid
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt
from sqlalchemy import select

from api.db import UserRow, init_db, session_scope
from api.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)


def _safe(user: dict) -> dict:
    """Return a user dict without the password hash."""
    return {k: v for k, v in user.items() if k != "hashed_password"}


class AuthService:
    """Handles user authentication, registration, and token management."""

    def __init__(self) -> None:
        """Initialize auth service with database-backed user storage."""
        init_db()
        self.hasher = PasswordHasher()
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days

    def register(
        self,
        username: str,
        email: str,
        password: str,
        display_name: str = "",
    ) -> dict:
        """
        Register a new user.

        Args:
            username: Unique username.
            email: User email address.
            password: Plain-text password to hash.
            display_name: Optional display name.

        Returns:
            User dict without hashed_password.

        Raises:
            ValueError: If validation fails or username/email already exists.
        """
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            raise ValueError("Username may only contain letters, numbers, hyphens, and underscores")
        if not email or "@" not in email:
            raise ValueError("A valid email address is required")
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        user_id = str(uuid.uuid4())
        row = UserRow(
            id=user_id,
            username=username,
            email=email,
            display_name=display_name or username,
            hashed_password=self._hash_password(password),
            created_at=datetime.now(UTC).isoformat(),
            role="user",
            is_active=True,
        )

        with session_scope() as db:
            if db.scalar(select(UserRow).where(UserRow.username == username)) is not None:
                raise ValueError(f"Username '{username}' is already taken")
            if db.scalar(select(UserRow).where(UserRow.email == email)) is not None:
                raise ValueError(f"Email '{email}' is already registered")
            db.add(row)
            db.flush()
            result = _safe(row.to_dict())

        logger.info("Registered new user: %s (id=%s)", username, user_id)
        return result

    def authenticate(self, username: str, password: str) -> dict | None:
        """
        Authenticate a user by username and password.

        Args:
            username: The username to look up.
            password: The plain-text password to verify.

        Returns:
            User dict without hashed_password, or None if authentication fails.
        """
        with session_scope() as db:
            row = db.scalar(select(UserRow).where(UserRow.username == username))
            if row is None:
                return None

            if not self._verify_password(password, row.hashed_password):
                logger.warning("Failed login attempt for user: %s", username)
                return None

            if not row.is_active:
                logger.warning("Login attempt for inactive user: %s", username)
                return None

            result = _safe(row.to_dict())

        logger.info("User authenticated: %s", username)
        return result

    def create_access_token(self, user_id: str, username: str, role: str = "user") -> str:
        """
        Create a JWT access token.

        Args:
            user_id: The user's unique ID.
            username: The user's username.
            role: The user's role.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire_minutes),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """
        Create a JWT refresh token.

        Args:
            user_id: The user's unique ID.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire_days),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict | None:
        """
        Decode and verify a JWT token.

        Args:
            token: The JWT string to verify.

        Returns:
            Decoded payload dict, or None if invalid/expired.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as exc:
            logger.debug("Token verification failed: %s", exc)
            return None

    def get_user(self, user_id: str) -> dict | None:
        """
        Load a user by ID, excluding the hashed password.

        Args:
            user_id: The user's unique ID.

        Returns:
            User dict without hashed_password, or None if not found.
        """
        with session_scope() as db:
            row = db.get(UserRow, user_id)
            if row is None:
                return None
            return _safe(row.to_dict())

    def get_user_by_username(self, username: str) -> dict | None:
        """
        Search for a user by username.

        Args:
            username: The username to search for.

        Returns:
            User dict without hashed_password, or None if not found.
        """
        with session_scope() as db:
            row = db.scalar(select(UserRow).where(UserRow.username == username))
            if row is None:
                return None
            return _safe(row.to_dict())

    def update_user(self, user_id: str, updates: dict) -> dict | None:
        """
        Update user fields (password changes are not allowed via this method).

        Args:
            user_id: The user's unique ID.
            updates: Dictionary of fields to update.

        Returns:
            Updated user dict without hashed_password, or None if not found.
        """
        protected_fields = {"id", "hashed_password", "created_at"}
        with session_scope() as db:
            row = db.get(UserRow, user_id)
            if row is None:
                return None
            for key, value in updates.items():
                if key not in protected_fields and hasattr(row, key):
                    setattr(row, key, value)
            db.flush()
            result = _safe(row.to_dict())
        logger.info("Updated user: %s", user_id)
        return result

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """
        Change a user's password after verifying the old one.

        Args:
            user_id: The user's unique ID.
            old_password: Current plain-text password.
            new_password: New plain-text password.

        Returns:
            True if the password was changed, False otherwise.
        """
        with session_scope() as db:
            row = db.get(UserRow, user_id)
            if row is None:
                return False

            if not self._verify_password(old_password, row.hashed_password):
                logger.warning("Password change failed for user %s: incorrect old password", user_id)
                return False

            if len(new_password) < 8:
                raise ValueError("New password must be at least 8 characters")

            row.hashed_password = self._hash_password(new_password)

        logger.info("Password changed for user: %s", user_id)
        return True

    def list_users(self) -> list[dict]:
        """
        Return all users without passwords.

        Returns:
            List of user dicts with hashed_password excluded.
        """
        with session_scope() as db:
            rows = db.scalars(select(UserRow)).all()
            return [_safe(row.to_dict()) for row in rows]

    def _hash_password(self, password: str) -> str:
        """Hash a password using Argon2id."""
        return self.hasher.hash(password)

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against an Argon2id hash."""
        try:
            return self.hasher.verify(hashed, password)
        except VerifyMismatchError:
            return False
