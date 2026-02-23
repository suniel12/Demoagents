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
    token_tolerance: float = 0.5,  # Allow 50% variance in tokens
    cost_tolerance: float = 0.5,
) -> None:
    """Compare a live trace against a golden trace.

    This function is what AgentCI should provide as a built-in:
        agentci.assert_golden_match(trace, "phase0_healthy_repo")

    Building it manually teaches us what developers need.
    """
    assertions = golden.get("assertions", {})
    errors = []

    # Tool call count
    if "tool_call_count" in assertions:
        expected = assertions["tool_call_count"]["value"]
        actual = live_trace.tool_call_count
        op = assertions["tool_call_count"]["op"]

        if op == "eq" and actual != expected:
            errors.append(
                f"tool_call_count: expected {expected}, got {actual}"
            )
        elif op == "lte" and actual > expected:
            errors.append(
                f"tool_call_count: expected <= {expected}, got {actual}"
            )

    # Tool names called
    if "tool_names_called" in assertions:
        expected = assertions["tool_names_called"]["value"]
        actual = live_trace.tool_names_called

        if assertions["tool_names_called"]["op"] == "eq":
            if actual != expected:
                errors.append(
                    f"tool_names_called: expected {expected}, got {actual}"
                )

    # Success
    if "success" in assertions:
        expected = assertions["success"]["value"]
        if live_trace.success != expected:
            errors.append(
                f"success: expected {expected}, got {live_trace.success}"
            )

    # Token budget (with tolerance)
    if "total_tokens" in assertions:
        max_tokens = assertions["total_tokens"]["value"]
        if live_trace.total_tokens > max_tokens:
            errors.append(
                f"total_tokens: {live_trace.total_tokens} exceeded "
                f"limit {max_tokens}"
            )

    # Cost budget (with tolerance)
    if "estimated_cost_usd" in assertions:
        max_cost = assertions["estimated_cost_usd"]["value"]
        if live_trace.estimated_cost_usd > max_cost:
            errors.append(
                f"estimated_cost_usd: ${live_trace.estimated_cost_usd:.6f} "
                f"exceeded limit ${max_cost}"
            )

    # Tool call input matching
    golden_tool_calls = golden.get("tool_calls", [])
    for i, golden_tc in enumerate(golden_tool_calls):
        if i >= len(live_trace.tool_calls):
            errors.append(
                f"Missing tool call #{i}: expected {golden_tc['tool_name']}"
            )
            continue

        live_tc = live_trace.tool_calls[i]

        if live_tc.tool_name != golden_tc["tool_name"]:
            errors.append(
                f"Tool call #{i}: expected '{golden_tc['tool_name']}', "
                f"got '{live_tc.tool_name}'"
            )

        if live_tc.tool_input != golden_tc["tool_input"]:
            errors.append(
                f"Tool call #{i} input mismatch:\n"
                f"  expected: {golden_tc['tool_input']}\n"
                f"  got:      {live_tc.tool_input}"
            )

    if errors:
        raise AssertionError(
            f"Golden trace mismatch ({len(errors)} differences):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


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
        golden = load_golden_trace("phase0_healthy_repo")
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert_trace_matches_golden(trace, golden)

    async def test_golden_trace_tool_inputs_exact_match(self, agent_healthy):
        """Tool inputs should match the golden trace exactly.
        This catches: URL parsing changes, field name changes,
        prompt regressions that alter how the LLM structures inputs.
        """
        golden = load_golden_trace("phase0_healthy_repo")
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])

        assert len(trace.tool_calls) == len(golden["tool_calls"]), (
            f"Tool call count mismatch: "
            f"live={len(trace.tool_calls)}, "
            f"golden={len(golden['tool_calls'])}"
        )

        for i, (live_tc, golden_tc) in enumerate(
            zip(trace.tool_calls, golden["tool_calls"])
        ):
            assert live_tc.tool_input == golden_tc["tool_input"], (
                f"Tool call #{i} ({live_tc.tool_name}) input changed:\n"
                f"  Golden: {golden_tc['tool_input']}\n"
                f"  Live:   {live_tc.tool_input}\n"
                f"This may indicate a prompt regression."
            )
