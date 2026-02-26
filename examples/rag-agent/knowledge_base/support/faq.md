# AgentCI Frequently Asked Questions

## General

### What is AgentCI?
AgentCI is an open-source, trace-based regression testing framework for AI agents. It records what your agent actually did (every tool call, LLM invocation, routing decision, and cost) and compares it against known-good baselines. When something drifts, you see exactly what changed — in your terminal, in your CI/CD pipeline, and as inline annotations on your GitHub PR.

### Is AgentCI free?
Yes. AgentCI is open source under the Apache 2.0 License. You can use it for free in any project, commercial or otherwise. There are no paid tiers, no usage limits, and no telemetry.

### What programming languages does AgentCI support?
AgentCI is a Python library. It supports Python 3.10 and later. Your agents must be Python-based to use AgentCI's trace capture and assertion features.

### Do I need API keys to run AgentCI tests?
No. AgentCI includes a mock system (OpenAIMocker and AnthropicMocker) that lets you define scripted LLM responses. This means your tests run deterministically, instantly, and with zero API cost. LLM-as-judge assertions do require an API key, but they're optional and can be skipped in CI when keys aren't available.

### How do I install AgentCI?
Install with pip: `pip install agentci`. Then run `agentci init` to scaffold your project.

## Framework Support

### Which agent frameworks does AgentCI support?
AgentCI works with:
- **OpenAI Agents SDK** — Native AgentCITraceProcessor (2 lines to enable)
- **LangGraph / LangChain** — Captures conditional edges and tool calls via state attachment
- **Anthropic (raw)** — AnthropicMocker for zero-cost replay; native tool_use capture
- **Any Python agent** — Manual Trace/Span construction for custom frameworks

### Can I use AgentCI with CrewAI or AutoGen?
Not yet natively, but it's on the v3.0 roadmap. You can still use AgentCI with any Python agent by manually constructing Trace objects from your agent's execution data.

### Does AgentCI work with LangSmith or LangFuse?
AgentCI is a testing framework, not an observability platform. It complements tools like LangSmith and LangFuse by providing CI/CD-native regression testing. You can use LangSmith for production tracing and AgentCI for pre-deployment testing. OpenTelemetry export is planned for v3.0.

## Testing

### What's the difference between AgentCI's three layers?
- **Correctness (Layer 1):** Hard fail — blocks CI. Checks if the answer is right (string matching, regex, LLM judge).
- **Path (Layer 2):** Soft warning — doesn't block CI. Checks if the agent took the right path (tool usage, routing, loops).
- **Cost (Layer 3):** Soft warning — doesn't block CI. Checks if the agent stayed within budget (tokens, cost, latency).

The only exception: `forbidden_tools` in the Path layer escalates to a hard fail.

### What is the agentci_spec.yaml?
It's a declarative YAML file that defines your agent's expected behavior — what queries to test, what the correct answers look like, which tools should be called, and what cost limits to enforce. Think of it as a test plan that's human-readable and machine-enforceable.

### What is a golden baseline?
A golden baseline is a saved trace from a known-good agent run. When you make changes, AgentCI diffs your new trace against the baseline to detect regressions in correctness, path, or cost.

### How does the LLM-as-a-judge work?
AgentCI sends your agent's output to an LLM (typically Claude Sonnet or GPT-4o-mini) with a structured rubric. The judge returns a JSON object with `score`, `label` (pass/fail/borderline), and `rationale`. Safeguards include: temperature always 0, structured JSON output required, ensemble voting across 3 models for high-stakes checks, and the `--sample-ensemble` flag for CI cost control.

### What are match modes?
Match modes control how AgentCI compares tool sequences:
- **strict** — Same tools, same order
- **unordered** — Same tools, any order
- **subset** (default) — All expected tools must appear, extras allowed
- **superset** — All used tools must be in the expected set

## CI/CD

### Does AgentCI integrate with GitHub Actions?
Yes. Run `agentci init` to generate a `.github/workflows/agentci.yml`. When correctness checks fail, they appear as `::error` annotations directly in the PR "Files Changed" tab. Path and cost warnings appear as `::warning` annotations. This is first-in-class among agent testing tools.

### What are the exit codes?
- 0 — All correctness checks pass (warnings may be printed)
- 1 — One or more correctness failures (blocks the merge)
- 2 — Infrastructure or runtime error

### Can I run AgentCI locally?
Yes. Use `agentci test --config agentci_spec.yaml --format console` for local development. The console format produces colorful tables showing each layer's status.

## Comparisons

### How does AgentCI compare to promptfoo?
promptfoo is a prompt evaluation tool focused on LLM output quality with a web UI. AgentCI is a CI/CD-native agent testing framework focused on multi-step agent behavior (tool sequences, routing, handoffs, cost tracking). AgentCI's three-layer severity model, GitHub annotations, trajectory metrics, and baseline versioning are not available in promptfoo.

### How does AgentCI compare to DeepEval?
DeepEval provides LLM evaluation metrics (faithfulness, hallucination, etc.) as Python assertions. AgentCI provides the same LLM-as-judge capabilities plus trajectory analysis, routing verification, cost budgets, golden baseline diffing, and CI/CD integration. DeepEval doesn't track tool sequences or agent handoffs.

### How does AgentCI compare to LangSmith?
LangSmith is a production observability platform (logging, tracing, monitoring). AgentCI is a pre-deployment testing framework (regression detection, CI/CD integration). They're complementary: use LangSmith to monitor production, use AgentCI to prevent regressions before deployment. LangSmith is a paid SaaS product; AgentCI is free and self-hosted.

### How does AgentCI compare to Braintrust?
Braintrust offers an evaluation and experimentation platform with a web UI and dataset management. AgentCI is CLI-first and CI/CD-native. AgentCI's advantages: open source, self-hosted, three-layer severity, GitHub annotations, trajectory analysis. Braintrust's advantages: web UI, hosted platform, dataset management.

### What makes AgentCI unique?
1. **Three-layer severity model** — Correctness (hard fail), Path (soft warn), Cost (soft warn). No other tool does this.
2. **GitHub PR annotations** — First-in-class inline `::error` and `::warning` in the PR diff view.
3. **Trajectory metrics** — Tool recall, precision, F1, sequence similarity, loop detection.
4. **Multi-agent routing assertions** — `expected_handoff`, `max_handoff_count`.
5. **YAML spec format** — Declarative, human-readable test definitions.
6. **Open source and self-hosted** — No vendor lock-in, no telemetry, Apache 2.0.
