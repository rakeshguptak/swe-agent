"""Run pytest in the cloned repo and parse results."""

from __future__ import annotations

import re

from graph.state import TestResult
from tools.code_sandbox import run

# Matches lines like: FAILED tests/test_auth.py::test_login - AssertionError
_FAILURE_RE = re.compile(r"^FAILED\s+(.+)$", re.MULTILINE)
# Matches the short summary "N failed, M passed"
_SUMMARY_RE = re.compile(r"(\d+) failed")


def run_tests(local_repo_path: str) -> TestResult:
    """
    Execute pytest inside the repo and return structured results.

    Assumes pytest is available in the active Python environment.
    """
    result = run(
        cmd=["python", "-m", "pytest", "--tb=short", "-q"],
        cwd=local_repo_path,
    )

    failures = _FAILURE_RE.findall(result.combined_output)
    passed = result.returncode == 0 and not result.timed_out

    return TestResult(
        passed=passed,
        output=result.combined_output,
        failures=failures,
    )


def format_failure_summary(test_result: TestResult) -> str:
    """Return a concise failure block for the debugger agent."""
    if test_result["passed"]:
        return "All tests passed."
    lines = ["Test failures:"]
    for f in test_result["failures"]:
        lines.append(f"  - {f}")
    # Include last 60 lines of output for context
    tail = test_result["output"].splitlines()[-60:]
    lines.append("\nTest output (tail):")
    lines.extend(tail)
    return "\n".join(lines)
