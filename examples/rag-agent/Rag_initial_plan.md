# AgentCI × RAG Agent: Incremental Build Plan

## The Philosophy

You are not building a RAG agent. You are building a **testing framework** and using a RAG agent as the vehicle to discover what needs testing. Every step below follows the same loop:

1. Add one capability to the agent
2. Run it, look at the trace
3. Ask: "What could go wrong here? What do I wish I could assert?"
4. Write that test
5. Intentionally break the agent to confirm the test catches it
6. Commit both the agent change and the test together

The template you're forking is the official [LangGraph Agentic RAG tutorial](https://docs.langchain.com/oss/python/langgraph/agentic-rag). It has 8 clean steps that map perfectly to an incremental testing journey.

---

## The Knowledge Base (Static, Ships With The Example)

Before any agent code, you need a small, controlled corpus. This is NOT the LangGraph tutorial's default (Lilian Weng blog posts) — those require web fetching and are uncontrolled. Instead, create 10-15 short markdown files for a fictional company called **"NovaCorp"**:

| File | Content | Purpose |
|------|---------|---------|
| `policies/refund-policy.md` | "Enterprise customers: full refund within 30 days. Startup plan: 14 days. No refunds after 60 days." | Direct-hit retrieval test |
| `policies/sla-terms.md` | "99.9% uptime SLA for Enterprise. 99.5% for Business. No SLA for Free tier." | Multi-fact retrieval |
| `products/pricing.md` | "Enterprise: $499/mo. Business: $199/mo. Starter: $49/mo. Free: $0." | Number extraction test |
| `products/features.md` | "Enterprise includes: SSO, audit logs, dedicated support. Business: email support, basic analytics." | Comparison queries |
| `support/faq.md` | "Password reset: Settings > Security > Reset. Two-factor: Settings > 2FA." | Procedural instruction |
| `support/contact.md` | "Email: support@novacorp.com. Phone: 1-800-NOVA. Hours: 9-5 PT weekdays." | Factual lookup |
| `company/about.md` | "NovaCorp founded 2019. HQ in Austin, TX. 450 employees." | Background retrieval |
| `company/team.md` | "CEO: Sarah Chen. CTO: Marcus Williams. VP Eng: Priya Patel." | Proper noun retrieval |
| `legal/privacy.md` | "Data stored in US-WEST-2. GDPR compliant. SOC 2 Type II certified." | Compliance queries |
| `legal/tos.md` | "Users must be 18+. Prohibited: scraping, resale, reverse engineering." | Restriction queries |

**Why this matters for testing:** You know exactly what's in these docs. When you ask "What's the refund policy for enterprise?" you KNOW the answer should contain "30 days" and should NOT contain "60 days" (that's the cutoff, not the window). This makes assertions deterministic without needing LLM-as-judge.

---

## Step 0: Skeleton (30 minutes)

### What you build
A project structure. No agent logic yet.

```
examples/rag-agent/
├── knowledge_base/           # The 10-15 NovaCorp markdown files
│   ├── policies/
│   ├── products/
│   ├── support/
│   ├── company/
│   └── legal/
├── agent.py                  # Will hold the agent (empty for now)
├── tests/
│   └── test_rag.py           # Will hold tests (empty for now)
├── golden_traces/            # Will hold baseline traces
├── mocks/
│   └── responses.yaml        # Will hold mock LLM/retrieval responses
└── conftest.py               # Pytest fixtures for AgentCI
```

### What you test
Nothing yet. But you set up `conftest.py` with the AgentCI fixtures you already built in Phase 1 — the `@agentci.trace` decorator, the mock system, the diff engine imports.

### What you learn
How the example project structure should look for other developers. This becomes the `agentci init --template rag` scaffold later.

### Commit message
`feat(examples): scaffold RAG agent project structure with NovaCorp knowledge base`

---

## Step 1: The Dumbest Possible RAG Agent (1-2 hours)

### What you build
The absolute minimum from the LangGraph tutorial:
- Load the NovaCorp markdown files
- Split them into chunks (RecursiveCharacterTextSplitter)
- Index into InMemoryVectorStore with OpenAI embeddings
- Create a `retrieve_docs` tool
- One LLM call that has access to the retriever tool
- That's it. No grading, no rewriting, no graph. Just: question → retrieve → answer.

