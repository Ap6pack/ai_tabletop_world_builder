#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Prometheus instrumentation for the API.

Collects HTTP request metrics plus a few domain metrics (LLM calls, game
actions, after-action reports) and serves them in the Prometheus text format
at ``GET /metrics`` for the scrape job in ``monitoring/prometheus.yml``.

Metrics live in a process-local registry. With several uvicorn workers each
worker keeps its own counters; run one worker per container (and scale
containers) if you need exact totals, or set ``PROMETHEUS_MULTIPROC_DIR``
as described in the prometheus_client documentation.
"""

from __future__ import annotations

import hmac
import time
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from api.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

# Standard HTTP metrics (names match monitoring/grafana/dashboards/api_metrics.json)
request_count = Counter("http_requests", "Total HTTP requests", ["method", "path", "status_code"])
request_duration = Histogram("http_request_duration_seconds", "Request duration in seconds", ["method", "path"])
active_requests = Gauge("http_active_requests", "Currently active requests")
error_count = Counter("http_errors", "Total HTTP error responses", ["method", "path", "status_code"])

# Domain-specific metrics
llm_calls_total = Counter("llm_calls", "Total LLM API calls", ["provider", "model", "outcome"])
llm_call_duration = Histogram("llm_call_duration_seconds", "LLM call duration in seconds", ["provider"])
game_actions_total = Counter("game_actions", "Total in-game actions processed", ["action_type"])
aar_generated_total = Counter("aar_generated", "Total after-action reports generated", ["grade"])

METRICS_PATH = "/metrics"


def _route_template(request: Request) -> str:
    """Label by route template (``/game/{session_id}``), not the raw path, to bound cardinality."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Collect per-request Prometheus metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == METRICS_PATH:
            return await call_next(request)

        method = request.method
        active_requests.inc()
        start = time.perf_counter()
        status = "500"
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        finally:
            path = _route_template(request)
            request_count.labels(method, path, status).inc()
            request_duration.labels(method, path).observe(time.perf_counter() - start)
            if int(status) >= 400:
                error_count.labels(method, path, status).inc()
            active_requests.dec()

    @staticmethod
    def setup_telemetry(app: FastAPI) -> None:
        """Expose ``GET /metrics`` on the application."""

        @app.get(METRICS_PATH, include_in_schema=False)
        async def metrics(request: Request) -> Response:
            token = settings.metrics_token
            if token:
                supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
                if not hmac.compare_digest(supplied.encode(), token.encode()):
                    raise HTTPException(status_code=401, detail="Invalid metrics token")
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Convenience helpers for domain-specific metrics
# ---------------------------------------------------------------------------


def record_llm_call(provider: str, model: str, duration: float, success: bool = True) -> None:
    """Record an LLM API call with provider, model, and duration."""
    llm_calls_total.labels(provider, model, "success" if success else "error").inc()
    llm_call_duration.labels(provider).observe(duration)


def record_game_action(action_type: str) -> None:
    """Record a game action executed within a session."""
    game_actions_total.labels(action_type).inc()


def record_aar_generation(grade: str) -> None:
    """Record generation of an after-action report."""
    aar_generated_total.labels(grade).inc()
