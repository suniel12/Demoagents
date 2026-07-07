import re
from typing import Any
from pydantic import BaseModel, Field
import httpx

from devagent.tools import ToolDefinition
from devagent.tools.github_list_files import github_list_files_tool
from devagent.tools.github_read_file import github_read_file_tool


class ActionsAnalyzerInput(BaseModel):
    owner: str = Field(..., description="The GitHub repository owner")
    repo: str = Field(..., description="The GitHub repository name")


class ActionsAnalyzerOutput(BaseModel):
    has_workflows: bool = Field(..., description="Whether GitHub Actions workflows were found")
    workflow_count: int = Field(default=0, description="Number of workflow files found")
    workflow_triggers: list[str] = Field(default_factory=list, description="Common triggers found (e.g., push, pull_request)")
    notes: str = Field(default="", description="Additional notes or findings")


async def analyze_actions(owner: str, repo: str) -> dict[str, Any]:
    """Analyzes GitHub Actions workflows by reading .github/workflows directory."""
    # First, try to list the .github/workflows directory.
    # We borrow the handler from github_list_files_tool for simplicity, 
    # though in a real scenario we might just call the GitHub API directly.
    import httpx
    import json
    import os
    
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AgentCI-DevAgent",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/.github/workflows"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 404:
                return ActionsAnalyzerOutput(
                    has_workflows=False,
                    notes="No .github/workflows directory found."
                ).model_dump()
                
            response.raise_for_status()
            contents = response.json()
            
            if not isinstance(contents, list):
                contents = [contents]
                
            workflows = [f for f in contents if f["name"].endswith((".yml", ".yaml"))]
             
            if not workflows:
                return ActionsAnalyzerOutput(
                    has_workflows=False,
                    notes="Directory found, but no YAML workflow files present."
                ).model_dump()
                 
            # Try to read the first workflow to extract triggers
            trigger_patterns = []
            first_wf = workflows[0]
             
            file_url = first_wf.get("download_url")
            if file_url:
                file_resp = await client.get(file_url, headers=headers)
                if file_resp.is_success:
                    content_text = file_resp.text
                    if "on:" in content_text or "on:\n" in content_text:
                        if "push" in content_text: trigger_patterns.append("push")
                        if "pull_request" in content_text: trigger_patterns.append("pull_request")
                        if "schedule" in content_text: trigger_patterns.append("schedule")
                         
            return ActionsAnalyzerOutput(
                has_workflows=True,
                workflow_count=len(workflows),
                workflow_triggers=trigger_patterns,
                notes=f"Found {len(workflows)} workflow files."
            ).model_dump()
             
    except Exception as e:
        return ActionsAnalyzerOutput(
            has_workflows=False,
            notes=f"Failed to analyze actions: {str(e)}"
        ).model_dump()


github_actions_analyzer_tool = ToolDefinition(
    name="github_actions_analyzer",
    description=(
        "Analyzes GitHub Actions workflows. "
        "Use this ONLY if you have verified that a .github/workflows directory exists."
    ),
    input_schema=ActionsAnalyzerInput.model_json_schema(),
    handler=analyze_actions,
    output_model=ActionsAnalyzerOutput,
)
