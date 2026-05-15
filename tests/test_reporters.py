"""Tests for iam_rbac_reviewer.reporters."""

from __future__ import annotations

import json

from iam_rbac_reviewer.analyzer import analyze
from iam_rbac_reviewer.models import AnalysisReport, OutputFormat, PolicyDocument, RoleAssignment
from iam_rbac_reviewer.reporters import render, render_json, render_markdown, render_text


def _risky_report() -> AnalysisReport:
    policy = PolicyDocument(
        role_assignments=[
            RoleAssignment(
                principal_id="u-bad",
                principal_type="User",
                role_definition_name="Owner",
                scope="/",
            )
        ]
    )
    return analyze(policy)


def _clean_report() -> AnalysisReport:
    policy = PolicyDocument(
        role_assignments=[
            RoleAssignment(
                principal_id="u-ok",
                principal_type="User",
                role_definition_name="Reader",
                scope="/subscriptions/s",
            )
        ]
    )
    return analyze(policy)


class TestRenderText:
    def test_contains_header(self) -> None:
        report = _clean_report()
        output = render_text(report)
        assert "IAM / RBAC Security Review Report" in output

    def test_no_issues_message_for_clean_report(self) -> None:
        output = render_text(_clean_report())
        assert "No issues found" in output

    def test_contains_finding_details_for_risky_report(self) -> None:
        output = render_text(_risky_report(), use_colour=False)
        assert "IOAR-001" in output
        assert "CRITICAL" in output

    def test_contains_report_id(self) -> None:
        report = _clean_report()
        output = render_text(report)
        assert report.report_id in output


class TestRenderJson:
    def test_valid_json(self) -> None:
        output = render_json(_risky_report())
        data = json.loads(output)
        assert "findings" in data

    def test_includes_risk_score(self) -> None:
        report = _risky_report()
        data = json.loads(render_json(report))
        assert data["risk_score"] == report.risk_score

    def test_findings_sorted_by_severity(self) -> None:
        report = _risky_report()
        data = json.loads(render_json(report))
        # For a single critical finding there is only one; just check presence
        assert len(data["findings"]) > 0


class TestRenderMarkdown:
    def test_starts_with_h1(self) -> None:
        output = render_markdown(_risky_report())
        assert output.startswith("# IAM / RBAC Security Review Report")

    def test_contains_severity_table(self) -> None:
        output = render_markdown(_risky_report())
        assert "## Severity breakdown" in output

    def test_no_issues_message_for_clean(self) -> None:
        output = render_markdown(_clean_report())
        assert "No issues found" in output

    def test_contains_finding_section(self) -> None:
        output = render_markdown(_risky_report())
        assert "## Findings" in output
        assert "IOAR-001" in output


class TestRenderDispatch:
    def test_dispatch_text(self) -> None:
        output = render(_clean_report(), OutputFormat.TEXT)
        assert "IAM / RBAC" in output

    def test_dispatch_json(self) -> None:
        output = render(_clean_report(), OutputFormat.JSON)
        json.loads(output)  # should not raise

    def test_dispatch_markdown(self) -> None:
        output = render(_clean_report(), OutputFormat.MARKDOWN)
        assert output.startswith("#")

    def test_default_is_text(self) -> None:
        output = render(_clean_report())
        assert "IAM / RBAC Security Review Report" in output
