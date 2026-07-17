#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Utility modules for Streamlit frontend.
"""

from .api_client import (
    API_BASE_URL,
    api_call,
    check_api_health,
    format_duration,
    format_timestamp,
    get_event_type_emoji,
    get_severity_emoji,
    get_status_emoji,
)

__all__ = [
    "API_BASE_URL",
    "check_api_health",
    "api_call",
    "format_timestamp",
    "format_duration",
    "get_status_emoji",
    "get_severity_emoji",
    "get_event_type_emoji",
]
