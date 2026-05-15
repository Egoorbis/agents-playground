"""IAM / RBAC Reviewer — Azure AI Foundry security agent package."""

from .agent import dispatch_tool_call, run_agent
from .analyzer import analyze, load_policy_from_dict
from .models import AnalysisReport, Finding, PolicyDocument, Severity
from .reporters import render

__all__ = [
    "AnalysisReport",
    "Finding",
    "PolicyDocument",
    "Severity",
    "analyze",
    "dispatch_tool_call",
    "load_policy_from_dict",
    "render",
    "run_agent",
]
