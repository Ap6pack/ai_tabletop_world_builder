#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
Factory for creating LLM providers.
"""

from typing import Literal

from config import settings

from .anthropic_provider import AnthropicProvider
from .base import BaseLLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

ProviderType = Literal["openai", "anthropic", "ollama"]


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def create_provider(provider_type: ProviderType | None = None, **kwargs) -> BaseLLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider_type: The type of provider to create (openai, anthropic, ollama)
                          If None, uses the default from settings
            **kwargs: Provider-specific configuration overrides

        Returns:
            An instance of BaseLLMProvider

        Raises:
            ValueError: If provider type is invalid or configuration is missing
        """
        if provider_type is None:
            provider_type = settings.default_llm_provider

        if provider_type == "openai":
            api_key = kwargs.get("api_key") or settings.openai_api_key
            if not api_key:
                raise ValueError("OpenAI API key is required")

            model = kwargs.get("model")
            if model is None:
                model = settings.openai_model

            temperature = kwargs.get("temperature")
            if temperature is None:
                temperature = settings.openai_temperature

            return OpenAIProvider(
                api_key=api_key,
                model=model,
                temperature=temperature,
            )

        elif provider_type == "anthropic":
            api_key = kwargs.get("api_key") or settings.anthropic_api_key
            if not api_key:
                raise ValueError("Anthropic API key is required")

            model = kwargs.get("model")
            if model is None:
                model = settings.anthropic_model

            temperature = kwargs.get("temperature")
            if temperature is None:
                temperature = settings.anthropic_temperature

            return AnthropicProvider(
                api_key=api_key,
                model=model,
                temperature=temperature,
            )

        elif provider_type == "ollama":
            base_url = kwargs.get("base_url")
            if base_url is None:
                base_url = settings.ollama_base_url

            model = kwargs.get("model")
            if model is None:
                model = settings.ollama_model

            temperature = kwargs.get("temperature")
            if temperature is None:
                temperature = settings.ollama_temperature

            return OllamaProvider(
                base_url=base_url,
                model=model,
                temperature=temperature,
            )

        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    @staticmethod
    def _is_valid_api_key(key: str) -> bool:
        """
        Check if an API key looks valid (not empty, not placeholder).

        Args:
            key: API key string to validate

        Returns:
            True if key looks valid, False otherwise
        """
        if not key or not key.strip():
            return False

        # Check for common placeholder values
        placeholders = ["your_", "insert_", "add_your_", "replace_", "paste_", "api_key_here", "key_here"]

        key_lower = key.lower()
        return not any(placeholder in key_lower for placeholder in placeholders)

    @staticmethod
    async def get_available_providers() -> dict[str, bool]:
        """
        Check which providers are available and configured.

        Returns:
            Dict mapping provider names to availability status
        """
        availability = {}

        # Check OpenAI - validate key looks real before attempting health check
        try:
            if LLMProviderFactory._is_valid_api_key(settings.openai_api_key):
                provider = LLMProviderFactory.create_provider("openai")
                availability["openai"] = await provider.health_check()
            else:
                availability["openai"] = False
        except Exception:
            availability["openai"] = False

        # Check Anthropic - validate key looks real before attempting health check
        try:
            if LLMProviderFactory._is_valid_api_key(settings.anthropic_api_key):
                provider = LLMProviderFactory.create_provider("anthropic")
                availability["anthropic"] = await provider.health_check()
            else:
                availability["anthropic"] = False
        except Exception:
            availability["anthropic"] = False

        # Check Ollama - doesn't need API key validation
        try:
            provider = LLMProviderFactory.create_provider("ollama")
            availability["ollama"] = await provider.health_check()
        except Exception:
            availability["ollama"] = False

        return availability
