#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Integrations API router for webhook management and API key administration.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.services.api_key_service import APIKeyService
from api.services.webhook_service import WebhookService
from api.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])

webhook_service = WebhookService()
api_key_service = APIKeyService()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class WebhookCreateRequest(BaseModel):
    """Payload for registering a webhook."""

    url: str = Field(..., description="Callback URL")
    events: list[str] = Field(..., description="Event types to subscribe to")
    user_id: str = Field("system", description="Owner user ID")
    secret: str | None = Field(None, description="HMAC signing secret")


class WebhookUpdateRequest(BaseModel):
    """Payload for updating a webhook."""

    url: str | None = None
    events: list[str] | None = None
    active: bool | None = None
    secret: str | None = None


class APIKeyCreateRequest(BaseModel):
    """Payload for creating an API key."""

    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Friendly key name")
    scopes: list[str] | None = Field(None, description="Permission scopes")


# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def register_webhook(request: WebhookCreateRequest) -> dict:
    """Register a new webhook endpoint."""
    try:
        webhook = webhook_service.register_webhook(
            url=request.url,
            events=request.events,
            user_id=request.user_id,
            secret=request.secret,
        )
        return webhook
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/webhooks")
async def list_webhooks(user_id: str | None = None) -> list[dict]:
    """List registered webhooks, optionally filtered by user."""
    return webhook_service.list_webhooks(user_id=user_id)


@router.get("/webhooks/{webhook_id}")
async def get_webhook(webhook_id: str) -> dict:
    """Get a single webhook by ID."""
    webhook = webhook_service.get_webhook(webhook_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return webhook


@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, request: WebhookUpdateRequest) -> dict:
    """Update a webhook's configuration."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    webhook = webhook_service.update_webhook(webhook_id, updates)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return webhook


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str) -> dict:
    """Delete a webhook registration."""
    if not webhook_service.unregister_webhook(webhook_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return {"message": "Webhook deleted"}


@router.get("/webhooks/{webhook_id}/deliveries")
async def get_delivery_log(webhook_id: str) -> list[dict]:
    """Get delivery history for a webhook."""
    if webhook_service.get_webhook(webhook_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return webhook_service.get_delivery_log(webhook_id)


# ---------------------------------------------------------------------------
# API Key endpoints
# ---------------------------------------------------------------------------


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(request: APIKeyCreateRequest) -> dict:
    """Create a new API key. The raw key is returned only in this response."""
    try:
        key = api_key_service.create_key(
            user_id=request.user_id,
            name=request.name,
            scopes=request.scopes,
        )
        return key
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/api-keys")
async def list_api_keys(user_id: str = "") -> list[dict]:
    """List API keys for a user (masked, no raw values)."""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
    return api_key_service.list_keys(user_id)


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str) -> dict:
    """Revoke an API key."""
    if not api_key_service.revoke_key(key_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return {"message": "API key revoked"}
