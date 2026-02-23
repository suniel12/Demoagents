"""GitHub Repository Metadata Tool.

Phase 0: The first and only tool. Fetches basic repo information
from the GitHub REST API.

Tool Schema Design Notes (important for AgentCI dogfooding):
─────────────────────────────────────────────────────────────
The schema is intentionally strict:
- `owner` and `repo` are separate fields (not a combined URL)
  → This forces the LLM to PARSE the URL correctly — testable!
- All output fields are explicitly typed
  → AgentCI can assert on field presence and types
- The description includes examples
  → Helps the LLM call the tool correctly, reduces test flakiness
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

from devagent.tools import ToolDefinition


# ──────────────────────────────────────────────
# Input/Output Models (Pydantic)
# ──────────────────────────────────────────────


class RepoMetadataInput(BaseModel):
    """Input schema for github_repo_metadata tool."""

    owner: str = Field(
        description="Repository owner (user or organization). Example: 'langchain-ai'"
    )
    repo: str = Field(
        description="Repository name. Example: 'langchain'"
    )


class RepoMetadataOutput(BaseModel):
    """Output schema — every field the agent receives back."""

    owner: str
    repo: str
    full_name: str                      # e.g., "langchain-ai/langchain"
    description: str | None
    language: str | None                # Primary language
    stars: int
    forks: int
    open_issues: int
    watchers: int
    license_name: str | None            # e.g., "MIT License"
    default_branch: str                 # e.g., "main"
    created_at: str                     # ISO 8601
    last_pushed_at: str                 # ISO 8601
    is_fork: bool
    is_archived: bool
    topics: list[str]
    size_kb: int                        # Repo size in KB


# ──────────────────────────────────────────────
# Tool Handler (async function)
# ──────────────────────────────────────────────


async def fetch_repo_metadata(owner: str, repo: str) -> dict:
    """Fetch repository metadata from GitHub REST API.

    Uses the public /repos endpoint. Authenticated requests get
    5,000 req/hr; unauthenticated get 60 req/hr.

    Raises:
        httpx.HTTPStatusError: On 404 (not found), 403 (rate limited), etc.
    """
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    # Map GitHub API response to our typed output
    return RepoMetadataOutput(
        owner=data["owner"]["login"],
        repo=data["name"],
        full_name=data["full_name"],
        description=data.get("description"),
        language=data.get("language"),
        stars=data["stargazers_count"],
        forks=data["forks_count"],
        open_issues=data["open_issues_count"],
        watchers=data["subscribers_count"],
        license_name=data["license"]["name"] if data.get("license") else None,
        default_branch=data["default_branch"],
        created_at=data["created_at"],
        last_pushed_at=data["pushed_at"],
        is_fork=data["fork"],
        is_archived=data["archived"],
        topics=data.get("topics", []),
        size_kb=data["size"],
    ).model_dump()


# ──────────────────────────────────────────────
# Anthropic Tool Schema (JSON Schema format)
# ──────────────────────────────────────────────

TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "owner": {
            "type": "string",
            "description": (
                "The GitHub repository owner (username or organization name). "
                "For 'https://github.com/langchain-ai/langchain', this is 'langchain-ai'."
            ),
        },
        "repo": {
            "type": "string",
            "description": (
                "The GitHub repository name. "
                "For 'https://github.com/langchain-ai/langchain', this is 'langchain'."
            ),
        },
    },
    "required": ["owner", "repo"],
}


# ──────────────────────────────────────────────
# Tool Definition (for registry)
# ──────────────────────────────────────────────

github_repo_metadata_tool = ToolDefinition(
    name="github_repo_metadata",
    description=(
        "Fetch metadata about a GitHub repository including stars, forks, "
        "language, license, last push date, topics, and other key metrics. "
        "Use this as the FIRST step when analyzing any repository — it tells you "
        "whether the repo exists, what language it uses, and its basic health signals."
    ),
    input_schema=TOOL_SCHEMA,
    handler=fetch_repo_metadata,
    output_model=RepoMetadataOutput,
)
