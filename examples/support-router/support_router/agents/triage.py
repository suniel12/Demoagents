"""Triage Agent — classifies customer intent and routes to the appropriate specialist."""

from agents import Agent
from .billing import billing_agent
from .general import general_agent


triage_agent = Agent(
    name="Triage Agent",
    instructions=(
        "You are TechCorp's customer support triage agent. "
        "Your ONLY job is to classify the customer's intent and hand off "
        "to the appropriate specialist agent.\n\n"
        "Route to:\n"
        "- Billing Agent: charges, invoices, refunds, plan upgrades/downgrades\n"
        "- General Agent: product info, feature requests, FAQ, anything else\n\n"
        "Do NOT try to answer the question yourself. Always hand off."
    ),
    handoffs=[billing_agent, general_agent],
)
