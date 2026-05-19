"""Core IAM / RBAC policy analysis engine.

This module is intentionally dependency-free (no Azure SDK calls).
It receives a ``PolicyDocument`` and returns an ``AnalysisReport``.
All checks are implemented as small, independently-testable functions.
"""

from __future__ import annotations

import uuid
from typing import Any

from .models import (
    AnalysisReport,
    Finding,
    PolicyDocument,
    Recommendation,
    RoleAssignment,
    RoleDefinition,
    Severity,
)

# ---------------------------------------------------------------------------
# Known high-privilege roles (Azure built-ins)
# ---------------------------------------------------------------------------

_CRITICAL_ROLES: frozenset[str] = frozenset(
    {
        "Owner",
        "Contributor",
        "User Access Administrator",
    }
)

_HIGH_PRIVILEGE_ROLES: frozenset[str] = frozenset(
    {
        "Security Admin",
        "Security Operator",
        "Role Based Access Control Administrator",
        "Key Vault Administrator",
        "Storage Account Key Operator Service Role",
    }
)

# Root scope prefix
_ROOT_SCOPE_PREFIX = "/"


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def check_owner_at_root_scope(
    assignments: list[RoleAssignment],
) -> list[Finding]:
    """IOAR-001: Detect Owner / Contributor roles assigned at root ('/') scope."""
    affected = [
        a
        for a in assignments
        if a.role_definition_name in _CRITICAL_ROLES
        and (a.scope == _ROOT_SCOPE_PREFIX or a.scope.startswith("/providers/Microsoft.Management/"))
    ]
    if not affected:
        return []

    return [
        Finding(
            finding_id="IOAR-001",
            title="Privileged role assigned at root or management-group scope",
            description=(
                f"{len(affected)} assignment(s) grant '{_CRITICAL_ROLES}' "
                "at root or management-group scope, giving unrestricted control "
                "over all resources in the tenant."
            ),
            severity=Severity.CRITICAL,
            affected_principals=[a.principal_id for a in affected],
            affected_roles=list({a.role_definition_name for a in affected}),
            affected_scopes=list({a.scope for a in affected}),
            evidence={"assignments": [a.model_dump() for a in affected]},
            recommendations=[
                Recommendation(
                    title="Reduce scope to resource group or specific resource",
                    description=(
                        "Reassign the role to the narrowest scope needed. "
                        "Use resource-group-level scope at minimum."
                    ),
                    reference_url="https://learn.microsoft.com/azure/role-based-access-control/best-practices",
                )
            ],
            cis_controls=["CIS-5.4", "CIS-5.6"],
        )
    ]


def check_too_many_owners(
    assignments: list[RoleAssignment],
    threshold: int = 3,
) -> list[Finding]:
    """IOAR-002: Detect subscriptions / scopes with more than *threshold* Owners."""
    from collections import defaultdict

    owners_by_scope: dict[str, list[RoleAssignment]] = defaultdict(list)
    for a in assignments:
        if a.role_definition_name == "Owner":
            owners_by_scope[a.scope].append(a)

    findings = []
    for scope, owners in owners_by_scope.items():
        if len(owners) > threshold:
            findings.append(
                Finding(
                    finding_id="IOAR-002",
                    title=f"Excessive number of Owners at scope '{scope}'",
                    description=(
                        f"{len(owners)} principals have the Owner role at '{scope}'. "
                        f"Best practice recommends no more than {threshold}."
                    ),
                    severity=Severity.HIGH,
                    affected_principals=[a.principal_id for a in owners],
                    affected_roles=["Owner"],
                    affected_scopes=[scope],
                    evidence={"owner_count": len(owners), "threshold": threshold},
                    recommendations=[
                        Recommendation(
                            title="Remove unnecessary Owner assignments",
                            description=(
                                "Review each Owner assignment and replace with a least-privilege role "
                                "(e.g. Contributor or a custom role) where full ownership is not required."
                            ),
                            reference_url="https://learn.microsoft.com/azure/role-based-access-control/best-practices#limit-number-of-subscription-owners",
                        )
                    ],
                    cis_controls=["CIS-5.3"],
                )
            )
    return findings


