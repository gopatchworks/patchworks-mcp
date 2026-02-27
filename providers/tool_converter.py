"""Convert tool definitions from Anthropic format to OpenAI and Gemini formats."""
from __future__ import annotations

import copy
from typing import Any

# Keys that Gemini's OpenAPI-subset schema does not support.
_GEMINI_UNSUPPORTED_KEYS = {"additionalProperties", "anyOf"}


def _sanitize_for_gemini(schema: dict) -> dict:
    """Recursively clean a JSON Schema for Gemini compatibility.

    Handles:
    - anyOf-with-null → collapses to the non-null type
    - additionalProperties → removed (Gemini rejects unknown fields)
    """
    schema = copy.deepcopy(schema)

    # --- Strip additionalProperties at every level ---
    schema.pop("additionalProperties", None)

    # --- Collapse anyOf-with-null ---
    if "anyOf" in schema:
        non_null = [s for s in schema["anyOf"] if s.get("type") != "null"]
        if len(non_null) == 1:
            # Merge the non-null type back, preserving description/default
            merged = {k: v for k, v in schema.items() if k != "anyOf"}
            merged.update(non_null[0])
            # The merged branch might itself contain unsupported keys
            schema = _sanitize_for_gemini(merged)
            return schema
        elif len(non_null) > 1:
            # Multiple non-null types — keep as-is (rare in this codebase)
            pass
        # Remove the anyOf key even if we couldn't collapse it
        # (Gemini doesn't support anyOf at all)
        if "anyOf" in schema:
            schema.pop("anyOf")
            if non_null:
                schema.update(non_null[0])

    # --- Recurse into properties ---
    if "properties" in schema:
        for key, prop in schema["properties"].items():
            schema["properties"][key] = _sanitize_for_gemini(prop)

    # --- Recurse into items ---
    if "items" in schema and isinstance(schema["items"], dict):
        schema["items"] = _sanitize_for_gemini(schema["items"])

    return schema


def to_openai(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool definitions to OpenAI function-calling format.

    Anthropic:  {"name", "description", "input_schema": {JSON Schema}}
    OpenAI:     {"type": "function", "function": {"name", "description", "parameters": {JSON Schema}}}
    """
    openai_tools = []
    for tool in anthropic_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return openai_tools


def to_gemini(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool definitions to Gemini function-declaration format.

    Gemini uses a subset of OpenAPI Schema and does not support:
    - anyOf (used for nullable types)
    - additionalProperties

    Returns a list of function declarations (not wrapped in a Tool object —
    the provider handles that).
    """
    declarations = []
    for tool in anthropic_tools:
        params = _sanitize_for_gemini(tool.get("input_schema", {}))
        declarations.append({
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": params,
        })
    return declarations
