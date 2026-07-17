#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Content policy API router.
"""

from fastapi import APIRouter, HTTPException

from api.models import ContentCheckRequest, ContentCheckResponse
from api.services import ContentPolicyService

router = APIRouter(prefix="/content-policy", tags=["Content Policy"])


@router.post("/check", response_model=ContentCheckResponse)
async def check_content(request: ContentCheckRequest):
    """
    Check if content complies with the specified policy.

    Args:
        request: Content check request with content and policy

    Returns:
        Content check response with safety assessment

    Raises:
        HTTPException: If check fails
    """
    try:
        return await ContentPolicyService.check_content(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content check failed: {str(e)}") from e


@router.get("/policies")
async def list_policies():
    """
    List all available content policies.

    Returns:
        Dict of policy configurations
    """
    return ContentPolicyService.list_policies()
