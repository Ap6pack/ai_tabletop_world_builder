#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Integrations API router for webhook management and API key administration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.middleware.auth import Caller, get_caller
from api.routers.access import owner_filter
from api.services.api_key_service import APIKeyService
from api.services.webhook_service import WebhookService
from api.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])

webhook_service = WebhookService()
api_key_service = APIKeyService()

# Webhooks and API keys belong to the user who created them. With auth on, the
# owner is always the logged-in user; only admins may act on someone else's
# (by passing user_id). With auth off (dev mode) the request's user_id is used.


def _effective_user(caller: Caller, requested: str | None, default: str | None = None) -> str | None:
    if caller.user_id is None:
        return requested or default
    if requested and requested != caller.user_id and not caller.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own resources")
    return requested or caller.user_id


def _public(webhook: dict) -> dict:
    """Hide the signing secret in responses; report only whether one is set."""
    shown = {k: v for k, v in webhook.items() if k != "secret"}
    shown["secret_configured"] = bool(webhook.get("secret"))
    return shown


def _owned_webhook(webhook_id: str, caller: Caller) -> dict:
    webhook = webhook_service.get_webhook(webhook_id)
    if webhook is None or not caller.owns(webhook.get("user_id")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return webhook


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class WebhookCreateRequest(BaseModel):
    """Payload for registering a webhook."""

    url: str = Field(..., description="Callback URL (https, public address)")
    events: list[str] = Field(..., description="Event types to subscribe to")
    user_id: str | None = Field(None, description="Owner (admins only; defaults to the caller)")
    secret: str | None = Field(None, description="HMAC signing secret")


class WebhookUpdateRequest(BaseModel):
    """Payload for updating a webhook."""

    url: str | None = None
    events: list[str] | None = None
    active: bool | None = None
    secret: str | None = None


class APIKeyCreateRequest(BaseModel):
    """Payload for creating an API key."""

    name: str = Field(..., description="Friendly key name")
    user_id: str | None = Field(None, description="Owner (admins only; defaults to the caller)")
    scopes: list[str] | None = Field(None, description="Permission scopes")


# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def register_webhook(request: WebhookCreateRequest, caller: Caller = Depends(get_caller)) -> dict:
    """Register a new webhook endpoint."""
    try:
        webhook = webhook_service.register_webhook(
            url=request.url,
            events=request.events,
            user_id=_effective_user(caller, request.user_id, default="system"),
            secret=request.secret,
        )
        return _public(webhook)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/webhooks")
async def list_webhooks(user_id: str | None = None, caller: Caller = Depends(get_caller)) -> list[dict]:
    """List the caller's webhooks (admins: all, or one user's with ``user_id``)."""
    scope = owner_filter(caller)
    return [_public(w) for w in webhook_service.list_webhooks(user_id=scope if scope is not None else user_id)]


@router.get("/webhooks/{webhook_id}")
async def get_webhook(webhook_id: str, caller: Caller = Depends(get_caller)) -> dict:
    """Get a single webhook by ID."""
    return _public(_owned_webhook(webhook_id, caller))


@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, request: WebhookUpdateRequest, caller: Caller = Depends(get_caller)) -> dict:
    """Update a webhook's configuration."""
    _owned_webhook(webhook_id, caller)
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    try:
        webhook = webhook_service.update_webhook(webhook_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return _public(webhook)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, caller: Caller = Depends(get_caller)) -> dict:
    """Delete a webhook registration."""
    _owned_webhook(webhook_id, caller)
    if not webhook_service.unregister_webhook(webhook_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return {"message": "Webhook deleted"}


@router.get("/webhooks/{webhook_id}/deliveries")
async def get_delivery_log(webhook_id: str, caller: Caller = Depends(get_caller)) -> list[dict]:
    """Get delivery history for a webhook."""
    _owned_webhook(webhook_id, caller)
    return webhook_service.get_delivery_log(webhook_id)


# ---------------------------------------------------------------------------
# API Key endpoints
# ---------------------------------------------------------------------------


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(request: APIKeyCreateRequest, caller: Caller = Depends(get_caller)) -> dict:
    """Create a new API key. The raw key is returned only in this response."""
    user_id = _effective_user(caller, request.user_id)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
    try:
        return api_key_service.create_key(user_id=user_id, name=request.name, scopes=request.scopes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/api-keys")
async def list_api_keys(user_id: str = "", caller: Caller = Depends(get_caller)) -> list[dict]:
    """List API keys for the caller (admins: for ``user_id``), masked."""
    target = _effective_user(caller, user_id or None)
    if not target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
    return api_key_service.list_keys(target)


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, caller: Caller = Depends(get_caller)) -> dict:
    """Revoke an API key."""
    key = api_key_service.get_key(key_id)
    if key is None or not caller.owns(key.get("user_id")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    api_key_service.revoke_key(key_id)
    return {"message": "API key revoked"}
