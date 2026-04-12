"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Required env var {name!r} is not set")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default)


GITHUB_TOKEN: str = _require("GITHUB_TOKEN")
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")

# Model used for planning, coding, debugging, reviewing
LLM_MODEL: str = _optional("LLM_MODEL", "claude-sonnet-4-6")

# Local directory where repos are cloned
WORKSPACE_DIR: str = _optional("WORKSPACE_DIR", "/tmp/swe_agent_workspace")

# Max debug/retry cycles before aborting
MAX_RETRIES: int = int(_optional("MAX_RETRIES", "3"))

# Sandbox subprocess timeout in seconds
SANDBOX_TIMEOUT: int = int(_optional("SANDBOX_TIMEOUT", "60"))
