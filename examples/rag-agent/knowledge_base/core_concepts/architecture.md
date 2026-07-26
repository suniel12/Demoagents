# CIAgent Architecture Overview

## System Architecture

CIAgent is organized into four main layers:

### 1. Schema Layer
- `ciagent_spec.yaml` — Declarative test specification
- `spec_models.py` — Pydantic models for validation (CIAgentSpec, GoldenQuery, CorrectnessSpec, PathSpec, CostSpec)
- `generate_schema.py` — Auto-generates JSON Schema for IDE autocomplete
- `loader.py` — YAML loading with defaults merging and tag filtering

### 2. Engine Layer
- `engine/correctness.py` — Layer 1 evaluation (string checks, regex, LLM judge)
- `engine/path.py` — Layer 2 evaluation (tool recall/precision, sequence similarity, loop detection, handoffs)
- `engine/cost.py` — Layer 3 evaluation (tokens, cost, latency budgets)
- `engine/judge.py` — LLM-as-a-judge with safeguards (temp=0, structured JSON, ensembles)

### 3. Infrastructure Layer
- `models.py` — Core Trace and Span models
- `baselines.py` — Versioned golden baseline save/load/list
- `cli.py` — Click-based CLI (validate, test, diff, save, baselines, init)

### 4. Framework Adapters
- `adapters/openai_agents.py` — OpenAI Agents SDK trace processor
- `adapters/langgraph.py` — LangGraph state capture
- `adapters/generic.py` — Generic trace construction helpers
- `mocks.py` — OpenAIMocker and AnthropicMocker for zero-cost testing

## Trace Data Model

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
