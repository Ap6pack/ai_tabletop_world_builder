#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
API endpoints for the scenario library: browsing, rating, sharing, and forking.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services.scenario_library_service import ScenarioLibraryService

router = APIRouter(prefix="/library", tags=["library"])

library_service = ScenarioLibraryService()


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
):
    """List library scenarios with optional filters."""
    scenarios = library_service.list_scenarios(category=category, difficulty=difficulty, sort_by=sort_by)
    return {"scenarios": scenarios, "total": len(scenarios)}


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get full scenario details."""
    scenario = library_service.get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.post("/scenarios")
async def add_scenario(request: AddScenarioRequest):
    """Add a scenario to the library."""
    scenario_data = request.model_dump()
    author = scenario_data.pop("author", "system")
    scenario = library_service.add_to_library(scenario_data, author=author)
    return {"message": "Scenario added to library", "scenario": scenario}


@router.post("/scenarios/{scenario_id}/rate")
async def rate_scenario(scenario_id: str, request: RateRequest):
    """Rate a scenario from 1 to 5."""
    result = library_service.rate_scenario(scenario_id, request.rating, request.user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/scenarios/{scenario_id}/fork")
async def fork_scenario(scenario_id: str, request: ForkRequest = None):
    """Fork (copy) a scenario for customization."""
    if request is None:
        request = ForkRequest()
    result = library_service.fork_scenario(scenario_id, request.user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"message": "Scenario forked successfully", "scenario": result}


@router.post("/scenarios/{scenario_id}/share")
async def share_scenario(scenario_id: str, request: ShareRequest):
    """Set scenario visibility (public/private/unlisted)."""
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
):
    """Search scenarios by name, description, and tags."""
    results = library_service.search_scenarios(q)
    return {"results": results, "total": len(results), "query": q}
