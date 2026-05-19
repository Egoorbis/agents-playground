"""Shared pytest fixtures for the IAM / RBAC reviewer test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iam_rbac_reviewer.models import (
    PolicyDocument,
    RoleAssignment,
    RoleDefinition,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Policy fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def clean_policy() -> PolicyDocument:
    """A policy with no security findings."""
    data = json.loads((FIXTURES_DIR / "clean_policy.json").read_text())
    return PolicyDocument(
        role_assignments=[RoleAssignment(**a) for a in data["role_assignments"]],
        role_definitions=[],
        source="test:clean",
    )


@pytest.fixture()
def risky_policy() -> PolicyDocument:
    """A policy that triggers multiple findings."""
    data = json.loads((FIXTURES_DIR / "risky_policy.json").read_text())
    return PolicyDocument(
        role_assignments=[RoleAssignment(**a) for a in data["role_assignments"]],
        role_definitions=[RoleDefinition(**r) for r in data["role_definitions"]],
        source="test:risky",
    )


@pytest.fixture()
def minimal_owner_at_root() -> PolicyDocument:
    """Single Owner assignment at root scope."""
    return PolicyDocument(
        role_assignments=[
            RoleAssignment(
                principal_id="user-001",
                principal_type="User",
                role_definition_name="Owner",
                scope="/",
            )
        ],
        source="test:root-owner",
    )


@pytest.fixture()
def sp_with_owner() -> PolicyDocument:
    """Service principal holding Owner on a subscription."""
    return PolicyDocument(
        role_assignments=[
            RoleAssignment(
                principal_id="sp-abc",
                principal_type="ServicePrincipal",
                role_definition_name="Owner",
                scope="/subscriptions/sub-x",
            )
        ],
        source="test:sp-owner",
    )


@pytest.fixture()
def policy_with_wildcard_custom_role() -> PolicyDocument:
    """Custom role that uses wildcard '*' actions."""
    return PolicyDocument(
        role_assignments=[],
        role_definitions=[
            RoleDefinition(
                role_id="cr-001",
                name="DangerRole",
                permissions=[{"actions": ["*"], "notActions": []}],
                is_custom=True,
            )
        ],
        source="test:wildcard-role",
    )
