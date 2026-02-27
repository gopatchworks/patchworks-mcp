"""Anthropic (Claude) provider — extracted from the original server.py /chat logic."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable

import anthropic

from .base import LLMProvider

log = logging.getLogger("patchworks-mcp")

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider(LLMProvider):
    """Runs the agentic chat loop against the Anthropic Messages API."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)

    # ------------------------------------------------------------------
    # Retry helper (exponential back-off on rate limits)
    # ------------------------------------------------------------------
    async def _call_with_retry(self, **kwargs) -> anthropic.types.Message:
        max_retries = 4
        base_delay = 15.0

        for attempt in range(max_retries):
            try:
                return self.client.messages.create(**kwargs)
            except anthropic.RateLimitError:
                if attempt == max_retries - 1:
                    log.error("Rate limit exceeded after %d attempts", max_retries)
                    raise
                delay = base_delay * (2 ** attempt)
                jitter = delay * 0.1 * (0.5 + asyncio.get_event_loop().time() % 1)
                total_delay = min(delay + jitter, 90)
                log.warning(
                    "Rate limited. Waiting %.1fs before retry %d/%d",
                    total_delay, attempt + 2, max_retries,
                )
                await asyncio.sleep(total_delay)
            except Exception:
                log.error("Claude API error", exc_info=True)
                raise

        raise RuntimeError("Unexpected: retry loop completed without return")

    # ------------------------------------------------------------------
    # Agentic loop
    # ------------------------------------------------------------------
    async def run_chat(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
        tool_executor: Callable[[str, dict], str],
        max_iterations: int,
    ) -> str:
        # Tools are already in Anthropic format — use as-is.
        for iteration in range(max_iterations):
            log.info("Anthropic API call (iteration %d/%d)", iteration + 1, max_iterations)

            try:
                response = await self._call_with_retry(
                    model=self.model,
                    max_tokens=2048,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    tools=tools,
                    messages=messages,
                )
            except Exception as e:
                return (
                    "I encountered an error communicating with the AI service. "
                    f"Please try again. Error: {e}"
                )

            # Model finished
            if response.stop_reason == "end_turn":
                text_parts = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_parts) or "No response generated."

            # Model wants to use tools
            if response.stop_reason == "tool_use":
                messages.append({
                    "role": "assistant",
                    "content": [block.model_dump() for block in response.content],
                })

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        log.info("Executing tool: %s", block.name)
                        result_str = tool_executor(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })

                messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason
            log.warning("Unexpected stop_reason: %s", response.stop_reason)
            text_parts = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_parts) or "Unexpected response from assistant."

        return (
            f"I needed more than {max_iterations} tool calls to answer this. "
            "Please try asking a more specific question or breaking it into smaller requests."
        )
