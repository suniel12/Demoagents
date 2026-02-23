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


def make_mock_list_files_tool(mock_response: dict | Exception) -> ToolDefinition:
    """Create a mock version of the github_list_files tool."""
    from devagent.tools.github_list_files import github_list_files_tool, ListFilesOutput
    
    async def mock_handler(owner: str, repo: str, tree_sha: str = "HEAD", recursive: bool = True) -> dict:
        if isinstance(mock_response, Exception):
            raise mock_response
        return ListFilesOutput(**mock_response).model_dump()
        
    return ToolDefinition(
        name=github_list_files_tool.name,
        description=github_list_files_tool.description,
        input_schema=github_list_files_tool.input_schema,
        handler=mock_handler,
        output_model=github_list_files_tool.output_model,
    )


def make_mock_read_file_tool(mock_responses: dict[str, dict | Exception]) -> ToolDefinition:
    """Create a mock version of github_read_file mapping paths to responses."""
    from devagent.tools.github_read_file import github_read_file_tool, ReadFileOutput
    
    async def mock_handler(owner: str, repo: str, path: str, ref: str | None = None) -> dict:
        response = mock_responses.get(path)
        if response is None:
            import httpx
            raise httpx.HTTPStatusError(
                "404 Not Found",
                request=httpx.Request("GET", f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"),
                response=httpx.Response(404),
            )
        if isinstance(response, Exception):
            raise response
        return ReadFileOutput(**response).model_dump()
        
    return ToolDefinition(
        name=github_read_file_tool.name,
        description=github_read_file_tool.description,
        input_schema=github_read_file_tool.input_schema,
        handler=mock_handler,
        output_model=github_read_file_tool.output_model,
    )


def make_mock_dependency_analyzer(mock_responses: dict[str, dict | Exception]) -> ToolDefinition:
    """Create a mock version of dependency_analyzer mapping manifest strings to responses."""
    from devagent.tools.dependency_analyzer import dependency_analyzer_tool, DependencyAnalyzerOutput
    
    async def mock_handler(manifest_content: str, manifest_type: str) -> dict:
        # Simple lookup fallback
        response = mock_responses.get(manifest_type, mock_responses.get("default"))
        if isinstance(response, Exception):
            raise response
        return DependencyAnalyzerOutput(**response).model_dump()
        
    return ToolDefinition(
        name=dependency_analyzer_tool.name,
        description=dependency_analyzer_tool.description,
        input_schema=dependency_analyzer_tool.input_schema,
        handler=mock_handler,
        output_model=dependency_analyzer_tool.output_model,
    )


def make_mock_registry(
    mock_metadata_response: dict | Exception,
    mock_tree_response: dict | Exception | None = None,
    mock_file_responses: dict[str, dict | Exception] | None = None,
    mock_dep_responses: dict[str, dict | Exception] | None = None,
) -> ToolRegistry:
    """Create a ToolRegistry with all Phase 1 mocked tools."""
    registry = ToolRegistry()
    registry.register(make_mock_github_tool(mock_metadata_response))
    
    if mock_tree_response is not None:
        registry.register(make_mock_list_files_tool(mock_tree_response))
        
    if mock_file_responses is not None:
        registry.register(make_mock_read_file_tool(mock_file_responses))
        
    if mock_dep_responses is not None:
        registry.register(make_mock_dependency_analyzer(mock_dep_responses))
        
    return registry


# ──────────────────────────────────────────────
# Mock LLM Client
# ──────────────────────────────────────────────


def mock_anthropic_client(fixture_name: str) -> AsyncMock:
    """Creates a mock Anthropic client that generates deterministic tool calls."""
    mock_client = AsyncMock()
    
    # helper for creating a tool use object with some token usage
    def make_response(tool_name: str, input_dict: dict, in_tok: int, out_tok: int):
        tu = MagicMock()
        tu.type = "tool_use"
        tu.id = f"mock_{tool_name}"
        tu.name = tool_name
        tu.input = input_dict
        r = MagicMock()
        r.content = [tu]
        r.stop_reason = "tool_use"
        r.usage.input_tokens = in_tok
        r.usage.output_tokens = out_tok
        return r
        
    def make_text_response(text: str, in_tok: int, out_tok: int):
        t = MagicMock()
        t.type = "text"
        t.text = text
        r = MagicMock()
        r.content = [t]
        r.stop_reason = "end_turn"
        r.usage.input_tokens = in_tok
        r.usage.output_tokens = out_tok
        return r

    # Determine input based on fixture type
    if fixture_name == "healthy":
        r1 = make_response("github_repo_metadata", {"owner": REPO_HEALTHY["owner"], "repo": REPO_HEALTHY["repo"]}, 500, 100)
        r2 = make_response("github_list_files", {"owner": REPO_HEALTHY["owner"], "repo": REPO_HEALTHY["repo"], "recursive": True}, 600, 100)
        r3 = make_response("github_read_file", {"owner": REPO_HEALTHY["owner"], "repo": REPO_HEALTHY["repo"], "path": "package.json"}, 1600, 100)
        r4 = make_response("dependency_analyzer", {"manifest_content": '{"dependencies": {"lodash": "4.17.10"}}', "manifest_type": "npm"}, 2600, 100)
        r5 = make_text_response(
            "### Repository Health Report: langchain-ai/langchain\n\n"
            "**Overview**\n"
            "- Description: Build context-aware reasoning applications\n"
            "- Primary Language: Python\n"
            "- License: MIT License\n\n"
            "**Popularity & Activity Metrics**\n"
            "- Stars: 102,000 | Forks: 15800\n\n"
            "**Security & Dependencies**\n"
            "- Analyzed package.json. Found 1 high and 3 medium vulnerabilities.\n\n"
            "**Initial Health Signals**\n"
            "- [GOOD] Activity: high\n"
            "- [GOOD] License: present\n"
            "- [WARN] Security: Has vulnerabilities\n\n"
            "**Composite Score**: A — Excellent health\n\n"
            "**Recommendations**\n"
            "- Keep merging PRs",
            3000, 300
        )
        mock_client.messages.create.side_effect = [r1, r2, r3, r4, r5]

    elif fixture_name == "stale":
        r1 = make_response("github_repo_metadata", {"owner": REPO_STALE["owner"], "repo": REPO_STALE["repo"]}, 500, 100)
        r2 = make_response("github_list_files", {"owner": REPO_STALE["owner"], "repo": REPO_STALE["repo"], "recursive": True}, 600, 100)
        # Skip read file and dependency analyzer (e.g. no manifest found)
        r3 = make_text_response(
            "### Repository Health Report: facebookarchive/react-native-fbsdk\n\n"
            "**Overview**\n"
            "- Description: Archived react native SDK\n"
            "- Primary Language: JavaScript\n"
            "- License: MIT\n\n"
            "**Popularity & Activity Metrics**\n"
            "- Stars: 5,000 | Forks: 1000\n\n"
            "**Security & Dependencies**\n"
            "- No dependency manifest found to analyze.\n\n"
            "**Initial Health Signals**\n"
            "- [CONCERN] Activity: Repo is archived and stale\n\n"
            "**Composite Score**: F — Archived\n\n"
            "**Recommendations**\n"
            "- Do not use this repo",
            1000, 300
        )
        mock_client.messages.create.side_effect = [r1, r2, r3]

    elif fixture_name == "error":
        r1 = make_response("github_repo_metadata", {"owner": REPO_NONEXISTENT["owner"], "repo": REPO_NONEXISTENT["repo"]}, 500, 100)
        r2 = make_text_response(
            "I could not analyze the repository because it does not exist or is inaccessible. "
            "The github_repo_metadata tool returned a 404 Not Found error. "
            "Please check the URL and try again.",
            600, 100
        )
        mock_client.messages.create.side_effect = [r1, r2]

    else:  # minimal
        r1 = make_response("github_repo_metadata", {"owner": REPO_MINIMAL["owner"], "repo": REPO_MINIMAL["repo"]}, 500, 100)
        r2 = make_response("github_list_files", {"owner": REPO_MINIMAL["owner"], "repo": REPO_MINIMAL["repo"], "recursive": True}, 600, 100)
        r3 = make_response("github_read_file", {"owner": REPO_MINIMAL["owner"], "repo": REPO_MINIMAL["repo"], "path": "requirements.txt"}, 800, 100)
        r4 = make_response("dependency_analyzer", {"manifest_content": "requests==2.20", "manifest_type": "pip"}, 1000, 100)
        r5 = make_text_response(
            "### Repository Health Report: user/repo\n\n"
            "**Overview**\n"
            "- Description: None\n"
            "- Primary Language: Not specified\n"
            "- License: None specified\n\n"
            "**Popularity & Activity Metrics**\n"
            "- Stars: 100 | Forks: 10\n\n"
            "**Security & Dependencies**\n"
            "- Analyzed requirements.txt. Found 1 critical vulnerability.\n\n"
            "**Initial Health Signals**\n"
            "- [WARN] Warning\n\n"
            "**Composite Score**: C — Needs work\n\n"
            "**Recommendations**\n"
            "- Add a license",
            1500, 300
        )
        mock_client.messages.create.side_effect = [r1, r2, r3, r4, r5]
    
    return mock_client


@pytest_asyncio.fixture
async def agent_healthy() -> DevAgent:
    """Agent with mocked GitHub API returning a healthy repo."""
    registry = make_mock_registry(
        mock_metadata_response=MOCK_HEALTHY_RESPONSE,
        mock_tree_response={"tree": [{"path": "package.json", "mode": "100644", "type": "blob", "size": 100, "sha": "abc"}], "truncated": False},
        mock_file_responses={"package.json": {"path": "package.json", "content": "{\"dependencies\": {\"lodash\": \"4.17.10\"}}", "size": 100, "encoding": "utf-8"}},
        mock_dep_responses={"npm": {"total_dependencies_found": 15, "critical_vulnerabilities": 0, "high_vulnerabilities": 1, "medium_vulnerabilities": 3, "low_vulnerabilities": 1, "notes": "Found vulnerabilities."}}
    )
    agent = DevAgent(registry=registry, max_tool_calls=10)
    agent.client = mock_anthropic_client("healthy")
    return agent


@pytest_asyncio.fixture
async def agent_stale() -> DevAgent:
    """Agent with mocked GitHub API returning a stale/archived repo."""
    registry = make_mock_registry(
        mock_metadata_response=MOCK_STALE_RESPONSE,
        mock_tree_response={"tree": [{"path": "README.md", "mode": "100644", "type": "blob", "size": 100, "sha": "abc"}], "truncated": False},
        mock_file_responses={"README.md": {"path": "README.md", "content": "Archived repo", "size": 100, "encoding": "utf-8"}},
        mock_dep_responses={}
    )
    agent = DevAgent(registry=registry, max_tool_calls=10)
    agent.client = mock_anthropic_client("stale")
    return agent


@pytest_asyncio.fixture
async def agent_minimal() -> DevAgent:
    """Agent with mocked GitHub API returning a minimal repo."""
    registry = make_mock_registry(
        mock_metadata_response=MOCK_MINIMAL_RESPONSE,
        mock_tree_response={"tree": [{"path": "requirements.txt", "mode": "100644", "type": "blob", "size": 100, "sha": "abc"}], "truncated": False},
        mock_file_responses={"requirements.txt": {"path": "requirements.txt", "content": "requests==2.20", "size": 100, "encoding": "utf-8"}},
        mock_dep_responses={"pip": {"total_dependencies_found": 15, "critical_vulnerabilities": 1, "high_vulnerabilities": 2, "medium_vulnerabilities": 0, "low_vulnerabilities": 1, "notes": "Vulnerable."}}
    )
    agent = DevAgent(registry=registry, max_tool_calls=10)
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
