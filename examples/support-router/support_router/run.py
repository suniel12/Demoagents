"""CLI runner for TechCorp Support Router with AgentCI tracing."""

import asyncio
import os
import sys
from typing import Any, cast

from dotenv import load_dotenv
from agents import Runner
from agents.tracing import set_trace_processors
from agents.tracing.processor_interface import TracingProcessor
from agents.exceptions import InputGuardrailTripwireTriggered

from ciagent.adapters.openai_agents import CIAgentTraceProcessor
from .agents.triage import triage_agent


# Load environment variables
load_dotenv()

# Global trace processor instance — shared across all runs
_processor = CIAgentTraceProcessor()


def get_processor() -> CIAgentTraceProcessor:
    """Return the shared AgentCI trace processor."""
    return _processor


async def run_agent_async(query: str):
    """Run the support router and return the AgentCI Trace."""
    # Replace default processors so we don't need an OpenAI API key 
    # for the traces dashboard (we only need it for the LLM calls)
    processors: list[TracingProcessor] = [_processor]
    set_trace_processors(processors)
    
    try:
        result = await Runner.run(triage_agent, query)
        trace = _processor.get_last_trace()
        
        # Attach the final output text to the trace
        if trace and result.final_output:
            trace.metadata["final_output"] = str(result.final_output)
            if trace.spans:
                trace.spans[-1].output_data = str(result.final_output)
        
        return trace
    except InputGuardrailTripwireTriggered as e:
        # Guardrail blocked the query — still return the trace
        trace = _processor.get_last_trace()
        if trace:
            trace.metadata["guardrail_blocked"] = True
            trace.metadata["guardrail_message"] = str(e)
        return trace


def run_agent(query: str):
    """Synchronous wrapper for run_agent_async."""
    return asyncio.run(run_agent_async(query))


async def respond_async(messages: list[dict]):
    """Multi-turn entry point: full conversation history in, Trace out.

    The history (user + assistant turns) is passed to the triage agent as
    the run input — the same shape a production multi-turn deployment would
    use, so input guardrails see the whole transcript, exactly as they
    would live.
    """
    processors: list[TracingProcessor] = [_processor]
    set_trace_processors(processors)

    try:
        result = await Runner.run(triage_agent, cast(Any, list(messages)))
        trace = _processor.get_last_trace()
        if trace and result.final_output:
            trace.metadata["final_output"] = str(result.final_output)
            if trace.spans:
                trace.spans[-1].output_data = str(result.final_output)
        return trace
    except InputGuardrailTripwireTriggered as e:
        # Guardrail blocked the turn — surface what the customer experiences
        # so scenario checks can assert on it.
        trace = _processor.get_last_trace()
        blocked_msg = f"[BLOCKED by input guardrail] {e}"
        if trace:
            trace.metadata["guardrail_blocked"] = True
            trace.metadata["guardrail_message"] = str(e)
            trace.metadata["final_output"] = blocked_msg
            return trace
        return blocked_msg


def respond(messages: list[dict]):
    """Synchronous conversation runner for `ciagent simulate`."""
    return asyncio.run(respond_async(messages))


def main():
    """Interactive CLI for testing the support router."""
    print("🏢 TechCorp Support Router")
    print("=" * 40)
    print("Type a customer query (or 'quit' to exit)\n")
    
    while True:
        try:
            query = input("Customer> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
            
        if not query or query.lower() in ("quit", "exit", "q"):
            break
        
        print("\n⏳ Processing...")
        trace = run_agent(query)
        
        if trace:
            print(f"\n📊 Trace Summary:")
            print(f"   Agents:   {trace.agents_involved}")
            handoffs = trace.get_handoffs()
            if handoffs:
                for h in handoffs:
                    print(f"   Handoff:  {h.from_agent} → {h.to_agent}")
            print(f"   Cost:     ${trace.total_cost_usd:.4f}")
            print(f"   Response: {trace.metadata.get('final_output', 'N/A')[:200]}")
        print()


if __name__ == "__main__":
    main()
