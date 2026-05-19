"""Tests for iam_rbac_reviewer.analyzer."""

from __future__ import annotations

from iam_rbac_reviewer.analyzer import (
    analyze,
    check_no_guest_users_with_privileged_roles,
    check_owner_at_root_scope,
    check_service_principal_with_owner,
    check_stale_assignments,
    check_too_many_owners,
    check_wildcard_permissions,
    load_policy_from_dict,
)
from iam_rbac_reviewer.models import (
    AnalysisReport,
    PolicyDocument,
    RoleAssignment,
    RoleDefinition,
    Severity,
)

# ---------------------------------------------------------------------------
# check_owner_at_root_scope
# ---------------------------------------------------------------------------


class TestCheckOwnerAtRootScope:
    def test_detects_owner_at_root(self, minimal_owner_at_root: PolicyDocument) -> None:
        findings = check_owner_at_root_scope(minimal_owner_at_root.role_assignments)
        assert len(findings) == 1
        assert findings[0].finding_id == "IOAR-001"
        assert findings[0].severity == Severity.CRITICAL

    def test_detects_owner_at_management_group(self) -> None:
        assignments = [
            RoleAssignment(
                principal_id="u-1",
                principal_type="User",
                role_definition_name="Owner",
                scope="/providers/Microsoft.Management/managementGroups/mg-root",
            )
        ]
        findings = check_owner_at_root_scope(assignments)
        assert len(findings) == 1

    def test_no_finding_for_subscription_scope(self) -> None:
        assignments = [
            RoleAssignment(
                principal_id="u-1",
                principal_type="User",
                role_definition_name="Owner",
                scope="/subscriptions/sub-001",
            )
        ]
        findings = check_owner_at_root_scope(assignments)
        assert findings == []

    def test_no_finding_for_reader_at_root(self) -> None:
        assignments = [
            RoleAssignment(
                principal_id="u-1",
                principal_type="User",
                role_definition_name="Reader",
                scope="/",
            )
        ]
        findings = check_owner_at_root_scope(assignments)
        assert findings == []

    def test_no_finding_empty_assignments(self) -> None:
        assert check_owner_at_root_scope([]) == []


# ---------------------------------------------------------------------------
# check_too_many_owners
# ---------------------------------------------------------------------------


class TestCheckTooManyOwners:
    def _make_owners(self, scope: str, count: int) -> list[RoleAssignment]:
        return [
            RoleAssignment(
                principal_id=f"u-{i}",
                principal_type="User",
                role_definition_name="Owner",
                scope=scope,
            )
            for i in range(count)
        ]

    def test_triggers_above_threshold(self) -> None:
        findings = check_too_many_owners(self._make_owners("/subscriptions/s", 5), threshold=3)
        assert len(findings) == 1
        assert findings[0].finding_id == "IOAR-002"
        assert findings[0].severity == Severity.HIGH

    def test_no_finding_at_threshold(self) -> None:
        findings = check_too_many_owners(self._make_owners("/subscriptions/s", 3), threshold=3)
        assert findings == []

    def test_no_finding_below_threshold(self) -> None:
        findings = check_too_many_owners(self._make_owners("/subscriptions/s", 2), threshold=3)
        assert findings == []

    def test_separate_scopes_tracked_independently(self) -> None:
        a1 = self._make_owners("/subscriptions/s1", 4)
        a2 = self._make_owners("/subscriptions/s2", 1)
        findings = check_too_many_owners(a1 + a2, threshold=3)
        assert len(findings) == 1
        assert "/subscriptions/s1" in findings[0].affected_scopes

    def test_no_finding_for_non_owner_roles(self) -> None:
        assignments = [
            RoleAssignment(
                principal_id=f"u-{i}",
                principal_type="User",
                role_definition_name="Contributor",
                scope="/subscriptions/s",
            )
            for i in range(10)
        ]
        assert check_too_many_owners(assignments, threshold=3) == []


