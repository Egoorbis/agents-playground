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

## Demo Deployment to Microsoft Foundry

Follow these steps to deploy and run the IAM RBAC reviewer agent on Azure AI Foundry for a demo session.

### Prerequisites

- **Azure AI Foundry project** with a model deployment (e.g., `gpt-4o`)
- **Azure CLI** installed and authenticated (`az login`)
- **Python 3.11+** available in your shell
- **Model deployment name** known (e.g., `gpt-4o` or your custom deployment)

### Environment Setup

```bash
# Set your Foundry project endpoint and model deployment name
export AZURE_AI_PROJECT_ENDPOINT="https://<your-hub>.services.ai.azure.com/..."
export AZURE_OPENAI_MODEL="<your-model-deployment-name>"  # e.g., gpt-4o

# Optional: Set default subscription for policy review
export AZURE_SUBSCRIPTION_ID="<your-subscription-id>"
```

Replace:
- `<your-hub>` with your Foundry hub name
- `<your-model-deployment-name>` with your model deployment name (e.g., `gpt-4o`)
- `<your-subscription-id>` (optional) with your default Azure subscription ID

### Install and Validate

```bash
# Install the package in development mode with dev dependencies
pip install -e ".[dev]"

# Verify CLI is available
iam-rbac-reviewer --help

# List all supported security checks
iam-rbac-reviewer list-checks
```

### Demo Smoke Tests

Run these commands to validate both CLI and Foundry agent workflows:

#### 1. Review Command (Works Offline)

```bash
# Analyze a local policy file and display findings as Markdown
iam-rbac-reviewer review tests/fixtures/risky_policy.json --output markdown

# Review with JSON output for automation
iam-rbac-reviewer review tests/fixtures/risky_policy.json --output json | jq
```

Expected result:
- At least one CRITICAL or HIGH finding displayed
- Findings sorted by severity (CRITICAL → HIGH → MEDIUM → LOW)
- Remediation steps included for each finding

#### 2. Ask Command (Requires Foundry)

```bash
# Ask the Foundry agent a free-form security question
# Agent uses configured tools to ground answers in policy data
iam-rbac-reviewer ask "Which roles grant Owner access at the root scope?"

iam-rbac-reviewer ask "List all critical RBAC findings from tests/fixtures/risky_policy.json"
```

Expected result:
- Agent returns a natural-language response
- Response references specific findings or checks
- Tool calls happen in the background (logs show tool dispatch)

#### 3. Explain Command

```bash
# Get detailed explanation and remediation for a specific check
iam-rbac-reviewer explain IOAR-001
iam-rbac-reviewer explain IOAR-002
```

### Demo Success Criteria

✅ **Setup**: Environment variables set, CLI entrypoint works  
✅ **Review**: Runs in under 5 seconds, finds at least one CRITICAL/HIGH finding  
✅ **Ask**: Foundry agent responds within 30 seconds, references tools  
✅ **Explain**: Returns remediation steps for each check  

### Troubleshooting

**Issue**: `AZURE_AI_PROJECT_ENDPOINT is not set`
- Solution: Set the environment variable: `export AZURE_AI_PROJECT_ENDPOINT="https://..."`

**Issue**: `Credential not found` or authentication fails
- Solution: Run `az login` first and ensure your account has access to the Foundry project

**Issue**: Model deployment name mismatch
- Solution: Verify `AZURE_OPENAI_MODEL` matches a real deployment in your Foundry project
- List deployments: Check your Foundry project portal or run `az ai model list` (if available)

**Issue**: `AttributeError: module 'azure.ai.projects' has no attribute 'aio'`
- Solution: Upgrade the package: `pip install --upgrade azure-ai-projects`

**Issue**: Review command runs but finds no findings
- Solution: Ensure policy file follows the normalized schema (see [Review a policy file](#review-a-policy-file))
- Test with the provided fixture: `iam-rbac-reviewer review tests/fixtures/risky_policy.json`

---

## License

MIT
