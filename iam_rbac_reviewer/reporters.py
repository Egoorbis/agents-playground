"""Report renderers for the IAM / RBAC reviewer.

Supports three output formats: plain text, JSON, and Markdown.
All renderers accept an ``AnalysisReport`` and return a ``str``.
"""

from __future__ import annotations

import json

from .models import AnalysisReport, OutputFormat, Severity

# Severity → ANSI colour for the plain-text renderer
_SEVERITY_COLOUR: dict[Severity, str] = {
    Severity.CRITICAL: "\033[1;31m",  # bold red
    Severity.HIGH: "\033[31m",  # red
    Severity.MEDIUM: "\033[33m",  # yellow
    Severity.LOW: "\033[34m",  # blue
    Severity.INFO: "\033[37m",  # grey
}
_RESET = "\033[0m"


def render(report: AnalysisReport, fmt: OutputFormat = OutputFormat.TEXT) -> str:
    """Dispatch to the appropriate renderer based on *fmt*.

    Args:
        report: The analysis report to render.
        fmt: The desired output format.

    Returns:
        A string ready to be written to stdout.
    """
    if fmt == OutputFormat.JSON:
        return render_json(report)
    if fmt == OutputFormat.MARKDOWN:
        return render_markdown(report)
    return render_text(report)


# ---------------------------------------------------------------------------
# Plain-text renderer
# ---------------------------------------------------------------------------


def render_text(report: AnalysisReport, *, use_colour: bool = True) -> str:
    """Render the report as a human-readable text block.

    Args:
        report: The analysis report to render.
        use_colour: Whether to include ANSI escape codes.

    Returns:
        Plain-text string.
    """
    lines: list[str] = []

    lines.append("=" * 70)
    lines.append("  IAM / RBAC Security Review Report")
    lines.append("=" * 70)
    lines.append(f"Report ID  : {report.report_id}")
    lines.append(f"Generated  : {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"Source     : {report.source or '(none)'}")
    lines.append(f"Policy type: {report.policy_type.value}")
    lines.append(
        f"Reviewed   : {report.total_assignments_reviewed} assignment(s), "
        f"{report.total_roles_reviewed} role definition(s)"
    )
    lines.append("")
    lines.append(f"Summary: {report.summary}")
    lines.append("")

    if not report.findings:
        lines.append("✅  No issues found.")
        return "\n".join(lines)

    lines.append(f"Findings ({len(report.findings)} total, risk score {report.risk_score}):")
    lines.append("-" * 70)

    for finding in report.findings_by_severity:
        sev_label = finding.severity.value
        if use_colour:
            colour = _SEVERITY_COLOUR.get(finding.severity, "")
            sev_label = f"{colour}{sev_label}{_RESET}"

        lines.append(f"\n[{sev_label}] {finding.finding_id}: {finding.title}")
        lines.append(f"  {finding.description}")

        if finding.affected_principals:
            lines.append(
                f"  Principals : {', '.join(finding.affected_principals[:5])}"
                + (" …" if len(finding.affected_principals) > 5 else "")
            )
        if finding.affected_roles:
            lines.append(f"  Roles      : {', '.join(finding.affected_roles)}")
        if finding.affected_scopes:
            lines.append(
                f"  Scopes     : {', '.join(finding.affected_scopes[:3])}"
                + (" …" if len(finding.affected_scopes) > 3 else "")
            )
        if finding.cis_controls:
            lines.append(f"  CIS        : {', '.join(finding.cis_controls)}")

        if finding.recommendations:
            lines.append("  Remediation:")
            for rec in finding.recommendations:
                lines.append(f"    • {rec.title}")
                lines.append(f"      {rec.description}")
                if rec.reference_url:
                    lines.append(f"      Ref: {rec.reference_url}")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON renderer
# ---------------------------------------------------------------------------


def render_json(report: AnalysisReport) -> str:
    """Render the report as a pretty-printed JSON string.

    Args:
        report: The analysis report to render.

    Returns:
        JSON string.
    """
    data = json.loads(report.model_dump_json())
    # Add computed properties
    data["risk_score"] = report.risk_score
    data["critical_count"] = report.critical_count
    data["high_count"] = report.high_count
    data["medium_count"] = report.medium_count
    data["low_count"] = report.low_count
    # Sort findings by severity
    data["findings"] = json.loads(
        AnalysisReport(**{**report.model_dump(), "findings": list(report.findings_by_severity)}).model_dump_json()
    )["findings"]
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def render_markdown(report: AnalysisReport) -> str:
    """Render the report as a GitHub-flavoured Markdown document.

    Args:
        report: The analysis report to render.

    Returns:
        Markdown string.
    """
    lines: list[str] = []

    lines.append("# IAM / RBAC Security Review Report\n")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| **Report ID** | `{report.report_id}` |")
    lines.append(f"| **Generated** | {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} |")
    lines.append(f"| **Source** | {report.source or '(none)'} |")
    lines.append(f"| **Policy type** | {report.policy_type.value} |")
    lines.append(f"| **Assignments reviewed** | {report.total_assignments_reviewed} |")
    lines.append(f"| **Role definitions reviewed** | {report.total_roles_reviewed} |")
    lines.append(f"| **Risk score** | **{report.risk_score}** |")
    lines.append("")
    lines.append(f"## Summary\n\n{report.summary}\n")

    if not report.findings:
        lines.append("✅ **No issues found.**\n")
        return "\n".join(lines)

    # Severity summary table
    lines.append("## Severity breakdown\n")
    lines.append("| Severity | Count |")
    lines.append("|---|---|")
    for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO):
        count = sum(1 for f in report.findings if f.severity == sev)
        if count:
            lines.append(f"| {sev.value} | {count} |")
    lines.append("")

    lines.append("## Findings\n")
    for idx, finding in enumerate(report.findings_by_severity, 1):
        lines.append(f"### {idx}. [{finding.severity.value}] {finding.finding_id} — {finding.title}\n")
        lines.append(f"{finding.description}\n")

        if finding.affected_principals:
            lines.append("**Affected principals:**")
            for p in finding.affected_principals[:10]:
                lines.append(f"- `{p}`")
            if len(finding.affected_principals) > 10:
                lines.append(f"- _(…and {len(finding.affected_principals) - 10} more)_")
            lines.append("")

        if finding.affected_roles:
            lines.append("**Affected roles:** " + ", ".join(f"`{r}`" for r in finding.affected_roles) + "\n")

        if finding.affected_scopes:
            lines.append("**Affected scopes:** " + ", ".join(f"`{s}`" for s in finding.affected_scopes) + "\n")

        if finding.cis_controls:
            lines.append("**CIS Controls:** " + ", ".join(finding.cis_controls) + "\n")

        if finding.recommendations:
            lines.append("**Recommendations:**\n")
            for rec in finding.recommendations:
                lines.append(f"- **{rec.title}**  ")
                lines.append(f"  {rec.description}")
                if rec.reference_url:
                    lines.append(f"  [Reference]({rec.reference_url})")
            lines.append("")

    return "\n".join(lines)
