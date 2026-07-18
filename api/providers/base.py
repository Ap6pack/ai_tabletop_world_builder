#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Base LLM provider interface.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str | None = None, **kwargs):
        """
        Initialize the LLM provider.

        Args:
            api_key: API key for the provider (if required)
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Generate a completion from the LLM.

        Args:
            prompt: The user prompt
            system_message: Optional system message to set context
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Dict containing:
                - content: The generated text
                - usage: Token usage information (optional)
                - model: The model used
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the current model name."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass

    async def health_check(self) -> bool:
        """
        Check if the provider is available and configured correctly.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            response = await self.complete(prompt="Say 'OK' if you can read this.", max_tokens=10)
            return bool(response.get("content"))
        except Exception:
            return False
