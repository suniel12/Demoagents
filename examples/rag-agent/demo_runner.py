from ciagent.capture import langgraph_trace
from agent import generate_answer_api

def run_for_agentci(query: str):
    with langgraph_trace("rag-agent") as ctx:
        output, state = generate_answer_api(query)
        ctx.attach(state)
        ctx.trace.metadata["final_output"] = str(output)
    return ctx.trace
