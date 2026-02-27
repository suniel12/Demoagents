# Installation & Quickstart

## Installation

Install AgentCI using pip:

```bash
pip install agentci
```

AgentCI requires Python 3.10 or later.

## Dependencies

AgentCI has minimal required dependencies:
- pydantic (for schema validation)
- click (for CLI)
- rich (for colorful terminal output)
- pyyaml (for YAML spec loading)
- jinja2 (for template generation)

Optional dependencies for specific features:
- anthropic (for LLM judge with Claude models)
- openai (for LLM judge with GPT models, and OpenAI embeddings)

## Quick Start

1. **Install AgentCI:**
   ```bash
   pip install agentci
   ```

2. **Initialize your project:**
   ```bash
   agentci init
   ```
   This generates:
   - `.github/workflows/agentci.yml` — GitHub Actions workflow
   - `agentci_spec.yaml` — Your test specification
   - `.git/hooks/pre-push` — Optional pre-push hook

3. **Write your spec:**
   Edit `agentci_spec.yaml` to define your agent's expected behavior. 

4. **Validate your spec:**
   ```bash
   agentci validate agentci_spec.yaml
   ```

5. **Run tests:**
   ```bash
   agentci test --config agentci_spec.yaml --format console
   ```

6. **Save a golden baseline:**
   ```bash
   agentci save --agent my-agent --version v1 --trace-file trace.json --config agentci_spec.yaml
   ```

7. **Diff against baselines:**
   ```bash
   agentci diff --baseline v1 --compare v2 --agent my-agent
   ```
