# AgentCI Architecture

## System Overview

AgentCI is organized into four main layers:

### 1. Schema Layer
- `agentci_spec.yaml` — Declarative test specification
- `spec_models.py` — Pydantic models for validation (AgentCISpec, GoldenQuery, CorrectnessSpec, PathSpec, CostSpec)
- `generate_schema.py` — Auto-generates JSON Schema for IDE autocomplete
- `loader.py` — YAML loading with defaults merging and tag filtering

### 2. Engine Layer
- `engine/correctness.py` — Layer 1 evaluation (string checks, regex, LLM judge)
- `engine/path.py` — Layer 2 evaluation (tool recall/precision, sequence similarity, loop detection, handoffs)
- `engine/cost.py` — Layer 3 evaluation (tokens, cost, latency budgets)
- `engine/judge.py` — LLM-as-a-judge with safeguards (temp=0, structured JSON, ensembles)
- `engine/metrics.py` — Pure metric functions (tool_f1, LCS, edit distance, loop count)
- `engine/runner.py` — Orchestrator: evaluate_query() and evaluate_spec()
- `engine/parallel.py` — ThreadPoolExecutor parallel execution with retry/backoff
- `engine/diff.py` — Three-tier baseline comparison (DiffReport, MetricDelta)
- `engine/reporter.py` — Output formatting (console, github, json, prometheus)
- `engine/results.py` — QueryResult and LayerResult data models

### 3. Infrastructure Layer
- `models.py` — Core Trace and Span models
- `baselines.py` — Versioned golden baseline save/load/list
- `cli.py` — Click-based CLI (validate, test, diff, save, baselines, init)
- `config.py` — Configuration management
- `exceptions.py` — Custom exception types

### 4. Framework Adapters
- `adapters/openai_agents.py` — OpenAI Agents SDK trace processor
- `adapters/langgraph.py` — LangGraph state capture
- `adapters/generic.py` — Generic trace construction helpers
- `mocks.py` — OpenAIMocker and AnthropicMocker for zero-cost testing

## Data Flow

When you run `agentci test --config spec.yaml --workers 4`:

1. **Load**: `load_spec()` parses the YAML, merges defaults, validates against Pydantic schema
2. **Resolve**: `resolve_runner()` dynamically imports the runner function from the spec's `runner` field
3. **Execute**: `run_spec_parallel()` dispatches queries to the runner via ThreadPoolExecutor, with retry + backoff on transient errors
4. **Evaluate**: For each query, `evaluate_query()` runs all three layers:
   - Correctness: fastest-first (string → regex → LLM judge)
   - Path: tool metrics + handoff checks
   - Cost: budget comparisons against spec and baseline
5. **Report**: `report_results()` formats output and returns exit code (0/1/2)

## Trace Model

A Trace is the fundamental unit. It captures everything an agent did during one invocation:

```
Trace
├── input_query: str
├── output: str
├── spans: list[Span]
│   ├── Span(kind=agent, name="triage_agent")
│   ├── Span(kind=tool, name="search_kb", arguments={...})
│   ├── Span(kind=llm, model="claude-sonnet", tokens_in=180, tokens_out=95)
│   └── Span(kind=handoff, from_agent="triage", to_agent="billing")
├── total_tokens: int
├── total_cost_usd: float
├── total_duration_ms: float
├── tool_call_sequence: list[str]
├── agents_involved: list[str]
└── guardrails_triggered: list[str]
```

## Results Model

Each evaluated query produces a QueryResult with three LayerResults:

```
QueryResult
├── query: str
├── correctness: LayerResult(status=PASS|FAIL|SKIP, details=[...])
├── path: LayerResult(status=PASS|WARN|SKIP, details=[...])
├── cost: LayerResult(status=PASS|WARN|SKIP, details=[...])
└── hard_fail: bool (true if correctness FAIL or forbidden_tools violated)
```
