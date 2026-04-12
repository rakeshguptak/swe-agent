"""Shared state threaded through all LangGraph nodes."""

from __future__ import annotations

from typing import TypedDict, Optional


class Issue(TypedDict):
    number: int
    title: str
    body: str
    repo_full_name: str  # "owner/repo"


class FilePatch(TypedDict):
    path: str       # relative path inside repo
    original: str   # original file content
    patched: str    # new file content


class FixPlan(TypedDict):
    summary: str            # one-sentence description of the fix
    files_to_change: list[str]  # relative paths that will be touched
    steps: list[str]        # ordered human-readable fix steps


class TestResult(TypedDict):
    passed: bool
    output: str     # full stdout/stderr from pytest
    failures: list[str]  # extracted failure messages


class AgentState(TypedDict):
    # ── Input ─────────────────────────────────────────
    repo_full_name: str         # "owner/repo"
    issue_number: int

    # ── Populated by fetch_issue ───────────────────────
    issue: Optional[Issue]

    # ── Populated by inspect_repo ─────────────────────
    local_repo_path: str        # absolute path to cloned repo
    repo_tree: list[str]        # relative file paths in repo
    relevant_files: dict[str, str]  # path → content for inspected files

    # ── Populated by plan_fix ──────────────────────────
    fix_plan: Optional[FixPlan]

    # ── Populated by write_code ───────────────────────
    patches: list[FilePatch]    # files that were modified

    # ── Populated by run_tests ────────────────────────
    test_result: Optional[TestResult]

    # ── Loop control ──────────────────────────────────
    retry_count: int            # how many debug cycles have run
    debug_notes: list[str]      # accumulated debugger observations

    # ── Populated by open_pr ──────────────────────────
    pr_url: Optional[str]

    # ── Terminal error ─────────────────────────────────
    error: Optional[str]        # set on unrecoverable failure
