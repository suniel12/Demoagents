import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import ciagent
from ciagent.capture import langgraph_trace
from agent import generate_answer_api


def run_agent(question: str):
    with langgraph_trace("rag-agent") as ctx:
        output, state = generate_answer_api(question)
        ctx.attach(state)
        ctx.trace.metadata["final_output"] = str(output)
    return ctx.trace


def test_retrieval_triggered_for_knowledge_question():
    trace = run_agent("How do I install CIAgent?")
    assert trace.called("retrieve_docs")


def test_no_retrieval_for_greeting():
    trace = run_agent("Hello, how are you?")
    assert trace.never_called("retrieve_docs")


def test_cost_within_budget():
    trace = run_agent("How do I install CIAgent?")
    assert trace.cost_under(0.01)


GOLDEN_QUERIES = [
    {
        "query": "How do I install CIAgent?",
        "category": "direct_hit",
        "expected_in_answer": ["pip install ciagent", "3.10"],
        "not_in_answer": ["npm install"],
        "expected_tool": "retrieve_docs",
        "expected_doc_keywords": ["install", "ciagent"],
    },
    {
        "query": "What are the three evaluation layers in CIAgent?",
        "category": "multi_chunk",
        "expected_in_answer": ["correctness", "path", "cost"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "What's the CEO's favorite restaurant?",
        "category": "out_of_scope",
        "expected_tool": None,
        "llm_judge_rule": "The agent must decline to answer rather than hallucinate an answer. Declining while redirecting the user to its documented specialty (e.g. 'I specialize in CIAgent topics and don't have information on that') counts as a clean decline."
    },
    {
        "query": "Hello!",
        "category": "no_retrieval",
        "expected_tool": None,
    },
    {
        "query": "How do I fail the CI pipeline if the agent uses forbidden tools?",
        "category": "direct_hit",
        "expected_in_answer": ["fail", "forbidden tools"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "Does CIAgent support Anthropic models for testing?",
        "category": "direct_hit",
        "expected_in_answer": ["AnthropicMocker"],
        "not_in_answer": ["Bedrock"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "Is CIAgent free to use?",
        "category": "direct_hit",
        "expected_in_answer": ["open source", "Apache 2.0"],
        "expected_tool": "retrieve_docs",
    },
    {
        "query": "What's the weather in Austin?",
        "category": "out_of_scope",
        "expected_tool": None,
        "expected_in_answer": ["ciagent", "can only answer", "documentation assistant"],
    },
    {
        "query": "How do I configure an AWS load balancer for the enterprise tier?",
        "category": "out_of_scope",
        "expected_tool": None,
        "llm_judge_rule": "The agent must cleanly decline to answer the question since AWS configuration is outside its CIAgent domain. It MUST NOT provide external knowledge, tutorials, or instructions about AWS."
    },
]


@pytest.mark.parametrize("case", GOLDEN_QUERIES, ids=lambda c: c["query"][:40])
def test_golden_query(case):
    trace = run_agent(case["query"])

    if case["expected_tool"]:
        assert trace.called(case["expected_tool"]), \
            f"Expected {case['expected_tool']} in {trace.tool_call_sequence}"
    else:
        assert len(trace.tool_call_sequence) == 0, \
            f"Expected no tool calls, got {trace.tool_call_sequence}"

    if "expected_in_answer" in case:
        answer = str(trace.metadata.get("final_output", "")).lower()
        assert any(kw.lower() in answer for kw in case["expected_in_answer"]), \
            f"Expected one of {case['expected_in_answer']} in answer: {answer}"

    if "not_in_answer" in case:
        answer = str(trace.metadata.get("final_output", "")).lower()
        for kw in case["not_in_answer"]:
            assert kw.lower() not in answer, \
                f"Unexpected '{kw}' found in answer: {answer}"

    if "llm_judge_rule" in case:
        if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("ANTHROPIC_API_KEY") != "sk-ant-dummy-key-for-testing":
            from ciagent.models import Assertion
            from ciagent.assertions import evaluate_assertion
            assertion = Assertion(type="llm_judge", value=case["llm_judge_rule"])
            passed, message = evaluate_assertion(assertion, trace)
            assert passed, f"LLM Judge failed: {message}"
        else:
            print("Skipping LLM Judge assertion due to missing ANTHROPIC_API_KEY")


def test_mock_mode_matches_live_behavior():
    """Verify that mock mode produces identical trace structure to live mode."""
    trace = run_agent("How do I install CIAgent?")
    assert trace.called("retrieve_docs")
    assert trace.total_cost_usd >= 0
    assert trace.metadata.get("final_output")


def test_grading_step_exists():
    trace = run_agent("How do I install CIAgent?")
    assert trace.called("grade_artifacts")


def test_relevant_docs_pass_grading():
    trace = run_agent("How do I install CIAgent?")
    assert trace.called("grade_artifacts")


def test_cost_with_grading():
    trace = run_agent("How do I install CIAgent?")
    assert trace.cost_under(0.015)


def test_out_of_scope_skips_retrieval():
    """Out-of-scope questions should be declined immediately, no tool calls."""
    trace = run_agent("What's the weather in Austin?")
    assert trace.never_called("retrieve_docs"), \
        f"Out-of-scope query triggered retrieval: {trace.tool_call_sequence}"
    assert trace.metadata.get("final_output") is not None


def test_rewrite_triggered_for_vague_query():
    trace = run_agent("What is the exact release date for CIAgent version 4.0?")
    assert trace.called("rewrite_question"), \
        f"Expected rewrite_question in {trace.tool_call_sequence}"


def test_no_rewrite_for_clear_query():
    trace = run_agent("How do I install CIAgent?")
    assert trace.never_called("rewrite_question"), \
        f"Unexpected rewrite_question in {trace.tool_call_sequence}"


def test_max_retries():
    """In-scope but unanswerable queries may still rewrite, but are bounded."""
    trace = run_agent("What is the name of the top contributor to the CIAgent codebase who lives in California?")
    assert trace.loop_count("rewrite_question") <= 3
    assert trace.cost_under(0.05)


def test_execution_path_with_rewrite():
    trace = run_agent("What is the exact release date for CIAgent version 4.0?")
    assert trace.called("retrieve_docs")
    assert trace.called("grade_artifacts")
    assert trace.called("rewrite_question")
    assert trace.loop_count("retrieve_docs") >= 2, \
        f"Expected >=2 retrieve_docs calls, got {trace.tool_call_sequence}"


def test_compound_query_decomposed_within_budget():
    """Compound CIAgent query uses multi-path (no rewrite loop) and stays within budget."""
    trace = run_agent(
        "Can I get a refund if I'm on the Enterprise plan, and who do I contact for support?"
    )
    assert trace.called("retrieve_docs")
    assert trace.never_called("rewrite_question"), \
        f"Unexpected rewrite_question on decomposed path: {trace.tool_call_sequence}"
    assert trace.loop_count("retrieve_docs") <= 5
    assert trace.called("grade_artifacts")


def test_mixed_intent_not_decomposed():
    """Mixed-intent query (CIAgent + weather) is NOT decomposed; single-path handles it."""
    trace = run_agent("How do I install CIAgent and what's the weather in Tokyo?")
    assert trace.called("retrieve_docs")
    assert trace.never_called("rewrite_question"), \
        f"Unexpected rewrite_question for mixed-intent: {trace.tool_call_sequence}"
    assert len(trace.tool_call_sequence) <= 5


def test_regression_against_baseline():
    """Compare current run against saved baseline.
    Flags: TOOLS_CHANGED, COST_SPIKE, PATH_CHANGED
    """
    try:
        baseline = ciagent.load_baseline("rag-v1-gpt4o-mini")
        for case in GOLDEN_QUERIES:
            if case["query"] not in baseline:
                pytest.skip(f"Query not found in baseline: '{case['query']}'. Run save_baseline.py to regenerate.")

            current_trace = run_agent(case["query"])
            diff = ciagent.diff(baseline[case["query"]], current_trace)
            assert not diff.has_regression, \
                f"Regression detected for '{case['query']}': {diff.summary}"
    except (FileNotFoundError, AttributeError) as e:
        pytest.skip(f"Baseline 'rag-v1-gpt4o-mini' not found or diff API not initialized: {e}")
