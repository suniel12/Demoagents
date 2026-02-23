"""Tool Call Tests — Assert the agent calls the right tools correctly.

These are the CORE AgentCI tests. They validate:
1. Which tools were called (tool selection)
2. What inputs were passed (input correctness)
3. How many times tools were called (efficiency)
4. The order of tool calls (sequencing — more relevant in Phase 1+)

Design Notes for AgentCI API:
─────────────────────────────
These tests define what the ideal AgentCI assertion API should look like.
As you write them, pay attention to:
- Which assertions feel natural vs. clunky
- Which assertions you wish existed but don't
- Where pytest's built-in asserts are sufficient vs. need custom matchers

Every awkward assertion here is a feature opportunity for AgentCI.
"""

import pytest

from devagent.agent.core import DevAgent, Trace
from tests.fixtures import REPO_HEALTHY, REPO_STALE, REPO_NONEXISTENT


# ──────────────────────────────────────────────
# Tool Selection Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestToolSelection:
    """Verify the agent calls the correct tool(s)."""

    async def test_calls_github_repo_metadata_for_valid_repo(self, agent_healthy):
        """The agent MUST call github_repo_metadata for any valid repo URL."""
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.success is True
        assert "github_repo_metadata" in trace.tool_names_called, (
            f"Expected 'github_repo_metadata' in tool calls, "
            f"got: {trace.tool_names_called}"
        )

    async def test_calls_multiple_tools_in_sequence_phase_1(self, agent_healthy):
        """In Phase 1, the agent should call multiple tools sequentially.
        
        A healthy repo with a manifest should trigger exactly 4 tool calls:
        metadata -> list_files -> read_file -> dependency_analyzer
        """
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.tool_call_count == 4, (
            f"Phase 1 healthy agent should make exactly 4 tool calls, "
            f"made {trace.tool_call_count}: {trace.tool_names_called}"
        )
        
        # Verify the exact sequence
        names = trace.tool_names_called
        assert names == [
            "github_repo_metadata",
            "github_list_files",
            "github_read_file",
            "dependency_analyzer"
        ], f"Incorrect tool call sequence: {names}"

    async def test_no_hallucinated_tool_calls(self, agent_healthy):
        """The agent must ONLY call tools that exist in the registry."""
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        valid_tools = {
            "github_repo_metadata",
            "github_list_files",
            "github_read_file",
            "dependency_analyzer"
        }  # Phase 1 has 4 valid tools

        for tool_name in trace.tool_names_called:
            assert tool_name in valid_tools, (
                f"Agent called non-existent tool '{tool_name}'. "
                f"Available tools: {valid_tools}"
            )

    async def test_stale_repo_still_calls_metadata_tool(self, agent_stale):
        """Even for archived/stale repos, the agent should still fetch metadata.
        It should fetch metadata and list files, but might stop there.
        """
        trace = await agent_stale.analyze(REPO_STALE["url"])

        assert trace.tool_call_count >= 1
        assert "github_repo_metadata" in trace.tool_names_called
        assert "github_list_files" in trace.tool_names_called


# ──────────────────────────────────────────────
# Tool Input Correctness Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestToolInputs:
    """Verify the agent passes correct inputs to tools."""

    async def test_correct_owner_and_repo_parsed_from_url(self, agent_healthy):
        """The agent must correctly parse the URL into owner/repo fields.

        This tests a critical LLM behavior: can it extract structured
        data from a URL? Failures here mean the system prompt or tool
        description needs improvement.
        """
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.tool_call_count >= 1
        tool_call = trace.tool_calls[0]

        assert tool_call.tool_input["owner"] == REPO_HEALTHY["owner"], (
            f"Expected owner '{REPO_HEALTHY['owner']}', "
            f"got '{tool_call.tool_input.get('owner')}'"
        )
        assert tool_call.tool_input["repo"] == REPO_HEALTHY["repo"], (
            f"Expected repo '{REPO_HEALTHY['repo']}', "
            f"got '{tool_call.tool_input.get('repo')}'"
        )

    async def test_correct_parsing_for_shorthand_url(self, agent_healthy):
        """Test that the agent handles owner/repo shorthand in the prompt."""
        trace = await agent_healthy.analyze("langchain-ai/langchain")

        assert trace.tool_call_count >= 1
        tool_call = trace.tool_calls[0]
        assert tool_call.tool_input["owner"] == "langchain-ai"
        assert tool_call.tool_input["repo"] == "langchain"

    async def test_tool_inputs_are_strings_not_urls(self, agent_healthy):
        """The tool expects owner and repo as separate strings,
        NOT the full URL. This is a common LLM mistake.
        """
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        tool_call = trace.tool_calls[0]
        owner = tool_call.tool_input.get("owner", "")
        repo = tool_call.tool_input.get("repo", "")

        assert "github.com" not in owner, (
            f"Owner should be 'langchain-ai', not a full URL: '{owner}'"
        )
        assert "github.com" not in repo, (
            f"Repo should be 'langchain', not a full URL: '{repo}'"
        )
        assert "/" not in owner, f"Owner should not contain '/': '{owner}'"


# ──────────────────────────────────────────────
# Tool Call Success Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestToolCallSuccess:
    """Verify that tool calls execute successfully."""

    async def test_all_tool_calls_succeed_for_healthy_repo(self, agent_healthy):
        """For a known-good repo, every tool call should succeed."""
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        for tc in trace.tool_calls:
            assert tc.success is True, (
                f"Tool '{tc.tool_name}' failed with error: {tc.error}"
            )

    async def test_tool_call_produces_output(self, agent_healthy):
        """Every successful tool call should return non-null output."""
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        for tc in trace.tool_calls:
            if tc.success:
                assert tc.tool_output is not None, (
                    f"Tool '{tc.tool_name}' succeeded but returned None"
                )
