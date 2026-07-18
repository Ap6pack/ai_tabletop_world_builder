#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
LLM API router.
"""

from fastapi import APIRouter, HTTPException

from api.models import LLMRequest, LLMResponse
from api.services import LLMService

router = APIRouter(prefix="/llm", tags=["LLM"])


@router.post("/complete", response_model=LLMResponse)
async def generate_completion(request: LLMRequest):
    """
    Generate a completion using the specified LLM provider.

    Args:
        request: LLM request with prompt and configuration

    Returns:
        LLM response with generated content

    Raises:
        HTTPException: If generation fails
    """
    try:
        return await LLMService.generate_completion(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}") from e


@router.get("/providers")
async def check_providers():
    """
    Check availability of all configured LLM providers.

    Returns:
        Dict mapping provider names to availability status
    """
    try:
        return await LLMService.check_providers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider check failed: {str(e)}") from e
