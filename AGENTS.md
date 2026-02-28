# AGENTS.md

> Machine-readable reference for coding agents (Claude Code, Cursor, Codex, Copilot).
> For human-friendly docs, see individual example READMEs.

## Overview

DemoAgents is a collection of three production-pattern AI agents that demonstrate AgentCI trace-based regression testing. Each example is a standalone project with its own tests, mocks, and golden baselines.

## Prerequisites

```bash
pip install ciagent
```

## Examples

### 1. Support Router (OpenAI Agents SDK)

Multi-agent customer support system with triage, billing, technical, account, and general support agents.

```bash
cd examples/support-router
pip install -r requirements.txt
```

**Run tests (mocked, no API keys needed):**
```bash
make test                    # 56 tests, ~3 seconds
pytest tests/ -v --tb=short  # Equivalent
```

**Run against live API:**
```bash
make test-live               # Requires OPENAI_API_KEY
```

**Record new mocks from live API:**
```bash
make record-mocks            # Requires OPENAI_API_KEY
```

**Run regression tests:**
```bash
make demo-break              # Tests against live API
```

**Package:** `support_router/`
**Test files:**
- `tests/test_routing.py` — 23 routing tests (parametrized)
- `tests/test_tool_calls.py` — 10 tool invocation tests
- `tests/test_guardrails.py` — 4 guardrail tests
- `tests/test_regression.py` — 19 regression tests
- `tests/conftest.py` — OpenAI mock setup via `agentci.mocks.OpenAIMocker`
- `tests/fixtures/mock_responses.yaml` — Recorded mock responses

**Key imports:**
```python
from support_router.run import run_support_agent
from support_router.agents.triage import triage_agent
from support_router.context import SupportContext
from agentci.mocks import OpenAIMocker
```

### 2. Dev Agent (Raw Anthropic API)

GitHub repository health analyzer using raw Anthropic API with a tool-calling agent loop.

```bash
cd examples/dev-agent
pip install -r requirements.txt
```

**Run tests:**
```bash
make test                    # All tests (unit + agent)
make test-unit               # Unit tests only (no LLM)
make test-tools              # Tool call tests (mocked)
make test-quality            # Output quality tests
make test-guardrails         # Guardrail tests
make test-errors             # Error handling tests
make test-golden             # Golden trace tests
```

**Run the agent:**
```bash
make run REPO=langchain-ai/langchain
make run-example             # Runs on langchain (default)
python -m devagent.agent.run "https://github.com/owner/repo"
```

**Record golden traces:**
```bash
make record-golden
```

**Package:** `devagent/`
**Test files:**
- `tests/test_url_parser.py` — URL parsing unit tests
- `tests/test_tool_calls.py` — Tool invocation tests
- `tests/test_guardrails.py` — Guardrail tests
- `tests/test_error_handling.py` — Error handling tests
- `tests/test_error_recovery.py` — Error recovery tests
- `tests/test_conditional_execution.py` — Conditional execution tests
- `tests/test_golden_traces.py` — Golden trace regression tests
- `tests/test_output_quality.py` — Output quality tests
- `tests/conftest.py` — AgentCI fixtures, Anthropic mock setup

**Key imports:**
```python
from devagent.agent.core import DevAgent, Trace
from devagent.tools import ToolRegistry, ToolDefinition
from devagent.tools.github_repo_metadata import github_repo_metadata_tool, RepoMetadataOutput
```

### 3. RAG Agent (LangGraph)

Retrieval-Augmented Generation agent using LangGraph with document retrieval and grading.

```bash
cd examples/rag-agent
pip install -r requirements.txt
```

**Run tests:**
```bash
make test                    # All tests (mocked)
make test-live               # Against live API
pytest tests/test_rag.py -v  # Direct pytest
```

**Record baselines:**
```bash
make baseline                # Record golden baseline
```

**Compare against baseline:**
```bash
make compare MODEL=gpt-4o-mini
```

**Package:** Root-level `agent.py` + `chat.py`
**Test files:**
- `tests/test_rag.py` — 17 RAG tests
- `conftest.py` — Minimal pytest config

**Key imports:**
```python
from agent import build_graph
from agentci.capture import TraceContext
```

## Project Structure

```
DemoAgents/
├── AGENTS.md                          # This file
├── agents/                            # Simple demo agents (weather, researcher, summarizer)
│   ├── weather_agent.py
│   ├── researcher_agent.py
│   ├── summarizer_agent.py
│   └── *_agentci.yaml                 # Per-agent test configs
├── examples/
│   ├── support-router/                # OpenAI Agents SDK multi-agent
│   │   ├── support_router/            # Package source
│   │   ├── tests/                     # 56 tests
│   │   ├── Makefile
│   │   └── pyproject.toml
│   ├── dev-agent/                     # Raw Anthropic tool-calling
│   │   ├── devagent/                  # Package source
│   │   ├── tests/                     # 8 test modules
│   │   ├── Makefile
│   │   └── pyproject.toml
│   └── rag-agent/                     # LangGraph RAG
│       ├── agent.py
│       ├── tests/
│       ├── knowledge_base/            # 10 markdown documents
│       └── Makefile
└── .agent/workflows/
    └── agentci-dogfood.md             # Development workflow
```

## Adding New Tests

Follow the existing patterns in each example:

1. **Create test file** in `tests/` directory
2. **Import fixtures** from `conftest.py` (mocks are auto-applied)
3. **Run the agent** and capture a trace
4. **Assert against the trace** using AgentCI assertions
5. **Record golden baseline** if regression testing is needed

Example test pattern (support-router):

```python
import pytest
from agents import Runner

@pytest.mark.asyncio
async def test_billing_routes_correctly(mock_openai):
    result = await Runner.run(triage_agent, "I have a billing question")
    # Assert routing, tool calls, output, etc.
    assert result.final_output is not None
```

## AgentCI Integration

All three examples integrate with AgentCI for:
- **Trace capture** — Every test run produces a `Trace` object
- **Mock responses** — Zero-cost testing without API keys
- **Golden baselines** — Regression detection via trace diffing
- **Assertions** — Tool calls, routing, cost, output quality

See [AgentCI AGENTS.md](https://github.com/agentci-org/agentci/blob/main/AGENTS.md) for the full AgentCI API reference.
