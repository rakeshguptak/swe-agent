"""
Smoke tests for the LangGraph graph.

All external calls (GitHub, git clone, LLM, test runner) are mocked so
these tests run without network access or real credentials.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setenv("MAX_RETRIES", "1")
    monkeypatch.setenv("WORKSPACE_DIR", "/tmp/swe_test")


_FAKE_ISSUE = {
    "number": 42,
    "title": "Login API timeout",
    "body": "The login endpoint times out under load",
    "repo_full_name": "owner/repo",
}

_FAKE_FIX_PLAN = {
    "summary": "Increase connection pool size to fix timeout",
    "files_to_change": ["api/auth.py"],
    "steps": ["Open api/auth.py", "Increase pool size"],
}

_FAKE_PATCHES = [
    {
        "path": "api/auth.py",
        "original": "POOL_SIZE = 5",
        "patched": "POOL_SIZE = 20",
    }
]


def test_happy_path_produces_pr_url():
    from graph import build_graph
    from graph.state import AgentState

    initial = AgentState(
        repo_full_name="owner/repo",
        issue_number=42,
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

    with (
        patch("tools.github_client.fetch_issue", return_value=_FAKE_ISSUE),
        patch("tools.repo_inspector.clone_repo", return_value="/tmp/swe_test/owner_repo"),
        patch("tools.repo_inspector.walk_repo", return_value=["api/auth.py"]),
        patch(
            "tools.repo_inspector.select_relevant_files",
            return_value={"api/auth.py": "POOL_SIZE = 5"},
        ),
        patch("agents.planner.plan_fix", return_value=_FAKE_FIX_PLAN),
        patch("agents.coder.write_code", return_value=_FAKE_PATCHES),
        patch("tools.git_ops.apply_patches"),
        patch(
            "tools.test_runner.run_tests",
            return_value={"passed": True, "output": "1 passed", "failures": []},
        ),
        patch("tools.git_ops.default_branch", return_value="main"),
        patch("tools.git_ops.create_branch"),
        patch("tools.git_ops.commit_all", return_value="abc123"),
        patch("tools.git_ops.push_branch"),
        patch(
            "agents.reviewer.write_pr",
            return_value=MagicMock(title="fix: increase pool size", body="Fixes #42"),
        ),
        patch(
            "tools.github_client.create_pull_request",
            return_value="https://github.com/owner/repo/pull/1",
        ),
    ):
        graph = build_graph()
        final = graph.invoke(initial)

    assert final["pr_url"] == "https://github.com/owner/repo/pull/1"
    assert final["error"] is None


def test_fetch_issue_failure_sets_error():
    with patch("tools.github_client.fetch_issue", side_effect=Exception("rate limited")):
        from graph import build_graph
        from graph.state import AgentState

        graph = build_graph()
        initial = AgentState(
            repo_full_name="owner/repo",
            issue_number=99,
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
        final = graph.invoke(initial)
        assert final["error"] is not None
        assert "fetch_issue" in final["error"]


def test_debug_loop_retries_on_test_failure():
    """Verify that test failure triggers the debug→write_code loop."""
    debug_note = "POOL_SIZE default is wrong, use environment variable"
    call_counts = {"write_code": 0}

    def counting_write_code(*args, **kwargs):
        call_counts["write_code"] += 1
        return _FAKE_PATCHES

    with (
        patch("tools.github_client.fetch_issue", return_value=_FAKE_ISSUE),
        patch("tools.repo_inspector.clone_repo", return_value="/tmp/swe_test/owner_repo"),
        patch("tools.repo_inspector.walk_repo", return_value=["api/auth.py"]),
        patch(
            "tools.repo_inspector.select_relevant_files",
            return_value={"api/auth.py": "POOL_SIZE = 5"},
        ),
        patch("agents.planner.plan_fix", return_value=_FAKE_FIX_PLAN),
        patch("agents.coder.write_code", side_effect=counting_write_code),
        patch("tools.git_ops.apply_patches"),
        patch(
            "tools.test_runner.run_tests",
            side_effect=[
                # First run: fail
                {"passed": False, "output": "1 failed", "failures": ["test_login"]},
                # Second run (after debug): pass
                {"passed": True, "output": "1 passed", "failures": []},
            ],
        ),
        patch("agents.debugger.debug", return_value=debug_note),
        patch("tools.git_ops.default_branch", return_value="main"),
        patch("tools.git_ops.create_branch"),
        patch("tools.git_ops.commit_all", return_value="abc123"),
        patch("tools.git_ops.push_branch"),
        patch(
            "agents.reviewer.write_pr",
            return_value=MagicMock(title="fix: pool size", body="Fixes #42"),
        ),
        patch(
            "tools.github_client.create_pull_request",
            return_value="https://github.com/owner/repo/pull/2",
        ),
    ):
        from graph import build_graph
        from graph.state import AgentState

        graph = build_graph()
        initial = AgentState(
            repo_full_name="owner/repo",
            issue_number=42,
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
        final = graph.invoke(initial)
        # write_code must have been called twice (initial + after debug)
        assert call_counts["write_code"] == 2
        assert final["pr_url"] == "https://github.com/owner/repo/pull/2"
        assert debug_note in final["debug_notes"]
