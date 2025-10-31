"""
Factory for creating LLM providers.
"""
from typing import Optional, Literal
from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .ollama_provider import OllamaProvider
from config import settings


ProviderType = Literal["openai", "anthropic", "ollama"]


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def create_provider(
        provider_type: Optional[ProviderType] = None,
        **kwargs
    ) -> BaseLLMProvider:
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
    async def get_available_providers() -> dict[str, bool]:
        """
        Check which providers are available and configured.

        Returns:
            Dict mapping provider names to availability status
        """
        availability = {}

        # Check OpenAI
        try:
            if settings.openai_api_key:
                provider = LLMProviderFactory.create_provider("openai")
                availability["openai"] = await provider.health_check()
            else:
                availability["openai"] = False
        except Exception:
            availability["openai"] = False

        # Check Anthropic
        try:
            if settings.anthropic_api_key:
                provider = LLMProviderFactory.create_provider("anthropic")
                availability["anthropic"] = await provider.health_check()
            else:
                availability["anthropic"] = False
        except Exception:
            availability["anthropic"] = False

        # Check Ollama
        try:
            provider = LLMProviderFactory.create_provider("ollama")
            availability["ollama"] = await provider.health_check()
        except Exception:
            availability["ollama"] = False

        return availability
