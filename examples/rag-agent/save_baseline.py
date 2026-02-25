"""Run all golden queries and save traces as a baseline JSON file."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tests.test_rag import run_agent, GOLDEN_QUERIES


def main():
    baseline = {}
    for case in GOLDEN_QUERIES:
        query = case["query"]
        print(f"Recording: {query[:60]}...")
        trace = run_agent(query)
        baseline[query] = trace._trace.model_dump(mode="json")

    os.makedirs("golden", exist_ok=True)
    with open("golden/rag-v1-gpt4o-mini.json", "w") as f:
        json.dump(baseline, f, indent=2, default=str)
    print(f"\nSaved {len(baseline)} traces to golden/rag-v1-gpt4o-mini.json")


if __name__ == "__main__":
    main()
