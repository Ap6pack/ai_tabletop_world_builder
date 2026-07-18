#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Fixed-window rate limiting for API endpoints.

Requests are counted per authenticated user (when a bearer token is present) or
per client IP. When ``REDIS_URL`` is configured the counters live in Redis so
limits hold across multiple API instances; otherwise an in-process counter is
used (suitable for a single instance / local development).
"""

import time

from fastapi import HTTPException, Request, status

from api.middleware.auth import auth_service
from api.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

try:
    import redis
except ImportError:  # pragma: no cover - redis is an optional dependency
    redis = None


class FixedWindowRateLimiter:
    """A simple fixed-window request counter with an optional Redis backend."""

    def __init__(self) -> None:
        self._memory: dict[str, tuple[int, int]] = {}
        self._redis = None
        if settings.redis_url and redis is not None:
            try:
                self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("Rate limiter using Redis backend")
            except Exception as exc:  # noqa: BLE001 - fall back to memory on any redis error
                logger.warning("Rate limiter Redis unavailable (%s); using in-process counter", exc)
                self._redis = None

    def reset(self) -> None:
        """Clear the in-process counters (used by tests)."""
        self._memory.clear()

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record a request for ``key``; return True if it is within ``limit``."""
        window_index = int(time.time() // window_seconds)

        if self._redis is not None:
            redis_key = f"ratelimit:{key}:{window_index}"
            count = self._redis.incr(redis_key)
            if count == 1:
                self._redis.expire(redis_key, window_seconds)
            return count <= limit

        stored_window, count = self._memory.get(key, (window_index, 0))
        if stored_window != window_index:
            count = 0
        count += 1
        self._memory[key] = (window_index, count)
        return count <= limit


# Module-level limiter shared across requests.
rate_limiter = FixedWindowRateLimiter()


def _client_key(request: Request) -> str:
    """Identify the caller: authenticated user id if available, else client IP."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        payload = auth_service.verify_token(auth_header[len("Bearer ") :])
        if payload and payload.get("sub"):
            return f"user:{payload['sub']}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


async def rate_limit(request: Request) -> None:
    """FastAPI dependency that enforces the configured request rate limit."""
    if not settings.rate_limit_enabled:
        return

    limit = settings.rate_limit_requests
    window = settings.rate_limit_window_seconds

    if not rate_limiter.hit(_client_key(request), limit, window):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down and try again shortly.",
            headers={"Retry-After": str(window)},
        )
