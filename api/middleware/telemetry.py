#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
OpenTelemetry instrumentation middleware for FastAPI.

Provides request metrics, custom application metrics, and distributed tracing
with a graceful no-op fallback when OpenTelemetry packages are not installed.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from opentelemetry import metrics, trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    meter = metrics.get_meter("ai_tabletop_world_builder")
    tracer = trace.get_tracer("ai_tabletop_world_builder")

    # Standard HTTP metrics
    request_count = meter.create_counter("http_requests_total", description="Total HTTP requests")
    request_duration = meter.create_histogram(
        "http_request_duration_seconds", description="Request duration in seconds"
    )
    active_requests = meter.create_up_down_counter("http_active_requests", description="Currently active requests")
    error_count = meter.create_counter("http_errors_total", description="Total HTTP error responses")

    # Domain-specific metrics
    llm_calls_total = meter.create_counter("llm_calls_total", description="Total LLM API calls")
    game_actions_total = meter.create_counter("game_actions_total", description="Total in-game actions processed")
    aar_generated_total = meter.create_counter(
        "aar_generated_total", description="Total after-action reports generated"
    )

    OTEL_AVAILABLE = True
    logger.info("OpenTelemetry instrumentation loaded")
except ImportError:
    OTEL_AVAILABLE = False
    logger.info("OpenTelemetry not installed; telemetry disabled")


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Collect per-request metrics when OpenTelemetry is available."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not OTEL_AVAILABLE:
            return await call_next(request)

        method = request.method
        path = request.url.path
        attrs = {"method": method, "path": path}

        active_requests.add(1, attrs)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration = time.perf_counter() - start
            status = response.status_code
            request_count.add(1, {**attrs, "status_code": str(status)})
            request_duration.record(duration, attrs)
            if status >= 400:
                error_count.add(1, {**attrs, "status_code": str(status)})
            return response
        except Exception:
            error_count.add(1, {**attrs, "status_code": "500"})
            raise
        finally:
            active_requests.add(-1, attrs)

    @staticmethod
    def setup_telemetry(app: FastAPI) -> None:
        """Instrument the FastAPI application with OpenTelemetry."""
        if not OTEL_AVAILABLE:
            logger.info("Skipping telemetry setup; OpenTelemetry unavailable")
            return
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OpenTelemetry instrumentation applied")


# ---------------------------------------------------------------------------
# Convenience helpers for domain-specific metrics
# ---------------------------------------------------------------------------


def record_llm_call(provider: str, model: str, duration: float) -> None:
    """Record an LLM API call with provider, model, and duration."""
    if not OTEL_AVAILABLE:
        return
    llm_calls_total.add(1, {"provider": provider, "model": model})
    logger.debug("LLM call recorded: provider=%s model=%s duration=%.3fs", provider, model, duration)


def record_game_action(session_id: str, action_type: str) -> None:
    """Record a game action executed within a session."""
    if not OTEL_AVAILABLE:
        return
    game_actions_total.add(1, {"session_id": session_id, "action_type": action_type})


def record_aar_generation(session_id: str, grade: str) -> None:
    """Record generation of an after-action report."""
    if not OTEL_AVAILABLE:
        return
    aar_generated_total.add(1, {"session_id": session_id, "grade": grade})
