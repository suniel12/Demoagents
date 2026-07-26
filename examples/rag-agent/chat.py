import os
import sys
import warnings

warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)

# Ensure we can import the agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import generate_answer_api

def get_trajectory(state):
    """Helper to extract the reasoning path from the LangGraph state."""
    path = []
    
    # The first message is the human query, the rest are the agent's reasoning
    for msg in state.get("messages", [])[1:]:
        
        # Check for tool calls (e.g. retrieve_docs)
        if hasattr(msg, "tool_calls") and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                path.append(f"Tool: {tc.get('name', 'unknown')}")
                
        # Check for named messages (e.g. from grade_documents or rewrite_question)
        elif getattr(msg, "name", ""):
            path.append(getattr(msg, "name"))
            
    return " -> ".join(path) if path else "Direct Answer"

def main():
    print("==================================================")
    print("🤖 CIAgent Documentation Assistant 🤖")
    print("==================================================")
    print("Ask anything about CIAgent — installation, specs, CLI, comparisons, roadmap.")
    print("Watch the agent's 'Trajectory' to see it retrieve, grade, and rewrite queries!")
    print("Type 'exit' or 'quit' to quit.\n")

    while True:
        try:
            user_input = input("You: ")
            
            if user_input.lower().strip() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
                
            if not user_input.strip():
                continue
                
            print("Thinking...\n")
            
            # Run the graph
            answer, state = generate_answer_api(user_input)
            
            trajectory = get_trajectory(state)
            
            print(f"[Trajectory: {trajectory}]")
            print(f"Agent: {answer}\n")
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError encountered: {e}")

if __name__ == "__main__":
    main()
