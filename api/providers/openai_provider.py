#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
OpenAI LLM provider implementation.
"""

from typing import Any

from openai import AsyncOpenAI

from .base import BaseLLMProvider

# Reasoning models take max_completion_tokens and reject temperature.
_REASONING_PREFIXES = ("gpt-5", "gpt-6", "o1", "o3", "o4")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str, model: str = "gpt-5.6-terra", **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def complete(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate completion using OpenAI API."""
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        params: dict[str, Any] = {}
        if self.model.startswith(_REASONING_PREFIXES):
            params["reasoning_effort"] = "low"
            if max_tokens is not None:
                params["max_completion_tokens"] = max_tokens
        else:
            params["temperature"] = temperature
            params["max_tokens"] = max_tokens
        params.update(kwargs)

        response = await self.client.chat.completions.create(model=self.model, messages=messages, **params)

        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "model": response.model,
        }

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "openai"
