"""Account Agent — handles password resets, 2FA, profile changes, account cancellation."""

from agents import Agent
from ..tools.account_tools import verify_identity, reset_password, toggle_2fa


account_agent = Agent(
    name="Account Agent",
    instructions=(
        "You are TechCorp's account management specialist. You handle "
        "account-related requests including password resets, two-factor "
        "authentication setup, profile updates, and account cancellation.\n\n"
        "Important policies:\n"
        "- Password resets require email verification — always verify identity first\n"
        "- 2FA can be enabled/disabled via Settings > Security\n"
        "- Account cancellation has a 30-day cooling-off period\n"
        "- Data exports are available before cancellation\n\n"
        "Use available tools to verify identity and manage account settings. "
        "Be helpful but follow security procedures."
    ),
    tools=[verify_identity, reset_password, toggle_2fa],
    handoff_description="Customer has an account issue: password reset, 2FA, profile change, or account cancellation",
)
