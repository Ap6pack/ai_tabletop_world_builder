#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for LLMProviderFactory and the Ollama / Together providers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

import api.providers.ollama_provider as ollama_module
from api.providers.anthropic_provider import AnthropicProvider
from api.providers.factory import LLMProviderFactory
from api.providers.ollama_provider import OllamaProvider
from api.providers.openai_provider import OpenAIProvider
from api.providers.together_provider import TogetherProvider
from config.settings import settings

# conftest replaces create_provider with a fake for every test; keep the real one.
real_create_provider = LLMProviderFactory.__dict__["create_provider"].__func__


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-real-looking")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-real-looking")
    monkeypatch.setattr(settings, "together_api_key", "tg-real-looking")


@pytest.mark.parametrize(
    ("provider_type", "cls"),
    [
        ("openai", OpenAIProvider),
        ("anthropic", AnthropicProvider),
        ("together", TogetherProvider),
        ("ollama", OllamaProvider),
    ],
)
def test_create_each_provider(keys, provider_type, cls):
    provider = real_create_provider(provider_type)
    assert isinstance(provider, cls)
    assert provider.get_provider_name() == provider_type


def test_defaults_and_overrides(keys, monkeypatch):
    monkeypatch.setattr(settings, "default_llm_provider", "anthropic")
    provider = real_create_provider()
    assert provider.get_model_name() == settings.anthropic_model
    assert real_create_provider("openai", model="gpt-6-astra").get_model_name() == "gpt-6-astra"
    assert real_create_provider("ollama", base_url="http://gpu:11434/").base_url == "http://gpu:11434"


@pytest.mark.parametrize("provider_type", ["openai", "anthropic", "together"])
def test_missing_key_raises(monkeypatch, provider_type):
    monkeypatch.setattr(settings, f"{provider_type}_api_key", "")
    with pytest.raises(ValueError, match="API key is required"):
        real_create_provider(provider_type)


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        real_create_provider("skynet")


@pytest.mark.parametrize(
    ("key", "valid"),
    [("", False), ("   ", False), ("your_openai_api_key_here", False), ("paste_key", False), ("sk-abc123", True)],
)
def test_is_valid_api_key(key, valid):
    assert LLMProviderFactory._is_valid_api_key(key) is valid


async def test_get_available_providers(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "your_openai_api_key_here")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-real")
    monkeypatch.setattr(settings, "together_api_key", "")

    healthy = SimpleNamespace(health_check=AsyncMock(return_value=True))

    def fake_create(provider_type=None, **kwargs):
        if provider_type == "ollama":
            raise RuntimeError("not reachable")
        return healthy

    monkeypatch.setattr(LLMProviderFactory, "create_provider", staticmethod(fake_create))
    assert await LLMProviderFactory.get_available_providers() == {
        "openai": False,  # placeholder key: never contacted
        "anthropic": True,
        "together": False,
        "ollama": False,  # errors are reported as unavailable
    }


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------


def _patch_httpx(monkeypatch, handler):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        ollama_module.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )


async def test_ollama_complete(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = request.read()
        return httpx.Response(
            200, json={"message": {"content": "hi"}, "model": "llama3", "prompt_eval_count": 3, "eval_count": 4}
        )

    _patch_httpx(monkeypatch, handler)
    result = await OllamaProvider(base_url="http://ollama:11434").complete("hello", system_message="sys", max_tokens=9)
    assert seen["url"] == "http://ollama:11434/api/chat"
    assert b'"num_predict":9' in seen["body"].replace(b" ", b"")
    assert result == {
        "content": "hi",
        "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        "model": "llama3",
    }


async def test_ollama_health_check(monkeypatch):
    _patch_httpx(monkeypatch, lambda request: httpx.Response(200, json={"models": [{"name": "llama3:latest"}]}))
    assert await OllamaProvider().health_check() is True
    _patch_httpx(monkeypatch, lambda request: httpx.Response(200, json={"models": [{"name": "mistral"}]}))
    assert await OllamaProvider().health_check() is False
    _patch_httpx(monkeypatch, lambda request: httpx.Response(500))
    assert await OllamaProvider().health_check() is False


# ---------------------------------------------------------------------------
# Together
# ---------------------------------------------------------------------------


async def test_together_complete():
    provider = TogetherProvider(api_key="tg")
    provider.client.chat.completions.create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            model="llama",
        )
    )
    result = await provider.complete("hi", system_message="sys", temperature=0.2, max_tokens=10)
    kwargs = provider.client.chat.completions.create.call_args.kwargs
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["temperature"] == 0.2
    assert result["usage"]["total_tokens"] == 3
    assert result["content"] == "ok"
