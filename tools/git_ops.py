"""Git operations: branch, apply patches, commit, push."""

from __future__ import annotations

from pathlib import Path

import git

from graph.state import FilePatch


def default_branch(local_repo_path: str) -> str:
    """Return the name of the remote HEAD branch (usually 'main' or 'master')."""
    repo = git.Repo(local_repo_path)
    try:
        return repo.remotes.origin.refs.HEAD.reference.remote_head
    except AttributeError:
        # Fallback: check for 'main' then 'master'
        remote_refs = [r.remote_head for r in repo.remotes.origin.refs]
        for candidate in ("main", "master"):
            if candidate in remote_refs:
                return candidate
        return "main"


def create_branch(local_repo_path: str, branch_name: str) -> None:
    """Create and checkout a new branch from current HEAD."""
    repo = git.Repo(local_repo_path)
    repo.git.checkout("-b", branch_name)


def apply_patches(local_repo_path: str, patches: list[FilePatch]) -> None:
    """Write patched content to disk for each FilePatch."""
    base = Path(local_repo_path)
    for patch in patches:
        target = base / patch["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(patch["patched"], encoding="utf-8")


def commit_all(local_repo_path: str, message: str) -> str:
    """Stage all changes and commit. Returns the new commit SHA."""
    repo = git.Repo(local_repo_path)
    repo.git.add("-A")
    commit = repo.index.commit(message)
    return commit.hexsha


def push_branch(local_repo_path: str, branch_name: str) -> None:
    """Push the branch to origin."""
    repo = git.Repo(local_repo_path)
    repo.remotes.origin.push(refspec=f"{branch_name}:{branch_name}")
