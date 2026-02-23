import asyncio
from tests.fixtures import save_golden_trace, MOCK_HEALTHY_RESPONSE, REPO_HEALTHY
from devagent.agent.core import DevAgent
from tests.conftest import make_mock_registry, mock_anthropic_client
import os

async def main():
    # Setup dummy env var so it doesn't fail
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy"
    registry = make_mock_registry(
        mock_metadata_response=MOCK_HEALTHY_RESPONSE,
        mock_tree_response={"tree": [{"path": "package.json", "mode": "100644", "type": "blob", "size": 100, "sha": "abc"}], "truncated": False},
        mock_file_responses={"package.json": {"path": "package.json", "content": '{"dependencies": {"lodash": "4.17.10"}}', "size": 100, "encoding": "utf-8"}},
        mock_dep_responses={"npm": {"total_dependencies_found": 15, "critical_vulnerabilities": 0, "high_vulnerabilities": 1, "medium_vulnerabilities": 3, "low_vulnerabilities": 1, "notes": "Found vulnerabilities."}}
    )
    agent = DevAgent(registry=registry, max_tool_calls=10)
    agent.client = mock_anthropic_client("healthy")
    
    trace = await agent.analyze(REPO_HEALTHY["url"])
    trace_dict = trace.to_dict()
    
    # Add assertions block expected by Phase 1 mock agent
    trace_dict["assertions"] = {
        "success": {"value": True, "op": "eq"},
        "tool_call_count": {"value": 4, "op": "eq"},
        "tool_names_called": {"value": ["github_repo_metadata", "github_list_files", "github_read_file", "dependency_analyzer"], "op": "eq"},
        "estimated_cost_usd": {"value": 0.05, "op": "lte"}
    }
    save_golden_trace("phase1_healthy_repo", trace_dict)
    print("Saved golden trace phase1_healthy_repo.")

if __name__ == "__main__":
    asyncio.run(main())
