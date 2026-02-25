"""General Agent — handles product info, feature requests, FAQ, and anything else."""

from agents import Agent
from ..tools.general_tools import search_knowledge_base


general_agent = Agent(
    name="General Agent",
    instructions=(
        "You are TechCorp's general support agent. You handle product information, "
        "feature requests, FAQ, and any questions that don't fit billing, technical, "
        "or account categories.\n\n"
        "Products:\n"
        "- CloudSync Pro ($49/mo): 100GB storage, 5 integrations, email support\n"
        "- CloudSync Business ($199/mo): 1TB storage, unlimited integrations, "
        "priority support, team management\n"
        "- CloudSync Enterprise ($499/mo): unlimited storage, dedicated support, "
        "custom integrations, SLA guarantee\n\n"
        "Use the knowledge base tool to find accurate product information. "
        "Be helpful and concise."
    ),
    tools=[search_knowledge_base],
    handoff_description="Customer has a general question, feature request, or FAQ",
)
