"""Shared customer context for TechCorp Support Router."""

from pydantic import BaseModel


class UserContext(BaseModel):
    """Context about the customer making the support request."""
    customer_id: str = ""
    name: str = ""
    plan: str = ""  # "pro", "business", "enterprise"
    email: str = ""
