"""
Guardrails for TechCorp Support Router.

Two input guardrails that run on the triage agent:
1. Relevance Guardrail — blocks off-topic queries (politics, recipes, etc.)
2. PII Guardrail — flags messages containing sensitive personal info (SSN, credit cards)
"""

import re
from agents import (
    GuardrailFunctionOutput,
    InputGuardrail,
    RunContextWrapper,
    Agent,
    input_guardrail,
)
from agents.items import TResponseInputItem


# ── Off-topic / relevance guardrail ───────────────────

OFF_TOPIC_KEYWORDS = [
    "recipe", "cooking", "weather forecast", "sports score",
    "election", "politics", "stock price", "cryptocurrency",
    "dating", "horoscope", "lottery",
]


@input_guardrail(name="relevance_check")
def relevance_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent[None],
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Block queries that are clearly off-topic for a tech support system."""
    text = _extract_text(input).lower()

    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in text:
            return GuardrailFunctionOutput(
                output_info=f"Off-topic detected: '{keyword}'",
                tripwire_triggered=True,
            )

    return GuardrailFunctionOutput(
        output_info="Relevance check passed",
        tripwire_triggered=False,
    )


# ── PII detection guardrail ──────────────────────────

# Simple regex patterns for PII that must never enter the transcript.
# Deliberately NOT included: phone numbers. A callback number is ordinary
# support traffic — blocking it killed live refund conversations (found by
# `ciagent simulate`, scenario refund-with-callback-number).
PII_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
}


@input_guardrail(name="pii_check")
def pii_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent[None],
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Flag messages that contain potentially sensitive PII."""
    text = _extract_text(input)

    found = []
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, text):
            found.append(pii_type)

    if found:
        return GuardrailFunctionOutput(
            output_info=f"PII detected: {', '.join(found)}",
            tripwire_triggered=True,
        )

    return GuardrailFunctionOutput(
        output_info="PII check passed",
        tripwire_triggered=False,
    )


# ── Helper ────────────────────────────────────────────

def _extract_text(input: str | list[TResponseInputItem]) -> str:
    """Extract the text of the NEWEST user message from the guardrail input.

    In a multi-turn run the input is the full conversation history. Each
    user message is checked exactly once — when it is the newest turn.
    Scanning the whole transcript instead poisons conversations forever:
    one flagged message (or even the agent's own earlier reply) re-trips
    the guardrail on every subsequent, innocent turn. Found live by
    `ciagent simulate` (scenario refund-with-callback-number).
    """
    if isinstance(input, str):
        return input
    for item in reversed(input):
        if isinstance(item, dict):
            if item.get("role") != "user":
                continue
            content = item.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # input_text-style content parts
                return " ".join(
                    p.get("text", "") for p in content if isinstance(p, dict)
                )
            return ""
        if isinstance(item, str):
            # Bare-string item: treat as the user text
            return item
    return ""