def check_service_principal_with_owner(
    assignments: list[RoleAssignment],
) -> list[Finding]:
    """IOAR-003: Service principals should not hold Owner or Contributor at broad scopes."""
    affected = [
        a
        for a in assignments
        if a.principal_type in {"ServicePrincipal", "ManagedIdentity"}
        and a.role_definition_name in _CRITICAL_ROLES
    ]
    if not affected:
        return []

    return [
        Finding(
            finding_id="IOAR-003",
            title="Service principal / managed identity assigned a highly privileged role",
            description=(
                f"{len(affected)} service principal(s) or managed identity(-ies) hold "
                f"'{_CRITICAL_ROLES}'. Compromise of such an identity grants full control."
            ),
            severity=Severity.HIGH,
            affected_principals=[a.principal_id for a in affected],
            affected_roles=list({a.role_definition_name for a in affected}),
            affected_scopes=list({a.scope for a in affected}),
            evidence={"assignments": [a.model_dump() for a in affected]},
            recommendations=[
                Recommendation(
                    title="Apply the principle of least privilege to service principals",
                    description=(
                        "Replace Owner/Contributor with a purpose-built custom role "
                        "or a built-in role scoped to only the resources the SP needs."
                    ),
                    reference_url="https://learn.microsoft.com/azure/active-directory/develop/secure-least-privileged-access",
                )
            ],
            cis_controls=["CIS-5.5"],
        )
    ]


def check_wildcard_permissions(
    role_definitions: list[RoleDefinition],
) -> list[Finding]:
    """IOAR-004: Custom roles should not use wildcard ('*') actions."""
    offending: list[RoleDefinition] = []
    for rd in role_definitions:
        if not rd.is_custom:
            continue
        for perm in rd.permissions:
            actions: list[str] = perm.get("actions", [])
            if "*" in actions:
                offending.append(rd)
                break

    if not offending:
        return []

    return [
        Finding(
            finding_id="IOAR-004",
            title="Custom role definition contains wildcard ('*') action",
            description=(
                f"{len(offending)} custom role(s) grant all actions via '*'. "
                "This defeats the purpose of a custom role and may exceed intended permissions."
            ),
            severity=Severity.HIGH,
            affected_roles=[rd.name for rd in offending],
            evidence={"role_ids": [rd.role_id for rd in offending]},
            recommendations=[
                Recommendation(
                    title="Replace '*' with specific action strings",
                    description=(
                        "Enumerate the exact resource provider actions the role needs and remove the wildcard."
                    ),
                    reference_url="https://learn.microsoft.com/azure/role-based-access-control/custom-roles",
                )
            ],
            cis_controls=["CIS-5.1"],
        )
    ]


def check_stale_assignments(
    assignments: list[RoleAssignment],
    known_principal_ids: set[str] | None = None,
) -> list[Finding]:
    """IOAR-005: Assignments for principals not present in the known-principals set.

    When *known_principal_ids* is ``None`` the check is skipped (not enough
    information to determine staleness).
    """
    if known_principal_ids is None:
        return []

    stale = [a for a in assignments if a.principal_id not in known_principal_ids]
    if not stale:
        return []

    return [
        Finding(
            finding_id="IOAR-005",
            title="Role assignment references an unknown or deleted principal",
            description=(
                f"{len(stale)} assignment(s) reference principal IDs that are not "
                "present in the supplied identity directory. These may be orphaned "
                "assignments for deleted users or service principals."
            ),
            severity=Severity.MEDIUM,
            affected_principals=[a.principal_id for a in stale],
            affected_roles=list({a.role_definition_name for a in stale}),
            affected_scopes=list({a.scope for a in stale}),
            evidence={"stale_count": len(stale)},
            recommendations=[
                Recommendation(
                    title="Remove orphaned role assignments",
                    description=(
                        "Use 'az role assignment delete' or the Azure Portal to remove "
                        "assignments whose principal no longer exists."
                    ),
                    reference_url="https://learn.microsoft.com/azure/role-based-access-control/role-assignments-remove",
                )
            ],
            cis_controls=["CIS-5.7"],
        )
    ]


