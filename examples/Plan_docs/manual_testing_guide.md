# AgentCI Demo Agents — Manual Testing Guide

> **Goal:** Interact with all three demo agents, observe their behavior, and see AgentCI v2 flag regressions, cost spikes, and hallucinations in real time.

---

## Environment Setup

All three agents live in `DemoAgents/examples/`. Each needs:

1. An `.env` file with your API key
2. Its own virtual environment (or the shared conda env)

```bash
# In each agent directory:
cp .env.example .env        # then fill in ANTHROPIC_API_KEY
```

| Agent | Directory | Start command | Port / mode |
|-------|-----------|---------------|-------------|
| RAG Agent | `examples/rag-agent/` | `python chat.py` | Interactive CLI |
| Support Router | `examples/support-router/` | `python chat.py` | Interactive CLI (async) |
| DevAgent | `examples/dev-agent/` | `python chat.py` | Interactive CLI (async) |

Each CLI prints tool calls and cost as you interact — that's your live AgentCI trace window.

---

## Part 1: RAG Agent (NovaCorp Q&A)

```bash
cd DemoAgents/examples/rag-agent
python chat.py
```

The CLI prints a `[Trajectory: ...]` line after every answer showing exactly which tools fired and in what order. Watch that line for every test below.

---

### Scenario R1 — Happy Path: In-Scope Question ✅

**Prompt:**
```
How do I install AgentCI?
```

**What you should see in Trajectory:**
```
[Trajectory: retriever_tool → grade_documents]
```

**Expected answer contains:** `pip install agentci`

**AgentCI v2 assertion this maps to:**
- `expected_in_answer: ["pip install"]` → deterministic pass/fail
- `expected_tools: [retriever_tool]`, `min_tool_recall: 1.0` → tool recall check
- `max_tool_calls: 5` → cost guard

**What a v1 regression looks like:** If you see `[Trajectory: retriever_tool → rewrite_question → retriever_tool]` with extra steps, the path layer warns. If `pip install` is missing from the answer, the correctness layer hard-fails.

---

### Scenario R2 — The Key Demo: Out-of-Scope Weather Query 🌤️

This is **the** before/after AgentCI story.

**Prompt:**
```
What's the weather in Tokyo?
```

**Expected Trajectory (v2-fixed):**
```
[Trajectory: Direct Answer]
```

**Expected answer:** A polite refusal — something like `"I can only answer questions about NovaCorp products and policies."`

**AgentCI v2 assertions:**
- `max_tool_calls: 0` — zero tools must fire (hard constraint)
- `forbidden_tools: [retriever_tool, tavily_search]` — escalates to **hard fail** if violated
- `not_in_answer: ["degrees", "forecast", "sunny", "rain"]`
- LLM judge: `"Agent politely declines"`, threshold 0.8

**How to trigger a v1 regression manually:**

1. Open `rag-agent/agent.py` and remove the out-of-scope check from the system prompt
2. Run the same prompt again
3. You'll likely see `[Trajectory: retriever_tool]` in the output — agent tried to search
4. Now run: `pytest tests/test_rag.py -v`
5. Watch it fail on `test_out_of_scope_query` — the `max_tool_calls: 0` assertion catches it

**v1 vs v2 comparison for this scenario:**

| | v1 (broken) | v2 (fixed) |
|---|---|---|
| Tool calls | 11 (retrieves repeatedly) | 0 |
| Cost | ~$0.008 | ~$0.0001 |
| Answer | Makes up weather data | Polite refusal |
| AgentCI | No spec — silent | Spec catches it with exit code 1 |

---

### Scenario R3 — Anti-Hallucination: AWS Question 🚫

**Prompt:**
```
How do I configure an AWS load balancer for the enterprise tier?
```

**Expected Trajectory:**
```
[Trajectory: Direct Answer]
```

**Expected answer:** Refusal. Must NOT contain: `ALB`, `target group`, `listener`, `health check`, `security group`

**AgentCI v2 assertions:**
- `not_in_answer: ["ALB", "target group", "listener", ...]` — hard fail if violated
- LLM judge: `"Agent does NOT provide AWS config steps from pre-trained knowledge"`, threshold 0.9

