#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Together AI LLM provider implementation.

Together exposes an OpenAI-compatible Chat Completions API, so this provider
reuses the OpenAI async client pointed at Together's base URL.
"""

from typing import Any

from openai import AsyncOpenAI

from .base import BaseLLMProvider

TOGETHER_BASE_URL = "https://api.together.xyz/v1"


class TogetherProvider(BaseLLMProvider):
    """Together AI provider (OpenAI-compatible), typically serving Llama/Mistral models."""

    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        base_url: str = TOGETHER_BASE_URL,
        **kwargs,
    ):
        super().__init__(api_key, **kwargs)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def complete(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate completion using Together's OpenAI-compatible API."""
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens, **kwargs
        )

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return {
            "content": response.choices[0].message.content,
            "usage": usage,
            "model": response.model,
        }

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "together"
