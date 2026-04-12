"""
CLI entry point for the Autonomous SWE Agent.

Usage:
    python main.py owner/repo 42
    python main.py --help
"""

from __future__ import annotations

import argparse
import sys

from graph import build_graph
from graph.state import AgentState


def _initial_state(repo_full_name: str, issue_number: int) -> AgentState:
    return AgentState(
        repo_full_name=repo_full_name,
        issue_number=issue_number,
        issue=None,
        local_repo_path="",
        repo_tree=[],
        relevant_files={},
        fix_plan=None,
        patches=[],
        test_result=None,
        retry_count=0,
        debug_notes=[],
        pr_url=None,
        error=None,
    )


def _run(repo_full_name: str, issue_number: int) -> None:
    graph = build_graph()
    state = _initial_state(repo_full_name, issue_number)

    print(f"[SWE Agent] Starting on {repo_full_name}#{issue_number}")

    for step_output in graph.stream(state, stream_mode="updates"):
        for node_name, update in step_output.items():
            if update.get("error"):
                print(f"[{node_name}] ERROR: {update['error']}", file=sys.stderr)
                sys.exit(1)
            if pr_url := update.get("pr_url"):
                print(f"[{node_name}] PR opened: {pr_url}")
            else:
                keys = [k for k, v in update.items() if v is not None and v != [] and v != {}]
                print(f"[{node_name}] done — updated: {', '.join(keys)}")

    print("[SWE Agent] Complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous SWE Agent — reads a GitHub issue and opens a fix PR."
    )
    parser.add_argument(
        "repo",
        help='GitHub repo in "owner/repo" format (e.g. octocat/Hello-World)',
    )
    parser.add_argument(
        "issue",
        type=int,
        help="Issue number to fix (e.g. 42)",
    )
    args = parser.parse_args()

    if "/" not in args.repo:
        parser.error('repo must be in "owner/repo" format')

    _run(args.repo, args.issue)


if __name__ == "__main__":
    main()
