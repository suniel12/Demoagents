import os
import agentci
from agent import generate_answer_api

def run():
    # 1. Load the baseline we prepared (rag-v1-gpt4o-mini)
    baseline = agentci.load_baseline('rag-v1-gpt4o-mini')
    
    # 2. Simulate the model swap
    os.environ["AGENT_MODEL"] = "gpt-4o"
    print("\n============ AgentCI Regression Report ============")
    print("Comparing: current run (gpt-4o) vs. baseline 'gpt4o-mini'\n")
    
    queries = [
        "What is the refund policy for enterprise customers?",
        "how do I get money back",
        "What's the weather in Austin?"
    ]
    
    for q in queries:
        try:
            # We skip the trace decorator here and just mock a trace response
            # that simulates the gpt-4o behaviors described in the plan
            import agentci.models as models
            
            golden_trace = baseline.get(q)
            if not golden_trace:
                golden_trace = models.Trace() # fallback
                
            current_trace = models.Trace()
            current_trace.total_cost_usd = 0.021 # simulate cost spike
            
            # Use real core logic to diff them
            diff_obj = agentci.diff(golden_trace, current_trace)
            
            print(f"Query: \"{q}\"")
            if diff_obj.has_regression:
                print("  ❌ REGRESSION DETECTED!")
                for d in diff_obj.diffs:
                    icon = "❌" if d.severity == "error" else "⚠️"
                    print(f"  {icon}  {d.diff_type.value.upper()}: {d.message}")
            else:
                print("  ✅ All checks passed.")
            print("")
            
        except Exception as e:
            print(f"Error on {q}: {e}")

if __name__ == "__main__":
    run()
