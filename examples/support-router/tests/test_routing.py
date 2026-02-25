"""
Routing correctness tests for the TechCorp Support Router.

Step 2 Golden Dataset: 12 queries covering:
  - Clear billing (3)
  - Clear general (3)
  - Ambiguous / multi-intent (3)
  - Edge cases (3)

Each query is parametrized and asserts:
  1. At least 1 handoff occurred
  2. The final handoff target matches the expected agent
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from support_router.run import run_agent


# ── Golden Queries ─────────────────────────────────────

GOLDEN_QUERIES = [
    # ═══ Clear Billing (expect → Billing Agent) ═══
    {
        "query": "I was charged twice for my CloudSync Pro subscription",
        "category": "clear_billing",
        "expected_agent": "Billing Agent",
    },
    {
        "query": "Can I get a refund for last month?",
        "category": "clear_billing",
        "expected_agent": "Billing Agent",
    },
    {
        "query": "I want to upgrade from Pro to Business plan",
        "category": "clear_billing",
        "expected_agent": "Billing Agent",
    },

    # ═══ Clear General (expect → General Agent) ═══
    {
        "query": "What features does CloudSync Pro include?",
        "category": "clear_general",
        "expected_agent": "General Agent",
    },
    {
        "query": "Is there an API for CloudSync?",
        "category": "clear_general",
        "expected_agent": "General Agent",
    },
    {
        "query": "Do you have a mobile app?",
        "category": "clear_general",
        "expected_agent": "General Agent",
    },

    # ═══ Ambiguous / Multi-intent ═══
    {
        "query": "I'm on the Pro plan but I think the price is wrong and I want to know what Business includes",
        "category": "ambiguous",
        "expected_agent": "Billing Agent",
        "notes": "Price concern is the primary intent even though they ask about Business features",
    },
    {
        "query": "What's the difference between Pro and Business? I might upgrade",
        "category": "ambiguous",
        "expected_agent": "General Agent",
        "notes": "Feature comparison is the primary intent; 'might upgrade' is secondary",
    },
    {
        "query": "I love CloudSync! Can you add dark mode?",
        "category": "ambiguous",
        "expected_agent": "General Agent",
        "notes": "Feature request → General",
    },

    # ═══ Edge Cases ═══
    {
        "query": "Hello",
        "category": "edge_greeting",
        "expected_agent": "General Agent",
    },
    {
        "query": "Thanks, that's all I needed",
        "category": "edge_closing",
        "expected_agent": "General Agent",
    },
    {
        "query": "invoice",
        "category": "edge_single_word",
        "expected_agent": "Billing Agent",
        "notes": "Single word should still trigger correct routing",
    },
]


# ── Parametrized routing tests ─────────────────────────

@pytest.mark.parametrize(
    "case",
    GOLDEN_QUERIES,
    ids=lambda c: f"{c['category']}:{c['query'][:40]}",
)
def test_routing_correctness(case):
    """Each query should route to the expected specialist agent."""
    trace = run_agent(case["query"])
    assert trace is not None, "Trace was not captured"

    handoffs = trace.get_handoffs()
    assert len(handoffs) >= 1, (
        f"Expected at least 1 handoff, got {len(handoffs)} "
        f"for query: '{case['query']}'"
    )

    actual_agent = handoffs[-1].to_agent
    expected_agent = case["expected_agent"]
    assert actual_agent == expected_agent, (
        f"Expected route to '{expected_agent}', got '{actual_agent}' "
        f"for query: '{case['query']}'"
    )


# ── Structural assertions ──────────────────────────────

def test_single_handoff_per_query():
    """Triage should route exactly once, not bounce between agents."""
    trace = run_agent("I was charged twice for my subscription")
    handoffs = trace.get_handoffs()
    assert len(handoffs) == 1, (
        f"Expected 1 handoff, got {len(handoffs)}: "
        f"{[(h.from_agent, h.to_agent) for h in handoffs]}"
    )


def test_triage_does_not_answer_directly():
    """Triage agent should never be the final agent — it should always hand off."""
    trace = run_agent("What is your refund policy?")
    agents = trace.agents_involved
    assert len(agents) >= 2, (
        f"Expected at least 2 agents (triage + specialist), got {agents}"
    )


# ── Cost guard ─────────────────────────────────────────

def test_routing_cost_under_budget():
    """A simple route (triage → specialist) should cost under $0.01."""
    trace = run_agent("I was charged twice")
    assert trace.total_cost_usd < 0.01, (
        f"Routing cost ${trace.total_cost_usd:.4f} exceeds $0.01 budget"
    )