def check_no_guest_users_with_privileged_roles(
    assignments: list[RoleAssignment],
    guest_principal_ids: set[str] | None = None,
) -> list[Finding]:
    """IOAR-006: Guest / external users should not hold privileged roles."""
    if guest_principal_ids is None:
        return []

    privileged_roles = _CRITICAL_ROLES | _HIGH_PRIVILEGE_ROLES
    affected = [
        a
        for a in assignments
        if a.principal_id in guest_principal_ids
        and a.role_definition_name in privileged_roles
    ]
    if not affected:
        return []

    return [
        Finding(
            finding_id="IOAR-006",
            title="Guest / external user holds a privileged role",
            description=(
                f"{len(affected)} role assignment(s) grant privileged access to guest principals. "
                "External identities should have minimal standing access."
            ),
            severity=Severity.HIGH,
            affected_principals=[a.principal_id for a in affected],
            affected_roles=list({a.role_definition_name for a in affected}),
            affected_scopes=list({a.scope for a in affected}),
            evidence={"assignments": [a.model_dump() for a in affected]},
            recommendations=[
                Recommendation(
                    title="Remove or downgrade guest user role assignments",
                    description=(
                        "Replace permanent privileged assignments with just-in-time (JIT) access "
                        "via Azure AD Privileged Identity Management (PIM)."
                    ),
                    reference_url="https://learn.microsoft.com/azure/active-directory/privileged-identity-management/",
                )
            ],
            cis_controls=["CIS-5.2"],
        )
    ]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_ALL_CHECKS = [
    check_owner_at_root_scope,
    check_too_many_owners,
    check_service_principal_with_owner,
    check_wildcard_permissions,
    check_stale_assignments,
    check_no_guest_users_with_privileged_roles,
]


def analyze(
    policy: PolicyDocument,
    known_principal_ids: set[str] | None = None,
    guest_principal_ids: set[str] | None = None,
    owner_threshold: int = 3,
) -> AnalysisReport:
    """Run all checks against *policy* and return a consolidated :class:`AnalysisReport`.

    Args:
        policy: The parsed policy document to review.
        known_principal_ids: Optional set of valid principal IDs for stale-assignment check.
        guest_principal_ids: Optional set of guest/external principal IDs.
        owner_threshold: Max owners per scope before triggering IOAR-002.

    Returns:
        A fully populated :class:`AnalysisReport`.
    """
    assignments = policy.role_assignments
    role_defs = policy.role_definitions

    findings: list[Finding] = []

    findings.extend(check_owner_at_root_scope(assignments))
    findings.extend(check_too_many_owners(assignments, threshold=owner_threshold))
    findings.extend(check_service_principal_with_owner(assignments))
    findings.extend(check_wildcard_permissions(role_defs))
    findings.extend(check_stale_assignments(assignments, known_principal_ids))
    findings.extend(check_no_guest_users_with_privileged_roles(assignments, guest_principal_ids))

    report = AnalysisReport(
        report_id=str(uuid.uuid4()),
        source=policy.source,
        policy_type=policy.policy_type,
        total_roles_reviewed=len(role_defs),
        total_assignments_reviewed=len(assignments),
        findings=findings,
    )
    report.summary = _build_summary(report)
    return report


def _build_summary(report: AnalysisReport) -> str:
    """Generate a one-paragraph plain-text summary of the report."""
    total = len(report.findings)
    if total == 0:
        return (
            f"Reviewed {report.total_assignments_reviewed} role assignment(s) and "
            f"{report.total_roles_reviewed} role definition(s). No issues found."
        )
    parts = []
    for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW):
        count = sum(1 for f in report.findings if f.severity == sev)
        if count:
            parts.append(f"{count} {sev.value}")
    severity_str = ", ".join(parts)
    return (
        f"Reviewed {report.total_assignments_reviewed} role assignment(s) and "
        f"{report.total_roles_reviewed} role definition(s). "
        f"Found {total} issue(s): {severity_str}. "
        f"Risk score: {report.risk_score}."
    )


def load_policy_from_dict(data: dict[str, Any], source: str = "") -> PolicyDocument:
    """Parse a raw dictionary into a :class:`PolicyDocument`.

    Supports a simple normalised format:
    ``{"role_assignments": [...], "role_definitions": [...]}``

    Args:
        data: Parsed JSON or YAML content.
        source: Optional label (file path, subscription ID) for the report.

    Returns:
        A validated :class:`PolicyDocument`.
    """
    return PolicyDocument(
        role_assignments=[RoleAssignment(**a) for a in data.get("role_assignments", [])],
        role_definitions=[RoleDefinition(**r) for r in data.get("role_definitions", [])],
        raw=data,
        source=source,
    )
