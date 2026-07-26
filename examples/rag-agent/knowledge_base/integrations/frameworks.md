# Supported Agent Frameworks

CIAgent works seamlessly with the following AI agent frameworks out of the box:

- **OpenAI Agents SDK** — Native CIAgentTraceProcessor (2 lines to enable)
- **LangGraph / LangChain** — Captures conditional edges and tool calls via state attachment
- **Anthropic (raw)** — AnthropicMocker for zero-cost replay; native tool_use capture
- **Any Python agent** — Manual Trace/Span construction for custom frameworks

### Custom Python Agents
If you are using CrewAI or AutoGen, you can still use CIAgent. You will need to construct the `Trace` and `Span` objects manually from your framework's debug output hooks and return the final `Trace` object from your runner function script. CIAgent's engine parses these standardized `Trace` outputs.

## Automated Example Agents

CIAgent ships with three demo agents that showcase different architectures and testing patterns. All three run with zero API keys using the mock system.

### RAG Agent (LangGraph)
**Directory:** `DemoAgents/examples/rag-agent/`
**Architecture:** Retrieval → Grade → Rewrite/Generate pipeline

### Support Router (OpenAI Agents SDK)
**Directory:** `DemoAgents/examples/support-router/`
**Architecture:** Triage → Specialist multi-agent handoff with guardrails

### DevAgent (Anthropic SDK)
**Directory:** `DemoAgents/examples/dev-agent/`
**Architecture:** Sequential 8-tool GitHub repository analyzer
