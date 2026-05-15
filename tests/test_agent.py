"""Tests for iam_rbac_reviewer.agent (dispatch_tool_call and local fallback)."""

from __future__ import annotations

import json
from pathlib import Path

from iam_rbac_reviewer.agent import _run_local_agent, dispatch_tool_call


class TestDispatchToolCall:
    def test_dispatches_get_supported_checks(self) -> None:
        result = dispatch_tool_call("get_supported_checks", {})
        checks = json.loads(result)
        assert isinstance(checks, list)

    def test_dispatches_with_json_string_args(self) -> None:
        result = dispatch_tool_call("explain_finding", json.dumps({"finding_id": "IOAR-001"}))
        data = json.loads(result)
        assert "explanation" in data

    def test_dispatches_with_dict_args(self) -> None:
        result = dispatch_tool_call("explain_finding", {"finding_id": "IOAR-002"})
        data = json.loads(result)
        assert "remediation" in data

    def test_unknown_tool_returns_error(self) -> None:
        result = dispatch_tool_call("nonexistent_tool", {})
        data = json.loads(result)
        assert "error" in data

    def test_bad_args_returns_error(self) -> None:
        result = dispatch_tool_call("explain_finding", {})  # missing required finding_id
        data = json.loads(result)
        assert "error" in data

    def test_invalid_json_string_treated_as_empty(self) -> None:
        result = dispatch_tool_call("get_supported_checks", "not-json")
        checks = json.loads(result)
        assert isinstance(checks, list)


class TestRunLocalAgent:
    def test_list_checks_keyword(self) -> None:
        response = _run_local_agent("list all supported checks")
        data = json.loads(response)
        assert isinstance(data, list)

    def test_explain_finding_keyword(self) -> None:
        response = _run_local_agent("explain IOAR-001")
        data = json.loads(response)
        assert "explanation" in data

    def test_unknown_request_returns_help(self) -> None:
        response = _run_local_agent("what is the meaning of life")
        assert "Local mode" in response

    def test_file_path_triggers_review(self, tmp_path: Path) -> None:

        policy_file = tmp_path / "p.json"
        policy_file.write_text(json.dumps({"role_assignments": [], "role_definitions": []}))
        response = _run_local_agent(f"review the file {policy_file}")
        data = json.loads(response)
        assert "findings" in data
