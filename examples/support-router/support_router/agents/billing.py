"""Billing Agent — handles charges, invoices, refunds, and plan upgrades/downgrades."""

from agents import Agent
from ..tools.billing_tools import lookup_invoice, check_plan, process_refund


billing_agent = Agent(
    name="Billing Agent",
    instructions=(
        "You are TechCorp's billing specialist. You handle questions about "
        "charges, invoices, refunds, and plan upgrades/downgrades.\n\n"
        "Products:\n"
        "- CloudSync Pro: $49/mo\n"
        "- CloudSync Business: $199/mo\n"
        "- CloudSync Enterprise: $499/mo\n\n"
        "Use available tools to look up invoices and plan details. "
        "Be helpful, concise, and empathetic. If you need customer details "
        "to process a request, ask for them."
    ),
    tools=[lookup_invoice, check_plan, process_refund],
    handoff_description="Customer has a billing, invoice, charge, or refund question",
)
