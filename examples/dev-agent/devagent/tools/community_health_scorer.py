from typing import Any
from pydantic import BaseModel, Field

from devagent.tools import ToolDefinition
from devagent.tools.github_list_files import github_list_files_tool
from devagent.tools.github_read_file import github_read_file_tool


class CommunityHealthInput(BaseModel):
    owner: str = Field(..., description="The GitHub repository owner")
    repo: str = Field(..., description="The GitHub repository name")


class CommunityHealthOutput(BaseModel):
    has_contributing: bool = Field(..., description="Whether a CONTRIBUTING.md file exists")
    has_code_of_conduct: bool = Field(..., description="Whether a CODE_OF_CONDUCT (or similar) file exists")
    has_issue_templates: bool = Field(..., description="Whether issue templates exist in .github/")
    has_pr_template: bool = Field(..., description="Whether a pull request template exists")
    health_score_adjustment: int = Field(..., description="Points to add/subtract based on community health (e.g., -1 to +2)")
    notes: str = Field("", description="Detailed findings")


async def analyze_community_health(owner: str, repo: str) -> dict[str, Any]:
    """Analyzes a repository for standard open-source community health documents."""
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
        
    base_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    
    # We will do a few lightweight calls to check for file existence
    # In a real tool we might use the GraphQL API to do this in one request.
    
    async def check_file(path: str, client: httpx.AsyncClient) -> bool:
        try:
             resp = await client.get(f"{base_url}/{path}", headers=headers)
             if resp.status_code == 200:
                 return True
             # Could be a directory, but generally template files are just exist checks
        except Exception:
            pass
        return False
        
    try:
        async with httpx.AsyncClient() as client:
            # Check CONTRIBUTING
            has_contrib = await check_file("CONTRIBUTING.md", client) or await check_file(".github/CONTRIBUTING.md", client)
            
            # Check CoC
            has_coc = await check_file("CODE_OF_CONDUCT.md", client) or await check_file(".github/CODE_OF_CONDUCT.md", client)
            
            # Check PR template
            has_pr_template = await check_file(".github/pull_request_template.md", client) or await check_file("PULL_REQUEST_TEMPLATE.md", client)
            
            # Check Issue templates (is directory present)
            has_issue_templates = False
            resp = await client.get(f"{base_url}/.github/ISSUE_TEMPLATE", headers=headers)
            if resp.status_code == 200 and isinstance(resp.json(), list) and len(resp.json()) > 0:
                has_issue_templates = True
            elif await check_file(".github/issue_template.md", client) or await check_file("ISSUE_TEMPLATE.md", client):
                 has_issue_templates = True
                 
            # Simple heuristic scoring
            score = 0
            if has_contrib: score += 1
            if has_coc: score += 1
            if has_issue_templates: score += 1
            if has_pr_template: score += 1
            
            adj = 0
            if score == 4: adj = 2
            elif score >= 2: adj = 1
            elif score == 0: adj = -1
            
            notes = f"Found: CONTRIBUTING ({has_contrib}), CODE_OF_CONDUCT ({has_coc}), PR Template ({has_pr_template}), Issue Templates ({has_issue_templates})."
            
            return CommunityHealthOutput(
                has_contributing=has_contrib,
                has_code_of_conduct=has_coc,
                has_issue_templates=has_issue_templates,
                has_pr_template=has_pr_template,
                health_score_adjustment=adj,
                notes=notes
            ).model_dump()
            
    except Exception as e:
        return CommunityHealthOutput(
            has_contributing=False,
            has_code_of_conduct=False,
            has_issue_templates=False,
            has_pr_template=False,
            health_score_adjustment=0,
            notes=f"Failed to analyze community health: {str(e)}"
        ).model_dump()


community_health_scorer_tool = ToolDefinition(
    name="community_health_scorer",
    description=(
        "Analyzes community health files (CONTRIBUTING, templates, CODE_OF_CONDUCT). "
        "Use this ONLY if the repository has >= 50 stars as discovered in the repo metadata."
    ),
    input_schema=CommunityHealthInput.model_json_schema(),
    handler=analyze_community_health,
    output_model=CommunityHealthOutput,
)
