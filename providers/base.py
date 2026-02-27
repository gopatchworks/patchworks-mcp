"""Abstract base class for LLM providers used by the /chat endpoint."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class LLMProvider(ABC):
    """Interface that each LLM provider must implement.

    The provider is responsible for:
    - Converting tool definitions to its native format
    - Running the agentic loop (API call → tool execution → repeat)
    - Returning the final text response
    """

    @abstractmethod
    async def run_chat(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
        tool_executor: Callable[[str, dict], str],
        max_iterations: int,
    ) -> str:
        """Run the agentic chat loop.

        Args:
            messages: Conversation history in a provider-neutral format.
                      Each message has {"role": "user"|"assistant", "content": str}.
            system_prompt: System instructions for the model.
            tools: Tool definitions in Anthropic format (canonical source).
            tool_executor: Callable(tool_name, tool_input) -> result_str.
            max_iterations: Max number of tool-use round-trips.

        Returns:
            The final assistant text response.
        """
        ...
