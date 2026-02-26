# AgentCI Spec Format (agentci_spec.yaml)

## Overview

The `agentci_spec.yaml` file is the heart of AgentCI v2. It is a declarative YAML file that defines what your agent should do, how it should behave, and what guardrails it must respect. AgentCI validates specs against a Pydantic schema and provides IDE autocomplete via JSON Schema.

## Root Fields

```yaml
version: 1                    # Schema version (currently 1)
agent: my-agent               # Agent identifier
baseline_dir: ./baselines     # Where versioned golden baselines are stored
runner: "myagent.run:run_fn"  # Python dotted path to agent runner (optional)

defaults:                     # Default settings applied to all queries
  correctness: { ... }
  path: { ... }
  cost: { ... }

judge_config:                 # Global LLM judge settings
  model: claude-sonnet-4-6
  temperature: 0
  structured_output: true

queries:                      # List of test cases (1 or more required)
  - query: "..."
    ...
```

## Query Structure

Each query defines one test case:

```yaml
- query: "How do I install AgentCI?"
  description: "Core in-scope question"
  tags: [smoke, happy-path]

  correctness:
    expected_in_answer: ["pip install"]
    not_in_answer: ["npm install"]
    exact_match: "..."
    regex_match: "pip install \\w+"
    llm_judge:
      - rule: "Response provides clear installation instructions"
        threshold: 0.7
    safety_check:
      rule: "No harmful content"
      threshold: 0.9
    hallucination_check:
      rule: "Answer grounded in context only"
      threshold: 0.8

  path:
    expected_tools: [retriever_tool, grade_documents]
    forbidden_tools: [web_search]
    max_tool_calls: 5
    min_tool_recall: 0.8
    min_tool_precision: 0.7
    min_sequence_similarity: 0.6
    max_loops: 2
    match_mode: subset  # strict | unordered | subset | superset
    expected_handoff: "billing_agent"
    max_handoff_count: 1

  cost:
    max_cost_usd: 0.05
    max_cost_multiplier: 2.0
    max_total_tokens: 3000
    max_llm_calls: 5
    max_latency_ms: 10000
```

## Three Layers Explained

### Layer 1: Correctness (Hard Fail)
If any correctness check fails, the entire test case fails and the CI pipeline exits with code 1. Checks run fastest-first:
1. String containment (expected_in_answer, not_in_answer)
2. Exact match and regex match
3. JSON schema validation
4. LLM judge (only if deterministic checks pass — saves API cost)
5. Safety and hallucination sub-checks

### Layer 2: Path (Soft Warning)
Path violations produce warnings (::warning annotations in GitHub Actions) but do NOT fail the build. Exception: `forbidden_tools` violations escalate to hard fail.

### Layer 3: Cost (Soft Warning)
Cost violations produce warnings but do not block the merge. They alert you to cost drift.

## Match Modes

When comparing tool sequences:
- **strict** — Same tools, same order
- **unordered** — Same tools, any order
- **subset** (default) — All expected tools must appear, extras OK
- **superset** — All used tools must be in the expected set

## Tags and Filtering

Add tags to queries for selective execution:
```yaml
tags: [smoke, edge-case, billing]
```

Run only specific tags:
```bash
agentci test --config agentci_spec.yaml --tags smoke
```

## Defaults Inheritance

Settings in the `defaults` block apply to all queries. Per-query settings override defaults:

```yaml
defaults:
  cost:
    max_cost_usd: 0.05

queries:
  - query: "cheap query"
    # inherits max_cost_usd: 0.05

  - query: "expensive query"
    cost:
      max_cost_usd: 0.20  # overrides default
```
