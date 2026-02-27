from agentci.capture import TraceContext
from agent import generate_answer_api

def run_for_agentci(query: str):
    with TraceContext(agent_name="rag-agent") as ctx:
        output, state = generate_answer_api(query)
        ctx.attach_langgraph_state(state)
        # We must assign the final string to the trace so AgentCI's Correctness layer can read it
        if ctx.trace.spans:
            ctx.trace.spans[-1].output_data = str(output)
        ctx.trace.metadata["final_output"] = str(output)
    return ctx.trace
