# About AgentCI

AgentCI is an open-source, trace-based regression testing framework for AI agents. It was created by Sunil Pandey to solve a critical gap in the AI agent ecosystem: there was no way to know if your agent broke after a model swap, prompt change, or dependency update until users complained.

## The Problem AgentCI Solves

When you build AI agents, you make changes constantly — swapping models, editing prompts, updating tools, changing routing logic. Each change can silently break behavior:

- A model swap changes routing decisions (billing queries go to the wrong agent)
- A prompt edit silently skips a tool call (vector search stops firing)
- A new model costs 6x more per query (surprise invoice at month-end)
- A RAG retriever returns irrelevant docs (hallucinated answers in production)
- A guardrail stops firing after a refactor (PII leaks through)

Traditional unit tests don't catch these because agent behavior is probabilistic, not deterministic. You can't just assertEqual() on LLM output.

## How AgentCI Works

AgentCI records what your agent *actually did* — every tool call, LLM invocation, routing decision, and cost — as a structured Trace. It then compares traces against known-good baselines using a three-layer evaluation:

1. **Correctness Layer** (Hard Fail) — Did the agent give the right answer? Deterministic checks (string matching, regex) plus LLM-as-a-judge for subjective quality.
2. **Path Layer** (Soft Warning) — Did the agent take the right path? Tool recall, precision, sequence similarity, loop detection, handoff verification.
3. **Cost Layer** (Soft Warning) — Did the agent stay within budget? Token count, LLM calls, latency, dollar cost.

## Current Version

AgentCI is currently at version 2.0. The core trace model, three-layer evaluation engine, diff engine, YAML spec format, CLI tools, and GitHub Actions integration are all stable and production-ready.

## License

AgentCI is open source under the Apache 2.0 License.

## Who It's For

AgentCI is for any team building AI agents who want to:
- Catch regressions before they hit production
- Track cost drift across model changes
- Enforce tool usage patterns and routing rules
- Get inline GitHub PR annotations when something breaks
- Run deterministic tests with zero API keys using the mock system
