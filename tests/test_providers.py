#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for how the LLM providers shape requests for current models."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.providers.anthropic_provider import AnthropicProvider
from api.providers.openai_provider import OpenAIProvider
from config.settings import Settings


def test_default_models_are_current():
    s = Settings(_env_file=None)
    assert s.anthropic_model == "claude-sonnet-5"
    assert s.openai_model == "gpt-5.6-terra"


def _anthropic(model):
    provider = AnthropicProvider(api_key="test", model=model)
    response = SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text="hello")],
        usage=SimpleNamespace(input_tokens=3, output_tokens=4),
        model=model,
    )
    provider.client.messages.create = AsyncMock(return_value=response)
    return provider


async def test_anthropic_sonnet_5_omits_temperature_and_disables_thinking():
    provider = _anthropic("claude-sonnet-5")
    result = await provider.complete("hi", temperature=0.3, max_tokens=500)
    kwargs = provider.client.messages.create.call_args.kwargs
    assert "temperature" not in kwargs
    assert kwargs["thinking"] == {"type": "disabled"}
    assert kwargs["max_tokens"] == 500
    assert result["content"] == "hello"


async def test_anthropic_always_thinking_model_gets_room():
    provider = _anthropic("claude-fable-5-1")
    await provider.complete("hi", max_tokens=100)
    kwargs = provider.client.messages.create.call_args.kwargs
    assert "thinking" not in kwargs
    assert "temperature" not in kwargs
    assert kwargs["max_tokens"] >= 16000


async def test_anthropic_older_model_keeps_temperature():
    provider = _anthropic("claude-haiku-4-5")
    await provider.complete("hi", temperature=0.3)
    kwargs = provider.client.messages.create.call_args.kwargs
    assert kwargs["temperature"] == 0.3
    assert "thinking" not in kwargs


def _openai(model):
    provider = OpenAIProvider(api_key="test", model=model)
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        model=model,
    )
    provider.client.chat.completions.create = AsyncMock(return_value=response)
    return provider


@pytest.mark.parametrize("model", ["gpt-5.6-terra", "gpt-6-astra"])
async def test_openai_reasoning_model_params(model):
    provider = _openai(model)
    await provider.complete("hi", temperature=0.7, max_tokens=800)
    kwargs = provider.client.chat.completions.create.call_args.kwargs
    assert "temperature" not in kwargs
    assert "max_tokens" not in kwargs
    assert kwargs["max_completion_tokens"] == 800
    assert kwargs["reasoning_effort"] == "low"


async def test_openai_classic_model_params():
    provider = _openai("gpt-4.1")
    await provider.complete("hi", temperature=0.2, max_tokens=50)
    kwargs = provider.client.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.2
    assert kwargs["max_tokens"] == 50
