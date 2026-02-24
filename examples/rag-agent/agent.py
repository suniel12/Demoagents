import os
from typing import Literal, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "agents", ".env")
load_dotenv(dotenv_path=ENV_PATH)

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END, MessagesState

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
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
splits = text_splitter.split_documents(docs)
vectorstore = InMemoryVectorStore.from_documents(documents=splits, embedding=OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

def retrieve_docs(query: str) -> str:
    """Retrieve internal Novacorp knowledge base documents."""
    docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)

# Setup LLM
llm = ChatOpenAI(model="gpt-4o-mini")

class GradeOutput(BaseModel):
    """Output for document grading."""
    binary_score: str = Field(description="Relevance score 'yes' or 'no'")

### Graph Nodes ###

def generate_query_or_respond(state: MessagesState):
    """First LLM call to decide if retrieval is needed or answer directly."""
    # We bind the retriever as a tool
    llm_with_tools = llm.bind_tools([{"name": "retrieve_docs", "description": "Retrieve internal Novacorp knowledge base documents.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}])
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def retrieve_docs_node(state: MessagesState):
    """Retrieve documents using the tool call."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        tc = last_msg.tool_calls[0]
        if tc["name"] == "retrieve_docs":
            docs_content = retrieve_docs(tc["args"]["query"])
            tool_msg = ToolMessage(content=docs_content, tool_call_id=tc["id"], name=tc["name"])
            return {"messages": [tool_msg]}
    return {"messages": []}

def grade_documents(state: MessagesState):
    """Grade the retrieved documents for relevance to the original question."""
    # The last message is the tool response containing docs. The first message is the user query.
    original_query = state["messages"][0].content
    docs_content = state["messages"][-1].content
    
    grader_llm = llm.with_structured_output(GradeOutput)
    prompt = f"Grade if the following docs are relevant to the query '{original_query}'. strictly reply 'yes' or 'no'.\n\nDocs:\n{docs_content}"
    result = grader_llm.invoke([HumanMessage(content=prompt)])
    
    # Store grading result as a message or state (we use an AI message to trace it easily)
    return {"messages": [AIMessage(content=f'{{"binary_score": "{result.binary_score.lower()}"}}', name="grade_artifacts")]}

def generate_answer(state: MessagesState):
    """Generate the final answer based on retrieved documents."""
    # The documents are 2 messages back (before the grade message)
    docs_msg = state["messages"][-2]
    original_query = state["messages"][0].content
    
    messages = [
        SystemMessage(content="You are a helpful assistant with access to a knowledge base. Answer the user's question based strictly on the provided context. If the context does not contain the answer, you must reply 'I don't have information about that.' Do not use your pre-trained knowledge to answer."),
        HumanMessage(content=f"Context: {docs_msg.content}\n\nQuestion: {original_query}")
    ]
    response = llm.invoke(messages)
    return {"messages": [response]}

def rewrite_question(state: MessagesState):
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

def route_after_query(state: MessagesState) -> Literal["retrieve_docs", "__end__"]:
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "retrieve_docs"
    return "__end__"

def route_after_grade(state: MessagesState) -> Literal["generate_answer", "rewrite_question"]:
    last_msg = state["messages"][-1]
    if "yes" in last_msg.content.lower():
        return "generate_answer"
    
    # Check for recursion limit: Count how many times we've rewriten
    rewrite_count = sum(1 for m in state["messages"] if getattr(m, "name", "") == "rewrite_question")
    if rewrite_count >= 3:
        return "generate_answer"
        
    return "rewrite_question"

### Build Graph ###
builder = StateGraph(MessagesState)

builder.add_node("generate_query_or_respond", generate_query_or_respond)
builder.add_node("retrieve_docs", retrieve_docs_node)
builder.add_node("grade_documents", grade_documents)
builder.add_node("generate_answer", generate_answer)
builder.add_node("rewrite_question", rewrite_question)

builder.add_edge(START, "generate_query_or_respond")
builder.add_conditional_edges("generate_query_or_respond", route_after_query)
builder.add_edge("retrieve_docs", "grade_documents")
builder.add_conditional_edges("grade_documents", route_after_grade)
builder.add_edge("rewrite_question", "retrieve_docs")
builder.add_edge("generate_answer", END)

graph = builder.compile()

# Our original generate_answer wrapper for backwards compat with tests
def generate_answer_api(query: str):
    result = graph.invoke({"messages": [HumanMessage(content=query)]})
    return result["messages"][-1].content, result
