#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Scenarios API router for generating and managing cybersecurity training scenarios.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from api.services import ScenarioOrchestrator
from api.models import Organization
from api.utils import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


# Request/Response models
class GenerateScenarioRequest(BaseModel):
    """Request model for scenario generation."""
    industry: str = Field(..., description="Industry sector", examples=["Financial Services"])
    size: str = Field("medium", description="Organization size", examples=["medium"])
    complexity: str = Field("moderate", description="Scenario complexity", examples=["moderate"])
    focus_areas: Optional[List[str]] = Field(None, description="Focus areas", examples=[["ransomware", "phishing"]])
    num_departments: int = Field(3, ge=1, le=10, description="Number of departments to generate")


class ScenarioListItem(BaseModel):
    """Metadata for a saved scenario."""
    filename: str
    name: str
    industry: str
    size: str
    created_at: str
    file_size: int


@router.post("/generate", response_model=Organization)
async def generate_scenario(request: GenerateScenarioRequest):
    """
    Generate a complete cybersecurity training scenario.

    This endpoint creates a hierarchical organization with:
    - Organization profile
    - Multiple departments
    - IT systems per department
    - Vulnerabilities per system
    - Threat actors targeting the organization

    The generation process may take 30-60 seconds depending on complexity.
    """
    try:
        orchestrator = ScenarioOrchestrator()

        organization = await orchestrator.generate_complete_scenario(
            industry=request.industry,
            size=request.size,
            complexity=request.complexity,
            focus_areas=request.focus_areas,
            num_departments=request.num_departments
        )

        # Auto-save the generated scenario
        filepath = await orchestrator.save_scenario(organization)
        logger.info(f"Generated and saved scenario: {organization.name} -> {filepath}")

        return organization

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario generation failed: {str(e)}")


@router.get("/industries", response_model=List[str])
async def list_industries():
    """
    Get list of supported industries for scenario generation.

    Returns:
        List of industry names
    """
    return ScenarioOrchestrator.get_supported_industries()


@router.get("/industries/{industry}")
async def get_industry_info(industry: str):
    """
    Get detailed information about a specific industry.

    Args:
        industry: Industry name

    Returns:
        Industry template information including typical systems, compliance frameworks, etc.

    Raises:
        HTTPException: If industry is not found
    """
    info = ScenarioOrchestrator.get_industry_info(industry)

    if info is None:
        raise HTTPException(
            status_code=404,
            detail=f"Industry '{industry}' not found. Use /scenarios/industries to see available industries."
        )

    return info


@router.get("/list", response_model=List[ScenarioListItem])
async def list_scenarios():
    """
    List all saved scenarios.

    Returns:
        List of scenario metadata
    """
    try:
        orchestrator = ScenarioOrchestrator()
        return orchestrator.list_scenarios()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list scenarios: {str(e)}")


@router.get("/{filename}", response_model=Organization)
async def get_scenario(filename: str):
    """
    Load a saved scenario by filename.

    Args:
        filename: Name of the scenario file (e.g., "Example_Corp_20231031_120000.json")

    Returns:
        Complete Organization data

    Raises:
        HTTPException: If file not found
    """
    try:
        orchestrator = ScenarioOrchestrator()
        organization = await orchestrator.load_scenario(filename)
        return organization
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario '{filename}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenario: {str(e)}")


@router.delete("/{filename}")
async def delete_scenario(filename: str):
    """
    Delete a saved scenario.

    Args:
        filename: Name of the scenario file to delete

    Returns:
        Success message

    Raises:
        HTTPException: If file not found or deletion fails
    """
    import os

    try:
        filepath = os.path.join("scenarios/generated", filename)

        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"Scenario '{filename}' not found")

        os.remove(filepath)

        return {"message": f"Scenario '{filename}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete scenario: {str(e)}")
