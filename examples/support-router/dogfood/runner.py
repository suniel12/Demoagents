"""Model-parametrized runner for the F7 dogfood gate.

Mirrors support_router.run.run_agent but pins the model via RunConfig so the
same imported regression test can be run against the FAILING config
(gpt-4o-mini, where the money-out bug reproduces) and the FIXED config
(gpt-4.1, where the model upgrade resolved it):

    ciagent eval -c dogfood/dogfood_spec.yaml                    # gpt-4o-mini → RED
    DOGFOOD_MODEL=gpt-4.1 ciagent eval -c dogfood/dogfood_spec.yaml  # → GREEN

The gate is the point: a real production failure, frozen, that discriminates
between the buggy and fixed agent.
"""

import asyncio
import os

from agents import Runner, RunConfig, set_default_openai_api
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.tracing import set_trace_processors
from agents.tracing.processor_interface import TracingProcessor

from ciagent.adapters.openai_agents import CIAgentTraceProcessor
from support_router.agents.triage import triage_agent

DEFAULT_MODEL = "gpt-4o-mini"  # the config the bug was found on
_processor = CIAgentTraceProcessor()


async def _run_async(query: str):
    set_default_openai_api("chat_completions")
    processors: list[TracingProcessor] = [_processor]
    set_trace_processors(processors)
    model = os.environ.get("DOGFOOD_MODEL", DEFAULT_MODEL)
    try:
        result = await Runner.run(triage_agent, query, run_config=RunConfig(model=model))
        trace = _processor.get_last_trace()
        if trace and result.final_output:
            trace.metadata["final_output"] = str(result.final_output)
            if trace.spans:
                trace.spans[-1].output_data = str(result.final_output)
        return trace
    except InputGuardrailTripwireTriggered as e:
        trace = _processor.get_last_trace()
        if trace:
            trace.metadata["guardrail_blocked"] = True
            trace.metadata["final_output"] = f"[BLOCKED by input guardrail] {e}"
        return trace


def run_agent(query: str):
    """Synchronous runner hook for `ciagent eval`/`test`."""
    return asyncio.run(_run_async(query))
