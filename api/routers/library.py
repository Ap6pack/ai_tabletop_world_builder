#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
API endpoints for the scenario library: browsing, rating, sharing, and forking.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.middleware.auth import Caller, get_caller
from api.services.scenario_library_service import ScenarioLibraryService

router = APIRouter(prefix="/library", tags=["library"])

library_service = ScenarioLibraryService()

# Visibility: "public" scenarios are listed for everyone, "unlisted" ones can be
# opened by anyone with the ID, and "private" ones only by their owner (and
# admins). Only the owner or an admin can change a scenario's visibility.
# Built-in templates have no owner, so only admins can change them.


def _can_view(scenario: dict, caller: Caller) -> bool:
    return scenario.get("visibility", "public") != "private" or caller.owns(scenario.get("owner_id"))


def _listed(scenario: dict, caller: Caller) -> bool:
    return scenario.get("visibility", "public") == "public" or caller.owns(scenario.get("owner_id"))


def _public(scenario: dict, caller: Caller) -> dict:
    """Response form: hide who rated what and the owner's user ID."""
    shown = {k: v for k, v in scenario.items() if k not in ("ratings", "owner_id")}
    shown["is_mine"] = caller.user_id is not None and scenario.get("owner_id") == caller.user_id
    return shown


def _visible_or_404(scenario_id: str, caller: Caller) -> dict:
    scenario = library_service.get_scenario(scenario_id)
    if scenario is None or not _can_view(scenario, caller):
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


class RateRequest(BaseModel):
    """Request body for rating a scenario."""

    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    user_id: str = "anonymous"


class ShareRequest(BaseModel):
    """Request body for setting scenario visibility."""

    visibility: str = Field(
        default="public",
        description="Visibility: public, private, or unlisted",
    )


class ForkRequest(BaseModel):
    """Request body for forking a scenario."""

    user_id: str = "anonymous"


class AddScenarioRequest(BaseModel):
    """Request body for adding a scenario to the library."""

    name: str
    description: str = ""
    industry: str = "general"
    difficulty: str = "intermediate"
    category: str = "incident-response"
    tags: list = []
    author: str = "system"
    scenario_data: dict = {}


@router.get("/scenarios")
async def list_scenarios(
    category: str | None = Query(None, description="Filter by category"),
    difficulty: str | None = Query(None, description="Filter by difficulty"),
    sort_by: str = Query("rating", description="Sort field"),
    caller: Caller = Depends(get_caller),
):
    """List library scenarios with optional filters."""
    scenarios = [
        _public(s, caller)
        for s in library_service.list_scenarios(category=category, difficulty=difficulty, sort_by=sort_by)
        if _listed(s, caller)
    ]
    return {"scenarios": scenarios, "total": len(scenarios)}


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str, caller: Caller = Depends(get_caller)):
    """Get full scenario details."""
    return _public(_visible_or_404(scenario_id, caller), caller)


@router.post("/scenarios")
async def add_scenario(request: AddScenarioRequest, caller: Caller = Depends(get_caller)):
    """Add a scenario to the library. With auth on, the caller is the author."""
    scenario_data = request.model_dump()
    requested_author = scenario_data.pop("author", "system")
    author = caller.username if caller.user_id else requested_author
    scenario = library_service.add_to_library(scenario_data, author=author, owner_id=caller.user_id)
    return {"message": "Scenario added to library", "scenario": _public(scenario, caller)}


@router.post("/scenarios/{scenario_id}/rate")
async def rate_scenario(scenario_id: str, request: RateRequest, caller: Caller = Depends(get_caller)):
    """Rate a scenario from 1 to 5 (one rating per user)."""
    _visible_or_404(scenario_id, caller)
    rater = caller.user_id or request.user_id
    result = library_service.rate_scenario(scenario_id, request.rating, rater)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/scenarios/{scenario_id}/fork")
async def fork_scenario(scenario_id: str, request: ForkRequest = None, caller: Caller = Depends(get_caller)):
    """Fork (copy) a scenario for customization; the copy is private to the caller."""
    _visible_or_404(scenario_id, caller)
    if request is None:
        request = ForkRequest()
    author = caller.username if caller.user_id else request.user_id
    result = library_service.fork_scenario(scenario_id, author, owner_id=caller.user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"message": "Scenario forked successfully", "scenario": _public(result, caller)}


@router.post("/scenarios/{scenario_id}/share")
async def share_scenario(scenario_id: str, request: ShareRequest, caller: Caller = Depends(get_caller)):
    """Set scenario visibility (public/private/unlisted). Owner or admin only."""
    scenario = _visible_or_404(scenario_id, caller)
    if not caller.owns(scenario.get("owner_id")):
        raise HTTPException(status_code=403, detail="Only the scenario's owner can change its visibility")
    result = library_service.share_scenario(scenario_id, request.visibility)
    if "error" in result:
        status = 404 if "not found" in result["error"].lower() else 400
        raise HTTPException(status_code=status, detail=result["error"])
    return result


@router.get("/templates")
async def get_templates():
    """Get pre-built scenario templates."""
    templates = library_service.get_templates()
    return {"templates": templates, "total": len(templates)}


@router.get("/search")
async def search_scenarios(
    q: str = Query(..., min_length=1, description="Search query"),
    caller: Caller = Depends(get_caller),
):
    """Search scenarios by name, description, and tags."""
    results = [_public(s, caller) for s in library_service.search_scenarios(q) if _listed(s, caller)]
    return {"results": results, "total": len(results), "query": q}
