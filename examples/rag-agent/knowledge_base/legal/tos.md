# AgentCI Assertions & Metrics Reference

## Deterministic Assertions (Correctness Layer)

These run fastest and require no API calls:

| Assertion | Field | What it checks |
|-----------|-------|----------------|
| String containment | `expected_in_answer` | Answer must contain ALL listed strings (case-insensitive) |
| Forbidden strings | `not_in_answer` | Answer must NOT contain ANY listed strings |
| Exact match | `exact_match` | Answer must equal this string exactly (whitespace-stripped) |
| Regex match | `regex_match` | Answer must match this Python regex pattern |
| JSON schema | `json_schema` | Answer must parse as JSON conforming to this schema |

## LLM Judge Assertions (Correctness Layer)

These use an LLM to evaluate subjective quality:

| Assertion | Field | What it checks |
|-----------|-------|----------------|
| Custom rubric | `llm_judge` | List of rubrics with rule, threshold (0-1), optional scale, optional few-shot examples |
| Safety check | `safety_check` | Single rubric for safety evaluation (hard fail) |
| Hallucination check | `hallucination_check` | Single rubric for grounding evaluation (hard fail) |

Built-in rubric templates (in `engine/judge.py`):
- `polite_refusal` — Agent declines out-of-scope questions politely
- `factual_grounded` — Answer is grounded in provided context, no fabrication
- `actionable_steps` — Response contains clear, actionable next steps

## Path Metrics (Path Layer)

| Metric | Field | Formula / Description |
|--------|-------|----------------------|
| Tool recall | `min_tool_recall` | `\|expected ∩ used\| / \|expected\|` — fraction of expected tools that were called |
| Tool precision | `min_tool_precision` | `\|expected ∩ used\| / \|used\|` — fraction of called tools that were expected |
| Tool F1 | (computed) | `2·P·R / (P+R)` — harmonic mean of precision and recall |
| Sequence similarity | `min_sequence_similarity` | `2·\|LCS(expected, actual)\| / (\|expected\| + \|actual\|)` — normalized LCS |
| Loop detection | `max_loops` | Count of max consecutive repeated tool invocations |
| Tool count | `max_tool_calls` | Total number of tool calls in the trace |
| Handoff target | `expected_handoff` | Name of the agent the query should be routed to |
| Handoff count | `max_handoff_count` | Maximum number of agent-to-agent transfers allowed |
| Forbidden tools | `forbidden_tools` | Tools that must NOT be called (escalates to hard fail) |
| Match mode | `match_mode` | How to compare tool sequences: strict, unordered, subset, superset |

## Cost Metrics (Cost Layer)

| Metric | Field | Description |
|--------|-------|-------------|
| Dollar cost | `max_cost_usd` | Maximum absolute cost in USD |
| Cost multiplier | `max_cost_multiplier` | Max cost as multiple of golden baseline (e.g. 2.0 = 2x baseline) |
| Token count | `max_total_tokens` | Maximum total tokens (input + output) across all LLM calls |
| LLM calls | `max_llm_calls` | Maximum number of LLM API calls |
| Latency | `max_latency_ms` | Maximum wall-clock time in milliseconds |

## Diff Report Types

When diffing two baselines, AgentCI reports these change categories:

| Diff Type | Meaning |
|-----------|---------|
| `TOOLS_CHANGED` | Different tools were called vs. baseline |
| `ARGS_CHANGED` | Same tools, but arguments changed |
| `SEQUENCE_CHANGED` | Tools called in a different order |
| `COST_SPIKE` | Cost increased beyond threshold |
| `LATENCY_SPIKE` | Duration increased beyond threshold |
| `ROUTING_CHANGED` | Agent handoff went to a different target |
| `GUARDRAILS_CHANGED` | Different guardrails fired vs. baseline |
| `OUTPUT_CHANGED` | Final output semantically different |

## Exit Codes

| Code | Meaning | When |
|------|---------|------|
| 0 | Pass | All correctness checks pass; warnings may be emitted |
| 1 | Fail | One or more correctness failures; blocks CI merge |
| 2 | Error | Infrastructure or configuration error |
