"""Unit tests for URL parsing — no LLM, no API, runs instantly.

These tests validate pure logic. They should ALWAYS pass regardless
of model behavior. If these fail, the bug is in your code, not the LLM.

This is an important AgentCI design principle:
Separate deterministic logic tests from LLM behavior tests.
"""

import pytest

from devagent.agent.core import parse_github_url


class TestParseGitHubUrl:
    """Test all URL formats the parser should handle."""

    def test_full_https_url(self):
        owner, repo = parse_github_url("https://github.com/langchain-ai/langchain")
        assert owner == "langchain-ai"
        assert repo == "langchain"

    def test_https_with_git_suffix(self):
        owner, repo = parse_github_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_https_with_trailing_slash(self):
        owner, repo = parse_github_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"

    def test_without_protocol(self):
        owner, repo = parse_github_url("github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_shorthand_owner_repo(self):
        owner, repo = parse_github_url("langchain-ai/langchain")
        assert owner == "langchain-ai"
        assert repo == "langchain"

    def test_with_www(self):
        owner, repo = parse_github_url("https://www.github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_whitespace_handling(self):
        owner, repo = parse_github_url("  https://github.com/owner/repo  ")
        assert owner == "owner"
        assert repo == "repo"

    def test_invalid_url_raises_valueerror(self):
        with pytest.raises(ValueError, match="Could not parse"):
            parse_github_url("not-a-url")

    def test_empty_string_raises_valueerror(self):
        with pytest.raises(ValueError, match="Could not parse"):
            parse_github_url("")

    def test_just_github_domain_raises_valueerror(self):
        with pytest.raises(ValueError, match="Could not parse"):
            parse_github_url("https://github.com/")

    def test_hyphenated_owner_and_repo(self):
        owner, repo = parse_github_url("https://github.com/my-org/my-cool-repo")
        assert owner == "my-org"
        assert repo == "my-cool-repo"

    def test_underscored_names(self):
        owner, repo = parse_github_url("https://github.com/my_org/my_repo")
        assert owner == "my_org"
        assert repo == "my_repo"
