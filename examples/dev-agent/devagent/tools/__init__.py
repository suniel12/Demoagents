"""Tool registry and base infrastructure for DevAgent.

Design Decisions:
- Tools are defined as Pydantic models for input/output (typed, validatable)
- Each tool has an Anthropic-compatible JSON schema for the LLM
- Tools are pure functions: input → output, no side effects, easily mockable
- The registry is a simple dict — AgentCI can inspect it for test setup

This architecture maps directly to how most developers build tool-calling agents,
making the AgentCI testing patterns transferable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from pydantic import BaseModel


@dataclass
class ToolDefinition:
    """A registered tool that the agent can call."""

    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema for Anthropic tool_use
    handler: Callable[..., Awaitable[Any]]  # async function that executes the tool
    output_model: type[BaseModel] | None = None  # Pydantic model for output validation


class ToolRegistry:
    """Registry of all tools available to the agent.

    The registry serves double duty:
    1. Provides tool definitions to the Anthropic API (for LLM tool selection)
    2. Provides tool metadata to AgentCI (for test assertions)

    Usage:
        registry = ToolRegistry()
        registry.register(github_repo_metadata_tool)
        
        # For the LLM
        anthropic_tools = registry.to_anthropic_format()
        
        # For AgentCI
        tool_names = registry.list_tools()
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool. Raises if name already exists."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        """Get a tool by name. Raises KeyError if not found."""
        return self._tools[name]

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def to_anthropic_format(self) -> list[dict[str, Any]]:
        """Convert all tools to Anthropic API format.

        Returns the format expected by the `tools` parameter in
        anthropic.messages.create().
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    async def execute(self, name: str, input_data: dict[str, Any]) -> Any:
        """Execute a tool by name with the given input.

        This is the method AgentCI hooks into for:
        - Trace capture (recording what was called with what input)
        - Mocking (replacing the handler with a mock in tests)
        - Cost tracking (measuring execution time and token usage)
        """
        tool = self.get(name)
        result = await tool.handler(**input_data)

        # If tool has an output model, validate the result
        if tool.output_model and isinstance(result, dict):
            validated = tool.output_model.model_validate(result)
            return validated.model_dump()

        return result