**What to break:** Change system prompt to allow answering outside scope. AgentCI's judge (threshold 0.9 — stricter than R2) catches the hallucination.

---

### Scenario R4 — Multi-Step Synthesis 🔗

**Prompt:**
```
Can I get a refund if I'm on the Enterprise plan, and who do I contact for support?
```

**Expected Trajectory:**
```
[Trajectory: retriever_tool → grade_documents → retriever_tool → grade_documents]
```

The agent should call `retriever_tool` twice — once for refund policy, once for contact info — then synthesize.

**Signs of regression:** Single tool call that returns partial answer, or answer missing either the refund terms or the support email.

---

### Scenario R5 — Ambiguous / Mixed Intent 🤔

**Prompt:**
```
Tell me about your pricing plans and also the weather
```

**Expected behavior:** Answer the pricing part, explicitly decline the weather part in the same response.

**Watch for:** Trajectory should show retriever\_tool fired for pricing, but no web search for weather.

---

## Part 2: Support Router (TechCorp Multi-Agent)

```bash
cd DemoAgents/examples/support-router
python chat.py
```

The CLI prints a structured `AgentCI Trace Summary` after every message showing: **Agents → Handoffs → Tokens → Cost**. Type `trace` after any interaction to see the full span tree.

---

### Scenario S1 — Clear Billing Intent ✅

**Prompt:**
```
I was charged twice on my credit card this month
```

**Expected trace summary:**
```
│  Agents:     triage_agent → billing_agent
│  Handoff:    triage_agent → billing_agent
│  Tokens:     ~300-500
│  Cost:       $0.00xx
```

**AgentCI v2 assertions:**
- `expected_handoff: "billing_agent"` — layer 2 check
- `max_handoff_count: 1` — direct routing, no bouncing
- LLM judge: `"Routes billing complaint to billing_agent"`, threshold 0.8

**Verify with:** `agentci validate agentci_spec.yaml` after confirming trace matches spec.

---

### Scenario S2 — Clear Technical Intent 🔧

**Prompt:**
```
My app keeps crashing on iOS 17 when I try to upload a photo
```

**Expected trace:**
```
│  Agents:     triage_agent → technical_agent
│  Handoff:    triage_agent → technical_agent
```

Try a variation:
```
The sync feature is completely broken, I'm getting error code 5001
```
Same expected routing: → `technical_agent`.

**AgentCI v2 assertion:** `expected_handoff: "technical_agent"`, `max_handoff_count: 1`

---

### Scenario S3 — Ambiguous Multi-Intent 🎯

**Prompt:**
```
I'm on the Pro plan but I think the price is wrong and it keeps crashing
```

The agent sees two issues: billing and technical. It must pick one.

**Expected trace:**
```
│  Agents:     triage_agent → billing_agent
│  Handoff:    triage_agent → billing_agent
```

Billing takes priority (per spec description). Max 2 handoffs allowed here.

**AgentCI v2 assertions:**
- `expected_handoff: "billing_agent"` — primary intent wins
- `max_handoff_count: 2` — allows triage to briefly consult before routing

**What failure looks like:** If you see `→ technical_agent` instead, the path layer emits a warning annotation. If handoff count > 2, it also warns.

---

### Scenario S4 — Off-Topic Guardrail 🛑

**Prompt:**
```
Write me a Python script to scrape Twitter
```

**Expected trace:**
```
│  Agents:     triage_agent
│  Handoff:    ⚠️  NONE (triage answered directly)
│  Guardrails: 🚨 off_topic
```

No handoff to any specialist. The triage agent declines directly.

**AgentCI v2 assertions:**
- LLM judge: `"Agent declines off-topic requests"`, threshold 0.9
- `max_handoff_count: 0`

---

### Scenario S5 — Edge Case: Single Word 💬

**Prompt:**
```
billing
```

**Expected behavior:** Triage asks for clarification before routing, or routes conservatively to billing. Should NOT route to technical.

**Then try:**
```
help
```
This should also request clarification, not blindly route.

**Variation to test:**
```
Hi
```
Expected: Friendly greeting, no handoff, stays in triage.

