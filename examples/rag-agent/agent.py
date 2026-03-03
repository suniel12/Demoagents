import os
from typing import Literal, List, TypedDict, Annotated, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "agents", ".env")
load_dotenv(dotenv_path=ENV_PATH)

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Build knowledge base path
KB_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")

def load_knowledge_base() -> List[Document]:
    docs = []
    for root, _, files in os.walk(KB_DIR):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    docs.append(Document(page_content=f.read(), metadata={"source": path}))
    return docs

docs = load_knowledge_base()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)
vectorstore = InMemoryVectorStore.from_documents(documents=splits, embedding=OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

def retrieve_docs(query: str) -> str:
    """Retrieve AgentCI documentation from the knowledge base."""
    docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)

# Setup LLM
llm = ChatOpenAI(model="gpt-4o-mini")

### State ###

class RAGState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    sub_questions: Optional[list[str]]   # set by decompose_query; empty = single path
    is_decomposed: Optional[bool]        # routing flag

### Pydantic Models ###

class GradeOutput(BaseModel):
    """Output for document grading."""
    binary_score: str = Field(description="Relevance score 'yes' or 'no'")

class DecomposeOutput(BaseModel):
    sub_questions: list[str] = Field(description=(
        "Atomic sub-questions if the query has 2+ DISTINCT AgentCI-only questions. "
        "Empty list for single questions, greetings, out-of-scope, or mixed-intent."
    ))

### Graph Nodes ###

def decompose_query(state: RAGState) -> dict:
    """Detect compound AgentCI queries and break them into atomic sub-questions."""
    original_query = state["messages"][0].content
    decompose_llm = llm.with_structured_output(DecomposeOutput)
    prompt = (
        "You are a query decomposition assistant for an AgentCI documentation chatbot.\n\n"
        "Your job: determine if a query contains 2 or more DISTINCT AgentCI-related questions "
        "that each need separate information. If so, return them as atomic sub-questions.\n\n"
        "RULES:\n"
        "1. Only decompose when EVERY sub-question is about AgentCI. If ANY part is out-of-scope "
        "(weather, AWS, sports, cooking, celebrities), return an empty list.\n"
        "2. Only decompose when there are genuinely 2+ distinct information needs.\n"
        "3. Greetings, single questions, and unanswerable single questions → return [].\n"
        "4. Mixed-intent queries (some AgentCI, some not) → return [] (the triage node handles them).\n\n"
        "EXAMPLES:\n"
        "- 'Can I get a refund if I'm on Enterprise, and who do I contact for support?' "
        "→ ['Can I get a refund on the Enterprise plan?', 'Who do I contact for support?']\n"
        "- 'How do I install AgentCI and what's the weather in Tokyo?' → [] (mixed-intent)\n"
        "- 'How do I install AgentCI?' → [] (single question)\n"
        "- 'Hello!' → [] (greeting)\n\n"
        f"Query: {original_query}"
    )
    result = decompose_llm.invoke([HumanMessage(content=prompt)])
    sub_questions = result.sub_questions
    if len(sub_questions) >= 2:
        return {"sub_questions": sub_questions, "is_decomposed": True}
    else:
        return {"sub_questions": [], "is_decomposed": False}


