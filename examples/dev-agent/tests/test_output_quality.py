"""Output Quality Tests — Assert the final report is accurate and complete.

These tests validate the CONTENT of the agent's output, not just
whether it called tools correctly. They catch:
- Hallucinated metrics (agent invents numbers not in the tool output)
- Missing sections (agent skips parts of the report format)
- Inconsistent assessments (says "GOOD" when data says otherwise)
- Generic advice (recommendations not specific to this repo)

AgentCI Learning Opportunity:
─────────────────────────────
Some assertions here are deterministic (field presence, number matching).
Others require judgment (is the assessment reasonable given the data?).
The judgment-based ones are candidates for LLM-as-judge in Phase 4.
For now, we use heuristic proxies.
"""

import pytest
import re

from devagent.agent.core import Trace
from tests.fixtures import REPO_HEALTHY, REPO_STALE


# ──────────────────────────────────────────────
# Report Structure Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestReportStructure:
    """The report must contain all required sections."""

    async def test_report_is_nonempty(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        assert trace.final_report, "Agent produced an empty report"
        assert len(trace.final_report) > 100, (
            f"Report suspiciously short ({len(trace.final_report)} chars)"
        )

    async def test_report_contains_repo_name(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report.lower()
        assert "langchain" in report, (
            "Report doesn't mention the repo name"
        )

    async def test_report_contains_overview_section(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report.lower()
        assert "overview" in report or "description" in report, (
            "Report missing overview/description section"
        )

    async def test_report_contains_metrics(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report.lower()

        # Should mention key metrics by name
        assert "star" in report, "Report doesn't mention stars"
        assert "fork" in report, "Report doesn't mention forks"

    async def test_report_contains_health_assessment(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report.lower()

        # Should contain some form of health signal
        has_assessment = any(
            keyword in report
            for keyword in ["good", "warn", "concern", "healthy", "score"]
        )
        assert has_assessment, "Report doesn't contain any health assessment"

    async def test_report_contains_composite_score(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report

        # Should contain a letter grade (A-F)
        has_grade = bool(re.search(r"\b[A-F][+-]?\b", report))
        assert has_grade, (
            "Report doesn't contain a composite score (A/B/C/D/F)"
        )

    async def test_report_contains_recommendations(self, agent_healthy):
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report.lower()
        assert "recommend" in report, (
            "Report doesn't contain a recommendations section"
        )


# ──────────────────────────────────────────────
# Factual Accuracy Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestFactualAccuracy:
    """The report must reflect actual data from tools, not hallucinations."""

    async def test_reports_correct_language(self, agent_healthy):
        """The report should say 'Python' since that's what the mock returns."""
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        assert "Python" in trace.final_report or "python" in trace.final_report, (
            "Report doesn't mention the correct primary language (Python)"
        )

    async def test_reports_correct_license(self, agent_healthy):
        """The report should mention MIT since that's the mock response."""
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        assert "MIT" in trace.final_report, (
            "Report doesn't mention the correct license (MIT)"
        )

    async def test_star_count_is_reasonable(self, agent_healthy):
        """The report should mention a star count close to the mock value (102,000).
        
        We don't require exact match because the LLM might format it
        differently (102K, 102,000, ~100K). But it shouldn't say 500 or 1M.
        """
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report

        # Check for reasonable representations of ~102,000
        has_reasonable_count = any(
            marker in report
            for marker in ["102,000", "102000", "102k", "102K", "102,0"]
        )
        assert has_reasonable_count, (
            f"Report doesn't contain a reasonable star count "
            f"(expected ~102,000). Report excerpt: {report[:500]}"
        )

    async def test_does_not_hallucinate_absent_data(self, agent_minimal):
        """For a repo with no language and no license, the report
        should NOT invent a language or license.
        """
        from tests.fixtures import REPO_MINIMAL
        trace = await agent_minimal.analyze(REPO_MINIMAL["url"])
        report = trace.final_report

        # The mock has language=None, so report shouldn't claim a specific language
        # (unless it says "None" or "Not specified" which is fine)
        hallucinated_languages = ["Python", "JavaScript", "TypeScript", "Java", "Go", "Rust"]
        for lang in hallucinated_languages:
            if lang in report:
                # Check it's in a "not specified" context, not a claim
                context_start = max(0, report.index(lang) - 30)
                context = report[context_start:report.index(lang) + len(lang) + 30]
                # This is a heuristic — Phase 4 LLM-as-judge will do this better
                assert any(
                    neg in context.lower()
                    for neg in ["no ", "none", "not ", "n/a", "unspecified"]
                ), (
                    f"Report may have hallucinated language '{lang}' "
                    f"(context: '{context}')"
                )

    async def test_archived_repo_flagged_as_stale(self, agent_stale):
        """An archived repo should be flagged as stale/archived/inactive."""
        trace = await agent_stale.analyze(REPO_STALE["url"])
        report = trace.final_report.lower()

        has_stale_flag = any(
            keyword in report
            for keyword in ["archived", "stale", "inactive", "no longer maintained",
                            "abandoned", "deprecated", "concern"]
        )
        assert has_stale_flag, (
            "Report doesn't flag an archived repo as stale/inactive"
        )


# ──────────────────────────────────────────────
# Anti-Hallucination Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestAntiHallucination:
    """Ensure the agent doesn't make up information it didn't receive."""

    async def test_no_fabricated_contributor_count(self, agent_healthy):
        """Phase 0 doesn't fetch contributor data.
        The report should NOT mention a specific contributor count.
        """
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report

        # Check for patterns like "500 contributors" or "contributors: 250"
        contributor_pattern = re.search(
            r"(\d+)\s*(?:contributors?|maintainers?)",
            report,
            re.IGNORECASE,
        )
        assert contributor_pattern is None, (
            f"Report fabricated contributor count: '{contributor_pattern.group(0)}'. "
            f"Phase 0 has no tool to fetch contributor data."
        )

    async def test_no_fabricated_test_coverage(self, agent_healthy):
        """Phase 0 has no code analysis tool. Report shouldn't mention
        test coverage percentages.
        """
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report

        coverage_pattern = re.search(
            r"(\d+)%\s*(?:test|code)?\s*coverage",
            report,
            re.IGNORECASE,
        )
        assert coverage_pattern is None, (
            f"Report fabricated coverage data: '{coverage_pattern.group(0)}'. "
            f"Phase 0 has no code analysis capability."
        )

    async def test_no_fabricated_vulnerability_count(self, agent_healthy):
        """Phase 0 has no security scanning tool. Report shouldn't mention
        specific vulnerability counts.
        """
        trace = await agent_healthy.analyze(REPO_HEALTHY["url"])
        report = trace.final_report

        vuln_pattern = re.search(
            r"(\d+)\s*(?:vulnerabilit|CVE|security issue)",
            report,
            re.IGNORECASE,
        )
        assert vuln_pattern is None, (
            f"Report fabricated vulnerability data: '{vuln_pattern.group(0)}'. "
            f"Phase 0 has no security scanning capability."
        )


# ──────────────────────────────────────────────
# LLM-As-Judge Tests
# ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestLLMAsJudge:
    """Uses AgentCI's llm_judge assertion to evaluate report quality."""

    async def test_report_quality_with_llm_judge_assertion(self, trace_healthy):
        """Passes the generated report to an LLM judge via AgentCI."""
        import os
        from agentci.models import Assertion
        from agentci.assertions import evaluate_assertion

        if not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-dummy-key-for-testing":
            pytest.skip("Skipping LLM-as-judge test: real ANTHROPIC_API_KEY not set.")
        
        trace = await trace_healthy()

        rule = """
        The report must clearly and professionally assess the repository's health. It must:
        1. Mention the repository name
        2. Include key metrics (like stars and forks)
        3. Provide a composite score (e.g. A, B, C, D, F)
        4. Provide actionable recommendations
        """
        
        assertion = Assertion(type="llm_judge", value=rule)
        passed, message = evaluate_assertion(assertion, trace)
        
        assert passed, message
