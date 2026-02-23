"""Tool to read the contents of a specific file in a GitHub repository."""

import base64
from typing import Any

import httpx
from pydantic import BaseModel, Field

from devagent.tools import ToolDefinition


class ReadFileInput(BaseModel):
    """Input schema for github_read_file."""

    owner: str = Field(..., description="The GitHub repository owner")
    repo: str = Field(..., description="The GitHub repository name")
    path: str = Field(..., description="The path to the file within the repository")
    ref: str | None = Field(
        default=None,
        description="The commit, branch, or tag to read from. Optional.",
    )


class ReadFileOutput(BaseModel):
    """Output schema for github_read_file."""

    path: str
    content: str = Field(description="The decoded text content of the file")
    size: int
    encoding: str


async def fetch_file_contents(
    owner: str, repo: str, path: str, ref: str | None = None
) -> dict[str, Any]:
    """Fetch and decode file contents from the GitHub API."""
    import os

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    if ref:
        url += f"?ref={ref}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        data = response.json()

    # The GitHub API returns file contents base64 encoded by default
    encoding = data.get("encoding", "")
    content = data.get("content", "")
    
    if encoding == "base64" and content:
        # Decode the base64 content
        try:
            decoded_bytes = base64.b64decode(content)
            # Try to decode as utf-8, fallback to simple string representation if binary
            try:
                decoded_str = decoded_bytes.decode("utf-8")
            except UnicodeDecodeError:
                # Truncate binary files for safety
                decoded_str = f"[Binary file of size {data.get('size')} bytes. Decoding preview: {repr(decoded_bytes[:50])}...]"
        except Exception as e:
            decoded_str = f"[Error decoding base64 content: {str(e)}]"
    else:
        # If not base64, assume it's already text (or it's a directory, which shouldn't happen with this tool)
        if isinstance(content, list):
             raise ValueError(f"Path '{path}' points to a directory, not a file. Use github_list_files instead.")
        decoded_str = str(content)

    result = ReadFileOutput(
        path=data["path"],
        content=decoded_str,
        size=data["size"],
        encoding="utf-8" if encoding == "base64" else encoding,
    )
    return result.model_dump()


github_read_file_tool = ToolDefinition(
    name="github_read_file",
    description="Read the text contents of a specific file in a GitHub repository. Use this to inspect configuration files, dependency manifests, or source code.",
    input_schema=ReadFileInput.model_json_schema(),
    output_model=ReadFileOutput,
    handler=fetch_file_contents,
)
