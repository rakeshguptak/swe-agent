"""Unit tests for code_sandbox subprocess runner."""

import sys
import pytest


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setenv("SANDBOX_TIMEOUT", "10")


def test_successful_command(tmp_path):
    from tools.code_sandbox import run

    result = run([sys.executable, "-c", "print('hello')"], cwd=str(tmp_path))
    assert result.success
    assert "hello" in result.stdout
    assert result.returncode == 0
    assert not result.timed_out


def test_failing_command(tmp_path):
    from tools.code_sandbox import run

    result = run([sys.executable, "-c", "raise RuntimeError('boom')"], cwd=str(tmp_path))
    assert not result.success
    assert result.returncode != 0
    assert "RuntimeError" in result.stderr


def test_timeout(tmp_path):
    from tools.code_sandbox import run

    result = run(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=str(tmp_path),
        timeout=1,
    )
    assert result.timed_out
    assert not result.success
    assert "TIMEOUT" in result.combined_output


def test_combined_output_includes_both_streams(tmp_path):
    from tools.code_sandbox import run

    result = run(
        [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"],
        cwd=str(tmp_path),
    )
    assert "out" in result.combined_output
    assert "err" in result.combined_output
