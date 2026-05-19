"""Azure AI Foundry agent orchestrator for the IAM / RBAC reviewer.

This module sets up and runs a Foundry (Azure AI Projects) agent that uses
the tools defined in :mod:`iam_rbac_reviewer.tools` to answer IAM security
questions and perform policy reviews.

Usage (programmatic):
    >>> from iam_rbac_reviewer.agent import run_agent
    >>> import asyncio
    >>> asyncio.run(run_agent("Review the policy in ./policy.json and list all findings."))

Environment variables required:
    AZURE_AI_PROJECT_ENDPOINT   - Azure AI Foundry project endpoint URL
    AZURE_OPENAI_MODEL          - model deployment name (e.g. "gpt-4o")
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .config import Settings, get_settings
from .tools import TOOL_DEFINITIONS, TOOL_REGISTRY

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert IAM / RBAC security reviewer specialising in Azure RBAC.
Your job is to analyse role assignments and role definitions for security risks,
apply best-practice checks, and produce clear, actionable findings.

When asked to review a policy, always:
1. Call `review_policy_document` or `review_policy_file` to obtain findings.
2. Summarise the most critical issues first (CRITICAL → HIGH → MEDIUM → LOW).
3. For each finding, offer concrete remediation steps.
4. If the user asks for more detail on a specific finding, call `explain_finding`.
5. Use `get_supported_checks` to answer questions about what checks are available.

Be concise, precise, and security-focused in all responses.
"""


# ---------------------------------------------------------------------------
# Tool dispatcher (shared between real and mock backends)
# ---------------------------------------------------------------------------


def dispatch_tool_call(tool_name: str, tool_arguments: str | dict[str, Any]) -> str:
    """Invoke the tool registered under *tool_name* with *tool_arguments*.

    Args:
        tool_name: Name of the tool to invoke.
        tool_arguments: Either a JSON string or already-parsed dict of arguments.

    Returns:
        Tool output as a string.
    """
    if isinstance(tool_arguments, str):
        try:
            args: dict[str, Any] = json.loads(tool_arguments)
        except json.JSONDecodeError:
            args = {}
    else:
        args = tool_arguments

    tool_fn = TOOL_REGISTRY.get(tool_name)
    if tool_fn is None:
        logger.error("dispatch_tool_call: unknown tool '%s'", tool_name)
        return json.dumps({"error": f"Unknown tool: '{tool_name}'"})

    try:
        result = tool_fn(**args)
    except TypeError as exc:
        logger.error("dispatch_tool_call: bad arguments for '%s': %s", tool_name, exc)
        return json.dumps({"error": f"Bad arguments for '{tool_name}': {exc}"})

    return result if isinstance(result, str) else json.dumps(result)


# ---------------------------------------------------------------------------
# Foundry agent runner
# ---------------------------------------------------------------------------


async def run_agent(user_message: str) -> str:
    """Run the IAM / RBAC reviewer agent and return its final text response.

    When the Azure AI Foundry endpoint is not configured, the function falls
    back to a lightweight local loop that dispatches tool calls directly.

    Args:
        user_message: The user's natural-language request.

    Returns:
        The agent's final response as a plain string.
    """
    settings = get_settings()

    if settings.foundry_configured:
        return await _run_foundry_agent(user_message, settings)

    logger.warning(
        "AZURE_AI_PROJECT_ENDPOINT is not set — running in local (offline) mode. Only direct tool calls will work."
    )
    return _run_local_agent(user_message)


async def _run_foundry_agent(user_message: str, settings: Settings) -> str:
    """Run the agent using the Azure AI Projects SDK.

    Args:
        user_message: The user's natural-language request.
        settings: Populated :class:`~iam_rbac_reviewer.config.Settings` instance.

    Returns:
        The agent's final text response.
    """
    try:
        from azure.ai.projects.aio import AIProjectClient
        from azure.identity.aio import DefaultAzureCredential
    except ImportError as exc:
        raise ImportError(
            "azure-ai-projects and azure-identity are required to use Foundry mode. "
            "Install them with: pip install azure-ai-projects azure-identity"
        ) from exc

    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=settings.azure_ai_project_endpoint,
            credential=credential,
        ) as client,
    ):
        # Create an ephemeral agent for this request
        agent = await client.agents.create_agent(
            model=settings.azure_openai_model,
            name="iam-rbac-reviewer",
            instructions=_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
        )
        logger.debug("Created Foundry agent: %s", agent.id)

        thread = await client.agents.create_thread()
        logger.debug("Created thread: %s", thread.id)

        await client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=user_message,
        )

        run = await client.agents.create_and_process_run(
            thread_id=thread.id,
            agent_id=agent.id,
        )
        logger.debug("Run status: %s", run.status)

        # Handle required tool actions (function calls)
        while run.status == "requires_action":
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                output = dispatch_tool_call(
                    tool_call.function.name,
                    tool_call.function.arguments,
                )
                tool_outputs.append({"tool_call_id": tool_call.id, "output": output})

            run = await client.agents.submit_tool_outputs_and_poll(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=tool_outputs,
            )

        # Retrieve the assistant's last message
        messages = await client.agents.list_messages(thread_id=thread.id)
        for msg in messages.data:
            if msg.role == "assistant":
                text_parts = [c.text.value for c in msg.content if hasattr(c, "text")]
                return "\n".join(text_parts)

        # Clean up ephemeral agent
        await client.agents.delete_agent(agent.id)

    return "(No response from agent)"


def _run_local_agent(user_message: str) -> str:
    """Very simple local dispatcher for offline / CI use.

    Looks for a tool name mentioned in the user message and calls it directly.
    This is intentionally limited — for real NLU, use the Foundry agent.

    Args:
        user_message: The user's message.

    Returns:
        Tool output or a help message.
    """
    msg_lower = user_message.lower()

    if "supported" in msg_lower or "checks" in msg_lower or "list" in msg_lower:
        return TOOL_REGISTRY["get_supported_checks"]()

    if "explain" in msg_lower:
        for fid in ("IOAR-001", "IOAR-002", "IOAR-003", "IOAR-004", "IOAR-005", "IOAR-006"):
            if fid.lower() in msg_lower:
                return TOOL_REGISTRY["explain_finding"](fid)

    # Try to extract a file path from the message (crude heuristic)
    import re

    file_match = re.search(r"[\w./\\-]+\.(json|yaml|yml)", user_message)
    if file_match:
        return TOOL_REGISTRY["review_policy_file"](file_match.group(0))

    return (
        "Local mode: No Foundry endpoint configured. "
        "Available tools: review_policy_document, review_policy_file, "
        "explain_finding, get_supported_checks. "
        "Set AZURE_AI_PROJECT_ENDPOINT to enable full agent mode."
    )
