---

description: "Task list template for feature implementation"
---

# Tasks: IAM RBAC Reviewer Foundry Demo Deployment

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Validate environment and dependencies

- [ ] T001 Validate local Python 3.11+ and pip in developer environment
- [ ] T002 Confirm `pip install -e .[dev]` succeeds without errors
- [ ] T003 [P] Verify CLI entrypoint works: `iam-rbac-reviewer --help`

**Checkpoint**: Development environment ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules must pass validation before story implementation

**⚠️ CRITICAL**: No story work can begin until this phase is complete

- [ ] T004 Verify Settings validation in `iam_rbac_reviewer/config.py` via `test_config.py`
- [ ] T005 Verify analyzer contract in `iam_rbac_reviewer/analyzer.py` with fixture files
- [ ] T006 Verify reporter outputs match expected formats in `iam_rbac_reviewer/reporters.py`
- [ ] T007 Verify tool dispatch and registry in `iam_rbac_reviewer/tools.py`

**Checkpoint**: Core modules validated - story implementation can proceed

---

## Phase 3: User Story 1 - Review IAM Policies from CLI (Priority: P1) 🎯 MVP

**Goal**: CLI review command analyzes policy files and produces severity-sorted findings with remediation

**Independent Test**: Can test with local fixtures without Foundry. Run: `iam-rbac-reviewer review tests/fixtures/risky_policy.json`

### Tests for User Story 1

- [ ] T008 [P] [US1] Test review command with JSON fixture in `tests/test_cli.py`
- [ ] T009 [P] [US1] Test review command with YAML fixture in `tests/test_cli.py`
- [ ] T010 [P] [US1] Test --output json format in `tests/test_reporters.py`
- [ ] T011 [P] [US1] Test --output markdown format in `tests/test_reporters.py`
- [ ] T012 [US1] Test severity sorting in `tests/test_reporters.py` (depends on T010, T011)

### Implementation for User Story 1

- [ ] T013 [P] [US1] Ensure load_policy_from_dict handles edge cases in `iam_rbac_reviewer/models.py`
- [ ] T014 [P] [US1] Ensure analyze() returns sorted findings in `iam_rbac_reviewer/analyzer.py`
- [ ] T015 [US1] Verify render() function produces all three formats in `iam_rbac_reviewer/reporters.py`
- [ ] T016 [US1] Verify review command error handling for missing/invalid files in `iam_rbac_reviewer/cli.py`
- [ ] T017 [US1] Verify exit codes: 0=clean, 2=critical, 3=high in `iam_rbac_reviewer/cli.py`

**Checkpoint**: CLI review works offline with fixtures and all output formats

---

## Phase 4: User Story 2 - Ask Free-Form Questions via Foundry Agent (Priority: P2)

**Goal**: Ask command dispatches to Foundry agent or local mode, tool calls work, responses are grounded

**Independent Test**: When endpoint configured, agent calls tools. When not configured, offline mode activates.

### Tests for User Story 2

- [ ] T018 [P] [US2] Test foundry_configured property in `tests/test_config.py`
- [ ] T019 [P] [US2] Test local agent fallback in `tests/test_agent.py`
- [ ] T020 [US2] Test dispatch_tool_call for each tool (review_policy_file, explain_finding, get_supported_checks) in `tests/test_tools.py`
- [ ] T021 [US2] Test tool argument error handling in `tests/test_tools.py` (depends on T020)

### Implementation for User Story 2

- [ ] T022 [P] [US2] Verify _run_foundry_agent creates agent with correct tools in `iam_rbac_reviewer/agent.py`
- [ ] T023 [P] [US2] Verify _run_foundry_agent handles requires_action loop in `iam_rbac_reviewer/agent.py`
- [ ] T024 [US2] Verify _run_local_agent fallback for offline mode in `iam_rbac_reviewer/agent.py` (depends on T022, T023)
- [ ] T025 [US2] Verify ask CLI command calls run_agent correctly in `iam_rbac_reviewer/cli.py`
- [ ] T026 [US2] Verify error messages when Foundry not configured in `iam_rbac_reviewer/cli.py`

**Checkpoint**: Agent mode works with Foundry; gracefully degrades offline

---

## Phase 5: User Story 3 - Demo Operator Deploys in < 10 Minutes (Priority: P3)

