#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""Tests for API boot — verifies the FastAPI app imports and wires correctly."""

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# App import
# ---------------------------------------------------------------------------


class TestAppImport:
    def test_app_imports_without_error(self):
        """Importing main.app should not raise."""
        from main import app

        assert app is not None

    def test_app_has_title(self):
        from main import app

        assert app.title == "Cybersecurity War Gaming Platform API"


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_200(self):
        from main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------


class TestRouterRegistration:
    def test_all_routers_registered(self):
        """Verify a minimum number of endpoints are registered.

        Counts paths via the OpenAPI schema rather than ``app.routes``: modern
        FastAPI includes routers lazily, so the raw route list holds router
        wrappers, not expanded endpoints.
        """
        from main import app

        paths = app.openapi()["paths"]
        # We have 60+ unique endpoint paths across 12 routers
        assert len(paths) >= 20, f"Only {len(paths)} endpoint paths registered"

    def test_key_endpoints_exist(self):
        """Verify critical endpoint paths are registered."""
        from main import app

        paths = {r.path for r in app.routes if hasattr(r, "path")}
        expected = ["/health", "/", "/docs", "/openapi.json"]
        for ep in expected:
            assert ep in paths, f"Missing endpoint: {ep}"


# ---------------------------------------------------------------------------
# OpenAPI schema
# ---------------------------------------------------------------------------


class TestOpenAPISchema:
    def test_openapi_schema_generates(self):
        from main import app

        schema = app.openapi()
        assert "info" in schema
        assert "paths" in schema
        assert len(schema["paths"]) > 0
