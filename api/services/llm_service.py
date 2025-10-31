"""
LLM service for managing LLM interactions.
"""
from typing import Optional, Dict, Any
from api.providers import LLMProviderFactory, ProviderType
from api.models import LLMRequest, LLMResponse


class LLMService:
    """Service for managing LLM completions."""

    @staticmethod
    async def generate_completion(request: LLMRequest) -> LLMResponse:
        """
        Generate a completion using the specified LLM provider.

        Args:
            request: LLM request parameters

        Returns:
            LLM response with generated content

        Raises:
            ValueError: If provider configuration is invalid
            Exception: If LLM API call fails
        """
        provider = LLMProviderFactory.create_provider(
            provider_type=request.provider,
            model=request.model,
            temperature=request.temperature,
        )

        result = await provider.complete(
            prompt=request.prompt,
            system_message=request.system_message,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens,
        )

        return LLMResponse(
            content=result["content"],
            provider=provider.get_provider_name(),
            model=result["model"],
            usage=result.get("usage"),
        )

    @staticmethod
    async def check_providers() -> Dict[str, bool]:
        """
        Check availability of all configured providers.

        Returns:
            Dict mapping provider names to availability status
        """
        return await LLMProviderFactory.get_available_providers()
