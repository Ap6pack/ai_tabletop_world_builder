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
and JWT token generation/verification.
"""
import json
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt, JWTError

from api.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)


class AuthService:
    """Handles user authentication, registration, and token management."""

    def __init__(self) -> None:
        """Initialize auth service with file-based user storage."""
        self.users_dir = "data/users"
        os.makedirs(self.users_dir, exist_ok=True)
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
    ) -> Dict:
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

        if self.get_user_by_username(username) is not None:
            raise ValueError(f"Username '{username}' is already taken")

        for filename in os.listdir(self.users_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.users_dir, filename)
                with open(filepath, "r") as f:
                    data = json.load(f)
                if data.get("email") == email:
                    raise ValueError(f"Email '{email}' is already registered")

        user_id = str(uuid.uuid4())
        user_data: Dict = {
            "id": user_id,
            "username": username,
            "email": email,
            "display_name": display_name or username,
            "hashed_password": self._hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "role": "user",
            "is_active": True,
        }

        self._save_user(user_data)
        logger.info("Registered new user: %s (id=%s)", username, user_id)

        safe_copy = {k: v for k, v in user_data.items() if k != "hashed_password"}
        return safe_copy

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate a user by username and password.

        Args:
            username: The username to look up.
            password: The plain-text password to verify.

        Returns:
            User dict without hashed_password, or None if authentication fails.
        """
        user_data = self.get_user_by_username(username)
        if user_data is None:
            return None

        full_user = self._load_user(user_data["id"])
        if full_user is None:
            return None

        if not self._verify_password(password, full_user["hashed_password"]):
            logger.warning("Failed login attempt for user: %s", username)
            return None

        if not full_user.get("is_active", True):
            logger.warning("Login attempt for inactive user: %s", username)
            return None

        logger.info("User authenticated: %s", username)
        safe_copy = {k: v for k, v in full_user.items() if k != "hashed_password"}
        return safe_copy

    def create_access_token(
        self, user_id: str, username: str, role: str = "user"
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: The user's unique ID.
            username: The user's username.
            role: The user's role.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(timezone.utc)
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
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire_days),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Decode and verify a JWT token.

        Args:
            token: The JWT string to verify.

        Returns:
            Decoded payload dict, or None if invalid/expired.
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            return payload
        except JWTError as exc:
            logger.debug("Token verification failed: %s", exc)
            return None

    def get_user(self, user_id: str) -> Optional[Dict]:
        """
        Load a user by ID, excluding the hashed password.

        Args:
            user_id: The user's unique ID.

        Returns:
            User dict without hashed_password, or None if not found.
        """
        user_data = self._load_user(user_id)
        if user_data is None:
            return None
        safe_copy = {k: v for k, v in user_data.items() if k != "hashed_password"}
        return safe_copy

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Search for a user by username.

        Args:
            username: The username to search for.

        Returns:
            User dict without hashed_password, or None if not found.
        """
        for filename in os.listdir(self.users_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.users_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                    if data.get("username") == username:
                        safe_copy = {
                            k: v for k, v in data.items() if k != "hashed_password"
                        }
                        return safe_copy
                except (json.JSONDecodeError, IOError):
                    continue
        return None

    def update_user(self, user_id: str, updates: Dict) -> Optional[Dict]:
        """
        Update user fields (password changes are not allowed via this method).

        Args:
            user_id: The user's unique ID.
            updates: Dictionary of fields to update.

        Returns:
            Updated user dict without hashed_password, or None if not found.
        """
        user_data = self._load_user(user_id)
        if user_data is None:
            return None

        protected_fields = {"id", "hashed_password", "created_at"}
        for key, value in updates.items():
            if key not in protected_fields:
                user_data[key] = value

        self._save_user(user_data)
        logger.info("Updated user: %s", user_id)
        safe_copy = {k: v for k, v in user_data.items() if k != "hashed_password"}
        return safe_copy

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """
        Change a user's password after verifying the old one.

        Args:
            user_id: The user's unique ID.
            old_password: Current plain-text password.
            new_password: New plain-text password.

        Returns:
            True if the password was changed, False otherwise.
        """
        user_data = self._load_user(user_id)
        if user_data is None:
            return False

        if not self._verify_password(old_password, user_data["hashed_password"]):
            logger.warning("Password change failed for user %s: incorrect old password", user_id)
            return False

        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters")

        user_data["hashed_password"] = self._hash_password(new_password)
        self._save_user(user_data)
        logger.info("Password changed for user: %s", user_id)
        return True

    def list_users(self) -> List[Dict]:
        """
        Return all users without passwords.

        Returns:
            List of user dicts with hashed_password excluded.
        """
        users: List[Dict] = []
        for filename in os.listdir(self.users_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.users_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                    safe_copy = {
                        k: v for k, v in data.items() if k != "hashed_password"
                    }
                    users.append(safe_copy)
                except (json.JSONDecodeError, IOError):
                    continue
        return users

    def _hash_password(self, password: str) -> str:
        """Hash a password using Argon2id."""
        return self.hasher.hash(password)

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against an Argon2id hash."""
        try:
            return self.hasher.verify(hashed, password)
        except VerifyMismatchError:
            return False

    def _save_user(self, user_data: Dict) -> None:
        """Save user data to a JSON file."""
        filepath = os.path.join(self.users_dir, f"{user_data['id']}.json")
        with open(filepath, "w") as f:
            json.dump(user_data, f, indent=2, default=str)

    def _load_user(self, user_id: str) -> Optional[Dict]:
        """Load user data from a JSON file."""
        filepath = os.path.join(self.users_dir, f"{user_id}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            logger.error("Failed to load user %s: %s", user_id, exc)
            return None
