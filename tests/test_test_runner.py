"""Unit tests for test_runner using mocked sandbox."""

from unittest.mock import patch

import pytest

from tools.code_sandbox import SandboxResult


def _sandbox_result(returncode=0, stdout="", stderr="", timed_out=False):
    return SandboxResult(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )


@patch("tools.test_runner.run")
def test_run_tests_passes_when_returncode_zero(mock_run, tmp_path):
    from tools.test_runner import run_tests

    mock_run.return_value = _sandbox_result(returncode=0, stdout="1 passed")
    result = run_tests(str(tmp_path))

    assert result["passed"] is True
    assert result["failures"] == []
    assert "1 passed" in result["output"]


@patch("tools.test_runner.run")
def test_run_tests_fails_on_nonzero_returncode(mock_run, tmp_path):
    from tools.test_runner import run_tests

    output = "FAILED tests/test_auth.py::test_login - AssertionError\n1 failed"
    mock_run.return_value = _sandbox_result(returncode=1, stdout=output)
    result = run_tests(str(tmp_path))

    assert result["passed"] is False
    assert "tests/test_auth.py::test_login - AssertionError" in result["failures"]


@patch("tools.test_runner.run")
def test_run_tests_fails_on_timeout(mock_run, tmp_path):
    from tools.test_runner import run_tests

    mock_run.return_value = _sandbox_result(
        returncode=-1, stdout="", stderr="", timed_out=True
    )
    result = run_tests(str(tmp_path))
    assert result["passed"] is False


@patch("tools.test_runner.run")
def test_run_tests_extracts_multiple_failures(mock_run, tmp_path):
    from tools.test_runner import run_tests

    output = (
        "FAILED tests/test_auth.py::test_login - AssertionError\n"
        "FAILED tests/test_api.py::test_timeout - TimeoutError\n"
        "2 failed"
    )
    mock_run.return_value = _sandbox_result(returncode=1, stdout=output)
    result = run_tests(str(tmp_path))

    assert len(result["failures"]) == 2


def test_format_failure_summary_all_passed():
    from tools.test_runner import format_failure_summary

    result = {"passed": True, "output": "5 passed", "failures": []}
    assert format_failure_summary(result) == "All tests passed."


def test_format_failure_summary_lists_failures():
    from tools.test_runner import format_failure_summary

    result = {
        "passed": False,
        "output": "FAILED test_a - Error\n1 failed",
        "failures": ["test_a - Error"],
    }
    summary = format_failure_summary(result)
    assert "test_a - Error" in summary
    assert "Test failures:" in summary
