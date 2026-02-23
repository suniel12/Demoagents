"""Tool to analyze a given dependency manifest for known security vulnerabilities.

In a real environment, this tool would call out to OSV.dev, Snyk, or GitHub Dependabot APIs
by parsing the manifest (package.json, requirements.txt, etc) and checking the dependencies.

For the purpose of the AgentCI Phase 1 demo, this tool is a mock that simulates finding
vulnerabilities based on simple keyword heuristics in the manifest string.
"""

from typing import Any

from pydantic import BaseModel, Field

from devagent.tools import ToolDefinition


class DependencyAnalyzerInput(BaseModel):
    """Input schema for dependency_analyzer."""

    manifest_content: str = Field(..., description="The raw string content of the dependency manifest file")
    manifest_type: str = Field(..., description="The type of manifest (e.g., 'npm', 'pip', 'cargo', 'maven')")


class DependencyAnalyzerOutput(BaseModel):
    """Output schema for dependency_analyzer."""

    total_dependencies_found: int = Field(description="Number of dependencies successfully parsed")
    critical_vulnerabilities: int
    high_vulnerabilities: int
    medium_vulnerabilities: int
    low_vulnerabilities: int
    notes: str = Field(description="Summary or context around the findings")


async def analyze_dependencies(
    manifest_content: str, manifest_type: str
) -> dict[str, Any]:
    """Analyze the manifest content for simulated vulnerabilities."""
    
    # Simple deterministic simulation logic for demo purposes
    content_lower = manifest_content.lower()
    
    # Estimate dependency count by counting lines or JSON keys roughly
    if manifest_type == "npm":
        deps_count = content_lower.count('"^') + content_lower.count('"~') + content_lower.count('": "')
    else:
        deps_count = len([line for line in content_lower.split("\n") if len(line.strip()) > 3 and not line.startswith("#")])
    
    # Ensure a minimum sensible default
    deps_count = max(deps_count, 15)

    # Inject simulated vulnerabilities based on common old packages just so the LLM has something to report
    critical = 0
    high = 0
    med = 0
    
    if "requests==2.20" in content_lower or "django==2.0" in content_lower:
        critical += 1
        high += 2
        notes = "Found severely outdated Python dependencies with known CVEs."
    elif "express\": \"4.16" in content_lower or "lodash\": \"4.17.10" in content_lower:
        high += 1
        med += 3
        notes = "Found prototype pollution and regex DOS vulnerabilities in NPM packages."
    else:
        # Default healthy state, but maybe 1 low-risk finding to look realistic
        notes = "Dependency tree looks mostly secure and up to date."

    result = DependencyAnalyzerOutput(
        total_dependencies_found=deps_count,
        critical_vulnerabilities=critical,
        high_vulnerabilities=high,
        medium_vulnerabilities=med,
        low_vulnerabilities=1,
        notes=notes,
    )
    return result.model_dump()


dependency_analyzer_tool = ToolDefinition(
    name="dependency_analyzer",
    description="Analyze the raw string text of a dependency manifest file (like package.json, requirements.txt, Cargo.toml) and return counts of known security vulnerabilities. You must read the file first to pass its contents to this tool.",
    input_schema=DependencyAnalyzerInput.model_json_schema(),
    output_model=DependencyAnalyzerOutput,
    handler=analyze_dependencies,
)
