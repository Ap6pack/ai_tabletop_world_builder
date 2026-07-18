#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
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
