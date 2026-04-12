"""Conditional routing logic between LangGraph nodes."""

from __future__ import annotations

import config
from graph.state import AgentState


def after_fetch_issue(state: AgentState) -> str:
    if state.get("error"):
        return "abort"
    return "inspect_repo"


def after_inspect_repo(state: AgentState) -> str:
    if state.get("error"):
        return "abort"
    return "plan_fix"


def after_plan_fix(state: AgentState) -> str:
    if state.get("error"):
        return "abort"
    return "write_code"


def after_write_code(state: AgentState) -> str:
    if state.get("error"):
        return "abort"
    return "run_tests"


def after_run_tests(state: AgentState) -> str:
    if state.get("error"):
        return "abort"
    test_result = state.get("test_result")
    if test_result and test_result["passed"]:
        return "open_pr"
    retry_count = state.get("retry_count", 0)
    if retry_count >= config.MAX_RETRIES:
        return "abort"
    return "debug"


def after_debug(state: AgentState) -> str:
    if state.get("error"):
        return "abort"
    return "write_code"


def after_open_pr(state: AgentState) -> str:
    if state.get("error"):
        return "abort"
    return "done"
