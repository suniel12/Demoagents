from typing import Any
from pydantic import BaseModel, Field

from devagent.tools import ToolDefinition


class LicenseCheckerInput(BaseModel):
    owner: str = Field(..., description="The GitHub repository owner")
    repo: str = Field(..., description="The GitHub repository name")


class LicenseCheckerOutput(BaseModel):
    has_license_file: bool = Field(..., description="Whether a LICENSE file exists")
    license_type: str = Field(..., description="SPDX license identifier or raw text representation")
    is_osi_approved: bool = Field(False, description="Whether the license is generally considered open-source OSI approved")
    notes: str = Field("", description="Additional notes or findings")


async def check_license(owner: str, repo: str) -> dict[str, Any]:
    """Analyzes GitHub repo license presence and permissiveness."""
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
        
    url = f"https://api.github.com/repos/{owner}/{repo}/license"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 404:
                return LicenseCheckerOutput(
                    has_license_file=False,
                    license_type="None",
                    is_osi_approved=False,
                    notes="No LICENSE file found in the root directory via GitHub API."
                ).model_dump()
                
            response.raise_for_status()
            data = response.json()
            
            license_info = data.get("license", {})
            spdx_id = license_info.get("spdx_id", "Unknown")
            name = license_info.get("name", "Unknown License")
            
            # Very basic OSI checking logic for demo purposes
            osi_approved = spdx_id in ["MIT", "Apache-2.0", "GPL-3.0", "GPL-2.0", "BSD-3-Clause", "BSD-2-Clause", "MPL-2.0", "AGPL-3.0"]
            
            return LicenseCheckerOutput(
                has_license_file=True,
                license_type=spdx_id if spdx_id != "NOASSERTION" else name,
                is_osi_approved=osi_approved,
                notes=f"Detected full license name: {name}"
            ).model_dump()
            
    except Exception as e:
        return LicenseCheckerOutput(
            has_license_file=False,
            license_type="Error",
            is_osi_approved=False,
            notes=f"Failed to analyze license: {str(e)}"
        ).model_dump()


license_checker_tool = ToolDefinition(
    name="license_checker",
    description=(
        "Checks repository license compatibility and permissiveness. "
        "Use this ONLY if you have verified that a LICENSE file exists in the repo."
    ),
    input_schema=LicenseCheckerInput.model_json_schema(),
    handler=check_license,
    output_model=LicenseCheckerOutput,
)
