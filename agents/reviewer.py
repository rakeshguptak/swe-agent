"""Reviewer agent: produces PR title + description from diff context."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

import config
from graph.state import FilePatch, FixPlan, Issue

_SYSTEM = """You are a senior software engineer writing a pull request description.
Given an issue, a fix plan, and the changed files, write a clear PR.

Respond with exactly two sections separated by a blank line:
TITLE: <concise PR title, ≤72 chars>

BODY:
<markdown body with:
- "## Summary" section (2-4 bullet points)
- "## Changes" section listing each modified file and what changed
- "## Test plan" section describing how to verify the fix
- "Fixes #<issue_number>" at the bottom
>
"""


@dataclass
class PRContent:
    title: str
    body: str


def _build_prompt(
    issue: Issue,
    fix_plan: FixPlan,
    patches: list[FilePatch],
) -> str:
    parts = [
        f"## Issue #{issue['number']}: {issue['title']}",
        "",
        issue["body"],
        "",
        f"## Fix summary",
        fix_plan["summary"],
        "",
        "## Changed files",
        "",
    ]
    for patch in patches:
        parts += [f"### {patch['path']}", "```diff"]
        # Simple diff: show the patched content
        parts += [patch["patched"][:3000], "```", ""]
    return "\n".join(parts)


def write_pr(
    issue: Issue,
    fix_plan: FixPlan,
    patches: list[FilePatch],
) -> PRContent:
    """Return a PRContent with title and body for the pull request."""
    llm = ChatAnthropic(
        model=config.LLM_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        max_tokens=1024,
    )
    prompt = _build_prompt(issue, fix_plan, patches)
    response = llm.invoke(
        [SystemMessage(content=_SYSTEM), HumanMessage(content=prompt)]
    )
    raw = response.content.strip()

    # Parse TITLE / BODY sections
    title = ""
    body = ""
    if "TITLE:" in raw and "BODY:" in raw:
        title_part, body_part = raw.split("BODY:", 1)
        title = title_part.replace("TITLE:", "").strip()
        body = body_part.strip()
    else:
        # Fallback
        lines = raw.splitlines()
        title = lines[0] if lines else fix_plan["summary"]
        body = "\n".join(lines[1:]) if len(lines) > 1 else fix_plan["summary"]

    return PRContent(title=title, body=body)
