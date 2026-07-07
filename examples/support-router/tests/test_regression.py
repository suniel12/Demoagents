"""
Regression tests for TechCorp Support Router.

Compares current execution of all 24 test queries against their golden baselines.
Fails if routing (handoffs) or tool usage changes, or if costs spike.
"""

import hashlib
import os
import pytest
from pathlib import Path

from ciagent.diff_engine import diff_traces
from ciagent.models import Trace, DiffType
from support_router.run import run_agent

from .test_routing import GOLDEN_QUERIES

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_baseline(query_name: str) -> Trace | None:
    path = GOLDEN_DIR / f"{query_name}.json"
    if not path.exists():
        return None
    with open(path, "r") as f:
        return Trace.model_validate_json(f.read())


def save_baseline(query_name: str, trace: Trace):
    GOLDEN_DIR.mkdir(exist_ok=True, parents=True)
    path = GOLDEN_DIR / f"{query_name}.json"
    with open(path, "w") as f:
        f.write(trace.model_dump_json(indent=2))


@pytest.mark.parametrize(
    "case",
    GOLDEN_QUERIES,
    ids=lambda c: f"{c['category']}",
)
def test_regression_against_baseline(case, request):
    """
    Run each query, compare with golden baseline.
    If --record-golden is passed, overwrite the baselines instead.
    """
    
    query = case["query"]
    # Deterministic hash for consistent file naming across runs
    query_hash = hashlib.md5(query.encode()).hexdigest()[:6]
    query_name = f"{case['category']}_{query_hash}"
    
    # Run the live agent
    trace = run_agent(query)
    assert trace is not None, "Agent returned no trace"
    
    # Annotate trace for AgentCI dashboard
    trace.test_name = request.node.name
    
    # Record mode
    if request.config.getoption("--record-golden", default=False):
        save_baseline(query_name, trace)
        pytest.skip(f"Recorded new golden trace for {query_name}")
        
    # Regression mode
    baseline = load_baseline(query_name)
    assert baseline is not None, f"No baseline found for {query_name}. Run with --record-golden"
    
    # Diff current trace against baseline
    diffs = diff_traces(trace, baseline)
    
    # We only care about ROUTING (handoffs/tools) and METRICS (cost) changes
    critical_diffs = [
        d for d in diffs
        if d.diff_type in (DiffType.TOOLS_CHANGED, DiffType.SEQUENCE_CHANGED, DiffType.COST_SPIKE, DiffType.ROUTING_CHANGED)
    ]
    
    if critical_diffs:
        diff_msgs = [f"- {d.diff_type.upper()}: {d.message}" for d in critical_diffs]
        pytest.fail(
            f"Regression detected for query '{query_name}':\n" + "\n".join(diff_msgs)
        )
