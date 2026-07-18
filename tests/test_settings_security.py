#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
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
