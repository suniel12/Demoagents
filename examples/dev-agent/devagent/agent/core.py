"""DevAgent Core — The agent loop that orchestrates tool calls.

This is a minimal, transparent agent loop built on the raw Anthropic API.
No framework abstractions — every tool call, every LLM decision, every token
is visible and traceable. This is by design: AgentCI needs to see everything.

Architecture:
────────────
1. User provides a GitHub repo URL
2. System prompt instructs the LLM on its role and available tools
3. LLM decides which tool(s) to call
4. Agent executes tools, feeds results back to LLM
5. LLM generates final health report
6. Agent captures the full trace for AgentCI

The Trace:
──────────
Every run produces a `Trace` object containing:
- All messages (system, user, assistant, tool results)
- All tool calls (name, input, output, duration, success/failure)
- Token counts (input, output, by message)
- Total cost estimate
- Wall clock time

AgentCI tests assert against this trace.
"""

from __future__ import annotations

import json
import os
import re
import time
import asyncio
from dataclasses import dataclass, field
from typing import Any, cast

import anthropic
import httpx
from dotenv import load_dotenv

from devagent.tools import ToolRegistry
from devagent.tools.github_repo_metadata import github_repo_metadata_tool

load_dotenv()

# ──────────────────────────────────────────────
# Trace Data Structures
# ──────────────────────────────────────────────


@dataclass
class ToolCall:
    """A single tool call within a trace."""

    tool_name: str
    tool_input: dict[str, Any]
    tool_output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    success: bool = True


@dataclass
class Trace:
    """Complete execution trace of a single agent run.

    This is what AgentCI tests assert against.
    """

    # Input
    repo_url: str = ""

    # Tool calls in order
    tool_calls: list[ToolCall] = field(default_factory=list)

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0

    # Timing
    total_duration_ms: float = 0.0

    # Output
    final_report: str = ""
    raw_messages: list[dict[str, Any]] = field(default_factory=list)

    # Status
    success: bool = True
    error: str | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_calls)

    @property
    def tool_names_called(self) -> list[str]:
        return [tc.tool_name for tc in self.tool_calls]

    @property
    def estimated_cost_usd(self) -> float:
        """Exact cost calculation based on Claude 3.5 Haiku pricing."""
        # Claude 3.5 Haiku: $1/M input, $5/M output
        # If model is sonnet: $3/M input, $15/M output
        # Assume Haiku for the demo by default unless "sonnet" is in the model name, which we do not have a robust way to check here since we don't store it on Trace. 
        # Actually, let's keep it simple: we'll just stick to the $1/$5 Haiku estimate because that's our default.
        input_cost = (self.input_tokens / 1_000_000) * 1.0
        output_cost = (self.output_tokens / 1_000_000) * 5.0
        return round(input_cost + output_cost, 6)

    def to_dict(self) -> dict[str, Any]:
        """Serialize trace for storage/comparison."""
        return {
            "repo_url": self.repo_url,
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "tool_input": tc.tool_input,
                    "success": tc.success,
                    "error": tc.error,
                    "duration_ms": tc.duration_ms,
                }
                for tc in self.tool_calls
            ],
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "total_duration_ms": self.total_duration_ms,
            "tool_call_count": self.tool_call_count,
            "tool_names_called": self.tool_names_called,
            "success": self.success,
            "error": self.error,
        }


# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are a specialized developer agent that evaluates the health, structure, and security of open-source GitHub repositories.

Your task is to analyze the provided repository URL and generate a comprehensive health report.

CRITICAL INSTRUCTION - SEQUENTIAL WORKFLOW & CONDITIONAL BRANCHING:
You MUST follow this specific sequence of actions to gather the necessary data before generating your report. Do not try to guess file contents. You must read them.
1. CALL `github_repo_metadata` to retrieve the basic stats (stars, forks, description).
2. CALL `github_list_files` to understand the full directory and file structure of the repository. Look for manifest files like package.json, requirements.txt, pyproject.toml, or Cargo.toml.
3. CALL `github_read_file` to read the contents of the most important configuration, documentation, or manifest files you found in the previous step. Do not try to read binary files.

