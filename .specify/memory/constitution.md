<!-- Sync Impact Report
Version change: 0.0.0 -> 1.0.0
Modified principles:
- Code quality and readability -> I. Code Quality and Readability
- Testing discipline -> II. Test-Driven Verification
- User experience consistency -> III. User Experience Consistency
- Performance requirements -> IV. Performance Budgets and Efficiency
- Delivery reproducibility -> V. Deterministic Delivery and Reproducibility
Added sections:
- Engineering Standards
- Delivery Workflow
Removed sections:
- None
Templates updated:
- ✅ /home/ghostbash/code/github-repos-own/agents-playground/.specify/templates/plan-template.md
- ✅ /home/ghostbash/code/github-repos-own/agents-playground/.specify/templates/spec-template.md
- ✅ /home/ghostbash/code/github-repos-own/agents-playground/.specify/templates/tasks-template.md
Deferred items:
- None
-->

# agents-playground Constitution

## Core Principles

### I. Code Quality and Readability
Every change MUST be the smallest complete fix for the problem at hand. Code MUST be
clear, idiomatic, and easy to review; names, structure, and control flow MUST make the
intent obvious without requiring extra explanation. Avoid duplicated logic, dead code,
and unrelated refactors unless they are required to preserve correctness.

Rationale: this repository is composed of workflow code and templates, so clarity and
local reasoning keep generated and maintained behavior predictable.

### II. Test-Driven Verification
Behavior-changing work MUST have an executable verification path that fails before the
fix whenever the environment allows it. New logic, regressions, and boundary conditions
MUST be covered by the narrowest useful test or validation command, and those checks
MUST run before broader changes are accepted.

Rationale: generated workflows are only trustworthy when their expected behavior is
codified in repeatable checks rather than manual inspection.

### III. User Experience Consistency
All user-facing text, prompts, command output, documentation, and workflow steps MUST
use canonical terminology and a consistent tone. Error messages MUST explain what went
wrong and the next action when possible. A change that affects user-facing flow MUST
preserve existing conventions unless a deliberate migration is documented.

Rationale: this project is an interactive coding workflow, so inconsistency in wording
or flow creates avoidable friction and misinterpretation.

### IV. Performance Budgets and Efficiency
Interactive paths MUST stay responsive, and changes MUST avoid unnecessary filesystem,
process, or network work. If a change may increase latency, output size, or resource
usage, the budget impact MUST be stated and verified with a measurable check. Prefer
single-pass or cached work over repeated scans when behavior remains equivalent.

Rationale: the repository is used in editor loops, so small inefficiencies compound
quickly into slow, noisy, or unreliable experiences.

### V. Deterministic Delivery and Reproducibility
Workflow steps MUST produce stable results for the same inputs, and any generated
artifact MUST be reproducible from the recorded source inputs. When a change touches a
shared template, script, or prompt file, the corresponding downstream artifact MUST be
updated in the same change set or explicitly deferred with a reason.

Rationale: this keeps the repository self-consistent and prevents hidden drift between
the spec kit templates, prompts, and generated outputs.

## Engineering Standards

All feature work MUST preserve the existing project structure unless a structural
change is justified in the plan. User-facing features SHOULD include measurable
acceptance criteria, and performance-sensitive work SHOULD define a concrete budget or
validation command. Any new or changed behavior MUST be traceable to the spec, plan,
and tasks for the feature.

## Delivery Workflow

Work SHOULD progress in a local loop: define the change, validate it with the smallest
meaningful check, and only then widen scope. Implementation tasks MUST remain aligned
with user stories, and story phases SHOULD remain independently testable. If a change is
likely to affect multiple artifacts, update them together rather than leaving known
drift behind.

## Governance

This constitution supersedes informal practice, generated defaults, and ad hoc
preferences. Amendments require an explicit rationale, a version bump, and a sync pass
over dependent templates or runtime guidance. A review is incomplete until it confirms
that the updated constitution is reflected in the plan, spec, and tasks templates when
those files carry guidance affected by the change.

Versioning policy:

- MAJOR for backward-incompatible governance changes or principle redefinitions.
- MINOR for new principles, new sections, or materially expanded guidance.
- PATCH for wording changes, clarifications, and non-semantic refinements.

Compliance review expectations:

- Every constitution-aware review MUST check the active feature files against these
	principles.
- Any justified exception MUST be documented in the plan's complexity tracking.
- If a change introduces a new quality risk, the reviewer MUST require a measurable
	validation step or explicit follow-up.

**Version**: 1.0.0 | **Ratified**: 2026-05-15 | **Last Amended**: 2026-05-15
