import json
import os
import yaml
from pathlib import Path

golden_dir = Path("tests/golden")
responses = {}

if not golden_dir.exists():
    print(f"Directory {golden_dir} not found. Ensure golden traces exist.")
    exit(1)

for f in golden_dir.glob("*.json"):
    with open(f) as file:
        data = json.load(file)
        
    query_name = f.stem
        
    seq = []
    
    spans = data.get("spans", [])
    
    # Sort spans by index to roughly emulate order
    # AgentCI actually has timestamps, but list order is usually insertion order
    
    for span in spans:
        kind = span.get("kind")
        metadata = span.get("metadata", {})
        
        if kind == "handoff":
            # Handoffs in the OpenAI Agents SDK are represented as a function call
            # with the name `transfer_to_Agent_Name` unless a specific name was provided 
            to_agent = span.get("to_agent")
            tool_name = span.get("name") # Usually "transfer_to_..."
            
            # OpenAI Agent routing relies on the generated tool name
            # The span name is the actual tool name called
            args = metadata.get("arguments", {})
            seq.append({"tool": tool_name, "arguments": args})
            
        elif kind == "tool_call":
            tool_name = span.get("name")
            args = metadata.get("arguments", {})
            if tool_name and not tool_name.startswith("transfer_to_") and tool_name not in ["Escalate", "handoff"]:
                seq.append({"tool": tool_name, "arguments": args})
                
    # Add final text
    final_text = "Mocked final answer: Success"
    # Or look for output from the last agent span
    agent_spans = [s for s in spans if s.get("kind") == "agent"]
    if agent_spans:
        last_agent = agent_spans[-1]
        outp = last_agent.get("metadata", {}).get("output", "")
        if outp and isinstance(outp, str):
            final_text = outp
            
    seq.append({"text": final_text})
    
    responses[query_name] = seq

os.makedirs("tests/fixtures", exist_ok=True)
with open("tests/fixtures/mock_responses.yaml", "w") as f:
    yaml.dump(responses, f, default_flow_style=False)

print(f"Regenerated mock_responses.yaml for {len(responses)} queries.")

