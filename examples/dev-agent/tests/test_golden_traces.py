"""Golden Trace Tests — Compare live traces against recorded baselines.

Golden trace testing is AgentCI's core differentiator. The idea:
1. Record a "known good" trace (tool calls, inputs, outputs, costs)
2. On every future run, diff the live trace against the golden one
3. Flag regressions: new tool calls, changed inputs, cost spikes

This catches the subtle regressions that no other approach catches:
- A model update changes tool-calling behavior
- A prompt edit causes the agent to skip a tool
- A new tool version returns different data shapes

AgentCI Design Questions This Raises:
──────────────────────────────────────
- How strict should the diff be? Exact match? Fuzzy match?
- Should token counts be exact or within a tolerance?
- How do you handle intentional changes (new feature) vs regressions?
- Should golden traces be versioned alongside code?
"""

import json
import pytest
from pathlib import Path

from devagent.agent.core import Trace
from tests.fixtures import REPO_HEALTHY, load_golden_trace


# ──────────────────────────────────────────────
# Golden Trace Comparison Helpers
# ──────────────────────────────────────────────


def assert_trace_matches_golden(
    live_trace: Trace,
    golden: dict,
    token_tolerance: float = 0.5,
    cost_tolerance: float = 0.5,
) -> None:
    """Compare a live trace against a golden trace using AgentCI diff engine."""
    from ciagent.models import Trace as AgentCITrace, Span, ToolCall as AgentCIToolCall
    from ciagent.diff_engine import diff

    # 1. Convert DevAgent Trace to AgentCI Trace
    agentci_live = AgentCITrace(
        spans=[
            Span(
                name="devagent",
                tool_calls=[
                    AgentCIToolCall(
                        tool_name=tc.tool_name,
                        arguments=tc.tool_input,
                        result=tc.tool_output,
                        error=tc.error,
                        duration_ms=tc.duration_ms,
                    )
                    for tc in live_trace.tool_calls
                ],
                total_tokens_in=live_trace.input_tokens,
                total_tokens_out=live_trace.output_tokens,
                total_cost_usd=live_trace.estimated_cost_usd,
                duration_ms=live_trace.total_duration_ms,
            )
        ]
    )
    agentci_live.compute_metrics()

    # 2. Convert Golden dict to AgentCI Trace
    agentci_golden = AgentCITrace(
        spans=[
            Span(
                name="devagent",
                tool_calls=[
                    AgentCIToolCall(
                        tool_name=tc["tool_name"],
                        arguments=tc["tool_input"],
                        result=None, # Baseline doesn't always have outputs
                        error=tc.get("error"),
                        duration_ms=tc.get("duration_ms", 0.0),
                    )
                    for tc in golden.get("tool_calls", [])
                ],
                total_cost_usd=golden.get("assertions", {}).get("estimated_cost_usd", {}).get("value", 0.0),
            )
        ]
    )
    agentci_golden.compute_metrics()

    # 3. Run Diff
    report = diff(agentci_golden, agentci_live)

    # 4. Assert no regressions
    if report.has_regression:
        raise AssertionError(f"Golden trace regression detected:\n{report.summary}")


# ──────────────────────────────────────────────
# Golden Trace Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestGoldenTraces:
    """Compare live agent runs against golden traces."""

    async def test_healthy_repo_matches_golden_trace(self, agent_healthy):
        """The most important regression test. If this fails after a
        code change, something fundamental about agent behavior changed.
        """
        golden = load_golden_trace("phase1_healthy_repo")
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert_trace_matches_golden(trace, golden)

    async def test_golden_trace_tool_inputs_exact_match(self, agent_healthy):
        """Tool inputs should match the golden trace exactly."""
        golden = load_golden_trace("phase1_healthy_repo")
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        
        # Test will now inherently check input matching via assert_trace_matches_golden
        assert_trace_matches_golden(trace, golden)
