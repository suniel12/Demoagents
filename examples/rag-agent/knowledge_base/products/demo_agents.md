# AgentCI Demo Agents

AgentCI ships with three demo agents that showcase different architectures and testing patterns. All three run with zero API keys using the mock system.

## RAG Agent (LangGraph)

**Directory:** `DemoAgents/examples/rag-agent/`
**Framework:** LangGraph / LangChain
**Architecture:** Retrieval → Grade → Rewrite/Generate pipeline

The RAG agent answers questions about product documentation. It:
1. Receives a question from the user
2. Retrieves relevant documents from a knowledge base using vector search
3. Grades the retrieved documents for relevance
4. If documents are irrelevant, rewrites the question and retries
5. Generates an answer grounded only in the retrieved context

**Key test scenarios:**
- In-scope questions (must retrieve and answer correctly)
- Out-of-scope questions (must decline politely with zero tool calls)
- Anti-hallucination (must not fabricate answers from pre-trained knowledge)
- Cost efficiency (must not loop excessively on retrieval)

**AgentCI spec:** 3 queries covering installation (happy path), weather (out-of-scope), and AWS (hallucination bait).

## Support Router (OpenAI Agents SDK)

**Directory:** `DemoAgents/examples/support-router/`
**Framework:** OpenAI Agents SDK
**Architecture:** Triage → Specialist multi-agent handoff with guardrails

The Support Router receives customer queries and routes them to the right specialist agent:
- **Billing Agent** — handles payment, invoicing, pricing questions
- **Technical Agent** — handles bugs, crashes, error codes
- **Account Agent** — handles login issues, password resets, account changes
- **General Agent** — handles feature comparisons, general inquiries

**Key test scenarios:**
- Clear single-intent routing (billing → billing agent, tech → tech agent)
- Ambiguous multi-intent resolution (billing + tech → billing wins)
- Off-topic guardrails (coding requests → triage declines directly)
- Edge cases (single-word inputs, greetings, closings)

**AgentCI spec:** 20 queries covering all routing categories, ambiguous intents, edge cases, and off-topic guardrails.

## DevAgent (Anthropic SDK)

**Directory:** `DemoAgents/examples/dev-agent/`
**Framework:** Anthropic (raw SDK)
**Architecture:** Sequential 8-tool GitHub repository analyzer

The DevAgent analyzes public GitHub repositories by:
1. Fetching repository metadata (stars, forks, description, license)
2. Listing directory structure
3. Reading key files (README, CI config, package files)
4. Producing a structured health report with composite scoring (A-F grade)

**Key test scenarios:**
- Happy path (well-maintained repo like FastAPI — full analysis)
- Sparse repo (minimal repo — must note missing files, not fabricate)
- Anti-hallucination (no CI repo — must not claim CI exists)
- Cost guard (loop detection on large repos)

**AgentCI spec:** 4 queries with tool recall, anti-hallucination, and cost budget assertions.

## Running Demo Agent Tests

```bash
# All three agents
cd DemoAgents
make test

# Individual agents
cd examples/rag-agent && pytest tests/ -v
cd examples/support-router && pytest tests/ -v
cd examples/dev-agent && pytest tests/ -v -m "not live"
```

All tests run in under 2 seconds with zero API keys required (using the mock system).
