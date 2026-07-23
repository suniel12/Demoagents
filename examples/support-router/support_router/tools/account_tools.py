"""Account tools — verify identity, reset password, manage 2FA."""

from agents import function_tool
from ciagent.world import world_tool


@function_tool
@world_tool
def verify_identity(customer_email: str) -> str:
    """Verify a customer's identity by sending a verification code to their email."""
    return f"Verification code sent to {customer_email}. Please ask the customer for the 6-digit code."


@function_tool
@world_tool
def reset_password(customer_email: str, verification_code: str) -> str:
    """Reset a customer's password after identity verification."""
    if verification_code == "000000":
        return "Invalid verification code. Please try again."
    return f"Password reset link sent to {customer_email}. The link expires in 24 hours."


@function_tool
@world_tool
def toggle_2fa(customer_email: str, enable: bool) -> str:
    """Enable or disable two-factor authentication for a customer."""
    action = "enabled" if enable else "disabled"
    return f"Two-factor authentication has been {action} for {customer_email}."
