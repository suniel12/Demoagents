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

2. **Run the test suite (Zero API keys needed!)**:
   ```bash
   make test
   ```
   This runs 13+ tests using the included mock system, validating the execution path, loop behavior, tool calling, and relevance grading.

## Try the Iterative Development Features

### 1. The Prompt Break
Open `agent.py` and change the system prompt in `generate_answer` from:
> "You are a helpful assistant with access to a knowledge base."
to:
> "You are a helpful assistant who answers questions from your own knowledge."

Run `make test`. You will see assertions immediately catch that `retrieve_docs` was skipped!

### 2. The Model Swap Regression
Run the full regression test suite to compare execution paths and costs against the golden baseline.
```bash
# Compare the current codebase against the gpt4o-mini baseline
make compare MODEL=gpt-4o
```
AgentCI's diff engine will output a beautifully formatted regression report showing you cost spikes and changes in agent reasoning paths.

## Project Structure

- `knowledge_base/` — The 10 curated markdown files for NovaCorp's policies and products.
- `agent.py` — The LangGraph workflow logic and prompts.
- `tests/test_rag.py` — 13 traces evaluating behavior across direct hits, multi-chunk queries, and out-of-scope interactions.
- `mocks/responses.yaml` — Pre-recorded agent tool calls and LLM decisions enabling mock-mode testing.
- `golden_traces/` — Check-in baseline snapshots formatted as JSON.
