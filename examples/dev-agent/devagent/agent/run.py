"""CLI entry point: python -m devagent.agent.run <repo_url>"""

from __future__ import annotations

import asyncio
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devagent.agent.core import DevAgent

console = Console()


async def main(repo_url: str) -> None:
    console.print(f"\n[bold blue]DevAgent[/bold blue] analyzing: {repo_url}\n")

    agent = DevAgent()
    trace = await agent.analyze(repo_url)

    # Print the report
    if trace.success and trace.final_report:
        console.print(Panel(trace.final_report, title="Health Report", border_style="green"))
    else:
        console.print(Panel(
            f"Analysis failed: {trace.error}",
            title="Error",
            border_style="red",
        ))

    # Print trace summary
    table = Table(title="Trace Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Tool calls", str(trace.tool_call_count))
    table.add_row("Tools used", ", ".join(trace.tool_names_called) or "none")
    table.add_row("Input tokens", f"{trace.input_tokens:,}")
    table.add_row("Output tokens", f"{trace.output_tokens:,}")
    table.add_row("Total tokens", f"{trace.total_tokens:,}")
    table.add_row("Estimated cost", f"${trace.estimated_cost_usd:.6f}")
    table.add_row("Duration", f"{trace.total_duration_ms:.0f}ms")
    table.add_row("Success", "✅" if trace.success else "❌")

    console.print(table)

    # Save trace to file for AgentCI inspection
    trace_path = "traces/latest.json"
    import os
    os.makedirs("traces", exist_ok=True)
    with open(trace_path, "w") as f:
        json.dump(trace.to_dict(), f, indent=2)
    console.print(f"\n[dim]Trace saved to {trace_path}[/dim]\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python -m devagent.agent.run <github_repo_url>[/red]")
        console.print("Example: python -m devagent.agent.run https://github.com/langchain-ai/langchain")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
