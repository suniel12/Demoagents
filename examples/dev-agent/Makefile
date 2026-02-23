.PHONY: help test test-unit test-agent test-all run clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─────────────────────────────────────────
# Testing
# ─────────────────────────────────────────

test-unit: ## Run unit tests (no LLM, instant)
	pytest tests/test_url_parser.py -v

test-tools: ## Run tool call tests (mocked, needs LLM)
	pytest tests/test_tool_calls.py -v --tb=long

test-quality: ## Run output quality tests
	pytest tests/test_output_quality.py -v --tb=long

test-guardrails: ## Run guardrail tests
	pytest tests/test_guardrails.py -v --tb=long

test-errors: ## Run error handling tests
	pytest tests/test_error_handling.py -v --tb=long

test-golden: ## Run golden trace tests
	pytest tests/test_golden_traces.py -v --tb=long

test-agent: ## Run all agent tests (mocked, needs LLM)
	pytest tests/ -v --tb=long --ignore=tests/test_url_parser.py

test: test-unit test-agent ## Run all tests

# ─────────────────────────────────────────
# Running
# ─────────────────────────────────────────

run: ## Run agent on a repo. Usage: make run REPO=langchain-ai/langchain
	python -m devagent.agent.run "https://github.com/$(REPO)"

run-example: ## Run agent on langchain (default example)
	python -m devagent.agent.run "https://github.com/langchain-ai/langchain"

# ─────────────────────────────────────────
# Maintenance
# ─────────────────────────────────────────

clean: ## Remove generated files
	rm -rf traces/ __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

record-golden: ## Record a new golden trace for the healthy repo
	python -c "import asyncio; from devagent.agent.core import DevAgent; from tests.fixtures import save_golden_trace, REPO_HEALTHY; \
		trace = asyncio.run(DevAgent().analyze(REPO_HEALTHY['url'])); \
		save_golden_trace('phase0_healthy_repo', trace.to_dict()); \
		print(f'Saved golden trace: {trace.tool_call_count} tool calls, {trace.total_tokens} tokens')"
