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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import llm_router, content_policy_router
from api.middleware.cors import get_cors_origins
from api.middleware.security import SecurityHeadersMiddleware
from api.middleware.request_logging import RequestLoggingMiddleware
from api.middleware.telemetry import TelemetryMiddleware
from config import settings

# Create FastAPI app
app = FastAPI(
    title="Cybersecurity War Gaming Platform API",
    description="AI-powered cybersecurity training and war gaming platform",
    version="0.1.0",
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

# Include routers
app.include_router(llm_router)
app.include_router(content_policy_router)

# Import scenarios, game, settings, and audit routers
from api.routers import (
    scenarios_router, game_router, settings_router, audit_router,
    analytics_router, auth_router, library_router, integrations_router,
    mitre_router, exercise_router,
)
app.include_router(scenarios_router)
app.include_router(game_router)
app.include_router(settings_router)
app.include_router(audit_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(library_router)
app.include_router(integrations_router)
app.include_router(mitre_router)
app.include_router(exercise_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Cybersecurity War Gaming Platform API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
