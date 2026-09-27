#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Anthropic Claude LLM provider implementation.
"""

from typing import Any

from anthropic import AsyncAnthropic

from .base import BaseLLMProvider

# Newer Claude models reject sampling parameters (temperature/top_p/top_k).
_NO_SAMPLING_PREFIXES = (
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-fable",
    "claude-mythos",
)
# Models where thinking cannot be turned off: omit the parameter and give the
# response room for thinking tokens.
_ALWAYS_THINKING_PREFIXES = ("claude-opus-5-5", "claude-fable", "claude-mythos")
_THINKING_MIN_MAX_TOKENS = 16000


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5", **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate completion using Anthropic API."""
        # Claude requires max_tokens to be set
        if max_tokens is None:
            max_tokens = 4096

        params: dict[str, Any] = {}
        if self.model.startswith(_ALWAYS_THINKING_PREFIXES):
            max_tokens = max(max_tokens, _THINKING_MIN_MAX_TOKENS)
        elif self.model.startswith(_NO_SAMPLING_PREFIXES):
            # Short, fast game-master replies: keep thinking off so the
            # caller's max_tokens budget goes to the answer.
            params["thinking"] = {"type": "disabled"}
        else:
            params["temperature"] = temperature
        params.update(kwargs)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_message if system_message else "",
            messages=[{"role": "user", "content": prompt}],
            **params,
        )

        return {
            "content": "".join(block.text for block in response.content if block.type == "text"),
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            "model": response.model,
        }

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "anthropic"
