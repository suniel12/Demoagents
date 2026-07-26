from demo_runner import run_for_ciagent
import json

trace = run_for_ciagent("How do I install CIAgent and what's the weather in Tokyo?")
for span in trace.spans:
    print(f"Span: {span.name} (Kind: {span.kind})")
    print(f"  Attrs: {span.attributes}")
    for tc in span.tool_calls:
        print(f"   ToolCall: {tc.tool_name}")
        print(f"      Args: {tc.arguments}")

from ciagent.loader import load_spec
from ciagent.engine.runner import evaluate_query
import json

spec = load_spec("ciagent_spec.yaml")
query = next(q for q in spec.queries if q.query == "How do I install CIAgent and what's the weather in Tokyo?")

res = evaluate_query(query, trace, None, None, ".")

print(json.dumps(res.correctness.details.get("span_assertions", []), indent=2))
print("Messages:", res.correctness.messages)