def generate_query_or_respond(state: RAGState):
    """First LLM call to decide if retrieval is needed or answer directly."""
    system = SystemMessage(content=(
        "You are an AgentCI documentation assistant. You help users with questions about "
        "AgentCI — the open-source, trace-based regression testing framework for AI agents.\n\n"
        "You can answer questions about: installation and setup, the agentci_spec.yaml format, "
        "You can answer questions about: installation and setup, the agentci_spec.yaml format, "
        "the three-layer evaluation model (Correctness / Path / Cost), CLI commands, "
        "assertions and metrics, the mock system, CI/CD and GitHub Actions integration, "
        "golden baselines and the diff engine, demo agents (RAG Agent, Support Router, DevAgent), "
        "the roadmap, pricing, licensing, open-source status, and how AgentCI compares to other "
        "tools (DeepEval, promptfoo, LangSmith, Braintrust). Assume any software/SaaS related question "
        "is intended about AgentCI unless proven otherwise.\n\n"
        "DECISION RULES:\n"
        "1. If the question is ENTIRELY about AgentCI or AI agent testing, call retrieve_docs "
        "with the full question.\n"
        "2. If the question is a MIX — some parts about AgentCI, some unrelated (e.g. 'How do I "
        "install AgentCI AND what is the weather?') — strip out the unrelated parts and only pass the relevant query to retrieve_docs.\n"
        "3. If the question is ENTIRELY unrelated to AgentCI or AI software (e.g. weather only, sports only, "
        "cooking), do NOT call retrieve_docs. Reply with a friendly, brief response. For greetings, "
        "greet back warmly and offer to help with AgentCI questions. For off-topic questions, briefly "
        "say you specialize in AgentCI and offer to help with that instead.\n"
        "- Never answer from pre-trained knowledge for AgentCI topics — always retrieve first."
    ))
    messages = [system] + state["messages"]
    llm_with_tools = llm.bind_tools([{"name": "retrieve_docs", "description": "Retrieve AgentCI documentation from the knowledge base.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def retrieve_docs_node(state: RAGState):
    """Retrieve documents using the tool call."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        tc = last_msg.tool_calls[0]
        if tc["name"] == "retrieve_docs":
            docs_content = retrieve_docs(tc["args"]["query"])
            tool_msg = ToolMessage(content=docs_content, tool_call_id=tc["id"], name=tc["name"])
            return {"messages": [tool_msg]}
    return {"messages": []}

def multi_retrieve(state: RAGState) -> dict:
    """Retrieve documents for each sub-question in parallel."""
    sub_questions = state.get("sub_questions") or []
    results = [""] * len(sub_questions)

    def retrieve_one(question, index):
        return index, retrieve_docs(question)

    with ThreadPoolExecutor(max_workers=len(sub_questions)) as executor:
        futures = {executor.submit(retrieve_one, q, i): i for i, q in enumerate(sub_questions)}
        for future in as_completed(futures):
            idx, content = future.result()
            results[idx] = content

    parts = [f"=== Sub-question {i+1}: {q} ===\n{d}"
             for i, (q, d) in enumerate(zip(sub_questions, results))]
    combined_docs = "\n\n".join(parts)

    # Synthetic AIMessage with tool_calls so AgentCI's attach_langgraph_state
    # captures each retrieve_docs call (it only reads tool_calls from AIMessages).
    synthetic_tool_calls = [
        {"name": "retrieve_docs", "args": {"query": q}, "id": f"multi_retrieve_{i}"}
        for i, q in enumerate(sub_questions)
    ]
    messages: list = [AIMessage(content="", tool_calls=synthetic_tool_calls)]

    # N-1 individual ToolMessages + 1 final combined ToolMessage.
    # The combined final one is what generate_answer reads via state["messages"][-2].
    for i, (q, d) in enumerate(zip(sub_questions, results)):
        if i < len(sub_questions) - 1:
            messages.append(ToolMessage(content=d,
                                        tool_call_id=f"multi_retrieve_{i}",
                                        name="retrieve_docs"))
    messages.append(ToolMessage(content=combined_docs,
                                tool_call_id=f"multi_retrieve_{len(sub_questions)-1}",
                                name="retrieve_docs"))
    return {"messages": messages}

def grade_documents(state: RAGState):
    """Grade the retrieved documents for relevance.

    For decomposed queries: grade combined context against all sub-questions with an
    answerability-biased prompt (a doc saying the topic doesn't exist IS a valid answer).

    For single queries: grade against the actual retrieval query (not the raw user input)
    to prevent the rewrite loop on mixed queries where only the AgentCI part was sent to
    retrieve_docs.
    """
    docs_content = state["messages"][-1].content
    grader_llm = llm.with_structured_output(GradeOutput)

    if state.get("is_decomposed"):
        sub_questions = state.get("sub_questions") or []
        questions_str = "\n".join(f"- {q}" for q in sub_questions)
        prompt = (
            f"Do these docs contain enough information to answer ALL of the following "
            f"sub-questions, even if it requires inference? Reply 'yes' if the docs address "
            f"the sub-questions adequately (a doc saying the topic doesn't exist IS a valid "
            f"answer). Reply 'no' only if the docs are entirely off-topic.\n\n"
            f"Sub-questions:\n{questions_str}\n\nDocs:\n{docs_content}"
        )
    else:
        # Find the retrieval query from the most recent AIMessage that made a tool call
        retrieval_query = state["messages"][0].content  # fallback to original
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                tc = msg.tool_calls[0]
                if tc.get("name") == "retrieve_docs":
                    retrieval_query = tc["args"].get("query", retrieval_query)
                    break
        prompt = f"Do these docs contain enough information to answer the following question, even if it requires inference? Question: '{retrieval_query}'. Reply 'yes' or 'no'.\n\nDocs:\n{docs_content}"

    result = grader_llm.invoke([HumanMessage(content=prompt)])
    return {"messages": [AIMessage(content=f'{{"binary_score": "{result.binary_score.lower()}"}}', name="grade_artifacts")]}

def generate_answer(state: RAGState):
    """Generate the final answer based on retrieved documents."""
    # The documents are 2 messages back (before the grade message)
    docs_msg = state["messages"][-2]
    original_query = state["messages"][0].content

    messages = [
        SystemMessage(content=(
            "You are an AgentCI documentation assistant answering from a retrieved knowledge base.\n\n"
            "RULES:\n"
            "1. Answer the AgentCI-related parts of the question using ONLY the provided context. "
            "Do not use pre-trained knowledge.\n"
            "2. If the context does not cover the AgentCI part of the question, say: "
            "'I don't have that information in my knowledge base.'\n"
            "3. If the user's question contains parts clearly unrelated to AgentCI "
            "(e.g. weather, sports, recipes), simply ignore those parts. "
            "Do NOT add disclaimers like 'I can only help with AgentCI topics' — "
            "just answer the in-scope parts naturally.\n"
            "4. Keep responses helpful and natural. Do not end responses with scope disclaimers.\n"
            "5. When counting or listing items, always name each item with key details from the context.\n"
            "6. Be thorough — include all relevant details from the context, especially unique features, "
            "differentiators, and specific technical capabilities. Do not omit information that directly "
            "answers the question just because other sections already partially address it."
        )),
        HumanMessage(content=f"Context:\n{docs_msg.content}\n\nQuestion: {original_query}")
    ]
    response = llm.invoke(messages)
    return {"messages": [response]}

def rewrite_question(state: RAGState):
    """Rewrite the question to be better suited for retrieval, if grading failed."""
    original_query = state["messages"][0].content
    prompt = f"Rewrite this query for better search results. Output only the new query.\n\nOriginal: {original_query}"
    response = llm.invoke([HumanMessage(content=prompt)])

    # We create an AIMessage with a tool call to retriever, so the graph natively routes to retrieve_docs next
    tool_call = {
        "name": "retrieve_docs",
        "args": {"query": response.content},
        "id": "rewrite_tc"
    }
    # Name the message rewrite_question so AgentCI / LangGraph traces catch it
    return {"messages": [AIMessage(content="", tool_calls=[tool_call], name="rewrite_question")]}


### Conditional Edges ###

def route_after_decompose(state: RAGState) -> Literal["multi_retrieve", "generate_query_or_respond"]:
    return "multi_retrieve" if state.get("is_decomposed") else "generate_query_or_respond"

def route_after_query(state: RAGState) -> Literal["retrieve_docs", "__end__"]:
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "retrieve_docs"
    return "__end__"

def route_after_grade(state: RAGState) -> Literal["generate_answer", "rewrite_question"]:
    if state.get("is_decomposed"):   # multi-path: never rewrite
        return "generate_answer"

    last_msg = state["messages"][-1]
    if "yes" in last_msg.content.lower():
        return "generate_answer"

    # Check for recursion limit: Count how many times we've rewritten
    rewrite_count = sum(1 for m in state["messages"] if getattr(m, "name", "") == "rewrite_question")
    if rewrite_count >= 3:
        return "generate_answer"

    return "rewrite_question"

### Build Graph ###
builder = StateGraph(RAGState)

builder.add_node("decompose_query", decompose_query)
builder.add_node("generate_query_or_respond", generate_query_or_respond)
builder.add_node("retrieve_docs", retrieve_docs_node)
builder.add_node("multi_retrieve", multi_retrieve)
builder.add_node("grade_documents", grade_documents)
builder.add_node("generate_answer", generate_answer)
builder.add_node("rewrite_question", rewrite_question)

builder.add_edge(START, "decompose_query")
builder.add_conditional_edges("decompose_query", route_after_decompose)
builder.add_conditional_edges("generate_query_or_respond", route_after_query)
builder.add_edge("retrieve_docs", "grade_documents")
builder.add_edge("multi_retrieve", "grade_documents")
builder.add_conditional_edges("grade_documents", route_after_grade)
builder.add_edge("rewrite_question", "retrieve_docs")
builder.add_edge("generate_answer", END)

graph = builder.compile()

# Our original generate_answer wrapper for backwards compat with tests
def generate_answer_api(query: str):
    result = graph.invoke({"messages": [HumanMessage(content=query)]})
    return result["messages"][-1].content, result