---

### How to Use the `trace` Command

After any interaction, type:
```
trace
```
You'll see the full span tree, e.g.:
```
📋 Full Trace Detail:
   Trace ID:  abc123
   Spans (4):
     [0] agent        name=triage_agent
     [1] handoff      name=route_to_billing
         handoff: triage_agent → billing_agent
         tool: transfer_to_billing({'reason': 'billing dispute'})
     [2] agent        name=billing_agent
     [3] llm          model=claude-sonnet tokens=180+95
```

This is the raw AgentCI trace. The `expected_handoff` assertion in the spec matches against span `[1]`.

---

## Part 3: DevAgent (GitHub Repository Analyzer)

```bash
cd DemoAgents/examples/dev-agent
python chat.py
```

The CLI prints a full trace result after each URL: tools called, duration, tokens, cost, and the final markdown report. This agent does real GitHub API calls — results vary with real repos.

---

### Scenario D1 — Happy Path: Well-Maintained Repo ✅

**Prompt:**
```
https://github.com/tiangolo/fastapi
```

**Expected tool sequence:**
```
Tools called: ['github_fetch_metadata', 'github_list_dir', 'github_read_file', ...]
Total Tools Used: 6-10
```

**Expected report sections:** README quality, license type, CI/CD pipeline detected, dependency health, community health.

**AgentCI v2 assertions (`agentci_spec.yaml` query 1):**
- LLM judge: `"Covers at least 3 of: README, license, CI/CD, dependencies, security"`, threshold 0.7
- `min_tool_recall: 0.8` — must use ≥80% of `expected_tools`
- `max_tool_calls: 12`

**Watch for:** Does the agent read `.github/workflows/`? That's the conditional tool logic. A regression here means the agent analyzed CI but didn't call `github_list_dir`.

---

### Scenario D2 — Sparse / Minimal Repo 📂

**Prompt:**
```
https://github.com/example/minimal-repo
```
*(Or any repo you know has no README, no CI, no license)*

**Expected tool sequence:** Fewer calls — agent should stop early once it finds nothing.

**Expected report:** Explicitly says "No README found", "No CI configuration detected" — should NOT fabricate or say "CI status unknown (likely configured)".

**AgentCI v2 assertion:**
- LLM judge: `"Report explicitly mentions missing README or CI as gaps, rather than fabricating"`, threshold 0.75

**How to spot hallucination:** If the report says "GitHub Actions is not configured" without calling `github_list_dir` to check, that's a hallucination path. The tool recall check (`min_tool_recall`) flags it.

---

### Scenario D3 — Anti-Hallucination: No CI Repo 🚫

**Prompt:**
```
https://github.com/example/no-ci-repo
```
*(Or a real repo with no `.github/workflows/` directory)*

**Expected answer must NOT contain:**
- `"GitHub Actions configured"`
- `"CI pipeline found"`
- `"automated tests detected"`

**AgentCI v2 assertion:**
- `not_in_answer: ["GitHub Actions configured", "CI pipeline found"]` — hard fail if violated
- LLM judge threshold 0.8

**How to spot it live:** If the report confidently describes CI/CD without the agent having called `github_list_dir` — that's a hallucination. Cross-check with `Tools called:` in the CLI output.

---

### Scenario D4 — Cost Guard: Loop Detection 🔁

**Prompt:**
```
https://github.com/psf/requests
```

**Watch for loops:** The requests library has many files. An unguarded agent can call `github_read_file` 10+ times redundantly.

**Expected:**
```
Total Tools Used: ≤15
```

**AgentCI v2 assertion:**
- `max_loops: 2` — no tool should be called more than twice in a row
- `max_total_tokens: 20000`
- `max_cost_usd: 0.08`

**How to trigger a regression:** In the agent's system prompt, remove any instruction about avoiding repeated file reads. Run the same query. Watch token count spike. AgentCI flags it as a cost warning.

---

### Scenario D5 — 404 / Non-Existent Repo 🛑

**Prompt:**
```
https://github.com/this-repo-definitely-does-not-exist-99283
```

**Expected:**
```
Tools called: ['github_fetch_metadata']
Total Tools Used: 1
```

