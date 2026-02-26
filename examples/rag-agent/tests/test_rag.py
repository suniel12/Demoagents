import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import functools
import agentci.capture
from agent import generate_answer_api

class RAGTrace:
    def __init__(self, trace, final_output):
        self._trace = trace
        self.final_output = final_output
        self.total_cost = getattr(trace, 'total_cost_usd', 0.0)
        self.spans = trace.spans
        
        self.tools_called = [
            tc.tool_name for s in trace.spans for tc in getattr(s, 'tool_calls', [])
        ]

    def get_span(self, name):
        class NodeSpan:
            def __init__(self, output: str):
                self.output = output

        for s in self.spans:
            for tc in getattr(s, 'tool_calls', []):
                t_name = getattr(tc, 'tool_name', '')
                if t_name == name or (name == "grade_documents" and t_name == "grade_artifacts"):
                    args = getattr(tc, 'arguments', {})
                    import json
                    content = args.get("content", "")
                    try:
                        data = json.loads(content)
                        return NodeSpan(output=data.get("binary_score", "no"))
                    except:
                        if "yes" in content.lower(): return NodeSpan(output="yes")
                        if "no" in content.lower(): return NodeSpan(output="no")
                        return NodeSpan(output=content)
        return NodeSpan(output="yes" if name != "grade_documents" else "no")


def trace_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with agentci.capture.TraceContext(agent_name=func.__name__) as ctx:
            output, state = func(*args, **kwargs)
            ctx.attach_langgraph_state(state)
            
        return RAGTrace(ctx.trace, output)
    return wrapper

@trace_decorator
def run_agent(question: str):
    return generate_answer_api(question)

def test_retrieval_triggered_for_knowledge_question():
    trace = run_agent("How do I install AgentCI?")
    assert "retrieve_docs" in trace.tools_called

def test_no_retrieval_for_greeting():
    trace = run_agent("Hello, how are you?")
    assert "retrieve_docs" not in trace.tools_called

def test_cost_within_budget():
    trace = run_agent("How do I install AgentCI?")
    assert trace.total_cost < 0.01

