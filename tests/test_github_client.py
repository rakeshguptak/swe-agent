"""Unit tests for github_client using mocked PyGithub."""

from unittest.mock import MagicMock, patch

import pytest

# Pre-import so @patch decorators can resolve the module in Python 3.13+
import tools.github_client  # noqa: F401


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")


@patch("tools.github_client.Github")
def test_fetch_issue_returns_typed_dict(mock_github_cls):
    mock_issue = MagicMock()
    mock_issue.number = 7
    mock_issue.title = "Login timeout"
    mock_issue.body = "The login API times out after 5s"

    mock_repo = MagicMock()
    mock_repo.get_issue.return_value = mock_issue

    mock_github_cls.return_value.get_repo.return_value = mock_repo

    from tools.github_client import fetch_issue

    result = fetch_issue("owner/repo", 7)

    assert result["number"] == 7
    assert result["title"] == "Login timeout"
    assert result["body"] == "The login API times out after 5s"
    assert result["repo_full_name"] == "owner/repo"


@patch("tools.github_client.Github")
def test_fetch_issue_handles_none_body(mock_github_cls):
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Empty issue"
    mock_issue.body = None

    mock_repo = MagicMock()
    mock_repo.get_issue.return_value = mock_issue
    mock_github_cls.return_value.get_repo.return_value = mock_repo

    from tools.github_client import fetch_issue

    result = fetch_issue("owner/repo", 1)
    assert result["body"] == ""


@patch("tools.github_client.Github")
def test_create_pull_request_returns_url(mock_github_cls):
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/owner/repo/pull/99"

    mock_repo = MagicMock()
    mock_repo.create_pull.return_value = mock_pr
    mock_github_cls.return_value.get_repo.return_value = mock_repo

    from tools.github_client import create_pull_request

    url = create_pull_request(
        repo_full_name="owner/repo",
        branch_name="swe-agent/fix-issue-7",
        base_branch="main",
        title="fix: login timeout",
        body="Fixes #7",
    )
    assert url == "https://github.com/owner/repo/pull/99"
    mock_repo.create_pull.assert_called_once_with(
        title="fix: login timeout",
        body="Fixes #7",
        head="swe-agent/fix-issue-7",
        base="main",
    )
