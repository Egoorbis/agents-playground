"""Command-line interface for the IAM / RBAC reviewer agent.

Usage examples::

    # Review a local policy file and print a Markdown report
    iam-rbac-reviewer review policy.json --output markdown

    # Ask the Foundry agent a free-form security question
    iam-rbac-reviewer ask "Which roles grant Owner at the root scope?"

    # List all supported security checks
    iam-rbac-reviewer list-checks

    # Explain a specific finding
    iam-rbac-reviewer explain IOAR-001
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .analyzer import analyze, load_policy_from_dict
from .config import get_settings
from .models import OutputFormat
from .reporters import render
from .tools import TOOL_REGISTRY

app = typer.Typer(
    name="iam-rbac-reviewer",
    help="IAM / RBAC security reviewer powered by Azure AI Foundry.",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True, style="bold red")


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# review command
# ---------------------------------------------------------------------------


@app.command()
def review(
    source: Annotated[
        Path,
        typer.Argument(help="Path to a JSON or YAML policy file to review."),
    ],
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output format: text | json | markdown."),
    ] = "text",
    owner_threshold: Annotated[
        int,
        typer.Option("--owner-threshold", help="Max Owners per scope before triggering IOAR-002."),
    ] = 3,
) -> None:
    """Review a local IAM / RBAC policy file for security issues."""
    _configure_logging(get_settings().log_level)

    if not source.exists():
        err_console.print(f"[Error] File not found: {source}")
        err_console.print("  Ensure the path is correct and the file is readable.")
        raise typer.Exit(code=1)

    try:
        text = source.read_text(encoding="utf-8")
        data = yaml.safe_load(text) if source.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    except Exception as exc:
        err_console.print(f"[Error] Could not parse {source}: {exc}")
        err_console.print("  Verify the file is valid JSON or YAML.")
        raise typer.Exit(code=1) from exc

    try:
        policy = load_policy_from_dict(data, source=str(source.resolve()))
    except Exception as exc:
        err_console.print(f"[Error] Policy validation failed: {exc}")
        raise typer.Exit(code=1) from exc

    report = analyze(policy, owner_threshold=owner_threshold)

    try:
        fmt = OutputFormat(output)
    except ValueError:
        err_console.print(
            f"[Warning] Unknown output format '{output}'. Falling back to 'text'."
        )
        fmt = OutputFormat.TEXT

    rendered = render(report, fmt)

    if fmt == OutputFormat.MARKDOWN:
        console.print(Markdown(rendered))
    elif fmt == OutputFormat.JSON:
        console.print_json(rendered)
    else:
        console.print(rendered)

    # Exit with a non-zero code when critical/high findings are present
    if report.critical_count > 0:
        raise typer.Exit(code=2)
    if report.high_count > 0:
        raise typer.Exit(code=3)


# ---------------------------------------------------------------------------
# list-checks command
# ---------------------------------------------------------------------------


@app.command(name="list-checks")
def list_checks() -> None:
    """List all supported security checks."""
    _configure_logging(get_settings().log_level)

    raw = TOOL_REGISTRY["get_supported_checks"]()
    checks = json.loads(raw)

    table = Table(title="Supported IAM / RBAC Security Checks", show_lines=True)
    table.add_column("ID", style="bold cyan", width=12)
    table.add_column("Severity", width=10)
    table.add_column("Title")

    severity_style = {
        "CRITICAL": "bold red",
        "HIGH": "red",
        "MEDIUM": "yellow",
        "LOW": "blue",
        "INFO": "dim",
    }
    for check in checks:
        style = severity_style.get(check["severity"], "")
        table.add_row(check["id"], f"[{style}]{check['severity']}[/{style}]", check["title"])

    console.print(table)


# ---------------------------------------------------------------------------
# explain command
# ---------------------------------------------------------------------------


@app.command()
def explain(
    finding_id: Annotated[
        str,
        typer.Argument(help="Finding ID to explain, e.g. IOAR-001."),
    ],
) -> None:
    """Show a detailed explanation and remediation guide for a finding."""
    _configure_logging(get_settings().log_level)

    raw = TOOL_REGISTRY["explain_finding"](finding_id)
    result = json.loads(raw)

    if "error" in result:
        err_console.print(f"[Error] {result['error']}")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[bold]{result['finding_id']}[/bold]\n\n"
            f"[underline]Explanation[/underline]\n{result['explanation']}\n\n"
            f"[underline]Remediation[/underline]\n{result['remediation']}",
            title="Finding Details",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# ask command
# ---------------------------------------------------------------------------


@app.command()
def ask(
    question: Annotated[
        str,
        typer.Argument(help="Free-form security question for the Foundry agent."),
    ],
) -> None:
    """Ask the Azure AI Foundry agent a free-form IAM security question."""
    _configure_logging(get_settings().log_level)

    from .agent import run_agent

    settings = get_settings()
    if not settings.foundry_configured:
        err_console.print(
            "[Warning] AZURE_AI_PROJECT_ENDPOINT is not set. "
            "Running in offline/local mode — full NLU is not available."
        )

    response = asyncio.run(run_agent(question))
    console.print(response)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point used by the 'iam-rbac-reviewer' console script."""
    app()


if __name__ == "__main__":
    main()
