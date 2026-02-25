"""Technical Agent — handles product issues, bugs, system status, error codes."""

from agents import Agent
from ..tools.technical_tools import check_system_status, lookup_error_code


technical_agent = Agent(
    name="Technical Agent",
    instructions=(
        "You are TechCorp's technical support specialist. You handle "
        "issues with the product not working, bug reports, system status "
        "inquiries, and error code lookups.\n\n"
        "Common issues:\n"
        "- Sync failures (error codes: E-SYNC-001 to E-SYNC-010)\n"
        "- Login issues (error codes: E-AUTH-001 to E-AUTH-005)\n"
        "- Performance problems\n"
        "- Integration setup help\n\n"
        "Use available tools to check system status and look up error codes. "
        "Be empathetic and thorough. Ask for error codes when relevant."
    ),
    tools=[check_system_status, lookup_error_code],
    handoff_description="Customer has a technical issue, bug report, error, or system status question",
)
