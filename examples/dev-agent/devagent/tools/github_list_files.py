"""Tool to list files and directories in a GitHub repository."""

from typing import Any

import httpx
from pydantic import BaseModel, Field

from devagent.tools import ToolDefinition


class ListFilesInput(BaseModel):
    """Input schema for github_list_files."""

    owner: str = Field(..., description="The GitHub repository owner")
    repo: str = Field(..., description="The GitHub repository name")
    tree_sha: str = Field(
        default="HEAD",
        description="The commit, branch, or tag to read from. Defaults to HEAD.",
    )
    recursive: bool = Field(
        default=True,
        description="Whether to list files recursively (entire tree). If false, only lists the top level.",
    )


class FileInfo(BaseModel):
    path: str
    mode: str
    type: str
    size: int | None = None
    sha: str


class ListFilesOutput(BaseModel):
    """Output schema for github_list_files."""

    tree: list[FileInfo]
    truncated: bool = Field(
        description="True if there were more files than the GitHub API limit could return"
    )


async def fetch_file_tree(
    owner: str, repo: str, tree_sha: str = "HEAD", recursive: bool = True
) -> dict[str, Any]:
    """Fetch the repository file tree from the GitHub API."""
    import os

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    recursive_flag = "1" if recursive else "0"
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}?recursive={recursive_flag}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        data = response.json()

    # The GitHub API returns a lot of extra metadata (like URLs) we don't need to pass to the LLM.
    # Map to our clean schema.
    cleaned_tree = []
    for item in data.get("tree", []):
        cleaned_tree.append(
            FileInfo(
                path=item["path"],
                mode=item["mode"],
                type=item["type"],
                size=item.get("size"),
                sha=item["sha"],
            )
        )

    # Note: For very large repos, we might want to truncate or filter the list here
    # before returning it, otherwise we could blow out the LLM context window.
    MAX_ITEMS = 1000
    is_truncated = data.get("truncated", False)
    if len(cleaned_tree) > MAX_ITEMS:
        cleaned_tree = cleaned_tree[:MAX_ITEMS]
        is_truncated = True

    result = ListFilesOutput(
        tree=cleaned_tree,
        truncated=is_truncated,
    )
    return result.model_dump()


github_list_files_tool = ToolDefinition(
    name="github_list_files",
    description="List all files and directories in a GitHub repository's specific branch or commit. Returns the file paths, types (blob/tree), and file sizes. Use this to understand the repository structure and locate files of interest.",
    input_schema=ListFilesInput.model_json_schema(),
    output_model=ListFilesOutput,
    handler=fetch_file_tree,
)
