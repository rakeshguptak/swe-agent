"""LangGraph graph factory for the SWE agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from graph.edges import (
    after_debug,
    after_fetch_issue,
    after_inspect_repo,
    after_open_pr,
    after_plan_fix,
    after_run_tests,
    after_write_code,
)
from graph.nodes import (
    node_debug,
    node_fetch_issue,
    node_inspect_repo,
    node_open_pr,
    node_plan_fix,
    node_run_tests,
    node_write_code,
)
from graph.state import AgentState


def build_graph() -> StateGraph:
    """Construct and compile the SWE agent graph."""
    g = StateGraph(AgentState)

    # Register nodes
    g.add_node("fetch_issue", node_fetch_issue)
    g.add_node("inspect_repo", node_inspect_repo)
    g.add_node("plan_fix", node_plan_fix)
    g.add_node("write_code", node_write_code)
    g.add_node("run_tests", node_run_tests)
    g.add_node("debug", node_debug)
    g.add_node("open_pr", node_open_pr)

    # Entry
    g.add_edge(START, "fetch_issue")

    # Conditional routing
    g.add_conditional_edges(
        "fetch_issue",
        after_fetch_issue,
        {"inspect_repo": "inspect_repo", "abort": END},
    )
    g.add_conditional_edges(
        "inspect_repo",
        after_inspect_repo,
        {"plan_fix": "plan_fix", "abort": END},
    )
    g.add_conditional_edges(
        "plan_fix",
        after_plan_fix,
        {"write_code": "write_code", "abort": END},
    )
    g.add_conditional_edges(
        "write_code",
        after_write_code,
        {"run_tests": "run_tests", "abort": END},
    )
    g.add_conditional_edges(
        "run_tests",
        after_run_tests,
        {"open_pr": "open_pr", "debug": "debug", "abort": END},
    )
    g.add_conditional_edges(
        "debug",
        after_debug,
        {"write_code": "write_code", "abort": END},
    )
    g.add_conditional_edges(
        "open_pr",
        after_open_pr,
        {"done": END, "abort": END},
    )

    return g.compile()
