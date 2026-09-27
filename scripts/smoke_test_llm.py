#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""Make one real, tiny call to each configured LLM provider.

The test suite never calls a real LLM (providers are faked), so it can't tell
whether an SDK upgrade still works. Run this after changing `openai`,
`anthropic` or provider code, with real keys in the environment or .env:

    python scripts/smoke_test_llm.py                 # every provider with a key
    python scripts/smoke_test_llm.py anthropic       # just one

Each call asks for a one-word reply and costs a fraction of a cent. Exit code is
non-zero if any attempted provider fails.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.providers.factory import LLMProviderFactory  # noqa: E402
from config.settings import settings  # noqa: E402

PROVIDERS = {
    "anthropic": lambda: settings.anthropic_api_key,
    "openai": lambda: settings.openai_api_key,
    "together": lambda: settings.together_api_key,
}


async def check(name: str) -> bool:
    try:
        provider = LLMProviderFactory.create_provider(name)
        result = await provider.complete(
            "Reply with the single word: ready",
            system_message="You are a connectivity check. Answer in one word.",
            max_tokens=20,
        )
    except Exception as exc:  # noqa: BLE001 - report any failure
        print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
        return False
    text = (result.get("content") or "").strip()
    if not text:
        print(f"FAIL  {name} ({result.get('model')}): empty reply")
        return False
    print(f"OK    {name} ({result.get('model')}): {text[:60]!r}")
    return True


async def main(selected: list[str]) -> int:
    names = selected or [n for n, key in PROVIDERS.items() if LLMProviderFactory._is_valid_api_key(key())]
    if not names:
        print("No provider API keys found. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY.")
        return 2
    results = [await check(name) for name in names]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
