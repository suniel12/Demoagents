"""Billing tools — lookup invoices, check plan, process refund requests."""

from agents import function_tool
from ciagent.world import world_tool


@function_tool
@world_tool
def lookup_invoice(customer_email: str) -> str:
    """Look up the most recent invoices for a customer by their email address."""
    # Simulated data
    invoices = {
        "alice@example.com": [
            {"id": "INV-2024-001", "amount": "$49.00", "date": "2024-01-15", "plan": "Pro", "status": "paid"},
            {"id": "INV-2024-002", "amount": "$49.00", "date": "2024-02-15", "plan": "Pro", "status": "paid"},
        ],
        "bob@techcorp-client.com": [
            {"id": "INV-2024-010", "amount": "$199.00", "date": "2024-02-01", "plan": "Business", "status": "paid"},
        ],
    }
    records = invoices.get(customer_email, [])
    if not records:
        return f"No invoices found for {customer_email}. Please verify the email."
    lines = [f"Invoices for {customer_email}:"]
    for inv in records:
        lines.append(f"  {inv['id']}  {inv['date']}  {inv['amount']}  {inv['plan']}  ({inv['status']})")
    return "\n".join(lines)


@function_tool
@world_tool
def check_plan(customer_email: str) -> str:
    """Check the current subscription plan for a customer."""
    plans = {
        "alice@example.com": {"plan": "Pro", "price": "$49/mo", "renewal": "2024-03-15"},
        "bob@techcorp-client.com": {"plan": "Business", "price": "$199/mo", "renewal": "2024-03-01"},
        "carol@bigcorp.com": {"plan": "Enterprise", "price": "$499/mo", "renewal": "2024-04-01"},
    }
    info = plans.get(customer_email)
    if not info:
        return f"No plan found for {customer_email}."
    return f"Plan: {info['plan']} ({info['price']}), renews {info['renewal']}"


@function_tool
@world_tool
def process_refund(invoice_id: str, reason: str) -> str:
    """Submit a refund request for a specific invoice."""
    return f"Refund request submitted for {invoice_id}. Reason: {reason}. Expected processing: 5-7 business days."
