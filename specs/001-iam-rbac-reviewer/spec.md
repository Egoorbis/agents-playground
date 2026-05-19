# Feature Specification: IAM RBAC Reviewer Foundry Demo Deployment

**Feature Branch**: `001-iam-rbac-reviewer`

**Created**: 2026-05-19

**Status**: Ready for Implementation

**Input**: Demo deployment of IAM RBAC reviewer agent to Azure AI Foundry for security analysis and demo session

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Review IAM Policies from CLI (Priority: P1)

A security analyst runs the `review` command on a local policy file and receives severity-sorted findings with concrete remediation steps.

**Why this priority**: Core CLI capability is essential MVP that works offline.

**Independent Test**: Can be fully tested with local fixture files without Foundry connectivity. Delivers analysis value standalone.

**Acceptance Scenarios**:

1. **Given** a valid JSON policy file with role assignments, **When** analyst runs `iam-rbac-reviewer review policy.json`, **Then** findings are displayed sorted CRITICAL → HIGH → MEDIUM → LOW with remediation for each.
2. **Given** a YAML policy file, **When** analyst specifies `--output markdown`, **Then** output is valid Markdown suitable for documentation.
3. **Given** a policy with no findings, **When** analyst reviews it, **Then** tool exits with code 0 and reports clean status.

---

### User Story 2 - Ask Free-Form Questions via Foundry Agent (Priority: P2)

A security analyst asks the Foundry-backed agent free-form natural-language questions about IAM/RBAC and receives accurate tool-grounded answers.

**Why this priority**: Differentiates this tool as an AI-powered agent; enables complex investigation workflows.

**Independent Test**: When Foundry endpoint is configured, ask command dispatches tools and returns agent responses. Gracefully degrades to offline mode with clear error when endpoint missing.

**Acceptance Scenarios**:

1. **Given** Foundry endpoint configured, **When** analyst asks "Which roles grant Owner at the root scope?", **Then** agent calls review tools and returns findings from policy.
2. **Given** no Foundry endpoint, **When** analyst runs ask, **Then** offline mode activates with clear message about limitations.
3. **Given** a malformed question, **When** agent processes it, **Then** error is logged and friendly fallback message returned.

---

### User Story 3 - Demo Operator Deploys and Validates in < 10 Minutes (Priority: P3)

A demo operator configures environment variables, runs setup, and validates both CLI and agent workflows with provided smoke-test commands.

**Why this priority**: Enables rapid deployment for customer/internal demos without troubleshooting friction.

**Independent Test**: Operator completes documented steps and successfully runs at least one review and one ask command with real Foundry endpoint.

**Acceptance Scenarios**:

1. **Given** documented Foundry endpoint and model name, **When** operator sets env vars and runs `pip install -e .`, **Then** setup completes without errors.
2. **Given** installed package, **When** operator runs `iam-rbac-reviewer list-checks`, **Then** all 6 supported checks are listed with severity.
3. **Given** configured Foundry, **When** operator runs smoke-test commands, **Then** both review and ask return results within 30 seconds.

### Edge Cases

- **Malformed input**: Policy file is invalid JSON or YAML — tool exits with clear error message.
- **Missing required fields**: Policy lacks `role_assignments` or `role_definitions` arrays — validation error with schema reference.
- **Unknown finding ID**: User requests `explain IOAR-999` for non-existent check — tool returns error with list of valid IDs.
- **Missing Foundry endpoint**: User runs `ask` without `AZURE_AI_PROJECT_ENDPOINT` — tool displays offline warning and falls back to local mode.
- **Tool call failure**: Foundry agent requires_action loop receives bad arguments from LLM — tool call dispatch catches TypeError and returns JSON error.
- **Empty policy**: Policy has empty role_assignments array — analysis completes with zero findings, exit code 0.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: CLI `review` command MUST accept JSON and YAML policy files via file path argument.
- **FR-002**: All findings MUST be sorted by severity (CRITICAL → HIGH → MEDIUM → LOW → INFO) in CLI output and all renderer formats.
- **FR-003**: CLI `review` MUST support three output formats: `text` (default with Rich formatting), `json` (structured output), and `markdown` (documentation-ready).
- **FR-004**: CLI `ask` command MUST use Foundry mode when `AZURE_AI_PROJECT_ENDPOINT` is set, and local/offline mode otherwise.
- **FR-005**: CLI `explain` command MUST return deterministic, tool-agnostic remediation guidance for each check ID (IOAR-001 through IOAR-006).
- **FR-006**: Demo deployment MUST succeed with only documented environment variable setup; no code edits required.
- **FR-007**: All error messages MUST explain what failed, why it failed, and how to fix it.
- **FR-008**: Test suite MUST run fully offline with mocked Azure calls; no external service dependencies in CI.

### Key Entities

- **RoleAssignment**: Role granted to a principal (user, service principal, managed identity) at a specific scope (subscription, resource group, etc.).
- **RoleDefinition**: Named role with a set of permissions; includes custom and built-in definitions.
- **Finding**: Security issue identified by a check, with severity, ID (IOAR-###), title, and remediation guidance.
- **AnalysisReport**: Result of analyzing a policy; contains sorted findings, counts by severity, and metadata (source, timestamp).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Demo operator completes full setup and executes at least one successful `review` and one `ask` command in ≤ 10 minutes using documented steps.
- **SC-002**: `review` command on risky_policy.json fixture returns at least one CRITICAL or HIGH finding and completes in ≤ 5 seconds on a standard laptop.
- **SC-003**: All three supported output formats (`text`, `json`, `markdown`) render without runtime errors on both clean and risky test fixtures.
- **SC-004**: Test suite achieves ≥ 90% line coverage on core modules: `analyzer.py`, `tools.py`, `reporters.py`.

## Assumptions

- Azure AI Foundry project and model deployment already exist in the target subscription.
- Demo operator can authenticate using Azure CLI default credential or managed identity.
- Input policies follow the normalized schema documented in README.md (role_assignments and role_definitions arrays).
- Offline/test mode (without Foundry) is acceptable for CI/CD and developer validation.
- Python 3.11+ runtime is available on demo machine.
