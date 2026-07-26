# Installation & Quickstart

## Installation

Install CIAgent using pip:

```bash
pip install ciagent
```

CIAgent requires Python 3.10 or later.

## Dependencies

CIAgent has minimal required dependencies:
- pydantic (for schema validation)
- click (for CLI)
- rich (for colorful terminal output)
- pyyaml (for YAML spec loading)
- jinja2 (for template generation)

Optional dependencies for specific features:
- anthropic (for LLM judge with Claude models)
- openai (for LLM judge with GPT models, and OpenAI embeddings)

## Quick Start

1. **Install CIAgent:**
   ```bash
   pip install ciagent
   ```

2. **Initialize your project:**
   ```bash
   ciagent init
   ```
   This generates:
   - `.github/workflows/ciagent.yml` — GitHub Actions workflow
   - `ciagent_spec.yaml` — Your test specification
   - `.git/hooks/pre-push` — Optional pre-push hook

3. **Write your spec:**
   Edit `ciagent_spec.yaml` to define your agent's expected behavior. 

4. **Validate your spec:**
   ```bash
   ciagent validate ciagent_spec.yaml
   ```

5. **Run tests:**
   ```bash
   ciagent test --config ciagent_spec.yaml --format console
   ```

6. **Save a golden baseline:**
   ```bash
   ciagent save --agent my-agent --version v1 --trace-file trace.json --config ciagent_spec.yaml
   ```

7. **Diff against baselines:**
   ```bash
   ciagent diff --baseline v1 --compare v2 --agent my-agent
   ```
