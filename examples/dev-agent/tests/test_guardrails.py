"""Guardrail Tests — Enforce cost, token, and performance limits.

These tests are the "circuit breakers" of your agent. They catch:
- Token budget overruns (LLM being verbose or making too many calls)
- Cost overruns (critical for agents that run in production loops)
- Performance degradation (agent getting slower over time)
- Runaway tool calls (agent stuck in a loop)

AgentCI Design Insight:
───────────────────────
Guardrails are the #1 feature request from developers building agents.
"My agent worked in dev but cost $50 in production because it made
200 API calls in a loop." These tests prevent that.

The thresholds here are PHASE 0 SPECIFIC. As you add more tools in
later phases, update the thresholds — and the fact that you HAVE to
update them is itself a useful regression signal.
"""

import pytest

from devagent.agent.core import Trace
from tests.fixtures import REPO_HEALTHY, REPO_STALE, REPO_MINIMAL


# ──────────────────────────────────────────────
# Token Budget Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestTokenBudget:
    """Ensure the agent stays within token limits."""

    # Phase 1 thresholds — up to 4 tool calls + report generation
    MAX_INPUT_TOKENS = 12000
    MAX_OUTPUT_TOKENS = 4000
    MAX_TOTAL_TOKENS = 16000

    async def test_input_tokens_within_budget(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.input_tokens <= self.MAX_INPUT_TOKENS, (
            f"Input tokens ({trace.input_tokens}) exceeded budget "
            f"({self.MAX_INPUT_TOKENS}). Check system prompt size or "
            f"tool result verbosity."
        )

    async def test_output_tokens_within_budget(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.output_tokens <= self.MAX_OUTPUT_TOKENS, (
            f"Output tokens ({trace.output_tokens}) exceeded budget "
            f"({self.MAX_OUTPUT_TOKENS}). The LLM may be generating "
            f"overly verbose reports."
        )

    async def test_total_tokens_within_budget(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.total_tokens <= self.MAX_TOTAL_TOKENS, (
            f"Total tokens ({trace.total_tokens}) exceeded budget "
            f"({self.MAX_TOTAL_TOKENS})."
        )

    async def test_stale_repo_similar_token_usage(self, agent_stale):
        """Token usage shouldn't spike dramatically for different repo types."""
        trace = await agent_stale.analyze(REPO_STALE["url"])

        assert trace.total_tokens <= self.MAX_TOTAL_TOKENS, (
            f"Stale repo analysis used {trace.total_tokens} tokens — "
            f"shouldn't be higher than healthy repo budget."
        )


# ──────────────────────────────────────────────
# Cost Guardrail Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestCostGuardrails:
    """Ensure the agent stays within cost limits."""

    # Phase 1: Multiple analysis calls increase total cost
    MAX_COST_USD = 0.05

    async def test_single_analysis_cost(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.estimated_cost_usd <= self.MAX_COST_USD, (
            f"Analysis cost ${trace.estimated_cost_usd:.6f} exceeded "
            f"limit ${self.MAX_COST_USD}. At this rate, 1000 analyses "
            f"would cost ${trace.estimated_cost_usd * 1000:.2f}."
        )

    async def test_cost_consistency_across_repo_types(self, agent_healthy, agent_stale, agent_minimal):
        """Cost should be roughly similar regardless of repo type in Phase 0.
        Large variance would suggest the agent is doing unnecessary work for some repos.
        """
        from tests.fixtures import REPO_MINIMAL

        trace_healthy = await agent_healthy.analyze(REPO_HEALTHY["url"])
        trace_stale = await agent_stale.analyze(REPO_STALE["url"])
        trace_minimal = await agent_minimal.analyze(REPO_MINIMAL["url"])

        costs = [
            trace_healthy.estimated_cost_usd,
            trace_stale.estimated_cost_usd,
            trace_minimal.estimated_cost_usd,
        ]

        max_cost = max(costs)
        min_cost = min(costs)

        # Costs should be within 3x of each other for Phase 0
        if min_cost > 0:
            ratio = max_cost / min_cost
            assert ratio <= 3.0, (
                f"Cost variance too high across repo types. "
                f"Costs: healthy=${costs[0]:.6f}, stale=${costs[1]:.6f}, "
                f"minimal=${costs[2]:.6f}. Ratio: {ratio:.1f}x"
            )


# ──────────────────────────────────────────────
# Tool Call Limit Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestToolCallLimits:
    """Prevent runaway tool call loops."""

    MAX_TOOL_CALLS = 10  # Phase 1 can need up to 4-6 calls

    async def test_tool_calls_within_limit(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.tool_call_count <= self.MAX_TOOL_CALLS, (
            f"Agent made {trace.tool_call_count} tool calls "
            f"(limit: {self.MAX_TOOL_CALLS}). "
            f"Tools called: {trace.tool_names_called}. "
            f"Possible infinite loop or unnecessary retries."
        )

    async def test_no_duplicate_tool_calls(self, agent_healthy):
        """In Phase 0, the agent shouldn't call the same tool twice
        with the same inputs (that's wasted API calls).
        """
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        seen = set()
        for tc in trace.tool_calls:
            key = (tc.tool_name, str(sorted(tc.tool_input.items())))
            assert key not in seen, (
                f"Duplicate tool call: {tc.tool_name} with {tc.tool_input}"
            )
            seen.add(key)


# ──────────────────────────────────────────────
# Performance Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestPerformance:
    """Ensure the agent runs within acceptable time limits."""

    # Phase 0 with mocks should be fast (LLM latency only)
    MAX_DURATION_MS = 30_000  # 30 seconds (generous, includes LLM latency)

    async def test_analysis_completes_in_time(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert trace.total_duration_ms <= self.MAX_DURATION_MS, (
            f"Analysis took {trace.total_duration_ms:.0f}ms "
            f"(limit: {self.MAX_DURATION_MS}ms). "
            f"Check for unnecessary retries or slow tool execution."
        )

    async def test_individual_tool_calls_are_fast(self, agent_healthy):
        """Each tool call should complete quickly (mocked, so <100ms)."""
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        for tc in trace.tool_calls:
            assert tc.duration_ms < 5000, (
                f"Tool '{tc.tool_name}' took {tc.duration_ms:.0f}ms. "
                f"With mocked tools this should be near-instant."
            )
