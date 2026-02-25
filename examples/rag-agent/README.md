# AgentCI × RAG Agent Example

This is a complete, production-ready RAG agent example demonstrating how to use **AgentCI** for trace-level regression testing.

It implements the LangGraph Agentic RAG tutorial with a custom NovaCorp knowledge base and includes a comprehensive test suite that catches logic regressions, cost spikes, and tool-call failures.

## 60-second Quickstart

1. **Clone and setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set your OpenAI API key** (for live runs):
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

3. **Run the full test suite**:
   ```bash
   make test
   ```
   This runs 17 tests validating the execution path, loop behavior, tool calling, relevance grading, and regression baselines.

4. **Chat with the agent**:
   ```bash
   python chat.py
   ```

## Try the Iterative Development Features

### 1. The Prompt Break
Open `agent.py` and change the system prompt in `generate_answer` from:
> "You are a helpful assistant with access to a knowledge base."
to:
> "You are a helpful assistant who answers questions from your own knowledge."

Run `make test`. You will see assertions immediately catch that `retrieve_docs` was skipped!

### 2. The Model Swap Regression
First, save a golden baseline with the current model:
```bash
make baseline
```

Then run the regression demo to compare against the baseline:
```bash
python demo_regression.py
```

AgentCI's diff engine outputs a regression report showing cost spikes, tool changes, and path deviations.

### 3. Compare with a Different Model
```bash
make compare MODEL=gpt-4o
```

## Project Structure

- `knowledge_base/` — 10 curated markdown files for NovaCorp policies, products, support, and legal docs.
- `agent.py` — LangGraph workflow: retrieve → grade → rewrite → generate.
- `tests/test_rag.py` — 17 test cases covering direct hits, multi-chunk queries, out-of-scope handling, rewrite loops, cost guards, and regression baselines.
- `mocks/responses.yaml` — Pre-recorded LLM decisions and retrieval results for mock-mode testing.
- `golden/` — Saved baseline traces for regression comparison.
- `save_baseline.py` — Script to re-record golden baselines from live runs.
- `demo_regression.py` — Standalone demo of AgentCI's regression report.
- `chat.py` — Interactive CLI to chat with the NovaCorp agent.
