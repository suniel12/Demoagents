"""Shared fixtures for AgentCI tests.

Design Philosophy:
──────────────────
- Fixtures provide DETERMINISTIC inputs and expected outputs
- Mock responses eliminate API dependency in CI (no GitHub token needed)
- Real API tests are separate and marked with @pytest.mark.live
- Each fixture represents a specific repo archetype:
  - HEALTHY: Well-maintained, popular open-source project
  - STALE: Abandoned project, no recent activity
  - NONEXISTENT: Repo that doesn't exist (error handling)
  - MINIMAL: Brand new repo with almost no content
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


# ──────────────────────────────────────────────
# Known Test Repos
# ──────────────────────────────────────────────

REPO_HEALTHY = {
    "url": "https://github.com/langchain-ai/langchain",
    "owner": "langchain-ai",
    "repo": "langchain",
}

REPO_STALE = {
    "url": "https://github.com/facebookarchive/react-native-fbsdk",
    "owner": "facebookarchive",
    "repo": "react-native-fbsdk",
}

REPO_NONEXISTENT = {
    "url": "https://github.com/definitely-not-real/repo-that-does-not-exist-12345",
    "owner": "definitely-not-real",
    "repo": "repo-that-does-not-exist-12345",
}

REPO_MINIMAL = {
    "url": "https://github.com/octocat/Hello-World",
    "owner": "octocat",
    "repo": "Hello-World",
}


# ──────────────────────────────────────────────
# Mock API Responses
# ──────────────────────────────────────────────

MOCK_HEALTHY_RESPONSE = {
    "owner": {"login": "langchain-ai"},
    "name": "langchain",
    "full_name": "langchain-ai/langchain",
    "description": "Build context-aware reasoning applications",
    "language": "Python",
    "stargazers_count": 102000,
    "forks_count": 15800,
    "open_issues_count": 1250,
    "subscribers_count": 890,
    "license": {"name": "MIT License"},
    "default_branch": "master",
    "created_at": "2022-10-17T00:00:00Z",
    "pushed_at": "2026-02-22T10:30:00Z",
    "fork": False,
    "archived": False,
    "topics": ["llm", "langchain", "rag", "ai", "agents"],
    "size": 245000,
}

MOCK_STALE_RESPONSE = {
    "owner": {"login": "facebookarchive"},
    "name": "react-native-fbsdk",
    "full_name": "facebookarchive/react-native-fbsdk",
    "description": "A React Native wrapper around the Facebook SDKs",
    "language": "Java",
    "stargazers_count": 2950,
    "forks_count": 910,
    "open_issues_count": 180,
    "subscribers_count": 75,
    "license": {"name": "MIT License"},
    "default_branch": "main",
    "created_at": "2015-08-20T00:00:00Z",
    "pushed_at": "2022-03-15T08:00:00Z",
    "fork": False,
    "archived": True,
    "topics": ["react-native", "facebook"],
    "size": 4500,
}

MOCK_MINIMAL_RESPONSE = {
    "owner": {"login": "octocat"},
    "name": "Hello-World",
    "full_name": "octocat/Hello-World",
    "description": "My first repository on GitHub!",
    "language": None,
    "stargazers_count": 2500,
    "forks_count": 2200,
    "open_issues_count": 1100,
    "subscribers_count": 120,
    "license": None,
    "default_branch": "master",
    "created_at": "2011-01-26T19:01:12Z",
    "pushed_at": "2024-06-10T12:00:00Z",
    "fork": False,
    "archived": False,
    "topics": [],
    "size": 1,
}


# ──────────────────────────────────────────────
# Fixture Helpers
# ──────────────────────────────────────────────


def load_golden_trace(name: str) -> dict[str, Any]:
    """Load a golden trace from the golden_traces directory."""
    path = Path(__file__).parent / "golden_traces" / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Golden trace '{name}' not found at {path}. "
            f"Run `agentci record {name}` to create it."
        )
    return json.loads(path.read_text())


def save_golden_trace(name: str, trace_dict: dict[str, Any]) -> None:
    """Save a trace as a golden trace for future comparison."""
    path = Path(__file__).parent / "golden_traces" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace_dict, indent=2))
