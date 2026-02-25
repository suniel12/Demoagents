"""
Tool call tests for the TechCorp Support Router.

Step 4: Verify specialists use their tools correctly:
  - Billing Agent calls lookup_invoice / check_plan when asked
  - Technical Agent calls check_system_status / lookup_error_code
  - Account Agent calls verify_identity for password resets
  - General Agent calls search_knowledge_base for product questions
  - Cross-agent isolation: billing tools should NOT appear in technical traces
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from support_router.run import run_agent


# ── Tool usage assertions ──────────────────────────────

def test_billing_calls_lookup_invoice():
    """When asked about invoices, Billing Agent should call lookup_invoice."""
    trace = run_agent("Can you check my invoices? My email is alice@example.com")
    assert trace is not None

    tool_names = trace.tool_call_sequence
    assert "lookup_invoice" in tool_names, (
        f"Expected 'lookup_invoice' in tool calls, got: {tool_names}"
    )


def test_billing_calls_check_plan():
    """When asked about plan details, Billing Agent should call check_plan."""
    trace = run_agent("When does my plan renew? My email is alice@example.com")
    assert trace is not None

    tool_names = trace.tool_call_sequence
    assert "check_plan" in tool_names, (
        f"Expected 'check_plan' in tool calls, got: {tool_names}"
    )


def test_technical_calls_lookup_error_code():
    """When given an error code, Technical Agent should look it up."""
    trace = run_agent("I'm getting error E-SYNC-003, what does it mean?")
    assert trace is not None

    tool_names = trace.tool_call_sequence
    assert "lookup_error_code" in tool_names, (
        f"Expected 'lookup_error_code' in tool calls, got: {tool_names}"
    )


def test_technical_calls_system_status():
    """When asked about outages, Technical Agent should check system status."""
    trace = run_agent("Is CloudSync down right now?")
    assert trace is not None

    tool_names = trace.tool_call_sequence
    assert "check_system_status" in tool_names, (
        f"Expected 'check_system_status' in tool calls, got: {tool_names}"
    )


def test_account_calls_verify_identity():
    """When asked to reset password, Account Agent should verify identity first."""
    trace = run_agent("I need to reset my password. My email is alice@example.com")
    assert trace is not None

    tool_names = trace.tool_call_sequence
    assert "verify_identity" in tool_names, (
        f"Expected 'verify_identity' in tool calls, got: {tool_names}"
    )


def test_general_calls_knowledge_base():
    """When asked product questions, General Agent should search the KB."""
    trace = run_agent("Do you have an API for CloudSync?")
    assert trace is not None

    tool_names = trace.tool_call_sequence
    assert "search_knowledge_base" in tool_names, (
        f"Expected 'search_knowledge_base' in tool calls, got: {tool_names}"
    )


# ── Cross-agent tool isolation ─────────────────────────

def test_billing_tools_not_used_for_technical():
    """Billing tools should not appear in Technical Agent traces."""
    trace = run_agent("CloudSync keeps crashing when I try to sync files")
    assert trace is not None

    billing_tools = {"lookup_invoice", "check_plan", "process_refund"}
    used_tools = set(trace.tool_call_sequence)
    overlap = billing_tools & used_tools
    assert not overlap, (
        f"Billing tools {overlap} should not be used for technical queries"
    )


def test_account_tools_not_used_for_billing():
    """Account tools should not appear in Billing Agent traces."""
    trace = run_agent("Can I get a refund for last month?")
    assert trace is not None

    account_tools = {"verify_identity", "reset_password", "toggle_2fa"}
    used_tools = set(trace.tool_call_sequence)
    overlap = account_tools & used_tools
    assert not overlap, (
        f"Account tools {overlap} should not be used for billing queries"
    )


# ── Malformed / garbled input resilience ───────────────

def test_garbled_error_code_still_routes_to_technical():
    """Garbled input with an error code should still route to Technical Agent."""
    trace = run_agent("error E-SYNC-003 jdfksdjf random garbage")
    assert trace is not None

    handoffs = trace.get_handoffs()
    assert len(handoffs) >= 1, "Expected at least 1 handoff"
    assert handoffs[-1].to_agent == "Technical Agent", (
        f"Expected Technical Agent, got {handoffs[-1].to_agent}"
    )

    # Should still call lookup_error_code despite the noise
    tool_names = trace.tool_call_sequence
    assert "lookup_error_code" in tool_names, (
        f"Expected 'lookup_error_code' even with noisy input, got: {tool_names}"
    )


def test_invalid_error_code_handled_gracefully():
    """A completely made-up error code should not crash — tool returns 'Unknown'."""
    trace = run_agent("I'm getting error ZZZZZ-999, help!")
    assert trace is not None

    # Should still route to technical
    handoffs = trace.get_handoffs()
    assert len(handoffs) >= 1, "Expected at least 1 handoff"
    assert handoffs[-1].to_agent == "Technical Agent", (
        f"Expected Technical Agent, got {handoffs[-1].to_agent}"
    )

