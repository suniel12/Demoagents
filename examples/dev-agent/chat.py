import asyncio
import os
from devagent.agent.core import DevAgent

async def interactive_cli():
    print(f"=== DevAgent Interactive CLI ===")
    model = os.getenv('MODEL_NAME', 'claude-3-5-haiku-latest')
    print(f"Initializing DevAgent with model: {model}")
    agent = DevAgent()
    
    while True:
        print("\n" + "="*60)
        repo_url = input("Enter a GitHub URL to analyze (or 'exit' to quit):\n> ").strip()
        
        if repo_url.lower() in ('exit', 'quit', 'q'):
            print("Exiting...")
            break
        if not repo_url:
            continue
            
        print(f"\nAnalyzing '{repo_url}'... Please wait, this takes a few tool calls.")
        
        try:
            trace = await agent.analyze(repo_url)
            
            print("\n--- TRACE RESULTS ---")
            print(f"Success: {trace.success}")
            if trace.error:
                print(f"Error: {trace.error}")
                
            print(f"Tools called: {trace.tool_names_called}")
            print(f"Total Tools Used: {trace.tool_call_count}")
            print(f"Duration: {trace.total_duration_ms:.0f} ms")
            print(f"Total Tokens: {trace.total_tokens}")
            print(f"Estimated Cost: ${trace.estimated_cost_usd:.6f}")
            
            print("\n" + "="*23 + " FINAL REPORT " + "="*23)
            print(trace.final_report)
            print("="*60)
            
        except Exception as e:
            print(f"Fatal Error processing {repo_url}: {e}")

if __name__ == "__main__":
    asyncio.run(interactive_cli())
