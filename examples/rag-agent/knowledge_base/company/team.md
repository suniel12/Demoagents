# AgentCI Vision & Roadmap

## Vision

AgentCI's vision is to become the standard CI/CD layer for AI agents — what pytest is for Python code, but designed for the probabilistic, multi-step nature of agent behavior.

Every team building AI agents should be able to:
1. Define what "correct" means in a YAML spec
2. Run those specs automatically on every commit
3. Get instant feedback in their GitHub PR when something regresses
4. Track cost and quality trends over time with versioned baselines

## What's Here Today (v2.0)

- **Three-layer evaluation engine** — Correctness (hard fail), Path (soft warn), Cost (soft warn)
- **YAML spec format** (agentci_spec.yaml) — Declarative test definitions with defaults inheritance
- **LLM-as-a-judge** — Structured JSON output, temperature 0, ensemble support, 3 built-in rubric templates
- **Diff engine** — Three-tier baseline comparison with MetricDelta reporting
- **CLI tools** — `agentci validate`, `agentci test`, `agentci diff`, `agentci save`, `agentci baselines`, `agentci init`
- **GitHub Actions integration** — Inline `::error` and `::warning` PR annotations (first-in-class)
- **Parallel execution** — ThreadPoolExecutor with retry and exponential backoff
- **Mock system** — Zero-cost testing with OpenAIMocker and AnthropicMocker
- **Framework adapters** — OpenAI Agents SDK, LangGraph/LangChain, Anthropic (raw)
- **Prometheus export** — Gauge exposition format for Grafana dashboards
- **Versioned baselines** — Save, load, list, and diff golden traces

## What's Coming (v3.0 Roadmap)

- **Dashboard UI** — Web-based trace visualization and trend tracking
- **OpenTelemetry export** — Trace export in OTel format for existing observability stacks
- **More framework adapters** — CrewAI, AutoGen, Microsoft Semantic Kernel
- **MCP server** — Model Context Protocol server for native coding agent integration
- **Agent Skills distribution** — Auto-discovery of AgentCI test patterns
- **Hosted regression tracking** — Cloud service for team-wide baseline management
- **pass^k reliability metric** — Statistical reliability scoring across multiple runs
- **Auto-spec generation** — Generate agentci_spec.yaml from existing test suites
- **YAML !include** — File references for shared assertion libraries
- **Grafana dashboard template** — Pre-built Prometheus → Grafana visualization
