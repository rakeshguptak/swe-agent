"""Repository inspection: clone, walk files, AST-parse symbols."""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Optional

import git

import config
from tools.github_client import get_clone_url

# Extensions considered source code worth inspecting
_SOURCE_EXTS = {".py", ".js", ".ts", ".go", ".java", ".rb", ".rs", ".cpp", ".c", ".cs"}
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build"}
_MAX_FILE_BYTES = 200_000  # skip files larger than ~200 KB


def clone_repo(repo_full_name: str) -> str:
    """Clone (or pull if already cloned) the repo. Returns local path."""
    dest = Path(config.WORKSPACE_DIR) / repo_full_name.replace("/", "_")
    if dest.exists():
        repo = git.Repo(str(dest))
        origin = repo.remotes.origin
        origin.pull()
    else:
        dest.mkdir(parents=True, exist_ok=True)
        clone_url = get_clone_url(repo_full_name)
        git.Repo.clone_from(clone_url, str(dest))
    return str(dest)


def walk_repo(local_path: str) -> list[str]:
    """Return all source-file relative paths inside the repo."""
    base = Path(local_path)
    paths: list[str] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix in _SOURCE_EXTS:
                paths.append(str(fpath.relative_to(base)))
    return sorted(p.replace("\\", "/") for p in paths)


def read_file(local_path: str, relative: str) -> Optional[str]:
    """Read a file's content; returns None if too large or unreadable."""
    full = Path(local_path) / relative
    if not full.exists():
        return None
    if full.stat().st_size > _MAX_FILE_BYTES:
        return None
    try:
        return full.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def extract_python_symbols(source: str) -> list[str]:
    """Return top-level function and class names from Python source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and isinstance(getattr(node, "col_offset", 1), int)
        and node.col_offset == 0
    ]


def select_relevant_files(
    local_path: str,
    all_files: list[str],
    keywords: list[str],
) -> dict[str, str]:
    """
    Heuristic: return files whose path or content contains any keyword.
    Caps at 20 files to stay within LLM context limits.
    """
    lower_kws = [k.lower() for k in keywords]
    relevant: dict[str, str] = {}

    for rel_path in all_files:
        if len(relevant) >= 20:
            break
        # Path match
        if any(kw in rel_path.lower() for kw in lower_kws):
            content = read_file(local_path, rel_path)
            if content is not None:
                relevant[rel_path] = content
                continue
        # Content match (only source files)
        content = read_file(local_path, rel_path)
        if content and any(kw in content.lower() for kw in lower_kws):
            relevant[rel_path] = content

    return relevant
