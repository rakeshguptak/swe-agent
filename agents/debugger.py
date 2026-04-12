"""Debugger / reflection agent: test failures → root-cause note."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

import config
from graph.state import FilePatch, FixPlan, TestResult

_SYSTEM = """You are a senior software engineer debugging a failing test suite.
You previously wrote a code patch that caused test failures.

Analyse the test output and the current patch, then produce a short
root-cause note (≤200 words) that explains:
1. What specifically went wrong in the code.
2. What must be changed in the next implementation attempt.

Be precise. Reference specific function names, line behaviour, or logic errors.
Do not write new code — only explain what needs to change.
"""


def _build_prompt(
    fix_plan: FixPlan,
    patches: list[FilePatch],
    test_result: TestResult,
) -> str:
    parts = [
        "## Fix plan",
        f"Summary: {fix_plan['summary']}",
        "",
        "## Code patches applied",
        "",
    ]
    for patch in patches:
        parts += [f"### {patch['path']}", "```", patch["patched"][:4000], "```", ""]

    parts += [
        "## Test failure output",
        "```",
        test_result["output"][-3000:],
        "```",
    ]
    return "\n".join(parts)


def debug(
    fix_plan: FixPlan,
    patches: list[FilePatch],
    test_result: TestResult,
) -> str:
    """Return a root-cause note string to pass back to the coder."""
    llm = ChatAnthropic(
        model=config.LLM_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        max_tokens=512,
    )
    prompt = _build_prompt(fix_plan, patches, test_result)
    response = llm.invoke(
        [SystemMessage(content=_SYSTEM), HumanMessage(content=prompt)]
    )
    return response.content.strip()
