#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""API routers module."""

from .analytics import router as analytics_router
from .audit import router as audit_router
from .auth import router as auth_router
from .content_policy import router as content_policy_router
from .exercise import router as exercise_router
from .game import router as game_router
from .integrations import router as integrations_router
from .library import router as library_router
from .llm import router as llm_router
from .mitre import router as mitre_router
from .scenarios import router as scenarios_router
from .settings import router as settings_router

__all__ = [
    "llm_router",
    "content_policy_router",
    "scenarios_router",
    "game_router",
    "settings_router",
    "audit_router",
    "analytics_router",
    "auth_router",
    "library_router",
    "integrations_router",
    "mitre_router",
    "exercise_router",
]
