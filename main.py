#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
FastAPI main application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import init_db
from api.middleware.auth import get_current_user
from api.middleware.cors import allow_credentials, get_cors_origins
from api.middleware.rate_limit import rate_limit
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

# Configure CORS. Credentials cannot be combined with a wildcard origin (the
# browser rejects it and it is a security footgun), so only allow credentials
# when the origins are an explicit allowlist.
cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials(cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security, logging, and telemetry middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TelemetryMiddleware)
TelemetryMiddleware.setup_telemetry(app)

# All routers are rate limited. Product routers additionally require
# authentication when REQUIRE_AUTH is enabled; with auth disabled (the local/dev
# default) get_current_user returns None and requests pass through unchanged. The
# auth router is left open (no auth dependency) but is still rate limited to slow
# credential-stuffing against register/login.
protected = [Depends(rate_limit), Depends(get_current_user)]
app.include_router(llm_router, dependencies=protected)
app.include_router(content_policy_router, dependencies=protected)
app.include_router(scenarios_router, dependencies=protected)
app.include_router(game_router, dependencies=protected)
app.include_router(settings_router, dependencies=protected)
app.include_router(audit_router, dependencies=protected)
app.include_router(analytics_router, dependencies=protected)
app.include_router(auth_router, dependencies=[Depends(rate_limit)])
app.include_router(library_router, dependencies=protected)
app.include_router(integrations_router, dependencies=protected)
app.include_router(mitre_router, dependencies=protected)
app.include_router(exercise_router, dependencies=protected)


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
