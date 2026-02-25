"""
Interactive Chat with TechCorp Support Router.

Usage:
    python chat.py

Sends your queries to the multi-agent support router and displays
the AgentCI trace summary after each interaction.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from support_router.run import run_agent_async, get_processor
from agents.tracing import set_trace_processors


async def main():
    processor = get_processor()
    set_trace_processors([processor])

    print()
    print("🏢  TechCorp Support Router")
    print("═" * 50)
    print("Interactive mode — type a customer query to test routing.")
    print("Commands:  'quit' to exit  |  'trace' for last trace detail")
    print("═" * 50)
    print()

    last_trace = None

    while True:
        try:
            query = input("💬 Customer> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye!")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("👋 Bye!")
            break

        if query.lower() == "trace" and last_trace:
            print("\n📋 Full Trace Detail:")
            print(f"   Trace ID:  {last_trace.trace_id}")
            print(f"   Framework: {last_trace.framework}")
            print(f"   Spans ({len(last_trace.spans)}):")
            for i, s in enumerate(last_trace.spans):
                print(f"     [{i}] {s.kind.value:12s}  name={s.name}")
                if s.from_agent or s.to_agent:
                    print(f"         handoff: {s.from_agent} → {s.to_agent}")
                if s.tool_calls:
                    for tc in s.tool_calls:
                        print(f"         tool: {tc.tool_name}({tc.arguments})")
                if s.llm_calls:
                    for lc in s.llm_calls:
                        print(f"         llm: model={lc.model} tokens={lc.tokens_in}+{lc.tokens_out}")
            print()
            continue

        if query.lower() == "trace" and not last_trace:
            print("   (no trace yet — send a query first)\n")
            continue

        print("⏳ Processing...\n")

        try:
            trace = await run_agent_async(query)
            last_trace = trace
        except Exception as e:
            print(f"❌ Error: {e}\n")
            continue

        if trace:
            # Routing summary
            agents = trace.agents_involved
            handoffs = trace.get_handoffs()
            guardrails = trace.guardrails_triggered

            print("┌─ 📊 AgentCI Trace Summary ─────────────────────")
            print(f"│  Agents:     {' → '.join(agents) if agents else '(none)'}")

            if handoffs:
                for h in handoffs:
                    print(f"│  Handoff:    {h.from_agent} → {h.to_agent}")
            else:
                print("│  Handoff:    ⚠️  NONE (triage answered directly)")

            if guardrails:
                print(f"│  Guardrails: 🚨 {', '.join(guardrails)}")

            print(f"│  Tokens:     {trace.total_tokens}")
            print(f"│  Cost:       ${trace.total_cost_usd:.4f}")
            print("├─ 💬 Response ──────────────────────────────────")

            output = trace.metadata.get("final_output", "(no output captured)")
            # Word-wrap the output
            words = output.split()
            line = "│  "
            for word in words:
                if len(line) + len(word) + 1 > 60:
                    print(line)
                    line = "│  " + word
                else:
                    line += " " + word if line != "│  " else word
            if line.strip("│ "):
                print(line)

            print("└────────────────────────────────────────────────")
        else:
            print("⚠️  No trace captured")

        print()


if __name__ == "__main__":
    asyncio.run(main())
