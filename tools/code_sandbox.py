"""Sandboxed subprocess execution for running arbitrary shell commands."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

import config


@dataclass
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def combined_output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        if self.timed_out:
            parts.append(f"[TIMEOUT after {config.SANDBOX_TIMEOUT}s]")
        return "\n".join(parts)


def run(
    cmd: list[str],
    cwd: str,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> SandboxResult:
    """
    Run a command in a subprocess with a hard timeout.

    Network access is NOT disabled here — callers that need isolation
    should pass a restricted env or wrap with a network namespace.
    The timeout is the primary safety valve.
    """
    effective_timeout = timeout if timeout is not None else config.SANDBOX_TIMEOUT
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            env=env,
        )
        return SandboxResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        return SandboxResult(
            returncode=-1,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            timed_out=True,
        )
