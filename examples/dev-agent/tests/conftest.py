"""Pytest conftest — sets up AgentCI fixtures and mock infrastructure.

This is where the magic happens. These fixtures let every test:
1. Run the agent with mocked tools (no real API calls in CI)
2. Run the agent with real tools (for live validation)
3. Capture and inspect traces
4. Compare against golden traces
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import os
import pytest
import pytest_asyncio

@pytest.fixture(autouse=True)
def dummy_env_vars():
    """Ensure Anthropic client can initialize without a real API key during tests."""
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy-key-for-testing"
    yield
    os.environ.pop("ANTHROPIC_API_KEY", None)

from devagent.agent.core import DevAgent, Trace
from devagent.tools import ToolRegistry, ToolDefinition
from devagent.tools.github_repo_metadata import (
    github_repo_metadata_tool,
    fetch_repo_metadata,
    RepoMetadataOutput,
)

from tests.fixtures import (
    MOCK_HEALTHY_RESPONSE,
    MOCK_STALE_RESPONSE,
    MOCK_MINIMAL_RESPONSE,
    REPO_HEALTHY,
    REPO_STALE,
    REPO_MINIMAL,
    REPO_NONEXISTENT,
)


# ──────────────────────────────────────────────
# Mock Tool Factory
# ──────────────────────────────────────────────


def make_mock_github_tool(mock_response: dict | Exception) -> ToolDefinition:
    """Create a mock version of the github_repo_metadata tool.

    If mock_response is a dict, the tool returns it successfully.
    If mock_response is an Exception, the tool raises it.

    This pattern is what AgentCI should provide as a built-in utility:
        agentci.mock_tool("github_repo_metadata", response={...})
    
    Building it manually here teaches us what the API should feel like.
    """
    async def mock_handler(owner: str, repo: str) -> dict:
        if isinstance(mock_response, Exception):
            raise mock_response

        # Simulate the real handler's output mapping
        return RepoMetadataOutput(
            owner=mock_response["owner"]["login"],
            repo=mock_response["name"],
            full_name=mock_response["full_name"],
            description=mock_response.get("description"),
            language=mock_response.get("language"),
            stars=mock_response["stargazers_count"],
            forks=mock_response["forks_count"],
            open_issues=mock_response["open_issues_count"],
            watchers=mock_response["subscribers_count"],
            license_name=(
                mock_response["license"]["name"]
                if mock_response.get("license")
                else None
            ),
            default_branch=mock_response["default_branch"],
            created_at=mock_response["created_at"],
            last_pushed_at=mock_response["pushed_at"],
            is_fork=mock_response["fork"],
            is_archived=mock_response["archived"],
            topics=mock_response.get("topics", []),
            size_kb=mock_response["size"],
        ).model_dump()

    return ToolDefinition(
        name=github_repo_metadata_tool.name,
        description=github_repo_metadata_tool.description,
        input_schema=github_repo_metadata_tool.input_schema,
        handler=mock_handler,
        output_model=github_repo_metadata_tool.output_model,
    )


def make_mock_registry(mock_response: dict | Exception) -> ToolRegistry:
    """Create a ToolRegistry with mocked tools."""
    registry = ToolRegistry()
    registry.register(make_mock_github_tool(mock_response))
    return registry


# ──────────────────────────────────────────────
# Pytest Fixtures
# ──────────────────────────────────────────────


def mock_anthropic_client(fixture_name: str) -> AsyncMock:
    """Creates a mock Anthropic client that generates deterministic tool calls.
    
    This replaces the live LLM so tests run fast, free, and deterministically.
    """
    mock_client = AsyncMock()
    
    # We need to simulate the multi-turn agent loop:
    # 1st call: LLM decides to use the github_repo_metadata tool
    # 2nd call: LLM sees the tool result and generates the final text report
    
    # Mock the response for the 1st turn (Tool Use)
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.id = "mock_tool_id_123"
    tool_use_block.name = "github_repo_metadata"
    
    # Determine input based on fixture type
    if fixture_name == "healthy":
        tool_use_block.input = {"owner": REPO_HEALTHY["owner"], "repo": REPO_HEALTHY["repo"]}
    elif fixture_name == "stale":
        tool_use_block.input = {"owner": REPO_STALE["owner"], "repo": REPO_STALE["repo"]}
    elif fixture_name == "minimal":
        tool_use_block.input = {"owner": REPO_MINIMAL["owner"], "repo": REPO_MINIMAL["repo"]}
    elif fixture_name == "error":
        tool_use_block.input = {"owner": REPO_NONEXISTENT["owner"], "repo": REPO_NONEXISTENT["repo"]}
        
    first_response = MagicMock()
    first_response.content = [tool_use_block]
    first_response.stop_reason = "tool_use"
    first_response.usage.input_tokens = 500
    first_response.usage.output_tokens = 100
    
    # Mock the response for the 2nd turn (Final Report)
    text_block = MagicMock()
    text_block.type = "text"
    
    # Determine realistic report content based on fixture
    if fixture_name == "healthy":
        text_block.text = (
            "### Repository Health Report: langchain-ai/langchain\n\n"
            "**Overview**\n"
            "- Description: Build context-aware reasoning applications\n"
            "- Primary Language: Python\n"
            "- License: MIT License\n\n"
            "**Popularity & Activity Metrics**\n"
            "- Stars: 102,000 | Forks: 15800\n\n"
            "**Initial Health Signals**\n"
            "- [GOOD] Activity: high\n"
            "- [GOOD] License: present\n\n"
            "**Composite Score**: A — Excellent health\n\n"
            "**Recommendations**\n"
            "- Keep merging PRs"
        )
    elif fixture_name == "stale":
        text_block.text = (
            "### Repository Health Report: facebookarchive/react-native-fbsdk\n\n"
            "**Overview**\n"
            "- Description: Archived react native SDK\n"
            "- Primary Language: JavaScript\n"
            "- License: MIT\n\n"
            "**Popularity & Activity Metrics**\n"
            "- Stars: 5,000 | Forks: 1000\n\n"
            "**Initial Health Signals**\n"
            "- [CONCERN] Activity: Repo is archived and stale\n\n"
            "**Composite Score**: F — Archived\n\n"
            "**Recommendations**\n"
            "- Do not use this repo"
        )
    elif fixture_name == "error":
        text_block.text = (
            "I could not analyze the repository because it does not exist or is inaccessible. "
            "The github_repo_metadata tool returned a 404 Not Found error. "
            "Please check the URL and try again."
        )
    else:  # minimal
        text_block.text = (
            "### Repository Health Report: user/repo\n\n"
            "**Overview**\n"
            "- Description: None\n"
            "- Primary Language: Not specified\n"
            "- License: None specified\n\n"
            "**Popularity & Activity Metrics**\n"
            "- Stars: 100 | Forks: 10\n\n"
            "**Initial Health Signals**\n"
            "- [WARN] Warning\n\n"
            "**Composite Score**: C — Needs work\n\n"
            "**Recommendations**\n"
            "- Add a license"
        )
    
    second_response = MagicMock()
    second_response.content = [text_block]
    second_response.stop_reason = "end_turn"
    second_response.usage.input_tokens = 800
    second_response.usage.output_tokens = 300
    
    # .side_effect allows us to return different things on sequential calls
    mock_client.messages.create.side_effect = [first_response, second_response]
    
    return mock_client


@pytest_asyncio.fixture
async def agent_healthy() -> DevAgent:
    """Agent with mocked GitHub API returning a healthy repo."""
    registry = make_mock_registry(MOCK_HEALTHY_RESPONSE)
    agent = DevAgent(registry=registry)
    agent.client = mock_anthropic_client("healthy")
    return agent


@pytest_asyncio.fixture
async def agent_stale() -> DevAgent:
    """Agent with mocked GitHub API returning a stale/archived repo."""
    registry = make_mock_registry(MOCK_STALE_RESPONSE)
    agent = DevAgent(registry=registry)
    agent.client = mock_anthropic_client("stale")
    return agent


@pytest_asyncio.fixture
async def agent_minimal() -> DevAgent:
    """Agent with mocked GitHub API returning a minimal repo."""
    registry = make_mock_registry(MOCK_MINIMAL_RESPONSE)
    agent = DevAgent(registry=registry)
    agent.client = mock_anthropic_client("minimal")
    return agent


@pytest_asyncio.fixture
async def agent_error() -> DevAgent:
    """Agent with mocked GitHub API that raises a 404 error."""
    import httpx

    error = httpx.HTTPStatusError(
        "404 Not Found",
        request=httpx.Request("GET", "https://api.github.com/repos/x/y"),
        response=httpx.Response(404),
    )
    registry = make_mock_registry(error)
    agent = DevAgent(registry=registry)
    agent.client = mock_anthropic_client("error")
    return agent


@pytest_asyncio.fixture
async def agent_live() -> DevAgent:
    """Agent with REAL GitHub API access. Only for @pytest.mark.live tests."""
    return DevAgent()


@pytest.fixture
def trace_healthy(agent_healthy):
    """Pre-run trace for a healthy repo. Use when you need the trace, not the agent."""
    # This is a factory fixture — call it to get the trace
    async def _run():
        return await agent_healthy.analyze(REPO_HEALTHY["url"])
    return _run


@pytest.fixture
def trace_stale(agent_stale):
    """Pre-run trace for a stale repo."""
    async def _run():
        return await agent_stale.analyze(REPO_STALE["url"])
    return _run
