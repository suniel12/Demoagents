# AgentCI Mock System & Zero-Cost Testing

## Overview

AgentCI's mock system lets you run your entire agent test suite without making any real API calls. Tests run deterministically, instantly, and for free. This is critical for CI/CD where you want fast, reliable, reproducible test runs.

## OpenAI Mocker

For agents built with the OpenAI Agents SDK:

```python
from agentci.mocks import OpenAIMocker
from agents import set_default_openai_client

# Define a scripted response sequence
mocker = OpenAIMocker([
    {"tool": "transfer_to_BillingAgent", "arguments": {}},
    {"tool": "lookup_invoice", "arguments": {"email": "user@test.com"}},
    {"text": "I found your invoice. The duplicate charge has been refunded."}
])

# Inject — no API key needed
set_default_openai_client(mocker.client)

trace = run_your_agent("I was charged twice")
assert trace.tool_call_sequence == ["transfer_to_BillingAgent", "lookup_invoice"]
```

The mocker creates a fake OpenAI client that returns your scripted responses in order. The first two calls return tool use requests; the third returns a text completion.

## Anthropic Mocker

For agents using the Anthropic SDK:

```python
from agentci.mocks import AnthropicMocker

mocker = AnthropicMocker([
    {"tool": "github_fetch_metadata", "arguments": {"url": "https://github.com/example/repo"}},
    {"tool": "github_read_file", "arguments": {"path": "README.md"}},
    {"text": "## Repository Analysis\n\nThis is a well-maintained repo with..."}
])

# Use mocker.client as your Anthropic client
client = mocker.client
```

## YAML Response Files

For complex test suites, you can define mock responses in YAML:

```yaml
# mocks/responses.yaml
- tool: search_knowledge_base
  arguments:
    query: "refund policy"
  result: "Our refund policy allows returns within 30 days..."

- tool: grade_documents
  arguments: {}
  result: "relevant"

- text: "Based on our refund policy, you can return items within 30 days."
```

## Benefits of Mock Testing

1. **Speed** — Tests run in milliseconds, not seconds
2. **Cost** — Zero API calls, zero cost
3. **Determinism** — Same inputs always produce same outputs
4. **Offline** — No network required
5. **CI/CD friendly** — No API key secrets needed for basic tests
6. **Reproducible** — Every developer gets the same results

## When to Use Real APIs

Use the mock system for:
- Deterministic logic tests (routing, tool sequencing)
- Cost budget assertions
- Golden baseline creation
- Quick iteration during development

Use real APIs for:
- LLM-as-a-judge evaluations (requires actual LLM calls)
- End-to-end integration tests
- Output quality assessment
- Pre-release validation

The recommended CI pattern is two jobs:
1. **Deterministic job** (mocked, always runs, fast) — catches routing, tool, and cost regressions
2. **LLM judge job** (real API, runs when keys available) — catches output quality regressions
