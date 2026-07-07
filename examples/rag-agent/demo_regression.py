"""
Demo: AgentCI Regression Report

Run the agent against key queries and compare with a saved baseline.
This showcases how AgentCI catches regressions on model swaps.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import ciagent
from agent import generate_answer_api
import ciagent.capture


def run_traced(query: str):
    """Run a query with tracing and return the Trace object."""
    with ciagent.capture.TraceContext(agent_name="rag-agent") as ctx:
        output, state = generate_answer_api(query)
        ctx.attach_langgraph_state(state)
    return ctx.trace


def main():
    # 1. Load the baseline
    try:
        baseline = ciagent.load_baseline("rag-v1-gpt4o-mini")
    except FileNotFoundError:
        print("❌ Baseline not found. Run 'make baseline' first to save golden traces.")
        return

    print("\n============ AgentCI Regression Report ============")
    print(f"Comparing: current run vs. baseline 'rag-v1-gpt4o-mini'\n")

    queries = [
        "What is the refund policy for enterprise customers?",
        "how do I get money back",
        "What's the weather in Austin?",
    ]

    regressions = 0
    warnings = 0

    for q in queries:
        try:
            golden_trace = baseline.get(q)
            if not golden_trace:
                print(f"Query: \"{q}\"")
                print("  ⏭️  Skipped — no baseline for this query\n")
                continue

            current_trace = run_traced(q)
            diff_obj = ciagent.diff(golden_trace, current_trace)

            print(f"Query: \"{q}\"")
            if diff_obj.has_regression:
                regressions += 1
                for d in diff_obj.diffs:
                    icon = "❌" if d.severity == "error" else "⚠️"
                    if d.severity == "warning":
                        warnings += 1
                    print(f"  {icon}  {d.diff_type.value.upper()}: {d.message}")
            else:
                if diff_obj.diffs:
                    for d in diff_obj.diffs:
                        warnings += 1
                        print(f"  ⚠️  {d.diff_type.value.upper()}: {d.message}")
                else:
                    print("  ✅ All checks passed.")
            print("")

        except Exception as e:
            print(f"  ❌ Error: {e}\n")

    print(f"SUMMARY: {regressions} regressions, {warnings} warnings across {len(queries)} queries")


if __name__ == "__main__":
    main()
