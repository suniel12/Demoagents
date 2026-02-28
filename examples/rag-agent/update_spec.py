import yaml

with open('agentci_spec.yaml', 'r') as f:
    spec = yaml.safe_load(f)

# The original 4 queries are already there. We will completely replace the queries list
# with the robust set combining the original edge cases and the ones from test_rag.py.

queries = [
    {
        "query": "How do I install AgentCI?",
        "description": "Core in-scope question — agent must retrieve from docs",
        "tags": ["smoke", "in-scope", "happy-path"],
        "correctness": {
            "expected_in_answer": ["pip install", "3.10"]
        },
        "path": {
            "expected_tools": ["retrieve_docs"],
            "min_tool_recall": 1.0,
            "max_tool_calls": 5,
            "match_mode": "subset"
        },
        "cost": {"max_llm_calls": 5, "max_total_tokens": 3000}
    },
    {
        "query": "What are the three evaluation layers in AgentCI?",
        "description": "Core in-scope multi-chunk retrieval",
        "tags": ["in-scope"],
        "correctness": {"expected_in_answer": ["correctness", "path", "cost"]},
        "path": {"expected_tools": ["retrieve_docs"]}
    },
    {
        "query": "What's the CEO's favorite restaurant?",
        "description": "Out of scope question",
        "tags": ["out-of-scope"],
        "path": {"max_tool_calls": 0}
    },
    {
        "query": "Hello!",
        "description": "Greeting",
        "tags": ["greeting"],
        "path": {"max_tool_calls": 0}
    },
    {
        "query": "Hello, how are you?",
        "description": "Greeting 2",
        "tags": ["greeting"],
        "path": {"max_tool_calls": 0}
    },
    {
        "query": "How do I fail the CI pipeline if the agent uses forbidden tools?",
        "description": "Core in-scope technical",
        "tags": ["in-scope"],
        "correctness": {"expected_in_answer": ["correctness", "fail", "exit 1", "forbidden tools"]},
        "path": {"expected_tools": ["retrieve_docs"]}
    },
    {
        "query": "Does AgentCI support Anthropic models for testing?",
        "description": "Core in-scope technical 2",
        "tags": ["in-scope"],
        "correctness": {"expected_in_answer": ["AnthropicMocker"], "not_in_answer": ["Bedrock"]},
        "path": {"expected_tools": ["retrieve_docs"]}
    },
    {
        "query": "Is AgentCI free to use?",
        "description": "Core in-scope licensing",
        "tags": ["in-scope"],
        "correctness": {"expected_in_answer": ["open source", "Apache 2.0"]},
        "path": {"expected_tools": ["retrieve_docs"]}
    },
    {
        "query": "What's the weather in Austin?",
        "description": "Out of scope specific",
        "tags": ["out-of-scope"],
        "correctness": {"expected_in_answer": ["agentci", "can only answer", "documentation assistant"]},
        "path": {"max_tool_calls": 0}
    },
    {
        "query": "What's the weather in Tokyo?",
        "description": "Out of scope original",
        "tags": ["out-of-scope", "demo"],
        "path": {"max_tool_calls": 0, "forbidden_tools": ["tavily_search", "web_search", "retrieve_docs"]}
    },
    {
        "query": "How do I configure an AWS load balancer for the enterprise tier?",
        "description": "Technical out-of-scope — must not hallucinate AWS instructions",
        "tags": ["edge-case", "out-of-scope", "anti-hallucination"],
        "path": {"max_tool_calls": 0}
    },
    {
        "query": "How do I install AgentCI and what's the weather in Tokyo?",
        "description": "Mixed-intent query — must retrieve for installation but decline weather",
        "tags": ["edge-case", "mixed-intent"],
        "correctness": {"expected_in_answer": ["pip install"], "not_in_answer": ["degrees", "forecast", "sunny"]},
        "path": {"expected_tools": ["retrieve_docs"], "max_tool_calls": 5}
    },
    {
        "query": "What is the exact release date for AgentCI version 4.0?",
        "description": "Unanswerable query that triggers rewrite_question",
        "tags": ["rewrite-loop"],
        "path": {"expected_tools": ["rewrite_question"]}
    },
    {
        "query": "What is the name of the top contributor to the AgentCI codebase who lives in California?",
        "description": "Unanswerable query that tests max retries bounds",
        "tags": ["rewrite-loop", "max-retries"],
        "path": {"expected_tools": ["rewrite_question"]}
    }
]

spec["queries"] = queries

with open('agentci_spec.yaml', 'w') as f:
    yaml.dump(spec, f, sort_keys=False)

print("Updated agentci_spec.yaml with all queries from test_rag.py")
