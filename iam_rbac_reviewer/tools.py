"""Azure AI Foundry tool definitions for the IAM / RBAC reviewer agent.

Each public function in this module is wrapped as a Foundry agent *tool*.
Tools must be pure-Python, serialisable, and independently testable.

Azure AI Foundry tool schema uses the OpenAI function-calling format:
  {
      "type": "function",
      "function": {
          "name": ...,
          "description": ...,
          "parameters": { ... }   # JSON Schema
      }
  }
"""

from __future__ import annotations

import json
import logging
from typing import Any

import yaml

from .analyzer import analyze, load_policy_from_dict
from .models import OutputFormat
from .reporters import render

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def review_policy_document(policy_json: str, output_format: str = "json") -> str:
    """Analyse a JSON-serialised IAM / RBAC policy document and return findings.

    Args:
        policy_json: JSON string conforming to the normalised policy schema:
            ``{"role_assignments": [...], "role_definitions": [...]}``
        output_format: One of ``"json"``, ``"text"``, ``"markdown"``.

    Returns:
        Rendered report as a string.
    """
    try:
        data: dict[str, Any] = json.loads(policy_json)
    except json.JSONDecodeError as exc:
        logger.error("review_policy_document: invalid JSON input: %s", exc)
        return json.dumps({"error": f"Invalid JSON: {exc}"})

    try:
        policy = load_policy_from_dict(data, source="agent-input")
    except Exception as exc:
        logger.error("review_policy_document: policy parse error: %s", exc)
        return json.dumps({"error": f"Policy parse error: {exc}"})

    report = analyze(policy)
    fmt = OutputFormat(output_format) if output_format in OutputFormat._value2member_map_ else OutputFormat.JSON
    return render(report, fmt)


