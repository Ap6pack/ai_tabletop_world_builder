#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""SQLAlchemy ORM models for mutable application state.

Flat aggregates (users, API keys, webhooks) use typed columns. Rich nested
aggregates (game sessions, exercises) are stored as a JSON payload column plus
a handful of indexed metadata columns for querying — this keeps the Pydantic
models the single source of truth while giving durable, concurrency-safe,
indexed storage.
"""

from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(32), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_dict(self) -> dict[str, Any]:
        """Full record including the password hash (internal use only)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "hashed_password": self.hashed_password,
            "created_at": self.created_at,
            "role": self.role,
            "is_active": self.is_active,
        }


class GameSessionRow(Base):
    __tablename__ = "game_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="in-progress")
    player_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    org_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    time_elapsed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)


class ExerciseRow(Base):
    __tablename__ = "exercises"

    exercise_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    phase: Mapped[str] = mapped_column(String(32), index=True, default="setup")
    facilitator_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    team_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)


class ApiKeyRow(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    hashed_key: Mapped[str] = mapped_column(String(128), index=True)
    prefix: Mapped[str] = mapped_column(String(32))
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(String(64))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def to_dict(self, include_hash: bool = False) -> dict[str, Any]:
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "prefix": self.prefix,
            "scopes": list(self.scopes or []),
            "created_at": self.created_at,
            "revoked": self.revoked,
        }
        if self.revoked_at is not None:
            data["revoked_at"] = self.revoked_at
        if include_hash:
            data["hashed_key"] = self.hashed_key
        return data


class WebhookRow(Base):
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    events: Mapped[list] = mapped_column(JSON, default=list)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="system")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "events": list(self.events or []),
            "user_id": self.user_id,
            "active": self.active,
            "secret": self.secret,
            "created_at": self.created_at,
        }


class WebhookDeliveryRow(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[str] = mapped_column(String(64), index=True)
    record: Mapped[dict[str, Any]] = mapped_column(JSON)


class GeneratedScenarioRow(Base):
    __tablename__ = "generated_scenarios"

    filename: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)


class LibraryScenarioRow(Base):
    __tablename__ = "library_scenarios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    rating: Mapped[float] = mapped_column(default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
