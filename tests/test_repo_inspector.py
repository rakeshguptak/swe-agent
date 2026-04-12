"""Unit tests for repo_inspector utilities."""

import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")


def test_extract_python_symbols_top_level_only():
    from tools.repo_inspector import extract_python_symbols

    source = textwrap.dedent("""\
        class AuthService:
            def login(self):
                pass

        def handle_timeout():
            pass

        def _private():
            pass
    """)
    symbols = extract_python_symbols(source)
    assert "AuthService" in symbols
    assert "handle_timeout" in symbols
    assert "_private" in symbols
    # Nested method should NOT appear
    assert "login" not in symbols


def test_extract_python_symbols_invalid_syntax():
    from tools.repo_inspector import extract_python_symbols

    symbols = extract_python_symbols("def broken(")
    assert symbols == []


def test_read_file_returns_none_for_missing(tmp_path):
    from tools.repo_inspector import read_file

    result = read_file(str(tmp_path), "nonexistent.py")
    assert result is None


def test_read_file_returns_content(tmp_path):
    from tools.repo_inspector import read_file

    (tmp_path / "hello.py").write_text("print('hi')", encoding="utf-8")
    result = read_file(str(tmp_path), "hello.py")
    assert result == "print('hi')"


def test_walk_repo_skips_hidden_dirs(tmp_path):
    from tools.repo_inspector import walk_repo

    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.pyc").write_text("", encoding="utf-8")

    files = walk_repo(str(tmp_path))
    assert "src/main.py" in files
    assert not any(".git" in f for f in files)
    assert not any("__pycache__" in f for f in files)


def test_select_relevant_files_matches_path_keyword(tmp_path):
    from tools.repo_inspector import select_relevant_files

    (tmp_path / "auth.py").write_text("class AuthService: pass", encoding="utf-8")
    (tmp_path / "models.py").write_text("class User: pass", encoding="utf-8")

    all_files = ["auth.py", "models.py"]
    result = select_relevant_files(str(tmp_path), all_files, ["auth"])
    assert "auth.py" in result
    assert "models.py" not in result


def test_select_relevant_files_caps_at_20(tmp_path):
    from tools.repo_inspector import select_relevant_files

    for i in range(25):
        (tmp_path / f"service_{i}.py").write_text(
            "# service logic here", encoding="utf-8"
        )
    all_files = [f"service_{i}.py" for i in range(25)]
    result = select_relevant_files(str(tmp_path), all_files, ["service"])
    assert len(result) <= 20