This maps to Steps 1-3 of the LangGraph tutorial, stripped to the bare minimum.

### What you observe when you run it
You run it with: "What is the refund policy for enterprise customers?"

You look at the trace. You see:
- LLM decided to call `retrieve_docs` ✓
- Retriever returned 4 chunks (default top_k=4)
- LLM generated an answer mentioning "30 days" ✓
- Total cost: ~$0.003
- Total tokens: ~800

You run it again with: "Hello, how are you?"

You look at the trace. You see:
- LLM did NOT call `retrieve_docs` — it responded directly ✓
- Total cost: ~$0.0002
- This is correct behavior! The agent decided retrieval wasn't needed.

### What tests emerge naturally

**Test 1: "Did the agent retrieve when it should have?"**
```python
def test_retrieval_triggered_for_knowledge_question():
    trace = run_agent("What is the refund policy for enterprise?")
    assert "retrieve_docs" in trace.tools_called
```

**Test 2: "Did the agent skip retrieval when appropriate?"**
```python
def test_no_retrieval_for_greeting():
    trace = run_agent("Hello, how are you?")
    assert "retrieve_docs" not in trace.tools_called
```

**Test 3: "Is the cost reasonable?"**
```python
def test_cost_within_budget():
    trace = run_agent("What is the refund policy for enterprise?")
    assert trace.total_cost < 0.01
```

### The intentional break
Change the system prompt from "You are a helpful assistant with access to a knowledge base" to "You are a helpful assistant who answers questions from your own knowledge."

Re-run Test 1. The agent stops calling `retrieve_docs` and answers from training data. Test fails. **This is your first "aha moment."** One sentence in a prompt silently killed your entire retrieval pipeline.

### What you might discover about AgentCI
- Does the trace capture tool calls correctly for LangGraph's tool binding?
- Is the mock system intercepting the right layer (LLM API calls vs. LangGraph internal calls)?
- Does `trace.tools_called` return a list you can easily assert on?

If any of these don't work smoothly, you fix AgentCI now — before you add complexity.

### Commit message
`feat(examples): step 1 — minimal RAG agent with retrieval and cost assertions`

---

## Step 2: Add the Golden Dataset (1 hour)

### What you build
No agent changes. Instead, you create a structured test dataset:

```python
GOLDEN_QUERIES = [
    {
        "query": "What is the refund policy for enterprise customers?",
        "category": "direct_hit",
        "expected_in_answer": ["30 days"],
        "not_in_answer": ["60 days"],  # 60 days is the cutoff, not the window
        "expected_tool": "retrieve_docs",
        "expected_doc_keywords": ["refund", "enterprise"],
    },
    {
        "query": "Compare enterprise and business plan features.",
        "category": "multi_chunk",
        "expected_in_answer": ["SSO", "audit logs"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "What's the CEO's favorite restaurant?",
        "category": "out_of_scope",
        "expected_in_answer": ["don't have", "not available", "no information"],
        "not_in_answer": [],  # should NOT hallucinate a restaurant
        "expected_tool": "retrieve_docs",  # should still TRY to retrieve
    },
    {
        "query": "Hello!",
        "category": "no_retrieval",
        "expected_tool": None,
    },
    {
        "query": "How do I reset my password?",
        "category": "direct_hit",
        "expected_in_answer": ["Settings", "Security"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "What's NovaCorp's uptime guarantee for the business plan?",
        "category": "direct_hit",
        "expected_in_answer": ["99.5"],
        "not_in_answer": ["99.9"],  # that's enterprise, not business
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "Is NovaCorp SOC 2 compliant?",
        "category": "direct_hit",
        "expected_in_answer": ["SOC 2", "certified"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "What's the weather in Austin?",
        "category": "out_of_scope",
        "expected_tool": "retrieve_docs",  # it'll try, but find nothing useful
        "expected_in_answer": ["don't have", "not available", "no information", "can't"],
    },
]
```

### What tests emerge naturally

