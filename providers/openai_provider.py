"""OpenAI (ChatGPT) provider for the /chat endpoint."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Callable

from openai import OpenAI, RateLimitError

from .base import LLMProvider
from .tool_converter import to_openai

log = logging.getLogger("patchworks-mcp")

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider(LLMProvider):
    """Runs the agentic chat loop against the OpenAI Chat Completions API."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------
    async def _call_with_retry(self, **kwargs):
        max_retries = 4
        base_delay = 15.0

        for attempt in range(max_retries):
            try:
                return self.client.chat.completions.create(**kwargs)
            except RateLimitError:
                if attempt == max_retries - 1:
                    log.error("OpenAI rate limit exceeded after %d attempts", max_retries)
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
                log.error("OpenAI API error", exc_info=True)
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
        openai_tools = to_openai(tools)

        # Build OpenAI message history.
        # OpenAI uses a system message in the messages array (not a separate param).
        openai_messages: list[dict] = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            openai_messages.append({"role": msg["role"], "content": msg["content"]})

        for iteration in range(max_iterations):
            log.info("OpenAI API call (iteration %d/%d)", iteration + 1, max_iterations)

            try:
                response = await self._call_with_retry(
                    model=self.model,
                    max_tokens=2048,
                    tools=openai_tools,
                    messages=openai_messages,
                )
            except Exception as e:
                return (
                    "I encountered an error communicating with the AI service. "
                    f"Please try again. Error: {e}"
                )

            choice = response.choices[0]
            message = choice.message

            # Model finished — no tool calls
            if choice.finish_reason == "stop":
                return message.content or "No response generated."

            # Model wants to use tools
            if choice.finish_reason == "tool_calls" and message.tool_calls:
                # Append the assistant message (with tool_calls) to history
                openai_messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                })

                # Execute each tool and append results
                for tc in message.tool_calls:
                    log.info("Executing tool: %s", tc.function.name)
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}
                    result_str = tool_executor(tc.function.name, tool_input)
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })

                continue

            # Unexpected finish reason
            log.warning("Unexpected finish_reason: %s", choice.finish_reason)
            return message.content or "Unexpected response from assistant."

        return (
            f"I needed more than {max_iterations} tool calls to answer this. "
            "Please try asking a more specific question or breaking it into smaller requests."
        )
