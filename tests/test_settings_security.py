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
