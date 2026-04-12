"""
LangGraph node functions.

Each node receives the full AgentState, performs one logical step,
and returns a partial state dict with only the keys it updates.
"""

from __future__ import annotations

import re

import config
from agents import coder, debugger, planner, reviewer
from graph.state import AgentState
from tools import git_ops, github_client, repo_inspector, test_runner


# ── Node 1: fetch_issue ───────────────────────────────────────────────────


def node_fetch_issue(state: AgentState) -> dict:
    """Download the GitHub issue."""
    try:
        issue = github_client.fetch_issue(
            state["repo_full_name"], state["issue_number"]
        )
        return {"issue": issue}
    except Exception as exc:
        return {"error": f"fetch_issue failed: {exc}"}


# ── Node 2: inspect_repo ──────────────────────────────────────────────────


def node_inspect_repo(state: AgentState) -> dict:
    """Clone repo, walk files, select relevant ones based on issue keywords."""
    try:
        local_path = repo_inspector.clone_repo(state["repo_full_name"])
        all_files = repo_inspector.walk_repo(local_path)

        issue = state["issue"]
        # Extract keywords from issue title + body
        text = f"{issue['title']} {issue['body']}"
        keywords = _extract_keywords(text)

        relevant = repo_inspector.select_relevant_files(local_path, all_files, keywords)

        return {
            "local_repo_path": local_path,
            "repo_tree": all_files,
            "relevant_files": relevant,
        }
    except Exception as exc:
        return {"error": f"inspect_repo failed: {exc}"}


def _extract_keywords(text: str) -> list[str]:
    """Pull meaningful words (>3 chars) from text as search keywords."""
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{3,}", text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            result.append(w)
    return result[:30]


# ── Node 3: plan_fix ─────────────────────────────────────────────────────


def node_plan_fix(state: AgentState) -> dict:
    """Generate a structured fix plan from issue + relevant files."""
    try:
        fix_plan = planner.plan_fix(state["issue"], state["relevant_files"])
        return {"fix_plan": fix_plan}
    except Exception as exc:
        return {"error": f"plan_fix failed: {exc}"}


# ── Node 4: write_code ────────────────────────────────────────────────────


def node_write_code(state: AgentState) -> dict:
    """Generate code patches. Uses debug_notes from previous attempts."""
    try:
        patches = coder.write_code(
            fix_plan=state["fix_plan"],
            relevant_files=state["relevant_files"],
            debug_notes=state.get("debug_notes", []),
        )
        return {"patches": patches}
    except Exception as exc:
        return {"error": f"write_code failed: {exc}"}


# ── Node 5: run_tests ─────────────────────────────────────────────────────


def node_run_tests(state: AgentState) -> dict:
    """Apply patches to disk and run the test suite."""
    try:
        local_path = state["local_repo_path"]
        patches = state["patches"]

        # Write patched files
        git_ops.apply_patches(local_path, patches)

        # Run tests
        result = test_runner.run_tests(local_path)
        return {"test_result": result}
    except Exception as exc:
        return {"error": f"run_tests failed: {exc}"}


# ── Node 6: debug ─────────────────────────────────────────────────────────


def node_debug(state: AgentState) -> dict:
    """Reflect on test failures and produce a root-cause note."""
    try:
        note = debugger.debug(
            fix_plan=state["fix_plan"],
            patches=state["patches"],
            test_result=state["test_result"],
        )
        existing = state.get("debug_notes", [])
        return {
            "debug_notes": existing + [note],
            "retry_count": state.get("retry_count", 0) + 1,
        }
    except Exception as exc:
        return {"error": f"debug failed: {exc}"}


# ── Node 7: open_pr ───────────────────────────────────────────────────────


def node_open_pr(state: AgentState) -> dict:
    """Commit patches, push branch, open a pull request."""
    try:
        local_path = state["local_repo_path"]
        issue = state["issue"]
        fix_plan = state["fix_plan"]
        patches = state["patches"]

        base = git_ops.default_branch(local_path)
        branch_name = f"swe-agent/fix-issue-{issue['number']}"

        git_ops.create_branch(local_path, branch_name)
        git_ops.apply_patches(local_path, patches)
        git_ops.commit_all(
            local_path,
            message=f"fix: {fix_plan['summary']}\n\nCloses #{issue['number']}",
        )
        git_ops.push_branch(local_path, branch_name)

        pr_content = reviewer.write_pr(issue, fix_plan, patches)
        pr_url = github_client.create_pull_request(
            repo_full_name=state["repo_full_name"],
            branch_name=branch_name,
            base_branch=base,
            title=pr_content.title,
            body=pr_content.body,
        )
        return {"pr_url": pr_url}
    except Exception as exc:
        return {"error": f"open_pr failed: {exc}"}