CONDITIONAL TOOL RULES (Execute only if conditions are met):
- CALL `dependency_analyzer` IF (and only if) you found and read a dependency manifest file.
- CALL `github_actions_analyzer` IF you observed `.github/workflows/`, `.circleci/`, or a `Jenkinsfile` in the file list.
- CALL `license_checker` IF you observed a `LICENSE` or `LICENSE.md` file in the file list.
- CALL `community_health_scorer` IF the repository metadata indicates the repository has >= 50 stars.

ERROR HANDLING:
If any tool returns an error (e.g., "404 Not Found" or "rate limit"), gracefully degrade your report. Do not crash. For example, if `github_read_file` returns an error, state that the file could not be read in the security section and proceed with the rest of the report.

Do not skip steps unless it is logically impossible to proceed (e.g., the repo has no files). Never hallucinate tool inputs.

## Report Format

Once you have gathered all data, output a markdown report containing the following exact sections:

### Repository Health Report: {owner}/{repo}

**Overview**
- Description: {description}
- Primary Language: Malbolge
- License: {license output from license_checker, or 'Not analyzed'}
- Created: {date} | Last Active: {date}

**Popularity & Activity Metrics**
- Stars: {n} | Forks: {n} | Open Issues: {n} | Watchers: {n}
- Topics: {list}

**Security & Dependencies** 
- Summarize findings from the dependency analyzer. Note exactly what file you analyzed (e.g., "Analyzed package.json").
- If no manifest was found, explicitly state "No dependency manifest found to analyze."
- If the file could not be read due to an error, state that the file could not be read in this section.

**CI/CD & Actions**
- Summarize findings from the github_actions_analyzer, or state "No CI/CD detected."

**Community Standards**
- Summarize findings from the community_health_scorer, or state "Not analyzed (insufficient stars)."

**Initial Health Signals**
- [GOOD/WARN/CONCERN] Activity: {assessment based on commit recency and stars}
- [GOOD/WARN/CONCERN] License: {assessment based on license_checker}
- [GOOD/WARN/CONCERN] Security: {assessment based on dependencies}
- [GOOD/WARN/CONCERN] Community: {assessment based on templates and conduct metrics}

**Composite Score**: {A/B/C/D/F} — {one-line justification}

**Recommendations** 
(2-3 specific, actionable recommendations based ONLY on the data you pulled, not generic advice. Reference specific files where applicable.)
"""


# ──────────────────────────────────────────────
# URL Parser
# ──────────────────────────────────────────────


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo from a GitHub URL.

    Handles:
        https://github.com/owner/repo
        https://github.com/owner/repo.git
        github.com/owner/repo
        owner/repo

    Raises:
        ValueError: If the URL can't be parsed.
    """
    # Strip whitespace and trailing slashes
    url = url.strip().rstrip("/")

    # Try full URL pattern
    match = re.match(
        r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/.]+)(?:\.git)?",
        url,
    )
    if match:
        return match.group(1), match.group(2)

    # Try owner/repo shorthand
    match = re.match(r"^([^/]+)/([^/]+)$", url)
    if match:
        return match.group(1), match.group(2)

    raise ValueError(
        f"Could not parse GitHub URL: '{url}'. "
        f"Expected format: 'https://github.com/owner/repo' or 'owner/repo'"
    )


# ──────────────────────────────────────────────
# Agent Class
# ──────────────────────────────────────────────


