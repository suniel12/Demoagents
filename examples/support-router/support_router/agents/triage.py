"""Triage Agent — classifies customer intent and routes to the appropriate specialist."""

from agents import Agent
from .billing import billing_agent
from .general import general_agent
from .technical import technical_agent
from .account import account_agent
from ..guardrails import relevance_guardrail, pii_guardrail


triage_agent = Agent(
    name="Triage Agent",
    instructions=(
        "You are TechCorp's customer support triage agent. "
        "Your ONLY job is to classify the customer's intent and hand off "
        "to the appropriate specialist agent.\n\n"
        "Route to:\n"
        "- Billing Agent: charges, invoices, refunds, plan upgrades/downgrades, pricing\n"
        "- Technical Agent: product not working, bugs, errors, sync issues, system status\n"
        "- Account Agent: password reset, 2FA, profile changes, account cancellation\n"
        "- General Agent: product info, feature requests, FAQ, anything else\n\n"
        "Do NOT try to answer the question yourself. Always hand off."
    ),
    handoffs=[billing_agent, technical_agent, account_agent, general_agent],
    input_guardrails=[relevance_guardrail, pii_guardrail],
)
