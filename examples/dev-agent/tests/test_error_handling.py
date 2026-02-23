"""Error Handling Tests — Verify graceful failure behavior.

These tests are critical because error handling is where most
agents fail in production. The agent should:
- Never crash with an unhandled exception
- Produce a meaningful error message for the user
- Not hallucinate a report when the tool fails

AgentCI Design Insight:
───────────────────────
Error handling tests require MOCK INJECTION — the ability to make
specific tools fail on demand. This is one of the most requested
features in testing frameworks. How easy is it to say
"make this tool return a 404" in your test?
"""

import pytest

from devagent.agent.core import DevAgent, Trace
from tests.fixtures import REPO_NONEXISTENT


# ──────────────────────────────────────────────
# Nonexistent Repository Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestNonexistentRepo:
    """Test behavior when the repo doesn't exist (404)."""

    async def test_does_not_crash_on_missing_repo(self, agent_error):
        """The agent must NEVER raise an unhandled exception.
        Even if the tool fails, the agent should handle it gracefully.
        """
        trace = await agent_error.analyze(REPO_NONEXISTENT["url"])

        # The trace should complete (not throw)
        assert trace is not None
        assert isinstance(trace, Trace)

    async def test_reports_error_clearly(self, agent_error):
        """When a repo doesn't exist, the agent should communicate this
        clearly — either in the report or as a trace-level error.
        """
        trace = await agent_error.analyze(REPO_NONEXISTENT["url"])

        # Either the trace itself has an error, or the report mentions it
        has_error_signal = (
            trace.error is not None
            or trace.success is False
            or any(
                keyword in trace.final_report.lower()
                for keyword in ["not found", "doesn't exist", "does not exist",
                                "404", "error", "unable", "could not",
                                "inaccessible", "cannot"]
            )
        )
        assert has_error_signal, (
            "Agent didn't indicate that the repo doesn't exist. "
            f"Trace success: {trace.success}, error: {trace.error}, "
            f"report start: {trace.final_report[:200]}"
        )

    async def test_does_not_hallucinate_report_on_error(self, agent_error):
        """When the tool fails, the agent must NOT generate a fake
        health report with invented metrics. This is the most dangerous
        failure mode — a confident-sounding report based on nothing.
        """
        trace = await agent_error.analyze(REPO_NONEXISTENT["url"])

        if trace.final_report:
            report = trace.final_report.lower()

            # Should NOT contain a composite score for a nonexistent repo
            has_fake_score = any(
                pattern in report
                for pattern in [
                    "score: a", "score: b", "score: c",
                    "composite score", "health score",
                    "overall: a", "overall: b",
                ]
            )
            # If there IS a score, it should only be in the context of
            # explaining the failure
            if has_fake_score:
                assert any(
                    neg in report
                    for neg in ["not found", "error", "unable", "n/a", "cannot"]
                ), (
                    "Agent generated a health score for a nonexistent repo. "
                    "This is a hallucination."
                )


# ──────────────────────────────────────────────
# Invalid URL Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestInvalidUrl:
    """Test behavior with malformed inputs."""

    async def test_invalid_url_handled_gracefully(self, agent_healthy):
        """Completely invalid URLs should fail fast without calling any tools."""
        trace = await agent_healthy.analyze("not-a-url-at-all")

        assert trace.success is False
        assert trace.error is not None
        assert trace.tool_call_count == 0, (
            "Agent called tools despite receiving an invalid URL. "
            "URL validation should happen before tool calls."
        )

    async def test_empty_url_handled_gracefully(self, agent_healthy):
        trace = await agent_healthy.analyze("")

        assert trace.success is False
        assert trace.error is not None
        assert trace.tool_call_count == 0


# ──────────────────────────────────────────────
# Tool Failure Propagation Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestToolFailurePropagation:
    """Verify that tool failures are recorded in the trace correctly."""

    async def test_failed_tool_call_recorded_in_trace(self, agent_error):
        """When a tool fails, the trace should record the failure."""
        trace = await agent_error.analyze(REPO_NONEXISTENT["url"])

        if trace.tool_calls:
            # At least one tool call should have failed
            has_failure = any(not tc.success for tc in trace.tool_calls)
            # OR the agent might have handled it by catching the error
            # and reporting it without the tool call registering as failed
            # Both are acceptable behaviors
            if not has_failure:
                # If no tool call failed, the agent caught it internally
                # That's fine, but the report should mention the issue
                assert any(
                    keyword in trace.final_report.lower()
                    for keyword in ["error", "not found", "unable", "failed"]
                ), (
                    "No tool call failure recorded and report doesn't mention error"
                )

    async def test_failed_tool_has_error_message(self, agent_error):
        """Failed tool calls should have a descriptive error message."""
        trace = await agent_error.analyze(REPO_NONEXISTENT["url"])

        for tc in trace.tool_calls:
            if not tc.success:
                assert tc.error is not None, (
                    f"Tool '{tc.tool_name}' failed but has no error message"
                )
                assert len(tc.error) > 0, (
                    f"Tool '{tc.tool_name}' has empty error message"
                )
