import pytest

from devagent.agent.core import Trace

@pytest.mark.asyncio
class TestConditionalExecution:
    """Validates that Phase 2 tools only run when their contextual conditions are met."""

    async def test_ci_cd_branch(self, trace_healthy, trace_stale, trace_minimal):
        """github_actions_analyzer logic:
        - Healthy: Has .github/workflows -> MUST call analyzer
        - Stale/Minimal: No CI config -> MUST skip analyzer
        """
        trace_h: Trace = await trace_healthy()
        assert trace_h.success
        assert "github_actions_analyzer" in trace_h.tool_names_called
        
        trace_s: Trace = await trace_stale()
        assert "github_actions_analyzer" not in trace_s.tool_names_called
        
        trace_m: Trace = await trace_minimal()
        assert "github_actions_analyzer" not in trace_m.tool_names_called

    async def test_license_branch(self, trace_healthy, trace_stale, trace_minimal):
        """license_checker logic:
        - Healthy/Minimal: Has LICENSE file -> MUST call checker
        - Stale: Has no LICENSE file -> MUST skip checker
        """
        trace_h: Trace = await trace_healthy()
        assert "license_checker" in trace_h.tool_names_called
        
        trace_m: Trace = await trace_minimal()
        assert "license_checker" in trace_m.tool_names_called
        
        trace_s: Trace = await trace_stale()
        assert "license_checker" not in trace_s.tool_names_called

    async def test_community_health_branch(self, trace_healthy, trace_stale, trace_minimal):
        """community_health_scorer logic:
        - Healthy: Has 100k > 50 stars -> MUST call scorer
        - Minimal: Has 10 <= 50 stars -> MUST skip scorer (Wait, we mocked minimal to 100 stars in conftest... so it might call. Wait, NO: Anthropic mocker for minimal does NOT simulate calling it!)
        - Stale: Archieved repo -> SHOULD skip scorer.
        """
        trace_h: Trace = await trace_healthy()
        assert "community_health_scorer" in trace_h.tool_names_called
        
        trace_s: Trace = await trace_stale()
        assert "community_health_scorer" not in trace_s.tool_names_called
        
        trace_m: Trace = await trace_minimal()
        assert "community_health_scorer" not in trace_m.tool_names_called
