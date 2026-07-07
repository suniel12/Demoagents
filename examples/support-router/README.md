# TechCorp Support Router

A multi-agent customer support system built with the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python), tested with [CIAgent](https://github.com/suniel12/ciagent).

## Architecture

```
Customer Query
     │
     ▼
┌─────────────┐
│ Triage Agent │──── Guardrails (relevance, PII)
└─────┬───────┘
      │ handoff
      ├──► Billing Agent    (lookup_invoice, check_plan, process_refund)
      ├──► Technical Agent  (check_system_status, lookup_error_code)
      ├──► Account Agent    (verify_identity, reset_password, toggle_2fa)
      └──► General Agent    (search_knowledge_base)
```

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests (no API key needed — uses mocks)
make test

# Interactive chat (requires OPENAI_API_KEY)
cp .env.example .env   # add your key
python chat.py
```

## Test Suite

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_routing.py` | 23 | Routing correctness across 19 golden queries + structural assertions |
| `test_tool_calls.py` | 10 | Tool usage by specialists + cross-agent isolation |
| `test_guardrails.py` | 4 | Relevance and PII guardrail blocking |
| `test_regression.py` | 19 | Golden baseline comparison via CIAgent DiffEngine |

**56 tests total.** Mock mode runs in ~3 seconds. Live mode runs in ~3 minutes.

## Make Targets

| Command | Description |
|---------|-------------|
| `make test` | Run all tests with mocks (no API key) |
| `make test-live` | Run against real OpenAI API |
| `make record-mocks` | Re-record mock responses from live API |
| `make demo-break` | Run regression tests against live API |

## CIAgent Integration

This demo uses CIAgent's `AgentCITraceProcessor` to capture traces from the OpenAI Agents SDK. The trace captures:

- **Handoffs** — which agent routed to which specialist
- **Tool calls** — which tools were called with what arguments
- **Guardrails** — which guardrails fired and which passed
- **Cost** — token usage and cost per query

The regression test suite uses `diff_traces()` to compare current runs against golden baselines, detecting:

- `ROUTING_CHANGED` — handoff target changed
- `TOOLS_CHANGED` — different tools called
- `GUARDRAILS_CHANGED` — different guardrails triggered
- `COST_SPIKE` — cost increased beyond threshold
- `AVAILABLE_HANDOFFS_CHANGED` — routing options changed

## For Coding Agents

If you're a coding agent integrating with this project, see the root [`AGENTS.md`](../../AGENTS.md) for structured setup instructions, test patterns, and Make targets.