# ---------------------------------------------------------------------------
# check_service_principal_with_owner
# ---------------------------------------------------------------------------


class TestCheckServicePrincipalWithOwner:
    def test_detects_sp_owner(self, sp_with_owner: PolicyDocument) -> None:
        findings = check_service_principal_with_owner(sp_with_owner.role_assignments)
        assert len(findings) == 1
        assert findings[0].finding_id == "IOAR-003"
        assert findings[0].severity == Severity.HIGH

    def test_detects_managed_identity_contributor(self) -> None:
        assignments = [
            RoleAssignment(
                principal_id="mi-1",
                principal_type="ManagedIdentity",
                role_definition_name="Contributor",
                scope="/subscriptions/s",
            )
        ]
        findings = check_service_principal_with_owner(assignments)
        assert len(findings) == 1

    def test_no_finding_for_user_owner(self) -> None:
        assignments = [
            RoleAssignment(
                principal_id="u-1",
                principal_type="User",
                role_definition_name="Owner",
                scope="/subscriptions/s",
            )
        ]
        assert check_service_principal_with_owner(assignments) == []

    def test_no_finding_for_sp_reader(self) -> None:
        assignments = [
            RoleAssignment(
                principal_id="sp-1",
                principal_type="ServicePrincipal",
                role_definition_name="Reader",
                scope="/subscriptions/s",
            )
        ]
        assert check_service_principal_with_owner(assignments) == []


# ---------------------------------------------------------------------------
# check_wildcard_permissions
# ---------------------------------------------------------------------------


class TestCheckWildcardPermissions:
    def test_detects_wildcard_in_custom_role(
        self, policy_with_wildcard_custom_role: PolicyDocument
    ) -> None:
        findings = check_wildcard_permissions(policy_with_wildcard_custom_role.role_definitions)
        assert len(findings) == 1
        assert findings[0].finding_id == "IOAR-004"

    def test_no_finding_for_builtin_wildcard(self) -> None:
        builtin = RoleDefinition(
            role_id="rd-builtin",
            name="Owner (built-in)",
            permissions=[{"actions": ["*"], "notActions": []}],
            is_custom=False,
        )
        assert check_wildcard_permissions([builtin]) == []

    def test_no_finding_for_specific_actions(self) -> None:
        custom = RoleDefinition(
            role_id="rd-custom",
            name="CustomReader",
            permissions=[{"actions": ["Microsoft.Compute/virtualMachines/read"], "notActions": []}],
            is_custom=True,
        )
        assert check_wildcard_permissions([custom]) == []

    def test_no_finding_empty_roles(self) -> None:
        assert check_wildcard_permissions([]) == []


# ---------------------------------------------------------------------------
# check_stale_assignments
# ---------------------------------------------------------------------------


class TestCheckStaleAssignments:
    def _assignment(self, principal_id: str) -> RoleAssignment:
        return RoleAssignment(
            principal_id=principal_id,
            principal_type="User",
            role_definition_name="Reader",
            scope="/subscriptions/s",
        )

    def test_detects_unknown_principal(self) -> None:
        assignments = [self._assignment("known"), self._assignment("ghost")]
        findings = check_stale_assignments(assignments, known_principal_ids={"known"})
        assert len(findings) == 1
        assert findings[0].finding_id == "IOAR-005"
        assert "ghost" in findings[0].affected_principals

    def test_no_finding_when_all_known(self) -> None:
        assignments = [self._assignment("u1"), self._assignment("u2")]
        assert check_stale_assignments(assignments, known_principal_ids={"u1", "u2"}) == []

    def test_skipped_when_no_known_ids_provided(self) -> None:
        assignments = [self._assignment("ghost")]
        assert check_stale_assignments(assignments, known_principal_ids=None) == []

    def test_no_finding_empty_assignments(self) -> None:
        assert check_stale_assignments([], known_principal_ids={"u1"}) == []