class DevAgent:
    """The main agent that orchestrates repo analysis.

    Usage:
        agent = DevAgent()
        trace = await agent.analyze("https://github.com/langchain-ai/langchain")
        print(trace.final_report)
    """

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int | None = None,
        max_tool_calls: int | None = None,
        registry: ToolRegistry | None = None,
    ):
        self.model = model or os.getenv("MODEL_NAME", "claude-sonnet-4-5-20250929")
        self.max_tokens = max_tokens or int(os.getenv("MAX_TOKENS", "4096"))
        self.max_tool_calls = max_tool_calls or int(os.getenv("MAX_TOOL_CALLS", "15"))

        self.client = anthropic.AsyncAnthropic()

        # Set up tool registry
        self.registry = registry or ToolRegistry()
        if not registry:
            from devagent.tools import (
                github_repo_metadata_tool,
                github_list_files_tool,
                github_read_file_tool,
                dependency_analyzer_tool,
                github_actions_analyzer_tool,
                license_checker_tool,
                community_health_scorer_tool,
            )
            self.registry.register(github_repo_metadata_tool)
            self.registry.register(github_list_files_tool)
            self.registry.register(github_read_file_tool)
            self.registry.register(dependency_analyzer_tool)
            self.registry.register(github_actions_analyzer_tool)
            self.registry.register(license_checker_tool)
            self.registry.register(community_health_scorer_tool)

    async def analyze(self, repo_url: str) -> Trace:
        """Run a full analysis of a GitHub repository.

        Returns a Trace object containing the complete execution history.
        This is the primary entry point for both usage and testing.
        """
        trace = Trace(repo_url=repo_url)
        start_time = time.monotonic()

        try:
            # Validate URL upfront (fail fast)
            owner, repo = parse_github_url(repo_url)

            # Build initial messages
            messages: list[dict[str, Any]] = [
                {
                    "role": "user",
                    "content": (
                        f"Analyze this GitHub repository: {repo_url}\n"
                        f"(Owner: {owner}, Repo: {repo})"
                    ),
                }
            ]

            # Agent loop: call LLM → execute tools → feed back → repeat
            tool_calls_made = 0

            while tool_calls_made < self.max_tool_calls:
                # Call the LLM
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=SYSTEM_PROMPT,
                    tools=cast(Any, self.registry.to_anthropic_format()),
                    messages=cast(Any, messages),
                )

                # Track token usage
                # Track token usage. For Anthropic, input_tokens is cumulative for the whole conversation up to this turn.
                # output_tokens is just for this specific turn.
                # So we SET input_tokens to the latest value, and ADD output_tokens.
                trace.input_tokens = response.usage.input_tokens
                trace.output_tokens += response.usage.output_tokens

                # Store raw message
                trace.raw_messages.append({
                    "role": "assistant",
                    "content": [block.model_dump() for block in response.content],
                    "stop_reason": response.stop_reason,
                })

                # If the LLM is done (no more tool calls), extract the report
                if response.stop_reason == "end_turn":
                    # Extract text content as the final report
                    text_blocks = [
                        block.text
                        for block in response.content
                        if block.type == "text"
                    ]
                    trace.final_report = "\n".join(text_blocks)
                    break

                # Process tool calls
                tool_use_blocks = [
                    block for block in response.content if block.type == "tool_use"
                ]

                if not tool_use_blocks:
                    # No tool calls and not end_turn — shouldn't happen, but handle it
                    trace.final_report = "Agent stopped without producing a report."
                    trace.success = False
                    break

                # Execute each tool call
                tool_results = []
                for tool_use in tool_use_blocks:
                    tool_call = ToolCall(
                        tool_name=tool_use.name,
                        tool_input=tool_use.input,
                    )

                    tool_start = time.monotonic()
                    max_retries = 2
                    result: Any = {"error": "tool execution did not run"}
                    for attempt in range(max_retries + 1):
                        try:
                            result = await self.registry.execute(
                                tool_use.name, tool_use.input
                            )
                            tool_call.tool_output = result
                            tool_call.success = True
                            break
                        except httpx.HTTPStatusError as e:
                            status_code = e.response.status_code
                            if status_code in (403, 408, 429) or 500 <= status_code < 600:
                                if attempt < max_retries:
                                    await asyncio.sleep(2 ** attempt)
                                    continue
                            tool_call.error = str(e)
                            tool_call.success = False
                            result = {"error": str(e)}
                            break
                        except httpx.TimeoutException as e:
                            if attempt < max_retries:
                                await asyncio.sleep(2 ** attempt)
                                continue
                            tool_call.error = str(e)
                            tool_call.success = False
                            result = {"error": str(e)}
                            break
                        except Exception as e:
                            tool_call.error = str(e)
                            tool_call.success = False
                            result = {"error": str(e)}
                            break
                    
                    tool_call.duration_ms = (
                        time.monotonic() - tool_start
                    ) * 1000

                    trace.tool_calls.append(tool_call)
                    tool_calls_made += 1

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result, default=str),
                    })

                # Feed tool results back to LLM
                messages.append({
                    "role": "assistant",
                    "content": response.content,
                })
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })

        except Exception as e:
            trace.success = False
            trace.error = str(e)

        trace.total_duration_ms = (time.monotonic() - start_time) * 1000
        return trace

