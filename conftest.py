"""
Set required env vars before any module is imported during collection.
This runs before pytest collects tests, so config.py can be safely imported.
"""

import os

os.environ.setdefault("GITHUB_TOKEN", "fake-token-for-tests")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake-key-for-tests")
os.environ.setdefault("WORKSPACE_DIR", "/tmp/swe_agent_test")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("SANDBOX_TIMEOUT", "60")