def review_policy_file(file_path: str, output_format: str = "json") -> str:
    """Load a local JSON or YAML policy file and analyse it.

    Args:
        file_path: Absolute or relative path to the policy file.
        output_format: One of ``"json"``, ``"text"``, ``"markdown"``.

    Returns:
        Rendered report as a string.
    """
    import pathlib

    path = pathlib.Path(file_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    except Exception as exc:
        logger.error("review_policy_file: read/parse error for %s: %s", file_path, exc)
        return json.dumps({"error": f"Read/parse error: {exc}"})

    policy = load_policy_from_dict(data, source=str(path.resolve()))
    report = analyze(policy)
    fmt = OutputFormat(output_format) if output_format in OutputFormat._value2member_map_ else OutputFormat.JSON
    return render(report, fmt)


def explain_finding(finding_id: str) -> str:
    """Return a detailed explanation and remediation guide for a finding ID.

    Args:
        finding_id: The finding identifier, e.g. ``"IOAR-001"``.

    Returns:
        JSON string with ``{"finding_id": ..., "explanation": ..., "remediation": ...}``
    """
    explanations: dict[str, dict[str, str]] = {
        "IOAR-001": {
            "explanation": (
                "Assigning the Owner, Contributor, or User Access Administrator role at the "
                "root ('/') scope or a management-group scope grants unrestricted access to "
                "every resource in the tenant. A single compromised credential can lead to "
                "total tenant compromise."
            ),
            "remediation": (
                "1. Identify each affected assignment with: "
                "   az role assignment list --scope / --output table\n"
                "2. Remove the broad assignment: "
                "   az role assignment delete --assignee <principal> --role Owner --scope /\n"
                "3. Re-assign the minimum required role at the narrowest necessary scope "
                "   (subscription, resource group, or specific resource)."
            ),
        },
        "IOAR-002": {
            "explanation": (
                "Having many Owners on a subscription increases the blast radius of a "
                "compromised account and makes access reviews harder."
            ),
            "remediation": (
                "1. List all Owner assignments: "
                "   az role assignment list --role Owner --output table\n"
                "2. For each owner, determine if the full Owner role is necessary.\n"
                "3. Replace with Contributor or a custom role where appropriate.\n"
                "4. Enable Azure AD Privileged Identity Management (PIM) for just-in-time Owner access."
            ),
        },
        "IOAR-003": {
            "explanation": (
                "Service principals and managed identities are non-human identities that often "
                "have weaker authentication controls (no MFA). Granting them Owner or Contributor "
                "at broad scope is high risk."
            ),
            "remediation": (
                "1. List SP/MI role assignments: "
                "   az role assignment list --assignee <sp-object-id> --output table\n"
                "2. Create a custom role with only the required permissions.\n"
                "3. Use managed identities instead of service principals where possible.\n"
                "4. Rotate service principal credentials regularly."
            ),
        },
        "IOAR-004": {
            "explanation": (
                "Custom roles with wildcard ('*') actions grant all current and future actions "
                "of every resource provider, making them effectively equivalent to built-in "
                "Contributor — this defeats the purpose of creating a custom role."
            ),
            "remediation": (
                "1. Review the role definition: "
                "   az role definition show --name <role-name>\n"
                "2. Replace '*' with specific action strings.\n"
                "3. Use 'az provider operation list' to enumerate available actions.\n"
                "4. Re-deploy the updated role definition."
            ),
        },
        "IOAR-005": {
            "explanation": (
                "Role assignments for deleted users, groups, or service principals are orphaned. "
                "They clutter the access model and may be re-activated if an object with the same "
                "ID is recreated."
            ),
            "remediation": (
                "1. List all role assignments: az role assignment list --all --output json\n"
                "2. Cross-reference principal IDs against your directory.\n"
                "3. Delete orphaned assignments: "
                "   az role assignment delete --ids <assignment-id>"
            ),
        },
        "IOAR-006": {
            "explanation": (
                "Guest users are external identities with potentially weaker authentication "
                "and governance controls. Granting them privileged roles bypasses internal "
                "security policies."
            ),
            "remediation": (
                "1. List guest assignments: "
                "   az role assignment list --all | jq '[.[] | select(.principalType==\"Guest\")]'\n"
                "2. Remove privileged assignments.\n"
                "3. Use Azure AD PIM for any temporary privileged access required by guests."
            ),
        },
    }

    info = explanations.get(finding_id.upper())
    if info is None:
        return json.dumps({"error": f"Unknown finding_id: '{finding_id}'. "
                           f"Known IDs: {list(explanations.keys())}"})

    return json.dumps({"finding_id": finding_id.upper(), **info})


def get_supported_checks() -> str:
    """Return a JSON list of all supported check IDs and their descriptions.

    Returns:
        JSON string with a list of ``{"id": ..., "title": ..., "severity": ...}`` objects.
    """
    checks = [
        {"id": "IOAR-001", "title": "Privileged role at root/management-group scope", "severity": "CRITICAL"},
        {"id": "IOAR-002", "title": "Excessive number of Owners per scope", "severity": "HIGH"},
        {"id": "IOAR-003", "title": "Service principal / MI with highly privileged role", "severity": "HIGH"},
        {"id": "IOAR-004", "title": "Custom role with wildcard ('*') action", "severity": "HIGH"},
        {"id": "IOAR-005", "title": "Orphaned role assignment (unknown principal)", "severity": "MEDIUM"},
        {"id": "IOAR-006", "title": "Guest user holds a privileged role", "severity": "HIGH"},
    ]
    return json.dumps(checks, indent=2)


# ---------------------------------------------------------------------------
# Foundry tool schema definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "review_policy_document",
            "description": (
                "Analyse an IAM / RBAC policy document provided as a JSON string. "
                "Returns a security review report with findings and recommendations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_json": {
                        "type": "string",
                        "description": (
                            "JSON string containing 'role_assignments' and optionally "
                            "'role_definitions' arrays."
                        ),
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["json", "text", "markdown"],
                        "description": "Output format for the report. Defaults to 'json'.",
                    },
                },
                "required": ["policy_json"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_policy_file",
            "description": (
                "Load a local JSON or YAML policy file and analyse it. "
                "Returns a security review report with findings and recommendations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the policy file (JSON or YAML).",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["json", "text", "markdown"],
                        "description": "Output format for the report. Defaults to 'json'.",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_finding",
            "description": (
                "Return a detailed explanation and step-by-step remediation guide "
                "for a specific finding ID (e.g. 'IOAR-001')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "finding_id": {
                        "type": "string",
                        "description": "The finding identifier, e.g. 'IOAR-001'.",
                    },
                },
                "required": ["finding_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_supported_checks",
            "description": "Return the list of all supported security check IDs with titles and severities.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# Map tool name → callable for the agent dispatcher
TOOL_REGISTRY: dict[str, Any] = {
    "review_policy_document": review_policy_document,
    "review_policy_file": review_policy_file,
    "explain_finding": explain_finding,
    "get_supported_checks": get_supported_checks,
}
