#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
API Client utilities for Streamlit frontend.
"""
import requests
import streamlit as st
from typing import Optional, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, HEALTH_CHECK_TIMEOUT


def check_api_health() -> bool:
    """Check if the API is running and healthy."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=HEALTH_CHECK_TIMEOUT)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def api_call(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    show_error: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Make an API call with error handling and user feedback.

    Args:
        method: HTTP method (GET, POST, DELETE, etc.)
        endpoint: API endpoint (e.g., '/scenarios/generate')
        json_data: JSON body for POST/PUT requests
        params: URL parameters
        timeout: Request timeout in seconds
        show_error: Whether to display error messages to user

    Returns:
        Response JSON if successful, None otherwise
    """
    url = f"{API_BASE_URL}{endpoint}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=json_data, params=params, timeout=timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, params=params, timeout=timeout)
        elif method.upper() == "PUT":
            response = requests.put(url, json=json_data, params=params, timeout=timeout)
        else:
            if show_error:
                st.error(f"Unsupported HTTP method: {method}")
            return None

        if response.status_code == 200:
            return response.json()
        else:
            if show_error:
                st.error(f"❌ API Error {response.status_code}: {response.text[:200]}")
            return None

    except requests.exceptions.Timeout:
        if show_error:
            st.error("⏱️ Request timed out. The server may be busy or unresponsive.")
        return None

    except requests.exceptions.ConnectionError:
        if show_error:
            st.error(f"🔌 Could not connect to API. Make sure the backend is running on {API_BASE_URL}")
            st.info("Run `uvicorn api.main:app --reload` to start the backend server.")
        return None

    except Exception as e:
        if show_error:
            st.error(f"❌ Unexpected error: {str(e)}")
        return None


def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp for display."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp


def format_duration(minutes: int) -> str:
    """Format duration in minutes to human-readable string."""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins > 0:
        return f"{hours}h {mins}m"
    return f"{hours}h"


def get_status_emoji(status: str) -> str:
    """Get emoji for session status."""
    return {
        "in_progress": "🟢",
        "completed": "✅",
        "failed": "❌",
        "pending": "⏳"
    }.get(status, "⚪")


def get_severity_emoji(severity: str) -> str:
    """Get emoji for severity level."""
    return {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "⚪"
    }.get(severity, "⚪")


def get_event_type_emoji(event_type: str) -> str:
    """Get emoji for event type."""
    return {
        "detection": "🚨",
        "action": "⚡",
        "consequence": "📍",
        "escalation": "⚠️",
        "discovery": "🔍",
        "success": "✅",
        "failure": "❌"
    }.get(event_type, "📌")