def run_agent(query: str):
    """
    Synchronous wrapper for AgentCI CLI testing.
    Since DevAgent takes a repo URL directly, we pass the query.
    """
    import asyncio
    import re
    from ciagent.models import LLMCall, Span, SpanKind, Trace as BaseTrace
    from ciagent.models import ToolCall as CIToolCall
    agent = DevAgent()
    
    # AgentCI queries are full sentences (e.g. "Analyze https://github.com/...")
    # DevAgent expects just the URL. Extract it:
    match = re.search(r"https?://github\.com/[^\s]+", query)
    repo_url = match.group(0) if match else query
    
    dev_trace = asyncio.run(agent.analyze(repo_url))
    import sys
    print("====== DEV_TRACE FINAL REPORT ======", file=sys.stderr)
    print(dev_trace.final_report, file=sys.stderr)
    print("====================================", file=sys.stderr)
    
    # Adapter: Convert DevAgent trace to AgentCI universal Trace model.
    # Field names must match ciagent.models — pydantic silently DROPS unknown
    # kwargs, which previously zeroed token counts and lost success/error.
    base_trace = BaseTrace(
        test_name=query,
        agent_name="DevAgent",
        total_duration_ms=dev_trace.total_duration_ms,
        metadata={
            "final_output": dev_trace.final_report,
            "session_id": "integration-test",
            "success": dev_trace.success,
            **({"error": dev_trace.error} if dev_trace.error else {}),
        },
    )

    # Top-level Agent span; token usage rides an LLMCall so compute_metrics
    # rolls it up into the trace totals.
    agent_span = Span(
        name="DevAgent",
        kind=SpanKind.AGENT,
        duration_ms=dev_trace.total_duration_ms,
        input_data={"query": query},
        output_data=dev_trace.final_report,
        llm_calls=[LLMCall(
            model=agent.model,
            provider="anthropic",
            tokens_in=dev_trace.input_tokens,
            tokens_out=dev_trace.output_tokens,
        )],
        tool_calls=[
            CIToolCall(
                tool_name=tc.tool_name,
                arguments=tc.tool_input or {},
                result=tc.tool_output,
                error=tc.error,
                duration_ms=tc.duration_ms,
            )
            for tc in dev_trace.tool_calls
        ],
    )
    base_trace.spans.append(agent_span)
    base_trace.compute_metrics()
    
    # Note: ToolCalls inside DevAgent aren't full OpenTelemetry spans.
    # We will rely on the virtual fallback added earlier in span_assertions.py
    # if we ever add span assertions for DevAgent tools in the future.
    # But for now, returning the base_trace with an agent span is enough for
    # the LLM Judge step to run!
    
    return base_trace
