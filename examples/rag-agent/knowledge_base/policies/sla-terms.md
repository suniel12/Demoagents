# AgentCI CI/CD Integration & GitHub Actions

## Overview

AgentCI is designed for CI/CD-first testing. Every feature — from exit codes to output formats — is built to work natively in automated pipelines.

## GitHub Actions Setup

Run `agentci init` to auto-generate the workflow:

```bash
agentci init
```

This creates `.github/workflows/agentci.yml` with three jobs:

### Job 1: Deterministic Tests
Runs with mocked LLMs — no API keys needed, completes in seconds.
```yaml
- name: Run deterministic tests
  run: pytest tests/ -v -m "not live"
  env:
    ANTHROPIC_API_KEY: sk-ant-dummy-key-for-testing
```

### Job 2: LLM Judge Evaluation
Runs with real API keys — only when secrets are available (skips in external PRs).
```yaml
- name: Run LLM judge tests
  if: env.ANTHROPIC_API_KEY != ''
  run: pytest tests/ -v
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Job 3: AgentCI Spec Evaluation
Runs `agentci test` for full three-layer evaluation:
```yaml
- name: Run AgentCI evaluation
  run: |
    agentci test \
      --config agentci_spec.yaml \
      --format github \
      --workers 4
```

## GitHub PR Annotations

When using `--format github`, AgentCI outputs:
- `::error file=agentci_spec.yaml::Query "..." FAILED: expected_in_answer not found` — Appears as a red annotation in the PR diff
- `::warning file=agentci_spec.yaml::Query "..." WARNING: max_tool_calls exceeded (8 > 5)` — Appears as a yellow annotation

This is **first-in-class** among agent testing tools. No other framework integrates this deeply with GitHub's review interface.

## Multi-Agent Matrix Strategy

For projects with multiple agents, use a matrix strategy:

```yaml
jobs:
  agentci-eval:
    strategy:
      matrix:
        agent: [rag-agent, support-router, dev-agent]
      fail-fast: false
    steps:
      - run: agentci test --config demos/${{ matrix.agent }}/agentci_spec.yaml --format github
```

## Exit Code Behavior

Exit codes are designed for CI gates:
- **Exit 0** — All correctness checks pass. Warnings (path/cost) are printed but don't block.
- **Exit 1** — One or more correctness failures. Should block the merge.
- **Exit 2** — Infrastructure error (invalid config, runner import failed, network issue).

## Severity Mapping

| Layer | CI Behavior | GitHub Annotation |
|-------|-------------|-------------------|
| Correctness (FAIL) | Blocks merge (exit 1) | `::error` — red badge |
| Path (WARN) | Doesn't block (exit 0) | `::warning` — yellow badge |
| Cost (WARN) | Doesn't block (exit 0) | `::warning` — yellow badge |
| Forbidden tools | Blocks merge (exit 1) | `::error` — escalated |

## Output Formats

| Format | Command | Best for |
|--------|---------|----------|
| Console | `--format console` | Local development, rich colorful tables |
| GitHub | `--format github` | CI/CD, inline PR annotations |
| JSON | `--format json` | Dashboards, downstream tooling, automation |
| Prometheus | `--format prometheus` | Grafana monitoring, gauge exposition format |

## Pre-Push Hook

`agentci init` can also install a git pre-push hook:

```bash
#!/bin/sh
# .git/hooks/pre-push
agentci test --config agentci_spec.yaml --format console --workers 2
```

This runs a quick evaluation before every push. If correctness fails, the push is rejected.
