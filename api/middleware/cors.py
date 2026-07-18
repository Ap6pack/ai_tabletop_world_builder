#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""CORS configuration module for FastAPI."""

from config.settings import settings

DEFAULTS = ["http://localhost:8501", "http://localhost:3000"]


def get_cors_origins() -> list:
    """Return allowed CORS origins from settings or defaults.

    Parses comma-separated origins from settings.cors_origins if available,
    otherwise returns defaults for Streamlit (8501) and Grafana (3000).
    """
    raw = getattr(settings, "cors_origins", None)
    if raw and isinstance(raw, str):
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return DEFAULTS


def allow_credentials(origins: list) -> bool:
    """Whether credentialed CORS requests may be allowed.

    Credentials must not be combined with a wildcard origin — browsers reject
    it and it defeats the purpose of an allowlist.
    """
    return "*" not in origins
