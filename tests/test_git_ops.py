"""Unit tests for git_ops using temporary git repositories."""

from pathlib import Path

import pytest
import git


@pytest.fixture()
def git_repo(tmp_path):
    """Create a minimal git repo with one commit."""
    repo = git.Repo.init(str(tmp_path))
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()

    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return tmp_path


def test_create_branch_switches_to_new_branch(git_repo):
    from tools.git_ops import create_branch

    create_branch(str(git_repo), "feature/my-branch")
    repo = git.Repo(str(git_repo))
    assert repo.active_branch.name == "feature/my-branch"


def test_apply_patches_writes_file(git_repo):
    from tools.git_ops import apply_patches

    patches = [{"path": "src/auth.py", "original": "", "patched": "POOL = 20\n"}]
    apply_patches(str(git_repo), patches)

    target = git_repo / "src" / "auth.py"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "POOL = 20\n"


def test_apply_patches_overwrites_existing_file(git_repo):
    from tools.git_ops import apply_patches

    (git_repo / "api.py").write_text("OLD = 1", encoding="utf-8")
    patches = [{"path": "api.py", "original": "OLD = 1", "patched": "NEW = 2\n"}]
    apply_patches(str(git_repo), patches)

    assert (git_repo / "api.py").read_text(encoding="utf-8") == "NEW = 2\n"


def test_commit_all_returns_sha(git_repo):
    from tools.git_ops import apply_patches, commit_all

    patches = [{"path": "fix.py", "original": "", "patched": "x = 1\n"}]
    apply_patches(str(git_repo), patches)

    sha = commit_all(str(git_repo), "fix: apply patch")
    assert len(sha) == 40  # full SHA hex string

    repo = git.Repo(str(git_repo))
    assert repo.head.commit.message == "fix: apply patch"


def test_create_branch_twice_raises(git_repo):
    from tools.git_ops import create_branch

    create_branch(str(git_repo), "duplicate-branch")
    with pytest.raises(git.GitCommandError):
        create_branch(str(git_repo), "duplicate-branch")