**Goal**: Documented setup enables operator to configure, install, and validate in ≤ 10 minutes

**Independent Test**: Follow README demo section; run two smoke commands successfully

### Tests for User Story 3

- [ ] T027 [P] [US3] Add Demo Deployment section to README with env var examples
- [ ] T028 [P] [US3] Add Prerequisites checklist in README (Foundry project, model deployment, Azure CLI)
- [ ] T029 [P] [US3] Add Install and Validate steps in README with copy-paste commands
- [ ] T030 [P] [US3] Add Demo Success Criteria section in README with expected outcomes

### Implementation for User Story 3

- [ ] T031 [US3] Add Troubleshooting section to README (missing endpoint, auth failures, model mismatch)
- [ ] T032 [US3] Verify sample commands in README work on a clean clone (operator experience)
- [ ] T033 [US3] Document demo script / talking points for running review and ask live (depends on T032)

**Checkpoint**: Operator can deploy and run demo without code edits

---

## Phase 6: Quality Gates & Deployment

**Purpose**: Ensure code quality and demo readiness before release

- [ ] T034 [P] Run ruff check on all modules and fix linting issues
- [ ] T035 [P] Run ruff format on all modules
- [ ] T036 [US1-US3] Run pytest with coverage: `pytest --cov=iam_rbac_reviewer --cov-report=term-missing` and verify ≥ 90% on analyzer, tools, reporters
- [ ] T037 [P] Run pip-audit and document any security findings
- [ ] T038 [US3] Execute demo walkthrough with risky_policy.json and ask a security question
- [ ] T039 [US3] Validate error paths (missing file, bad arg, no endpoint)

**Checkpoint**: All quality gates pass; deployment ready

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - Stories can proceed in priority order (P1 → P2 → P3) or in parallel (if team capacity)
- **Quality Gates (Phase 6)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational - No dependencies on US2/US3 (MVP)
- **US2 (P2)**: Can start after Foundational - Integrates with US1 tools but independently testable
- **US3 (P3)**: Can start after US1 implementation (needs working review and ask commands for demo)

### Requirement-to-Task Traceability

| Requirement | Task ID(s) | Notes |
|-------------|-----------|-------|
| FR-001 | T002, T008, T009 | CLI review accepts JSON and YAML files |
| FR-002 | T012, T010, T011 | Findings sorted by severity in all formats |
| FR-003 | T010, T011, T015 | Three output formats (text, json, markdown) |
| FR-004 | T018, T024 | Ask uses Foundry when endpoint configured |
| FR-005 | T020, T021 | Explain command returns deterministic remediation |
| FR-006 | T027, T028, T029 | Demo setup requires only env vars |
| FR-007 | T016, T026, T031 | Error messages explain what/why/how |
| FR-008 | T005, T018, T019 | Tests run offline with mocked calls |
| SC-001 | T027, T028, T029, T032 | Operator demo completes in ≤ 10 minutes |
| SC-002 | T012, T015, T036 | Review on risky fixture returns findings in ≤ 5 seconds |
| SC-003 | T010, T011, T015, T036 | All formats render without errors on fixtures |
| SC-004 | T036, T037 | ≥ 90% coverage on analyzer, tools, reporters |

### Parallel Opportunities

- All Setup tasks marked [P] (T001–T003) can run in parallel
- All Foundational tasks marked [P] (T004–T007) can run in parallel
- Once Foundational passes, US1 tests (T008–T012) marked [P] can run in parallel
- Once US1 tests pass, US1 implementation (T013–T017) marked [P] can run in parallel
- Once US1 and US2 tests complete, stories can proceed in parallel
- Quality gate tasks (T034, T035, T037) marked [P] can run in parallel

---

## Execution Checklist

**Before starting any task**:
1. Review phase dependencies above
2. Ensure all blocking tasks are complete
3. Run `pytest` to validate no regressions
4. Run `ruff check` to validate code style

**While implementing each task**:
1. Edit only the specified file(s)
2. Run tests for that module (e.g., `pytest tests/test_cli.py` for T008)
3. Run linter before committing
4. Commit with message referencing task ID

**After each phase**:
1. Run full test suite: `pytest --cov=iam_rbac_reviewer`
2. Run linting: `ruff check .` and `ruff format .`
3. Document any blockers or deviations

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Keep user-facing copy consistent, measurable, and tied to the feature's acceptance criteria
