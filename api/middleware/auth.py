#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
FastAPI dependency functions for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.services.auth_service import AuthService
from config.settings import settings

security = HTTPBearer(auto_error=False)
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """
    Extract and validate the current user from a Bearer token.

    Returns None when ``settings.require_auth`` is False (auth disabled).
    Raises 401 when auth is required but the token is missing or invalid.
    """
    if not settings.require_auth:
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user(payload.get("sub", ""))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_auth(
    user: dict | None = Depends(get_current_user),
) -> dict:
    """Ensure a valid user is present. Raises 401 if user is None."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: dict | None = Depends(get_current_user),
) -> dict | None:
    """Authorize admin-only endpoints (e.g. destructive settings operations).

    When ``settings.require_auth`` is enabled, requires an authenticated user
    with the ``admin`` role. When auth is disabled (local/dev), access is
    allowed — production must set ``REQUIRE_AUTH=true`` (which also enforces a
    real ``JWT_SECRET_KEY``; see config.settings), at which point these
    endpoints become admin-only.
    """
    if not settings.require_auth:
        return None
    if user is None or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return user


def require_role(required_role: str):
    """Return a dependency that checks whether the user has the required role."""

    async def _check_role(user: dict = Depends(require_auth)) -> dict:
        user_role = user.get("role", "")
        if user_role == "admin" or user_role == required_role:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{required_role}' is required",
        )

    return _check_role
