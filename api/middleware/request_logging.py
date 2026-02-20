"""
Structured JSON request/response logging middleware.

Logs method, path, status code, duration, client IP, and user-agent
for every request except health-check endpoints.
"""
from __future__ import annotations

import json
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.utils.logger import setup_logger

logger = setup_logger(__name__)

SKIP_PATHS = {"/health", "/healthz", "/health/"}
MAX_UA_LENGTH = 120


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit a structured JSON log line for every HTTP request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        user_agent = (request.headers.get("user-agent") or "")[:MAX_UA_LENGTH]
        client_ip = request.client.host if request.client else "unknown"

        log_data = {
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        level = "warning" if response.status_code >= 400 else "info"
        getattr(logger, level)(json.dumps(log_data))

        return response
