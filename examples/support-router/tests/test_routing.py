"""
Routing correctness tests for the TechCorp Support Router.

Step 3 Golden Dataset: 20 queries covering 4 agents:
  - Clear billing (3)
  - Clear technical (3)
  - Clear account (3)
  - Clear general (3)
  - Ambiguous / multi-intent (4)
  - Edge cases (4)
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

    # ═══ Clear Technical (expect → Technical Agent) ═══
    {
        "query": "CloudSync keeps crashing when I try to sync files",
        "category": "clear_technical",
        "expected_agent": "Technical Agent",
    },
    {
        "query": "I'm getting error code E-SYNC-003 on every upload",
        "category": "clear_technical",
        "expected_agent": "Technical Agent",
    },
    {
        "query": "Is the CloudSync service down right now?",
        "category": "clear_technical",
        "expected_agent": "Technical Agent",
    },

    # ═══ Clear Account (expect → Account Agent) ═══
    {
        "query": "I forgot my password and need to reset it",
        "category": "clear_account",
        "expected_agent": "Account Agent",
    },
    {
        "query": "How do I enable two-factor authentication?",
        "category": "clear_account",
        "expected_agent": "Account Agent",
    },
    {
        "query": "I want to cancel my account",
        "category": "clear_account",
        "expected_agent": "Account Agent",
    },

    # ═══ Clear General (expect → General Agent) ═══
    {
        "query": "What features does CloudSync Pro include?",
        "category": "clear_general",
        "expected_agent": "General Agent",
    },
    {
        "query": "Do you have a mobile app?",
        "category": "clear_general",
        "expected_agent": "General Agent",
    },
    {
        "query": "I love CloudSync! Can you add dark mode?",
        "category": "clear_general",
        "expected_agent": "General Agent",
    },

    # ═══ Ambiguous / Multi-intent ═══
    {
        "query": "I'm on the Pro plan but I think the price is wrong and it keeps crashing",
        "category": "ambiguous",
        "expected_agent": "Billing Agent",
        "notes": "Price concern is the primary intent",
    },
    {
        "query": "What's the difference between Pro and Business?",
        "category": "ambiguous",
        "expected_agent": "General Agent",
        "notes": "Feature comparison → General",
    },
    {
        "query": "My sync isn't working and I want to cancel",
        "category": "ambiguous",
        "expected_agent": "Technical Agent",
        "notes": "Technical issue is the immediate problem to solve first",
    },
    {
        "query": "I can't log in to change my billing info",
        "category": "ambiguous",
        "expected_agent": "Account Agent",
        "notes": "Login issue is the blocking problem to solve first",
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
    },
    {
        "query": "password",
        "category": "edge_single_word",
        "expected_agent": "Account Agent",
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


def test_all_four_agents_reachable():
    """Verify each specialist can be reached with a clear query."""
    queries = {
        "Billing Agent": "I was double-charged",
        "Technical Agent": "My sync is broken",
        "Account Agent": "Reset my password",
        "General Agent": "What plans do you offer?",
    }
    for expected, query in queries.items():
        trace = run_agent(query)
        handoffs = trace.get_handoffs()
        assert len(handoffs) >= 1, f"No handoff for '{query}'"
        actual = handoffs[-1].to_agent
        assert actual == expected, (
            f"'{query}' routed to '{actual}', expected '{expected}'"
        )


# ── Cost guard ─────────────────────────────────────────

def test_routing_cost_under_budget():
    """A simple route (triage → specialist) should cost under $0.01."""
    trace = run_agent("I was charged twice")
    assert trace.total_cost_usd < 0.01, (
        f"Routing cost ${trace.total_cost_usd:.4f} exceeds $0.01 budget"
    )
