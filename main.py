#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
FastAPI main application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import init_db
from api.middleware.auth import get_current_user
from api.middleware.cors import get_cors_origins
from api.middleware.request_logging import RequestLoggingMiddleware
from api.middleware.security import SecurityHeadersMiddleware
from api.middleware.telemetry import TelemetryMiddleware
from api.routers import (
    analytics_router,
    audit_router,
    auth_router,
    content_policy_router,
    exercise_router,
    game_router,
    integrations_router,
    library_router,
    llm_router,
    mitre_router,
    scenarios_router,
    settings_router,
)
from config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ensure the database schema exists before serving requests."""
    init_db()
    yield


# Create FastAPI app
app = FastAPI(
    title="Cybersecurity War Gaming Platform API",
    description="AI-powered cybersecurity training and war gaming platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security, logging, and telemetry middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TelemetryMiddleware)
TelemetryMiddleware.setup_telemetry(app)

# Product routers require authentication when REQUIRE_AUTH is enabled. With auth
# disabled (the local/dev default) get_current_user returns None and requests
# pass through unchanged. The auth router is intentionally left open so users can
# register and log in.
auth_required = [Depends(get_current_user)]
app.include_router(llm_router, dependencies=auth_required)
app.include_router(content_policy_router, dependencies=auth_required)
app.include_router(scenarios_router, dependencies=auth_required)
app.include_router(game_router, dependencies=auth_required)
app.include_router(settings_router, dependencies=auth_required)
app.include_router(audit_router, dependencies=auth_required)
app.include_router(analytics_router, dependencies=auth_required)
app.include_router(auth_router)
app.include_router(library_router, dependencies=auth_required)
app.include_router(integrations_router, dependencies=auth_required)
app.include_router(mitre_router, dependencies=auth_required)
app.include_router(exercise_router, dependencies=auth_required)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Cybersecurity War Gaming Platform API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=settings.api_reload)
