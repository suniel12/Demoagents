"""CLI runner for TechCorp Support Router with AgentCI tracing."""

import asyncio
import os
import sys

from dotenv import load_dotenv
from agents import Runner
from agents.tracing import set_trace_processors

from agentci.adapters.openai_agents import AgentCITraceProcessor
from .agents.triage import triage_agent


# Load environment variables
load_dotenv()

# Global trace processor instance — shared across all runs
_processor = AgentCITraceProcessor()


def get_processor() -> AgentCITraceProcessor:
    """Return the shared AgentCI trace processor."""
    return _processor


async def run_agent_async(query: str):
    """Run the support router and return the AgentCI Trace."""
    # Replace default processors so we don't need an OpenAI API key 
    # for the traces dashboard (we only need it for the LLM calls)
    set_trace_processors([_processor])
    
    result = await Runner.run(triage_agent, query)
    trace = _processor.get_last_trace()
    
    # Attach the final output text to the trace
    if trace and result.final_output:
        trace.metadata["final_output"] = str(result.final_output)
    
    return trace


def run_agent(query: str):
    """Synchronous wrapper for run_agent_async."""
    return asyncio.run(run_agent_async(query))


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
