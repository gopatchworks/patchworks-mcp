"""Google Gemini provider for the /chat endpoint."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Callable

from google import genai
from google.genai import types

from .base import LLMProvider
from .tool_converter import to_gemini

log = logging.getLogger("patchworks-mcp")

DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiProvider(LLMProvider):
    """Runs the agentic chat loop against the Google Gemini API."""

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_tools(anthropic_tools: list[dict]) -> list[types.Tool]:
        """Convert Anthropic tool definitions to Gemini Tool objects."""
        declarations = to_gemini(anthropic_tools)
        return [types.Tool(function_declarations=declarations)]

    @staticmethod
    def _extract_text(response) -> str:
        """Pull plain text from a Gemini GenerateContentResponse."""
        parts = []
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.text:
                    parts.append(part.text)
        return "\n".join(parts)

    @staticmethod
    def _extract_function_calls(response) -> list[tuple[str, dict]]:
        """Return [(name, args), ...] for all function_call parts in the response."""
        calls = []
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.function_call:
                    fc = part.function_call
                    # fc.args is a proto Struct — convert to plain dict
                    args = dict(fc.args) if fc.args else {}
                    calls.append((fc.name, args))
        return calls

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------
    async def _call_with_retry(self, **kwargs):
        max_retries = 4
        base_delay = 15.0

        for attempt in range(max_retries):
            try:
                return await self.client.aio.models.generate_content(**kwargs)
            except Exception as e:
                error_str = str(e).lower()
                if "resource exhausted" in error_str or "429" in error_str:
                    if attempt == max_retries - 1:
                        log.error("Gemini rate limit exceeded after %d attempts", max_retries)
                        raise
                    delay = base_delay * (2 ** attempt)
                    jitter = delay * 0.1 * (0.5 + asyncio.get_event_loop().time() % 1)
                    total_delay = min(delay + jitter, 90)
                    log.warning(
                        "Rate limited. Waiting %.1fs before retry %d/%d",
                        total_delay, attempt + 2, max_retries,
                    )
                    await asyncio.sleep(total_delay)
                else:
                    log.error("Gemini API error", exc_info=True)
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
        gemini_tools = self._build_tools(tools)

        # Build Gemini contents from message history.
        # Gemini uses "user" and "model" roles (not "assistant").
        contents: list[types.Content] = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=gemini_tools,
            max_output_tokens=2048,
        )

        for iteration in range(max_iterations):
            log.info("Gemini API call (iteration %d/%d)", iteration + 1, max_iterations)

            try:
                response = await self._call_with_retry(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                return (
                    "I encountered an error communicating with the AI service. "
                    f"Please try again. Error: {e}"
                )

            function_calls = self._extract_function_calls(response)

            # No function calls — model is done
            if not function_calls:
                return self._extract_text(response) or "No response generated."

            # Append the model's response (with function calls) to contents
            contents.append(response.candidates[0].content)

            # Execute tools and build function responses
            function_response_parts = []
            for name, args in function_calls:
                log.info("Executing tool: %s", name)
                result_str = tool_executor(name, args)
                # Parse result back to dict for Gemini (it expects structured data)
                try:
                    result_data = json.loads(result_str)
                except json.JSONDecodeError:
                    result_data = {"result": result_str}

                function_response_parts.append(
                    types.Part.from_function_response(
                        name=name,
                        response=result_data,
                    )
                )

            # Append tool results as a user turn
            contents.append(
                types.Content(role="user", parts=function_response_parts)
            )
            continue

        return (
            f"I needed more than {max_iterations} tool calls to answer this. "
            "Please try asking a more specific question or breaking it into smaller requests."
        )
