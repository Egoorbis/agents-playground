"""Tests for iam_rbac_reviewer.cli."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from iam_rbac_reviewer.cli import app

runner = CliRunner()

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestReviewCommand:
    def test_review_clean_policy_exits_zero(self) -> None:
        result = runner.invoke(app, ["review", str(FIXTURES_DIR / "clean_policy.json")])
        assert result.exit_code == 0
        assert "IAM / RBAC Security Review Report" in result.output

    def test_review_risky_policy_exits_nonzero(self) -> None:
        result = runner.invoke(app, ["review", str(FIXTURES_DIR / "risky_policy.json")])
        # CRITICAL or HIGH findings → exit code 2 or 3
        assert result.exit_code in (2, 3)

    def test_review_json_output(self) -> None:
        result = runner.invoke(
            app, ["review", str(FIXTURES_DIR / "clean_policy.json"), "--output", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "findings" in data

    def test_review_markdown_output(self) -> None:
        result = runner.invoke(
            app, ["review", str(FIXTURES_DIR / "clean_policy.json"), "--output", "markdown"]
        )
        assert result.exit_code == 0
        # Rich renders Markdown as styled text (strips '#'), but key content must be present
        assert "IAM / RBAC Security Review Report" in result.output

    def test_review_nonexistent_file_exits_one(self) -> None:
        result = runner.invoke(app, ["review", "/tmp/does_not_exist_xyz.json"])
        assert result.exit_code == 1

    def test_review_invalid_json_exits_one(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json at all")
        result = runner.invoke(app, ["review", str(bad_file)])
        assert result.exit_code == 1

    def test_review_yaml_file(self, tmp_path: Path) -> None:
        yaml_content = (
            "role_assignments:\n"
            "  - principal_id: u-1\n"
            "    principal_type: User\n"
            "    role_definition_name: Reader\n"
            "    scope: /subscriptions/s\n"
        )
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(yaml_content)
        result = runner.invoke(app, ["review", str(policy_file)])
        assert result.exit_code == 0

    def test_review_custom_owner_threshold(self) -> None:
        result = runner.invoke(
            app,
            [
                "review",
                str(FIXTURES_DIR / "risky_policy.json"),
                "--owner-threshold",
                "100",
            ],
        )
        # With a high threshold, IOAR-002 won't fire; still CRITICAL for root-scope Owner
        assert result.exit_code in (0, 2, 3)


class TestListChecksCommand:
    def test_lists_checks(self) -> None:
        result = runner.invoke(app, ["list-checks"])
        assert result.exit_code == 0
        assert "IOAR-001" in result.output

    def test_shows_all_known_check_ids(self) -> None:
        result = runner.invoke(app, ["list-checks"])
        for check_id in ("IOAR-001", "IOAR-002", "IOAR-003", "IOAR-004", "IOAR-005", "IOAR-006"):
            assert check_id in result.output


class TestExplainCommand:
    def test_explain_known_finding(self) -> None:
        result = runner.invoke(app, ["explain", "IOAR-001"])
        assert result.exit_code == 0
        assert "IOAR-001" in result.output

    def test_explain_all_findings(self) -> None:
        for fid in ("IOAR-001", "IOAR-002", "IOAR-003", "IOAR-004", "IOAR-005", "IOAR-006"):
            result = runner.invoke(app, ["explain", fid])
            assert result.exit_code == 0, f"explain {fid} failed"

    def test_explain_unknown_finding_exits_one(self) -> None:
        result = runner.invoke(app, ["explain", "IOAR-999"])
        assert result.exit_code == 1


class TestAskCommand:
    def test_ask_local_mode_lists_checks(self) -> None:
        # No AZURE_AI_PROJECT_ENDPOINT set → local mode
        result = runner.invoke(app, ["ask", "list all supported checks"])
        assert result.exit_code == 0
        # Local mode returns JSON list or help text
        assert result.output.strip() != ""

    def test_ask_local_mode_returns_response(self) -> None:
        result = runner.invoke(app, ["ask", "what is the meaning of life"])
        assert result.exit_code == 0
        assert "Local mode" in result.output
