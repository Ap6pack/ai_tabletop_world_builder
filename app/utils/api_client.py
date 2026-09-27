#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
API Client utilities for Streamlit frontend.
"""

import contextlib
import os
import sys
from typing import Any

import requests
import streamlit as st

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import API_BASE_URL, HEALTH_CHECK_TIMEOUT

# ---------------------------------------------------------------------------
# Authenticated HTTP
# ---------------------------------------------------------------------------
#
# Every page sends its API calls through ``http`` (a drop-in for the
# requests.get/post/put/delete functions). It attaches the login token from
# st.session_state.auth_token, and when the API answers 401 it tries the refresh
# token once; if that fails too, the stale login is cleared and the user is asked
# to sign in again. With REQUIRE_AUTH=false the API never returns 401, so
# pages keep working without an account.

_AUTH_FREE_PATHS = ("/auth/login", "/auth/register", "/auth/refresh", "/health")


def _session_state():
    """st.session_state, or an empty dict outside a Streamlit run (e.g. imports in tests)."""
    try:
        return st.session_state
    except Exception:  # noqa: BLE001 - no script run context
        return {}


def _auth_headers(headers: dict | None) -> dict:
    merged = dict(headers or {})
    token = _session_state().get("auth_token")
    if token and "Authorization" not in merged:
        merged["Authorization"] = f"Bearer {token}"
    return merged


def _try_refresh(timeout: float) -> bool:
    """Exchange the refresh token for a new access token. Returns True on success."""
    state = _session_state()
    refresh_token = state.get("refresh_token")
    if not refresh_token:
        return False
    try:
        resp = requests.post(f"{API_BASE_URL}/auth/refresh", json={"refresh_token": refresh_token}, timeout=timeout)
    except requests.exceptions.RequestException:
        return False
    if resp.status_code != 200:
        return False
    tokens = resp.json()
    state["auth_token"] = tokens["access_token"]
    state["refresh_token"] = tokens.get("refresh_token", refresh_token)
    return True


def _handle_auth_failure() -> None:
    """Clear an expired login and point the user at the Login page."""
    state = _session_state()
    had_login = bool(state.get("auth_token"))
    for key in ("auth_token", "refresh_token", "current_user"):
        if key in state:
            state[key] = None
    message = (
        "Your session has expired. Please sign in again."
        if had_login
        else "This server requires you to sign in before using this page."
    )
    # Outside a page run, or where the Login page isn't registered, skip the UI hint.
    with contextlib.suppress(Exception):
        st.warning(f"🔐 {message}")
        st.page_link("pages/8_Login.py", label="Go to Login", icon="🔐")


def authed_request(method: str, url: str, headers: dict | None = None, timeout: float = 30, **kwargs):
    """requests.request with the login token attached and one refresh on 401."""
    response = requests.request(method, url, headers=_auth_headers(headers), timeout=timeout, **kwargs)
    if response.status_code != 401 or url.endswith(_AUTH_FREE_PATHS):
        return response
    if _try_refresh(timeout):
        response = requests.request(method, url, headers=_auth_headers(headers), timeout=timeout, **kwargs)
        if response.status_code != 401:
            return response
    _handle_auth_failure()
    return response


class _AuthedHTTP:
    """Drop-in for the requests module's verb functions, with authentication."""

    @staticmethod
    def get(url: str, **kwargs):
        return authed_request("GET", url, **kwargs)

    @staticmethod
    def post(url: str, **kwargs):
        return authed_request("POST", url, **kwargs)

    @staticmethod
    def put(url: str, **kwargs):
        return authed_request("PUT", url, **kwargs)

    @staticmethod
    def delete(url: str, **kwargs):
        return authed_request("DELETE", url, **kwargs)

    @staticmethod
    def patch(url: str, **kwargs):
        return authed_request("PATCH", url, **kwargs)


http = _AuthedHTTP()


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
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = 30,
    show_error: bool = True,
) -> dict[str, Any] | None:
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
        if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            if show_error:
                st.error(f"Unsupported HTTP method: {method}")
            return None
        response = authed_request(method.upper(), url, json=json_data, params=params, timeout=timeout)

        if 200 <= response.status_code < 300:
            return response.json()
        elif response.status_code == 401:
            return None  # authed_request already asked the user to sign in
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

        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
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
    return {"in_progress": "🟢", "completed": "✅", "failed": "❌", "pending": "⏳"}.get(status, "⚪")


def get_severity_emoji(severity: str) -> str:
    """Get emoji for severity level."""
    return {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "⚪"}.get(severity, "⚪")


def get_event_type_emoji(event_type: str) -> str:
    """Get emoji for event type."""
    return {
        "detection": "🚨",
        "action": "⚡",
        "consequence": "📍",
        "escalation": "⚠️",
        "discovery": "🔍",
        "success": "✅",
        "failure": "❌",
    }.get(event_type, "📌")