# ---------------------------------------------------------------------------
# check_no_guest_users_with_privileged_roles
# ---------------------------------------------------------------------------


class TestCheckGuestUsersWithPrivilegedRoles:
    def _assignment(self, principal_id: str, role: str) -> RoleAssignment:
        return RoleAssignment(
            principal_id=principal_id,
            principal_type="User",
            role_definition_name=role,
            scope="/subscriptions/s",
        )

    def test_detects_guest_with_owner(self) -> None:
        assignments = [self._assignment("guest-001", "Owner")]
        findings = check_no_guest_users_with_privileged_roles(
            assignments, guest_principal_ids={"guest-001"}
        )
        assert len(findings) == 1
        assert findings[0].finding_id == "IOAR-006"

    def test_no_finding_for_guest_reader(self) -> None:
        assignments = [self._assignment("guest-001", "Reader")]
        findings = check_no_guest_users_with_privileged_roles(
            assignments, guest_principal_ids={"guest-001"}
        )
        assert findings == []

    def test_no_finding_when_guest_ids_not_provided(self) -> None:
        assignments = [self._assignment("guest-001", "Owner")]
        assert check_no_guest_users_with_privileged_roles(assignments, guest_principal_ids=None) == []


# ---------------------------------------------------------------------------
# analyze (orchestrator)
# ---------------------------------------------------------------------------


class TestAnalyze:
    def test_clean_policy_no_findings(self, clean_policy: PolicyDocument) -> None:
        report = analyze(clean_policy)
        assert isinstance(report, AnalysisReport)
        assert report.findings == []
        assert report.risk_score == 0

    def test_risky_policy_has_findings(self, risky_policy: PolicyDocument) -> None:
        report = analyze(
            risky_policy,
            known_principal_ids={"aaaa-1001", "sp-2001", "bbbb-1002", "cccc-1003", "dddd-1004"},
        )
        assert len(report.findings) > 0
        severities = {f.severity for f in report.findings}
        assert Severity.CRITICAL in severities or Severity.HIGH in severities

    def test_report_has_summary(self, risky_policy: PolicyDocument) -> None:
        report = analyze(risky_policy)
        assert isinstance(report.summary, str)
        assert len(report.summary) > 0

    def test_findings_sorted_by_severity(self, risky_policy: PolicyDocument) -> None:
        report = analyze(risky_policy)
        orders = [f.severity.sort_order for f in report.findings_by_severity]
        assert orders == sorted(orders)

    def test_report_counts_correct(self) -> None:
        policy = PolicyDocument(
            role_assignments=[
                RoleAssignment(
                    principal_id="u-1",
                    principal_type="User",
                    role_definition_name="Owner",
                    scope="/",
                )
            ],
            role_definitions=[],
        )
        report = analyze(policy)
        assert report.total_assignments_reviewed == 1
        assert report.total_roles_reviewed == 0

    def test_risk_score_positive_for_risky_policy(self, risky_policy: PolicyDocument) -> None:
        report = analyze(risky_policy)
        assert report.risk_score > 0


# ---------------------------------------------------------------------------
# load_policy_from_dict
# ---------------------------------------------------------------------------


class TestLoadPolicyFromDict:
    def test_loads_minimal_dict(self) -> None:
        data = {
            "role_assignments": [
                {
                    "principal_id": "u-1",
                    "principal_type": "User",
                    "role_definition_name": "Reader",
                    "scope": "/subscriptions/s",
                }
            ]
        }
        policy = load_policy_from_dict(data, source="test")
        assert len(policy.role_assignments) == 1
        assert policy.source == "test"

    def test_loads_empty_dict(self) -> None:
        policy = load_policy_from_dict({})
        assert policy.role_assignments == []
        assert policy.role_definitions == []

    def test_preserves_raw(self) -> None:
        data = {"role_assignments": [], "extra_field": "value"}
        policy = load_policy_from_dict(data)
        assert policy.raw == data
