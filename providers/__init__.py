"""LLM provider factory.

Reads LLM_PROVIDER from the environment (default: "anthropic") and returns
the corresponding provider instance.  Provider-specific API keys and model
overrides are also read from env vars — see .env.example.
"""
from __future__ import annotations

import os
import logging

from .base import LLMProvider

log = logging.getLogger("patchworks-mcp")

SUPPORTED_PROVIDERS = ("anthropic", "openai", "gemini")


def get_provider(name: str | None = None) -> LLMProvider:
    """Return an LLMProvider instance for the given (or configured) provider name.

    Args:
        name: One of "anthropic", "openai", "gemini".
              Falls back to the LLM_PROVIDER env var, then to "anthropic".
    """
    provider_name = (name or os.getenv("LLM_PROVIDER", "anthropic")).lower().strip()

    if provider_name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        log.info("Using Anthropic (Claude) provider — model: %s", os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"))
        return AnthropicProvider()

    if provider_name == "openai":
        from .openai_provider import OpenAIProvider
        log.info("Using OpenAI provider — model: %s", os.getenv("OPENAI_MODEL", "gpt-4o"))
        return OpenAIProvider()

    if provider_name == "gemini":
        from .gemini_provider import GeminiProvider
        log.info("Using Gemini provider — model: %s", os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
        return GeminiProvider()

    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider_name!r}. "
        f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
    )
