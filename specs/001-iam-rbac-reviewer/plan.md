# Implementation Plan: IAM RBAC Reviewer Foundry Demo Deployment

**Branch**: `001-iam-rbac-reviewer` | **Date**: 2026-05-19 | **Spec**: [specs/001-iam-rbac-reviewer/spec.md](specs/001-iam-rbac-reviewer/spec.md)

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: azure-ai-projects, azure-identity, typer, rich, pydantic, pyyaml, httpx

**Storage**: File-based inputs (JSON/YAML policy files); no persistent storage required.

**Testing**: pytest, pytest-cov, pytest-asyncio with mocked Azure SDK calls.

**Target Platform**: Linux/macOS/Windows CLI runtime (Python environment).

**Project Type**: Single-project Python CLI with integrated Foundry agent orchestration.

**Performance Goals**: Analyze up to 500 IAM roles in ≤ 30 seconds on a standard laptop (M1/i7, 16 GB RAM).

**Constraints**: Tests run fully offline with no external service calls; CLI output must be deterministic; no credentials logged or printed.

**Scale/Scope**: Single subscription or management-group RBAC snapshot (typical policy files 50–500 role assignments).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates determined from the constitution:

- Code changes MUST be scoped to the smallest complete fix and keep the diff readable.
- Behavior changes MUST have an executable validation path before broader acceptance.
- User-facing text, prompts, and flows MUST use consistent, canonical terminology.
- Performance-sensitive work MUST state and verify a measurable budget or efficiency limit.
- Shared templates, prompts, and scripts MUST be updated together when they change.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
