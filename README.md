# IAM / RBAC Reviewer — Azure AI Foundry Agent

An **Azure AI Foundry** agent that analyses Azure RBAC (and generic IAM) policies
for security risks and produces actionable findings with CIS Control references and
step-by-step remediation guidance.

---

## Features

| Check ID | Severity | Description |
|---|---|---|
| IOAR-001 | 🔴 CRITICAL | Owner / Contributor at root or management-group scope |
| IOAR-002 | 🟠 HIGH | Too many Owners per subscription |
| IOAR-003 | 🟠 HIGH | Service principal / managed identity holds a privileged role |
| IOAR-004 | 🟠 HIGH | Custom role definition uses wildcard (`*`) action |
| IOAR-005 | 🟡 MEDIUM | Orphaned assignment (unknown / deleted principal) |
| IOAR-006 | 🟠 HIGH | Guest / external user holds a privileged role |

---

## Quick Start

### Prerequisites

- Python ≥ 3.11
- An [Azure AI Foundry](https://learn.microsoft.com/azure/ai-foundry/) project (optional for offline use)

### Install

```bash
pip install -e ".[dev]"
```

### Review a policy file

```bash
# Plain-text report
iam-rbac-reviewer review policy.json

# JSON report
iam-rbac-reviewer review policy.json --output json

# Markdown report
iam-rbac-reviewer review policy.json --output markdown
```

The policy file must follow the normalised schema:

```json
{
  "role_assignments": [
    {
      "principal_id": "aaaa-0001",
      "principal_type": "User",
      "role_definition_name": "Owner",
      "scope": "/subscriptions/sub-001"
    }
  ],
  "role_definitions": []
}
```

### List all supported checks

```bash
iam-rbac-reviewer list-checks
```

### Explain a specific finding

```bash
iam-rbac-reviewer explain IOAR-001
```

### Ask the Foundry agent a free-form question

```bash
export AZURE_AI_PROJECT_ENDPOINT="https://<hub>.services.ai.azure.com/..."
export AZURE_OPENAI_MODEL="gpt-4o"

iam-rbac-reviewer ask "Which roles grant Owner access at the root scope?"
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AZURE_AI_PROJECT_ENDPOINT` | For agent mode | Azure AI Foundry project endpoint URL |
| `AZURE_OPENAI_MODEL` | For agent mode | Model deployment name (default: `gpt-4o`) |
| `AZURE_SUBSCRIPTION_ID` | Optional | Default subscription to analyse |
| `IAM_REVIEWER_OWNER_THRESHOLD` | Optional | Max Owners per scope (default: `3`) |
| `IAM_REVIEWER_LOG_LEVEL` | Optional | Log level: DEBUG/INFO/WARNING/ERROR (default: `INFO`) |

---

## Development

```bash
# Run tests with coverage
pytest

# Lint and format
ruff check .
ruff format .

# Security audit
pip-audit
```

---

## Architecture

```
iam_rbac_reviewer/
├── models.py      ← Pydantic data models (PolicyDocument, Finding, AnalysisReport)
├── analyzer.py    ← Core rule-based analysis engine (no Azure SDK dependency)
├── reporters.py   ← Output renderers: text, JSON, Markdown
├── tools.py       ← Azure AI Foundry tool definitions + implementations
├── agent.py       ← Foundry agent orchestrator (async, tool-calling loop)
├── config.py      ← Settings loaded from environment variables
└── cli.py         ← Typer + Rich CLI
```

**Implementation phases:**

1. **Phase 1** — Foundation: project structure, Pydantic models, configuration
2. **Phase 2** — Core analysis engine: rule checks, report generation, renderers
3. **Phase 3** — Foundry integration: tool definitions, agent orchestrator
4. **Phase 4** — CLI & packaging: Typer CLI, entry point, comprehensive tests

---

## License

MIT
