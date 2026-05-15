"""Tests for iam_rbac_reviewer.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from iam_rbac_reviewer.models import (
    AnalysisReport,
    Finding,
    RoleAssignment,
    Severity,
)


class TestSeverity:
    def test_sort_order_critical_lowest(self) -> None:
        assert Severity.CRITICAL.sort_order < Severity.HIGH.sort_order

    def test_sort_order_high_before_medium(self) -> None:
        assert Severity.HIGH.sort_order < Severity.MEDIUM.sort_order

    def test_info_sort_order_highest(self) -> None:
        assert Severity.INFO.sort_order > Severity.LOW.sort_order


class TestRoleAssignment:
    def test_valid_assignment(self) -> None:
        a = RoleAssignment(
            principal_id="abc",
            principal_type="User",
            role_definition_name="Reader",
            scope="/subscriptions/s",
        )
        assert a.principal_type == "User"

    def test_invalid_principal_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            RoleAssignment(
                principal_id="abc",
                principal_type="Robot",
                role_definition_name="Reader",
                scope="/subscriptions/s",
            )


class TestAnalysisReport:
    def _make_report(self) -> AnalysisReport:
        return AnalysisReport(
            report_id="r-001",
            findings=[
                Finding(
                    finding_id="IOAR-001",
                    title="T",
                    description="D",
                    severity=Severity.CRITICAL,
                ),
                Finding(
                    finding_id="IOAR-002",
                    title="T2",
                    description="D2",
                    severity=Severity.HIGH,
                ),
                Finding(
                    finding_id="IOAR-005",
                    title="T5",
                    description="D5",
                    severity=Severity.MEDIUM,
                ),
            ],
        )

    def test_critical_count(self) -> None:
        report = self._make_report()
        assert report.critical_count == 1

    def test_high_count(self) -> None:
        assert self._make_report().high_count == 1

    def test_medium_count(self) -> None:
        assert self._make_report().medium_count == 1

    def test_risk_score(self) -> None:
        report = self._make_report()
        # CRITICAL=10, HIGH=5, MEDIUM=2
        assert report.risk_score == 17

    def test_findings_by_severity_ordered(self) -> None:
        report = self._make_report()
        orders = [f.severity.sort_order for f in report.findings_by_severity]
        assert orders == sorted(orders)
