import asyncio
import os
import json
from devagent.agent.core import DevAgent

async def test_live_agent():
    print(f"Initializing DevAgent with model: {os.getenv('MODEL_NAME', 'claude-3-5-haiku-latest')}")
    agent = DevAgent()
    print("Agent initialized. Running analysis on 'langchain-ai/langchain'...")
    
    trace = await agent.analyze("https://github.com/langchain-ai/langchain")
    
    print("\n--- TRACE RESULTS ---")
    print(f"Success: {trace.success}")
    if trace.error:
        print(f"Error: {trace.error}")
        
    print(f"Tools called: {trace.tool_names_called}")
    print(f"Duration: {trace.total_duration_ms:.0f} ms")
    print(f"Input Tokens: {trace.input_tokens}")
    print(f"Output Tokens: {trace.output_tokens}")
    print(f"Total Tokens: {trace.total_tokens}")
    print(f"Estimated Cost: ${trace.estimated_cost_usd:.6f}")
    
    print("\n--- FINAL REPORT ---")
    print(trace.final_report)

if __name__ == "__main__":
    asyncio.run(test_live_agent())
