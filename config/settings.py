#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Application configuration settings.
"""

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder secret shipped as the default; must never be used with auth enabled.
DEFAULT_JWT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # API Configuration
    api_host: str = "0.0.0.0"  # noqa: S104 — bind all interfaces (intended for containers)
    api_port: int = 8000
    api_reload: bool = True

    # LLM Provider Configuration
    default_llm_provider: Literal["openai", "anthropic", "together", "ollama"] = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_temperature: float = 0.7

    # Together AI
    together_api_key: str = ""
    together_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    together_temperature: float = 0.7

    # Ollama (Local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_temperature: float = 0.7

    # Content Policy
    default_content_policy: Literal["defensive", "educational", "advanced", "unrestricted"] = "educational"

    # Session Configuration
    session_timeout: int = 3600
    max_context_length: int = 4000

    # Authentication
    # NOTE: auth is opt-in. When require_auth is False (the default), the API
    # endpoints are NOT protected — see api/middleware/auth.py. Product routers
    # do not yet declare an auth dependency, so enabling require_auth only
    # guards the /auth router today. Treat this as development-grade until auth
    # is wired onto the product endpoints.
    require_auth: bool = False
    jwt_secret_key: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = ""

    # Storage Paths
    scenarios_path: str = "./scenarios/generated"
    data_path: str = "./data"

    # Database
    # SQLAlchemy URL for mutable application state (users, sessions, exercises,
    # API keys, webhooks). Defaults to a local SQLite file; set to a Postgres
    # URL (e.g. postgresql+psycopg://user:pass@host/db) for production.
    database_url: str = "sqlite:///./data/app.db"

    @model_validator(mode="after")
    def _reject_insecure_auth_config(self) -> "Settings":
        """Fail fast if auth is enabled without a real JWT secret.

        Only fires when require_auth is True, so the default (auth-off)
        configuration and the test suite are unaffected. This prevents
        deploying with the shipped placeholder secret, which would let anyone
        forge valid tokens.
        """
        if self.require_auth and self.jwt_secret_key.strip() in ("", DEFAULT_JWT_SECRET):
            raise ValueError(
                "REQUIRE_AUTH is enabled but JWT_SECRET_KEY is unset or still the default "
                "placeholder. Set JWT_SECRET_KEY to a strong random secret "
                "(e.g. `python -c 'import secrets; print(secrets.token_urlsafe(48))'`)."
            )
        return self


# Global settings instance
settings = Settings()