**Test 4: Parametrized golden dataset**
```python
@pytest.mark.parametrize("case", GOLDEN_QUERIES, ids=lambda c: c["query"][:40])
def test_golden_query(case):
    trace = run_agent(case["query"])

    # Tool call assertion
    if case["expected_tool"]:
        assert case["expected_tool"] in trace.tools_called
    else:
        assert len(trace.tools_called) == 0

    # Content assertion (only for cases with expected content)
    if "expected_in_answer" in case:
        answer = trace.final_output.lower()
        assert any(kw.lower() in answer for kw in case["expected_in_answer"]), \
            f"Expected one of {case['expected_in_answer']} in answer: {answer[:200]}"

    if "not_in_answer" in case:
        answer = trace.final_output.lower()
        for kw in case["not_in_answer"]:
            assert kw.lower() not in answer, \
                f"Unexpected '{kw}' found in answer: {answer[:200]}"
```

### What you learn
- Which golden queries pass and which fail with your minimal agent
- Whether the out-of-scope handling works (it probably doesn't yet — the agent will likely hallucinate)
- The exact failure output format AgentCI should produce for parametrized tests

### The intentional break
You don't need to break anything. Some golden queries will naturally fail with the Step 1 agent. The out-of-scope queries ("CEO's favorite restaurant") will likely get hallucinated answers. This sets up the motivation for Step 3.

### Commit message
`feat(examples): step 2 — golden dataset with 8 parametrized test cases`

---

## Step 3: Add the Mock System (1-2 hours)

### What you build
Record real traces from Step 1-2 runs and create mock fixtures so everything runs without API keys.

For each golden query, you capture:
- The LLM's tool-calling decision (mock response 1)
- The retriever's results (mock retrieval data)
- The LLM's final answer (mock response 2)

Store these in `mocks/responses.yaml`:

```yaml
- query_pattern: "refund policy"
  llm_responses:
    - role: tool_call
      tool: retrieve_docs
      args: {query: "enterprise refund policy"}
    - role: assistant
      content: "Enterprise customers are eligible for a full refund within 30 days..."
  retrieval_results:
    - doc_id: "policies/refund-policy-chunk-1"
      score: 0.92
      text: "Enterprise customers: full refund within 30 days..."
    - doc_id: "policies/refund-policy-chunk-2"
      score: 0.85
      text: "No refunds after 60 days for any plan..."
  cost: 0.0035
  tokens: {prompt: 720, completion: 85}
```

### What tests emerge naturally

**Test 5: Mock mode parity check**
```python
def test_mock_mode_matches_live_behavior():
    """Verify that mock mode produces identical trace structure to live mode."""
    # This test runs in mock mode by default (CI)
    trace = run_agent("What is the refund policy for enterprise?")
    assert "retrieve_docs" in trace.tools_called
    assert trace.total_cost > 0  # mock should still report cost
    assert trace.final_output  # mock should still produce output
```

### What you discover about AgentCI
This is where you'll find friction in the mock system:
- Does the mock intercept at the right layer for LangGraph? (LangGraph wraps OpenAI calls — you need to intercept the inner API call, not the LangGraph wrapper)
- Does the mock correctly report token counts and costs?
- Is the YAML format intuitive? Would a developer actually write these mocks?
- Should there be a `agentci record` command that auto-generates mocks from live runs?

This is pure AgentCI product discovery. Every friction point you find here is a feature gap worth fixing.

### Commit message
`feat(examples): step 3 — mock system for zero-API-key testing`

---

## Step 4: Add Document Grading (1-2 hours)

### What you build
This is Step 4 from the LangGraph tutorial. After retrieval, a second LLM call grades whether the retrieved documents are relevant. If they're not relevant, the workflow takes a different path.

This adds a new node to the graph:
- `generate_query_or_respond` → calls retriever tool
- **NEW: `grade_documents`** → LLM grades retrieved docs as "yes"/"no" relevant
- If "yes" → `generate_answer`
- If "no" → `rewrite_question` (you'll add this in Step 5)

The grading LLM call uses structured output (Pydantic model with `binary_score: str`).

### What you observe when you run it
The trace now has a new span:

```
Trace
├── Span: generate_query (LLM call #1) — decides to retrieve
├── Span: retrieve_docs (Tool call) — gets chunks
├── Span: grade_documents (LLM call #2) — NEW: grades relevance
│   ├── input: {retrieved chunks + original question}
│   ├── output: {"binary_score": "yes"}
│   ├── model: gpt-4o-mini
│   └── cost: $0.001
├── Span: generate_answer (LLM call #3) — generates response
└── Trace Summary
    ├── total_cost: $0.005 (went up!)
    ├── llm_call_count: 3 (was 2)
    └── tools_called: ["retrieve_docs"]
```

### What tests emerge naturally

**Test 6: "Did the grading step actually run?"**
```python
def test_grading_step_exists():
    trace = run_agent("What is the refund policy for enterprise?")
    span_names = [s.name for s in trace.spans]
    assert "grade_documents" in span_names
```

**Test 7: "Did grading produce the right decision?"**
```python
def test_relevant_docs_pass_grading():
    trace = run_agent("What is the refund policy for enterprise?")
    grade_span = trace.get_span("grade_documents")
    # The grading should say "yes" for a direct-hit question
    assert "yes" in grade_span.output.lower()
```

**Test 8: "Cost increased — is it within the new budget?"**
```python
def test_cost_with_grading():
    trace = run_agent("What is the refund policy for enterprise?")
    # Budget is now higher because we have 3 LLM calls
    assert trace.total_cost < 0.015
```

### The intentional break
The interesting break here: you ask an out-of-scope question ("What's the weather in Austin?"). The retriever returns irrelevant chunks. The grader says "no." But you haven't built the rewrite path yet, so... what happens? The agent might crash, return nothing, or hang.

This is a real discovery moment. Your test catches it:

```python
def test_irrelevant_docs_get_rejected():
    trace = run_agent("What's the weather in Austin?")
    grade_span = trace.get_span("grade_documents")
    assert "no" in grade_span.output.lower()
    # What happens next? Does the agent handle this gracefully?
    assert trace.final_output is not None  # shouldn't crash
```

### What you discover about AgentCI
- Can AgentCI capture spans from conditional edges in LangGraph?
- Does `trace.get_span("grade_documents")` work for named graph nodes?
- When the graph takes a different path (grade → rewrite vs. grade → generate), does the trace correctly reflect the branching?

**This is where AgentCI's trace model gets tested against real-world conditional logic.** If it can't capture LangGraph's conditional edges, that's a critical gap to fix before Phase 2.

### Commit message
`feat(examples): step 4 — document grading with relevance assertions and cost tracking`

---

## Step 5: Add Question Rewriting (1-2 hours)

### What you build
Step 5 from the LangGraph tutorial. When the grader rejects the retrieved docs, instead of failing, the agent rewrites the question and tries retrieval again.

This creates a **loop** in the graph:
```
query → retrieve → grade → [yes] → generate
                          → [no]  → rewrite → retrieve → grade → ...
```

This is the first time the workflow can cycle. The trace gets more complex.

### What you observe when you run it
For a well-phrased question like "refund policy for enterprise," the trace looks the same as Step 4 — no rewriting needed.

For a poorly-phrased question like "how do I get money back," the trace now shows:

```
Trace
├── Span: generate_query (LLM #1) — decides to retrieve
├── Span: retrieve_docs (Tool call #1) — gets chunks (mediocre match)
├── Span: grade_documents (LLM #2) — grades "no"
├── Span: rewrite_question (LLM #3) — NEW: rewrites to "refund policy return money"
├── Span: retrieve_docs (Tool call #2) — second retrieval (better match!)
├── Span: grade_documents (LLM #4) — grades "yes"
├── Span: generate_answer (LLM #5) — generates response
└── Trace Summary
    ├── total_cost: $0.009 (nearly doubled!)
    ├── llm_call_count: 5
    ├── tool_call_count: 2
    └── tools_called: ["retrieve_docs", "retrieve_docs"]
```

### What tests emerge naturally

**Test 9: "Rewriting happens for vague queries"**
```python
def test_rewrite_triggered_for_vague_query():
    trace = run_agent("how do I get money back")
    span_names = [s.name for s in trace.spans]
    assert "rewrite_question" in span_names
```

**Test 10: "Rewriting does NOT happen for clear queries"**
```python
def test_no_rewrite_for_clear_query():
    trace = run_agent("What is the refund policy for enterprise customers?")
    span_names = [s.name for s in trace.spans]
    assert "rewrite_question" not in span_names
```

**Test 11: "Rewrite loop doesn't run forever"**
```python
def test_max_retries():
    # For a truly unanswerable question, the loop should stop
    trace = run_agent("What color is the CEO's car?")
    rewrite_count = sum(1 for s in trace.spans if s.name == "rewrite_question")
    assert rewrite_count <= 2  # max 2 rewrites before giving up
    assert trace.total_cost < 0.03  # even with retries, cost is bounded
```

**Test 12: "The execution path is correct"**
```python
def test_execution_path_with_rewrite():
    trace = run_agent("how do I get money back")
    expected_path = [
        "generate_query",
        "retrieve_docs",
        "grade_documents",
        "rewrite_question",
        "retrieve_docs",
        "grade_documents",
        "generate_answer"
    ]
    actual_path = [s.name for s in trace.spans]
    assert actual_path == expected_path
```

### This is the AgentCI differentiator moment
Test 12 is something **no other tool does well.** DeepEval checks metrics. LangSmith visualizes traces. But neither of them lets you write `assert actual_path == expected_path` as a CI gate. This is the test that catches silent workflow regressions — when a prompt change causes the agent to skip grading, or loop 5 times instead of 2, or grade before retrieving.

**This test is the hero of your README.**

### The intentional break
Change the grading prompt to be more lenient (e.g., change "only grade as relevant if directly related" to "grade as relevant if somewhat related"). Now the grader always says "yes." The rewrite path never fires. Test 9 fails. Test 12 fails (path is shorter than expected).

The developer realizes: a single-word change in the grading prompt silently disabled their self-correction loop.

### What you discover about AgentCI
- Can the trace capture repeated spans? (Two `retrieve_docs` calls, two `grade_documents` calls)
- Does the execution path ordering reflect actual execution order?
- How does the diff engine handle variable-length traces? (Baseline had 4 spans, new run has 7)

If the diff engine can't handle variable-length traces, that's a critical feature to add.

### Commit message
`feat(examples): step 5 — question rewriting with loop detection and execution path assertions`

---

## Step 6: The Full Assembled Graph + Regression Baselines (1-2 hours)

### What you build
The complete LangGraph graph with all components wired together. This maps to Steps 7-8 of the LangGraph tutorial. The agent is now "done" — it can:
- Decide whether to retrieve
- Retrieve relevant documents
- Grade them for relevance
- Rewrite the query if needed
- Generate a grounded answer

At this point, you save **golden baselines** for every query in the golden dataset.

```python
# One-time: record baselines
agentci baseline save --name "rag-v1-gpt4o-mini" --queries golden_queries.json
```

This saves the full trace for each query: tool calls, costs, outputs, execution paths.

### What tests emerge naturally

**Test 13: The full regression test**
```python
def test_regression_against_baseline():
    """Compare current run against saved baseline.
    Flags: TOOLS_CHANGED, COST_SPIKE, PATH_CHANGED
    """
    baseline = agentci.load_baseline("rag-v1-gpt4o-mini")
    for query in GOLDEN_QUERIES:
        current_trace = run_agent(query["query"])
        diff = agentci.diff(baseline[query["query"]], current_trace)
        assert not diff.has_regression, \
            f"Regression detected for '{query['query']}': {diff.summary}"
```

### The big demo: Model Swap Regression

This is the climax of the entire example. You run:

```bash
# Baseline: gpt-4o-mini
agentci baseline save --name "gpt4o-mini" --queries golden_queries.json

# Switch model to gpt-4o
export AGENT_MODEL=gpt-4o
pytest tests/test_rag.py --agentci-compare gpt4o-mini
```

AgentCI output:
```
============ AgentCI Regression Report ============
Comparing: current run vs. baseline "gpt4o-mini"

Query: "What is the refund policy for enterprise?"
  ✅ TOOLS: identical [retrieve_docs]
  ⚠️  COST_SPIKE: $0.003 → $0.018 (6.0x increase)
  ✅ PATH: identical [generate_query → retrieve → grade → generate]
  ✅ OUTPUT: contains expected keywords

Query: "How do I get money back"
  ⚠️  PATH_CHANGED:
    baseline: [query → retrieve → grade → rewrite → retrieve → grade → generate]
    current:  [query → retrieve → grade → generate]
    Note: gpt-4o grading was more lenient — skipped rewrite loop
  ⚠️  COST_SPIKE: $0.009 → $0.021 (2.3x increase)
  ✅ OUTPUT: contains expected keywords

Query: "What's the weather in Austin?"
  ❌ OUTPUT_CHANGED:
    baseline: "I don't have information about weather..."
    current:  "The weather in Austin is typically warm..." (HALLUCINATION)
    Note: gpt-4o used training knowledge instead of saying "I don't know"

SUMMARY: 2 regressions, 4 warnings across 8 queries
```

**This is the entire sales pitch of AgentCI in one terminal output.** A developer sees exactly what changed, why, and whether it matters. No other tool produces this view.

### Commit message
`feat(examples): step 6 — full graph assembly with regression baselines and model swap demo`

---

## Step 7: Polish and Package (2-3 hours)

### What you build
No new agent features. This is about making the example production-quality:

1. **README.md** for the example with:
   - "60-second quickstart" (clone, install, run tests in mock mode)
   - "Try the model swap" (change one env var, see regressions)
   - "Try the prompt break" (uncomment a line, see tool calls disappear)

2. **Makefile or script** with:
   - `make test` — runs all tests in mock mode
   - `make test-live` — runs against real APIs
   - `make baseline` — saves golden baselines
   - `make compare MODEL=gpt-4o` — runs comparison against baseline

3. **GitHub Actions workflow** — the `agentci-template.yml` from Phase 1, configured for this example

4. **Mock fixtures** — complete YAML mocks for all 8 golden queries so `make test` runs in <2 seconds with zero API keys

### What you discover about AgentCI
- Is the end-to-end developer experience smooth? Clone → test → break → catch.
- Are the error messages clear enough for someone who didn't build this?
- Does GitHub Actions actually work with the mock system?

### Commit message
`feat(examples): step 7 — polished RAG example with README, makefile, CI workflow`

---

## Summary: What You Build vs. What You Discover

| Step | Agent Capability Added | Test Discovered | AgentCI Gap Found |
|------|----------------------|-----------------|-------------------|
| 0 | Project scaffold | — | — |
| 1 | Basic retrieve + generate | Tool call assertion, cost guard | Mock interception layer for LangGraph |
| 2 | Golden dataset | Parametrized content checks | Parametrized test output format |
| 3 | Mock system | Mock parity verification | YAML mock authoring UX |
| 4 | Document grading | Span capture, conditional path | Conditional edge tracing |
| 5 | Question rewriting | Loop detection, execution path assertion | Variable-length trace diffing |
| 6 | Full graph + baselines | Regression detection, model swap | Diff report format and output |
| 7 | Polish | — | End-to-end DX |

## Time Estimate

| Step | Time | Running Total |
|------|------|---------------|
| Step 0: Scaffold | 30 min | 30 min |
| Step 1: Minimal RAG | 1-2 hrs | 2.5 hrs |
| Step 2: Golden dataset | 1 hr | 3.5 hrs |
| Step 3: Mock system | 1-2 hrs | 5 hrs |
| Step 4: Grading | 1-2 hrs | 7 hrs |
| Step 5: Rewriting | 1-2 hrs | 9 hrs |
| Step 6: Full graph + baselines | 1-2 hrs | 11 hrs |
| Step 7: Polish | 2-3 hrs | 14 hrs |

**Total: ~3 days of focused work**

## What Happens After This

This one deep example replaces the need for five shallow ones. When you're done, you have:
- **13+ tests** that emerged organically from real development
- **A commit history** that IS the tutorial
- **3 intentional break scenarios** that demonstrate AgentCI's value
- **A regression report** that is the hero screenshot for your README
- **A list of AgentCI gaps** you discovered and fixed along the way

The other four agents (Text-to-SQL, routing, sales outreach, email triage) become 1-day tasks each because you now know exactly what patterns to test. You won't need to discover them — you'll just apply the patterns from this deep dive.