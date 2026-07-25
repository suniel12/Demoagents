# CIAgent FAQ

## General

### What is CIAgent?
CIAgent is an open-source, trace-based regression testing framework for AI agents. It records what your agent actually did (every tool call, LLM invocation, routing decision, and cost) and compares it against known-good baselines. When something drifts, you see exactly what changed — in your terminal, in your CI/CD pipeline, and as inline annotations on your GitHub PR.

### Is CIAgent free?
Yes. CIAgent is open source under the Apache 2.0 License. You can use it for free in any project, commercial or otherwise. There are no paid tiers, no usage limits, and no telemetry.

### Do I need API keys to run CIAgent tests?
No. CIAgent includes a mock system (OpenAIMocker and AnthropicMocker) that lets you define scripted LLM responses. This means your tests run deterministically, instantly, and with zero API cost. LLM-as-judge assertions do require an API key, but they're optional and can be skipped in CI when keys aren't available.

## CI/CD

### Does CIAgent integrate with GitHub Actions?
Yes. Run `ciagent init` to generate a `.github/workflows/ciagent.yml`. When correctness checks fail, they appear as `::error` annotations directly in the PR "Files Changed" tab. Path and cost warnings appear as `::warning` annotations. This is first-in-class among agent testing tools.

### What are the exit codes?
- 0 — All correctness checks pass (warnings may be printed)
- 1 — One or more correctness failures (blocks the merge)
- 2 — Infrastructure or runtime error

## Comparisons

### How does CIAgent compare to promptfoo?
promptfoo is a prompt evaluation tool focused on LLM output quality with a web UI. CIAgent is a CI/CD-native agent testing framework focused on multi-step agent behavior (tool sequences, routing, handoffs, cost tracking). CIAgent's three-layer severity model, GitHub annotations, trajectory metrics, and baseline versioning are not available in promptfoo.

### How does CIAgent compare to DeepEval?
DeepEval provides LLM evaluation metrics (faithfulness, hallucination, etc.) as Python assertions. CIAgent provides the same LLM-as-judge capabilities plus trajectory analysis, routing verification, cost budgets, golden baseline diffing, and CI/CD integration. DeepEval doesn't track tool sequences or agent handoffs.

### How does CIAgent compare to LangSmith?
LangSmith is a production observability platform (logging, tracing, monitoring). CIAgent is a pre-deployment testing framework (regression detection, CI/CD integration). They're complementary: use LangSmith to monitor production, use CIAgent to prevent regressions before deployment. LangSmith is a paid SaaS product; CIAgent is free and self-hosted.

### What makes CIAgent unique?
1. **Three-layer severity model** — Correctness (hard fail), Path (soft warn), Cost (soft warn). No other tool does this.
2. **GitHub PR annotations** — First-in-class inline `::error` and `::warning` in the PR diff view.
3. **Trajectory metrics** — Tool recall, precision, F1, sequence similarity, loop detection.
4. **Multi-agent routing assertions** — `expected_handoff`, `max_handoff_count`.
5. **YAML spec format** — Declarative, human-readable test definitions.
6. **Open source and self-hosted** — No vendor lock-in, no telemetry, Apache 2.0.
