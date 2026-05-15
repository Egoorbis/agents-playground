"""Data models for the IAM / RBAC reviewer agent.

All structures that cross a boundary (file I/O, API calls, CLI output) are
represented as Pydantic v2 models so that validation is always enforced.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    """Finding severity levels, ordered from most to least critical."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def sort_order(self) -> int:
        """Return an integer so findings can be sorted deterministically."""
        return {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }[self]


class PolicyType(StrEnum):
    """Source format for an IAM / RBAC policy document."""

    AZURE_RBAC = "azure_rbac"
    AWS_IAM = "aws_iam"
    GENERIC_JSON = "generic_json"
    GENERIC_YAML = "generic_yaml"


class OutputFormat(StrEnum):
    """CLI output format options."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


# ---------------------------------------------------------------------------
# Policy input models
# ---------------------------------------------------------------------------


class RoleAssignment(BaseModel):
    """A single principal-to-role binding."""

    principal_id: str = Field(..., description="Object ID of the user, group, or service principal.")
    principal_type: str = Field(..., description="User | Group | ServicePrincipal | ManagedIdentity")
    role_definition_name: str = Field(..., description="Human-readable role name (e.g. 'Owner').")
    role_definition_id: str = Field(default="", description="Full resource ID of the role definition.")
    scope: str = Field(..., description="Azure resource scope at which the role is assigned.")
    condition: str | None = Field(default=None, description="Optional ABAC condition expression.")

    @field_validator("principal_type")
    @classmethod
    def validate_principal_type(cls, v: str) -> str:
        allowed = {"User", "Group", "ServicePrincipal", "ManagedIdentity"}
        if v not in allowed:
            raise ValueError(f"principal_type must be one of {allowed}, got '{v}'")
        return v


class RoleDefinition(BaseModel):
    """A custom or built-in role definition."""

    role_id: str = Field(..., description="Unique identifier for the role definition.")
    name: str = Field(..., description="Display name of the role.")
    description: str = Field(default="", description="Human-readable description.")
    permissions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of permission objects with 'actions', 'notActions', etc.",
    )
    assignable_scopes: list[str] = Field(default_factory=list)
    is_custom: bool = Field(default=False)


class PolicyDocument(BaseModel):
    """The full policy corpus submitted for review."""

    policy_type: PolicyType = Field(default=PolicyType.AZURE_RBAC)
    role_assignments: list[RoleAssignment] = Field(default_factory=list)
    role_definitions: list[RoleDefinition] = Field(default_factory=list)
    raw: dict[str, Any] = Field(
        default_factory=dict,
        description="Original parsed document, preserved for context.",
    )
    source: str = Field(default="", description="File path or subscription ID that was analysed.")


# ---------------------------------------------------------------------------
# Finding / report models
# ---------------------------------------------------------------------------


class Recommendation(BaseModel):
    """A concrete remediation step attached to a finding."""

    title: str
    description: str
    reference_url: str = Field(default="")


class Finding(BaseModel):
    """A single security or compliance issue discovered during analysis."""

    finding_id: str = Field(..., description="Unique, stable identifier for this finding type.")
    title: str
    description: str
    severity: Severity
    affected_principals: list[str] = Field(default_factory=list)
    affected_roles: list[str] = Field(default_factory=list)
    affected_scopes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data supporting the finding.",
    )
    recommendations: list[Recommendation] = Field(default_factory=list)
    cis_controls: list[str] = Field(
        default_factory=list,
        description="Relevant CIS Control identifiers (e.g. 'CIS-5.4').",
    )


class AnalysisReport(BaseModel):
    """Top-level report returned by the analyzer."""

    report_id: str = Field(..., description="UUID for this report run.")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = Field(default="")
    policy_type: PolicyType = Field(default=PolicyType.AZURE_RBAC)
    total_roles_reviewed: int = Field(default=0)
    total_assignments_reviewed: int = Field(default=0)
    findings: list[Finding] = Field(default_factory=list)
    summary: str = Field(default="")

    @property
    def findings_by_severity(self) -> list[Finding]:
        """Return findings sorted CRITICAL → INFO."""
        return sorted(self.findings, key=lambda f: f.severity.sort_order)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.LOW)

    @property
    def risk_score(self) -> int:
        """Weighted risk score: CRITICAL=10, HIGH=5, MEDIUM=2, LOW=1."""
        weights = {
            Severity.CRITICAL: 10,
            Severity.HIGH: 5,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
            Severity.INFO: 0,
        }
        return sum(weights[f.severity] for f in self.findings)
