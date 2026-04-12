"""GitHub operations: read issues, create pull requests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import github
from github import Github, Repository, PullRequest

import config

if TYPE_CHECKING:
    from graph.state import Issue


def _client() -> Github:
    return Github(config.GITHUB_TOKEN)


def fetch_issue(repo_full_name: str, issue_number: int) -> Issue:
    """Fetch a GitHub issue and return a typed Issue dict."""
    from graph.state import Issue as _Issue  # local import avoids circular at module level

    g = _client()
    repo = g.get_repo(repo_full_name)
    gh_issue = repo.get_issue(issue_number)
    return _Issue(
        number=gh_issue.number,
        title=gh_issue.title,
        body=gh_issue.body or "",
        repo_full_name=repo_full_name,
    )


def get_clone_url(repo_full_name: str) -> str:
    """Return the HTTPS clone URL with embedded token for auth."""
    token = config.GITHUB_TOKEN
    return f"https://{token}@github.com/{repo_full_name}.git"


def create_pull_request(
    repo_full_name: str,
    branch_name: str,
    base_branch: str,
    title: str,
    body: str,
) -> str:
    """Open a PR and return its HTML URL."""
    g = _client()
    repo = g.get_repo(repo_full_name)
    pr: PullRequest.PullRequest = repo.create_pull(
        title=title,
        body=body,
        head=branch_name,
        base=base_branch,
    )
    return pr.html_url