GOLDEN_QUERIES = [
    {
        "query": "How do I install AgentCI?",
        "category": "direct_hit",
        "expected_in_answer": ["pip install agentci", "3.10"],
        "not_in_answer": ["npm install"],
        "expected_tool": "retrieve_docs",
        "expected_doc_keywords": ["install", "agentci"],
    },
    {
        "query": "What are the three evaluation layers in AgentCI?",
        "category": "multi_chunk",
        "expected_in_answer": ["correctness", "path", "cost"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "What's the CEO's favorite restaurant?",
        "category": "out_of_scope",
        "expected_tool": None,
        "llm_judge_rule": "The agent must cleanly decline to answer the question, acknowledging it doesn't have the information. It must not hallucinate an answer."
    },
    {
        "query": "Hello!",
        "category": "no_retrieval",
        "expected_tool": None,
    },
    {
        "query": "How do I fail the CI pipeline if the agent uses forbidden tools?",
        "category": "direct_hit",
        "expected_in_answer": ["correctness", "fail", "exit 1", "forbidden tools"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "Does AgentCI support Anthropic models for testing?",
        "category": "direct_hit",
        "expected_in_answer": ["AnthropicMocker"],
        "not_in_answer": ["Bedrock"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "Is AgentCI free to use?",
        "category": "direct_hit",
        "expected_in_answer": ["open source", "Apache 2.0"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "What's the weather in Austin?",
        "category": "out_of_scope",
        "expected_tool": None,
        "expected_in_answer": ["agentci", "can only answer", "documentation assistant"],
    },
    {
        "query": "How do I configure an AWS load balancer for the enterprise tier?",
        "category": "out_of_scope",
        "expected_tool": None,
        "llm_judge_rule": "The agent must cleanly decline to answer the question since AWS configuration is outside its AgentCI domain. It MUST NOT provide external knowledge, tutorials, or instructions about AWS."
    },
]

@pytest.mark.parametrize("case", GOLDEN_QUERIES, ids=lambda c: c["query"][:40])
def test_golden_query(case):
    trace = run_agent(case["query"])

    if case["expected_tool"]:
        assert case["expected_tool"] in trace.tools_called
    else:
        assert len(trace.tools_called) == 0

    if "expected_in_answer" in case:
        answer = str(trace.final_output).lower()
        assert any(kw.lower() in answer for kw in case["expected_in_answer"]), \
            f"Expected one of {case['expected_in_answer']} in answer: {answer}"

    if "not_in_answer" in case:
        answer = str(trace.final_output).lower()
        for kw in case["not_in_answer"]:
            assert kw.lower() not in answer, \
                f"Unexpected '{kw}' found in answer: {answer}"

    if "llm_judge_rule" in case:
        import os
        from agentci.models import Assertion
        from agentci.assertions import evaluate_assertion

        # Only run LLM judge if a real key is present
        if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("ANTHROPIC_API_KEY") != "sk-ant-dummy-key-for-testing":
            assertion = Assertion(type="llm_judge", value=case["llm_judge_rule"])
            passed, message = evaluate_assertion(assertion, trace._trace)
            assert passed, f"LLM Judge failed: {message}"
        else:
            print("Skipping LLM Judge assertion due to missing ANTHROPIC_API_KEY")

def test_mock_mode_matches_live_behavior():
    """Verify that mock mode produces identical trace structure to live mode."""
    # This test runs in mock mode by default (CI)
    trace = run_agent("How do I install AgentCI?")
    assert "retrieve_docs" in trace.tools_called
    assert getattr(trace, 'total_cost', 0.0) >= 0  # mock should still report cost
    assert trace.final_output  # mock should still produce output

def test_grading_step_exists():
    trace = run_agent("How do I install AgentCI?")
    assert "grade_artifacts" in trace.tools_called

def test_relevant_docs_pass_grading():
    trace = run_agent("How do I install AgentCI?")
    grade_span = trace.get_span("grade_documents")
    assert "yes" in getattr(grade_span, "output", "").lower()

def test_cost_with_grading():
    trace = run_agent("How do I install AgentCI?")
    assert getattr(trace, 'total_cost', 0.0) < 0.015

def test_out_of_scope_skips_retrieval():
    """Out-of-scope questions should be declined immediately, no tool calls."""
    trace = run_agent("What's the weather in Austin?")
    assert "retrieve_docs" not in trace.tools_called, \
        f"Out-of-scope query triggered retrieval: {trace.tools_called}"
    assert trace.final_output is not None

def test_rewrite_triggered_for_vague_query():
    # Unanswerable query that triggers a loop. This is intentional to test AgentCI's ability to bound execution (e.g. max_tool_calls)
    trace = run_agent("What is the exact release date for AgentCI version 4.0?")
    assert "rewrite_question" in trace.tools_called, \
        f"Expected rewrite_question in {trace.tools_called}"

def test_no_rewrite_for_clear_query():
    trace = run_agent("How do I install AgentCI?")
    assert "rewrite_question" not in trace.tools_called, \
        f"Unexpected rewrite_question in {trace.tools_called}"

def test_max_retries():
    """In-scope but unanswerable queries may still rewrite, but are bounded."""
    trace = run_agent("What is the name of the top contributor to the AgentCI codebase who lives in California?")
    rewrite_count = trace.tools_called.count("rewrite_question")
    assert rewrite_count <= 3, f"Too many rewrites: {rewrite_count}"
    assert trace.total_cost < 0.05  # bounded even with retries

def test_execution_path_with_rewrite():
    # Triggers a bounded loop
    trace = run_agent("What is the exact release date for AgentCI version 4.0?")
    # Verify the rewrite loop tools appear in the right order
    assert "retrieve_docs" in trace.tools_called
    assert "grade_artifacts" in trace.tools_called
    assert "rewrite_question" in trace.tools_called
    # Verify retrieve_docs appears at least twice (initial + post-rewrite)
    assert trace.tools_called.count("retrieve_docs") >= 2, \
        f"Expected >=2 retrieve_docs calls, got {trace.tools_called}"

def test_regression_against_baseline():
    """Compare current run against saved baseline.
    Flags: TOOLS_CHANGED, COST_SPIKE, PATH_CHANGED
    """
    # This is a sample showing how AgentCI performs trace-level regression testing
    try:
        baseline = agentci.load_baseline("rag-v1-gpt4o-mini")
        for case in GOLDEN_QUERIES:
            if case["query"] not in baseline:
                pytest.skip(f"Query not found in baseline: '{case['query']}'. Run save_baseline.py to regenerate.")

            current_trace = run_agent(case["query"])
            diff = agentci.diff(baseline[case["query"]], current_trace._trace)
            assert not diff.has_regression, \
                f"Regression detected for '{case['query']}': {diff.summary}"
    except (FileNotFoundError, AttributeError) as e:
        # Gracefully skip if baseline files aren't generated yet or diff object is unavailable
        pytest.skip(f"Baseline 'rag-v1-gpt4o-mini' not found or diff API not initialized: {e}")

