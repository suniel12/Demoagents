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

# Simple regex patterns for common PII
PII_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "phone_US": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
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
    """Extract plain text from the guardrail input."""
    if isinstance(input, str):
        return input
    # For list inputs, concatenate all text content
    parts = []
    for item in input:
        if isinstance(item, dict):
            content = item.get("content", "")
            if isinstance(content, str):
                parts.append(content)
        elif isinstance(item, str):
            parts.append(item)
    return " ".join(parts)