Agent should recognize the 404 and gracefully reply: `"I couldn't find that repository. Please verify the URL is correct and the repository is public."`

**What not to see:** Agent retrying the same failed call 3 times (loop), or trying to fabricate a report for a nonexistent repo.

---

## Comparing v1 vs v2 Behavior — Scoreboard

| Scenario | v1 Behavior | v2 Behavior | What AgentCI Catches |
|----------|-------------|-------------|----------------------|
| RAG: weather query | 11 tool calls, hallucinated answer | 0 tool calls, polite decline | `max_tool_calls: 0` hard fail |
| RAG: AWS hallucination | Provides fake AWS steps | Declines | `not_in_answer` + judge (0.9) |
| Router: ambiguous query | Routes to wrong agent | Picks primary intent | `expected_handoff` path check |
| Router: off-topic | Sometimes routes to a specialist | Triage declines directly | `max_handoff_count: 0` |
| DevAgent: sparse repo | Fabricates "no CI available" | Explicitly notes gaps | LLM judge threshold 0.75 |
| DevAgent: loop on big repo | 25+ `read_file` calls | ≤15 tools | `max_loops: 2`, `max_cost_usd` |

---

## Running the AgentCI Test Suite After Manual Testing

After experimenting manually, run the automated test suite to confirm everything passes:

```bash
# RAG Agent
cd DemoAgents/examples/rag-agent
pytest tests/test_rag.py -v

# Support Router
cd DemoAgents/examples/support-router
pytest tests/ -v

# DevAgent
cd DemoAgents/examples/dev-agent
pytest tests/ -v -m "not live"
```

### Validate specs

```bash
agentci validate agentci_spec.yaml
```

All three should:
```
✅ Valid: N queries, agent='<agent-name>'
```

---

## How to Intentionally Break an Agent (and See AgentCI Flag It)

### Break the RAG Agent

1. Open `rag-agent/agent.py`
2. Remove out-of-scope checking from the system prompt
3. Ask: `What's the weather in Tokyo?`
4. Observe: trajectory shows `retriever_tool` fires
5. Run: `pytest tests/test_rag.py -v`
6. Watch `test_out_of_scope_query` **fail** with:
   ```
   AssertionError: max_tool_calls violated: expected ≤0, got 2
   ```

### Break the Support Router

1. Open `support_router/agents/triage.py`
2. Change routing logic to always route to `technical_agent` regardless of intent
3. Ask: `I was charged twice this month`
4. Observe: routes to `technical_agent` instead of `billing_agent`
5. Run: `pytest tests/ -v`
6. AgentCI flags: `expected_handoff: billing_agent — got: technical_agent → WARNING`

### Break the DevAgent

1. Open `devagent/agent/core.py`
2. Change the grade scale from `"Grade A through F"` to `"Grade 1 through 10"` in the system prompt
3. Analyze any repo
4. Run: `pytest tests/ -m "not live" -v`
5. Watch deterministic string assertions fail:
   ```
   AssertionError: "Grade A" not in answer
   ```

---

## Reading the AgentCI Output

### Console format (local)

```
┌─────────────────────────────────────────────────────┐
│  Query: "What's the weather in Tokyo?"              │
├── Layer 1: Correctness  ──────────────── ✅ PASS    │
│   [PASS] not_in_answer: no weather terms found      │
│   [PASS] llm_judge: polite refusal (score: 4/5)     │
├── Layer 2: Path  ─────────────────────── ✅ PASS    │
│   [PASS] max_tool_calls: 0 used / 0 allowed         │
├── Layer 3: Cost  ─────────────────────── ✅ PASS    │
│   [PASS] tokens: 180 / 500 max                      │
└─────────────────────────────────────────────────────┘
Exit code: 0
```

### GitHub Actions format

When you push to your repo with the `.github/workflows/agentci.yml` configured:
- ✅ **Correctness failures** appear as `::error` annotations on the PR "Files Changed" tab
- ⚠️ **Path/Cost warnings** appear as `::warning` annotations — they don't block merge

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | All correctness checks pass |
| `1` | One or more correctness failures |
| `2` | Infrastructure / runtime error |
