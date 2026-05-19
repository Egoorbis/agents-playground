"""Tests for iam_rbac_reviewer.tools (Foundry tool implementations)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iam_rbac_reviewer.tools import (
    TOOL_DEFINITIONS,
    TOOL_REGISTRY,
    explain_finding,
    get_supported_checks,
    review_policy_document,
    review_policy_file,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# review_policy_document
# ---------------------------------------------------------------------------


class TestReviewPolicyDocument:
    _CLEAN_POLICY = json.dumps(
        {
            "role_assignments": [
                {
                    "principal_id": "u-1",
                    "principal_type": "User",
                    "role_definition_name": "Reader",
                    "scope": "/subscriptions/s",
                }
            ]
        }
    )

    _RISKY_POLICY = json.dumps(
        {
            "role_assignments": [
                {
                    "principal_id": "u-bad",
                    "principal_type": "User",
                    "role_definition_name": "Owner",
                    "scope": "/",
                }
            ]
        }
    )

    def test_returns_json_by_default(self) -> None:
        result = review_policy_document(self._CLEAN_POLICY)
        data = json.loads(result)
        assert "findings" in data

    def test_json_format_explicit(self) -> None:
        result = review_policy_document(self._RISKY_POLICY, output_format="json")
        data = json.loads(result)
        assert len(data["findings"]) > 0

    def test_text_format(self) -> None:
        result = review_policy_document(self._RISKY_POLICY, output_format="text")
        assert "IAM / RBAC Security Review Report" in result

    def test_markdown_format(self) -> None:
        result = review_policy_document(self._RISKY_POLICY, output_format="markdown")
        assert "# IAM / RBAC Security Review Report" in result

    def test_invalid_json_returns_error(self) -> None:
        result = review_policy_document("not valid json")
        data = json.loads(result)
        assert "error" in data

    def test_unknown_output_format_falls_back_to_json(self) -> None:
        result = review_policy_document(self._CLEAN_POLICY, output_format="xml")
        data = json.loads(result)
        assert "findings" in data

    def test_empty_policy(self) -> None:
        result = review_policy_document(json.dumps({}))
        data = json.loads(result)
        assert data["findings"] == []


# ---------------------------------------------------------------------------
# review_policy_file
# ---------------------------------------------------------------------------


class TestReviewPolicyFile:
    def test_reviews_json_fixture(self) -> None:
        path = str(FIXTURES_DIR / "clean_policy.json")
        result = review_policy_file(path)
        data = json.loads(result)
        assert "findings" in data

    def test_reviews_risky_fixture(self) -> None:
        path = str(FIXTURES_DIR / "risky_policy.json")
        result = review_policy_file(path)
        data = json.loads(result)
        assert len(data["findings"]) > 0

    def test_nonexistent_file_returns_error(self) -> None:
        result = review_policy_file("/tmp/does_not_exist_abc123.json")
        data = json.loads(result)
        assert "error" in data

    def test_yaml_fixture(self, tmp_path: Path) -> None:
        yaml_content = (
            "role_assignments:\n"
            "  - principal_id: u-1\n"
            "    principal_type: User\n"
            "    role_definition_name: Reader\n"
            "    scope: /subscriptions/s\n"
        )
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(yaml_content)
        result = review_policy_file(str(policy_file))
        data = json.loads(result)
        assert "findings" in data


# ---------------------------------------------------------------------------
# explain_finding
# ---------------------------------------------------------------------------


class TestExplainFinding:
    @pytest.mark.parametrize("finding_id", ["IOAR-001", "IOAR-002", "IOAR-003", "IOAR-004", "IOAR-005", "IOAR-006"])
    def test_known_findings_return_explanation(self, finding_id: str) -> None:
        result = explain_finding(finding_id)
        data = json.loads(result)
        assert "error" not in data
        assert data["finding_id"] == finding_id
        assert "explanation" in data
        assert "remediation" in data

    def test_case_insensitive(self) -> None:
        result = explain_finding("ioar-001")
        data = json.loads(result)
        assert "error" not in data

    def test_unknown_finding_returns_error(self) -> None:
        result = explain_finding("IOAR-999")
        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# get_supported_checks
# ---------------------------------------------------------------------------


class TestGetSupportedChecks:
    def test_returns_list_of_checks(self) -> None:
        result = get_supported_checks()
        checks = json.loads(result)
        assert isinstance(checks, list)
        assert len(checks) >= 6

    def test_each_check_has_required_fields(self) -> None:
        checks = json.loads(get_supported_checks())
        for check in checks:
            assert "id" in check
            assert "title" in check
            assert "severity" in check

    def test_contains_ioar_001(self) -> None:
        checks = json.loads(get_supported_checks())
        ids = [c["id"] for c in checks]
        assert "IOAR-001" in ids


# ---------------------------------------------------------------------------
# TOOL_DEFINITIONS schema
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    def test_all_tools_defined(self) -> None:
        names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
        assert set(names) == {
            "review_policy_document",
            "review_policy_file",
            "explain_finding",
            "get_supported_checks",
        }

    def test_each_definition_has_required_fields(self) -> None:
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn


# ---------------------------------------------------------------------------
# TOOL_REGISTRY
# ---------------------------------------------------------------------------


class TestToolRegistry:
    def test_registry_contains_all_tools(self) -> None:
        assert set(TOOL_REGISTRY.keys()) == {
            "review_policy_document",
            "review_policy_file",
            "explain_finding",
            "get_supported_checks",
        }

    def test_registry_values_are_callable(self) -> None:
        for fn in TOOL_REGISTRY.values():
            assert callable(fn)
