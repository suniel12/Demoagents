# DevAgent — GitHub Repository Health Analyzer

> An AI-powered agent that analyzes GitHub repositories for code quality, dependency health, security signals, and community activity. Built as the reference demo for [AgentCI](https://github.com/your-org/agentci) — the CI/CD testing framework for AI agents.

## Why This Exists

DevAgent is not just a useful tool — it's the **dogfooding vehicle** for AgentCI. Every testing challenge that developers face when building AI agents shows up naturally in this project:

- **Tool selection**: Does the agent pick the right tool for the job?
- **Sequencing**: Does it call tools in the right order?
- **Error recovery**: What happens when the GitHub API rate-limits us?
- **Cost guardrails**: Does a single repo analysis stay within budget?
- **Output quality**: Is the health report accurate and specific?

Each phase of development adds complexity and a corresponding new layer of AgentCI tests.

## Project Phases

| Phase | Focus | Tools | AgentCI Capabilities Tested |
|-------|-------|-------|-----------------------------|
| **0** | Foundation | `github_repo_metadata` | Trace capture, basic assertions, cost tracking |
| **1** | Multi-tool sequential | + `github_list_files`, `github_read_file`, `dependency_analyzer` | Sequencing assertions, golden trace diffing |
| **2** | Conditional branching | + `github_actions_analyzer`, `license_checker`, `community_health_scorer` | Conditional execution, dynamic tool selection |
| **3** | Error recovery | Mock/failure injection | Retry testing, graceful degradation, chaos tests |
| **4** | Output quality | LLM-as-judge | Factual accuracy, specificity, completeness evals |
| **5** | CI/CD integration | GitHub Actions pipeline | Full pipeline, regression detection, dashboards |

## Current Phase: 0 — Foundation

### Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/devagent.git
cd devagent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set your API keys
cp .env.example .env
# Edit .env with your GITHUB_TOKEN and ANTHROPIC_API_KEY

# Run the agent
python -m devagent.agent.run "https://github.com/langchain-ai/langchain"

# Run AgentCI tests
agentci test tests/
```

## Architecture

```
User Input (repo URL)
       │
       ▼
┌─────────────────┐
│   Agent Core     │  ← LLM decides which tools to call
│   (Claude API)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Tool Registry   │  ← All tools registered with schemas
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│Tool 1 │ │Tool N │  ← Each tool: typed input → typed output
└───────┘ └───────┘
         │
         ▼
┌─────────────────┐
│ Report Generator │  ← Structured health report
└─────────────────┘
```

## License

MIT
