# Getting Started with AgentCI

## Installation

Install AgentCI using pip:

```
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
   ```
   pip install agentci
   ```

2. **Initialize your project:**
   ```
   agentci init
   ```
   This generates:
   - `.github/workflows/agentci.yml` — GitHub Actions workflow
   - `agentci_spec.yaml` — Your test specification
   - `.git/hooks/pre-push` — Optional pre-push hook

3. **Write your spec:**
   Edit `agentci_spec.yaml` to define your agent's expected behavior. See the Spec Format section for details.

4. **Validate your spec:**
   ```
   agentci validate agentci_spec.yaml
   ```

5. **Run tests:**
   ```
   agentci test --config agentci_spec.yaml --format console
   ```

6. **Save a golden baseline:**
   ```
   agentci save --agent my-agent --version v1 --trace-file trace.json --config agentci_spec.yaml
   ```

7. **Diff against baselines:**
   ```
   agentci diff --baseline v1 --compare v2 --agent my-agent
   ```

## Integration with pytest

AgentCI also works natively with pytest. You can use the Python API directly:

```python
from agentci import load_spec, run_spec

spec = load_spec("agentci_spec.yaml")
results = run_spec(spec, my_agent_function, max_workers=4)

for result in results:
    assert not result.hard_fail, f"Query '{result.query}' failed correctness"
```

Or use the pytest plugin with fixtures:

```python
from agentci.assertions import assert_golden_match

def test_billing_regression():
    trace = run_your_agent("I was charged twice")
    assert_golden_match(trace, "golden/billing_flow.json")
```
