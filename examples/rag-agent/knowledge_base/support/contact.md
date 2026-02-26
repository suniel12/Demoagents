# AgentCI CLI Reference

AgentCI provides six CLI commands for the full testing lifecycle.

## agentci init

Scaffold a new AgentCI test suite in your project:

```bash
agentci init
```

Generates:
- `.github/workflows/agentci.yml` — GitHub Actions workflow with deterministic + LLM judge jobs
- `agentci_spec.yaml` — Starter spec template
- `.git/hooks/pre-push` — Optional git hook to run tests before pushing

Options:
- `--python-version` — Python version for CI (default: 3.10)
- `--test-path` — Path to your test directory
- `--dependency-file` — requirements.txt or pyproject.toml

## agentci validate

Validate an agentci_spec.yaml file against the Pydantic schema:

```bash
agentci validate agentci_spec.yaml
```

Output: `✅ Valid: 20 queries, agent='support-router'`

Checks for: missing required fields, invalid match modes, threshold ranges, empty queries.

## agentci test

Run the full evaluation pipeline:

```bash
agentci test --config agentci_spec.yaml --format console --workers 4
```

Options:
- `--config`, `-c` — Path to spec file (default: agentci_spec.yaml)
- `--tags`, `-t` — Filter queries by tag (repeatable)
- `--format` — Output format: console, github, json, prometheus
- `--baseline-dir` — Override baseline directory
- `--workers`, `-w` — Max parallel workers (default: 4)
- `--sample-ensemble` — Fraction of queries for ensemble judging (0.0-1.0)

Exit codes:
- 0 — All correctness checks pass
- 1 — One or more correctness failures
- 2 — Infrastructure / runtime error

Requires the spec to declare a `runner` field (Python dotted path to your agent function).

## agentci diff

Compare two baseline versions:

```bash
agentci diff --baseline v1-broken --compare v2-fixed --agent rag-agent
```

Options:
- `--baseline` — The reference version
- `--compare` — The version to compare against
- `--agent` — Agent identifier
- `--config` — Path to spec for three-tier evaluation
- `--format` — Output format: console, json, github (default: console)
- `--baseline-dir` — Override baseline directory

Output shows:
- Correctness delta (PASS → FAIL or vice versa)
- Path metrics with percentage changes
- Cost metrics with percentage changes

## agentci save

Save a trace as a versioned golden baseline:

```bash
agentci save --agent rag-agent --version v1 --trace-file trace.json --config agentci_spec.yaml
```

Options:
- `--agent` — Agent identifier
- `--version` — Version tag (e.g. v1-broken, v2-fixed)
- `--trace-file` — Path to the trace JSON file
- `--config` — Spec file for precheck
- `--force-save` — Bypass correctness precheck

The precheck runs correctness checks before saving. If the trace fails correctness, it won't be saved as a baseline (unless `--force-save` is used).

## agentci baselines

List all available baseline versions:

```bash
agentci baselines --agent rag-agent
```

Displays a rich table with version, agent, query, timestamp, model, and precheck status.
