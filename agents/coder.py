"""Coder agent: fix plan + source files → patched file contents."""

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

import config
from graph.state import FilePatch, FixPlan

_SYSTEM = """You are a senior software engineer implementing a bug fix.
Given a fix plan and the current content of files to change, return the
complete new content for each file.

Respond with ONLY valid JSON matching this schema:
[
  {
    "path": "<relative/path/to/file.py>",
    "patched": "<full new file content as a string>"
  },
  ...
]

Rules:
- Return the ENTIRE file content, not just the diff.
- Do not omit any existing code that should remain.
- Do not add comments explaining what changed.
- Only return files that actually need to change.
"""


def _build_prompt(
    fix_plan: FixPlan,
    file_contents: dict[str, str],
    debug_notes: list[str],
) -> str:
    parts = [
        "## Fix plan",
        "",
        f"Summary: {fix_plan['summary']}",
        "",
        "Steps:",
    ]
    for i, step in enumerate(fix_plan["steps"], 1):
        parts.append(f"{i}. {step}")

    if debug_notes:
        parts += ["", "## Debug observations from previous attempts", ""]
        parts.extend(debug_notes)

    parts += ["", "## Files to modify", ""]
    for path in fix_plan["files_to_change"]:
        content = file_contents.get(path, "")
        parts += [f"### {path}", "```", content[:6000], "```", ""]

    return "\n".join(parts)


def write_code(
    fix_plan: FixPlan,
    relevant_files: dict[str, str],
    debug_notes: list[str],
) -> list[FilePatch]:
    """Call the LLM and return typed FilePatch list."""
    llm = ChatAnthropic(
        model=config.LLM_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        max_tokens=8192,
    )
    prompt = _build_prompt(fix_plan, relevant_files, debug_notes)
    response = llm.invoke(
        [SystemMessage(content=_SYSTEM), HumanMessage(content=prompt)]
    )
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    patches_data = json.loads(raw)
    return [
        FilePatch(
            path=p["path"],
            original=relevant_files.get(p["path"], ""),
            patched=p["patched"],
        )
        for p in patches_data
    ]
