#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Settings security guard (auth + JWT secret validation)."""

import pytest

from config.settings import DEFAULT_JWT_SECRET, Settings


def test_default_config_loads():
    """With auth off (the default), settings load without a real secret."""
    s = Settings(_env_file=None)
    assert s.require_auth is False
    assert s.jwt_secret_key == DEFAULT_JWT_SECRET


def test_auth_enabled_with_placeholder_secret_is_rejected():
    """Enabling auth with the shipped placeholder secret must fail fast."""
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, require_auth=True)


def test_auth_enabled_with_empty_secret_is_rejected():
    """Enabling auth with an empty secret must fail fast."""
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, require_auth=True, jwt_secret_key="   ")


def test_auth_enabled_with_real_secret_loads():
    """A strong secret with auth enabled is accepted."""
    s = Settings(
        _env_file=None,
        require_auth=True,
        jwt_secret_key="a-strong-random-secret-value-1234567890",
    )
    assert s.require_auth is True


@pytest.mark.parametrize("secret", ["abc", "x" * 31, "short-but-not-the-placeholder"])
def test_auth_enabled_with_short_secret_is_rejected(secret):
    """Secrets shorter than 32 bytes are too weak for HS256."""
    with pytest.raises(ValueError, match="at least 32 bytes"):
        Settings(_env_file=None, require_auth=True, jwt_secret_key=secret)


def test_auth_enabled_with_32_byte_secret_loads():
    assert Settings(_env_file=None, require_auth=True, jwt_secret_key="x" * 32).require_auth is True
