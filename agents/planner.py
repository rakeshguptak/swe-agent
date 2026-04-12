"""Planner agent: issue + codebase context → structured fix plan."""

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

import config
from graph.state import FixPlan, Issue

_SYSTEM = """You are a senior software engineer planning a bug fix.
Given a GitHub issue and relevant source files, produce a concise fix plan.

Respond with ONLY valid JSON matching this schema:
{
  "summary": "<one sentence describing the fix>",
  "files_to_change": ["<relative/path/to/file.py>", ...],
  "steps": ["<step 1>", "<step 2>", ...]
}

Rules:
- Only include files that actually need to change.
- Steps must be concrete and actionable, not vague.
- Do not include test files in files_to_change unless the bug is in the test.
"""


def _build_prompt(issue: Issue, relevant_files: dict[str, str]) -> str:
    parts = [
        f"## Issue #{issue['number']}: {issue['title']}",
        "",
        issue["body"],
        "",
        "## Relevant source files",
        "",
    ]
    for path, content in relevant_files.items():
        parts += [f"### {path}", "```", content[:4000], "```", ""]
    return "\n".join(parts)


def plan_fix(issue: Issue, relevant_files: dict[str, str]) -> FixPlan:
    """Call the LLM and return a typed FixPlan."""
    llm = ChatAnthropic(
        model=config.LLM_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        max_tokens=1024,
    )
    prompt = _build_prompt(issue, relevant_files)
    response = llm.invoke(
        [SystemMessage(content=_SYSTEM), HumanMessage(content=prompt)]
    )
    raw = response.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)
    return FixPlan(
        summary=data["summary"],
        files_to_change=data["files_to_change"],
        steps=data["steps"],
    )
