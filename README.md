# Autonomous SWE Agent

A mini [Devin](https://www.cognition.ai/blog/introducing-devin) / Cognition-style autonomous software engineering agent built with LangGraph. Give it a GitHub issue number and it will inspect the codebase, plan a fix, write the code, run tests, self-debug on failures, and open a pull request all without human intervention.

---

## Demo

```
$ python main.py octocat/Hello-World 42

[SWE Agent] Starting on octocat/Hello-World#42
[fetch_issue]   done — updated: issue
[inspect_repo]  done — updated: local_repo_path, repo_tree, relevant_files
[plan_fix]      done — updated: fix_plan
[write_code]    done — updated: patches
[run_tests]     done — updated: test_result
[open_pr]       PR opened: https://github.com/octocat/Hello-World/pull/99
[SWE Agent] Complete.
```

---

## How It Works

```
fetch_issue → inspect_repo → plan_fix → write_code → run_tests
                                                          │
                                                   pass ──┤── open_pr ──→ DONE
                                                          │
                                           fail (retry<3)─┤── debug ──→ write_code
                                                          │
                                           fail (retry≥3)─┴── ABORT
```

Each step is a LangGraph node. State flows through a single `AgentState` TypedDict, making every transition inspectable and resumable.

### Nodes

| Node | What it does |
|------|-------------|
| `fetch_issue` | Downloads the GitHub issue title + body via the GitHub API |
| `inspect_repo` | Clones the repo, walks all source files, uses keyword heuristics to select the ≤20 most relevant files |
| `plan_fix` | Sends issue + relevant files to Claude and gets back a structured JSON fix plan (summary, files to change, ordered steps) |
| `write_code` | Sends the fix plan + current file contents to Claude and gets back complete patched file content |
| `run_tests` | Applies patches to disk and runs `pytest --tb=short` in a sandboxed subprocess |
| `debug` | On test failure, sends the failure output + patch to Claude for root-cause analysis; the note is fed back into the next `write_code` call |
| `open_pr` | Commits the patch on a new branch, pushes it, and opens a pull request with an LLM-generated title and description |

---

## Project Structure

```
swe_agent/
├── main.py                   # CLI entry point
├── config.py                 # Env-var loader with startup validation
├── conftest.py               # pytest env setup
├── requirements.txt
│
├── graph/
│   ├── state.py              # AgentState TypedDict — single source of truth
│   ├── nodes.py              # All 7 LangGraph node functions
│   ├── edges.py              # Conditional routing (pass / fail / retry)
│   └── __init__.py           # build_graph() factory
│
├── tools/                    # Pure I/O functions — no LLM calls
│   ├── github_client.py      # Read issues, create PRs (PyGithub)
│   ├── repo_inspector.py     # Clone, walk, AST-parse, select relevant files
│   ├── code_sandbox.py       # Subprocess runner with hard timeout
│   ├── test_runner.py        # pytest runner + structured failure extractor
│   └── git_ops.py            # Branch, apply patches, commit, push (GitPython)
│
├── agents/                   # LLM-backed functions
│   ├── planner.py            # Issue → FixPlan (structured JSON)
│   ├── coder.py              # FixPlan → FilePatch list (full file content)
│   ├── debugger.py           # Failures → root-cause note (reflection)
│   └── reviewer.py           # Diff → PR title + body
│
└── tests/
    ├── test_github_client.py
    ├── test_repo_inspector.py
    ├── test_sandbox.py
    ├── test_test_runner.py
    ├── test_git_ops.py
    └── test_graph.py         # End-to-end smoke tests with all IO mocked
```

---

## Quickstart

### 1. Prerequisites

- Python 3.11+
- A GitHub account with a [Personal Access Token](https://github.com/settings/tokens) (`repo` scope)
- An [Anthropic API key](https://console.anthropic.com/)

### 2. Clone & install

```bash
git clone https://github.com/rakeshguptak/swe-agent.git
cd swe-agent
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
GITHUB_TOKEN=ghp_your_token_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

### 4. Run

```bash
python main.py owner/repo 42
```

The agent will:
1. Fetch issue `#42` from `owner/repo`
2. Clone the repo locally to `$WORKSPACE_DIR`
3. Inspect source files relevant to the issue
4. Ask Claude to produce a fix plan
5. Ask Claude to write the patched code
6. Run `pytest` against the patch
7. If tests fail, ask Claude to debug and retry (up to `MAX_RETRIES` times)
8. Open a pull request with the working patch

---

## Configuration

All options are set via environment variables (or `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | **required** | GitHub Personal Access Token (`repo` scope) |
| `ANTHROPIC_API_KEY` | **required** | Anthropic API key |
| `LLM_MODEL` | `claude-sonnet-4-6` | Claude model to use for all LLM calls |
| `WORKSPACE_DIR` | `/tmp/swe_agent_workspace` | Where repos are cloned |
| `MAX_RETRIES` | `3` | Max debug→rewrite cycles before aborting |
| `SANDBOX_TIMEOUT` | `60` | Seconds before a subprocess is killed |

---

## Running Tests

```bash
pytest tests/ -v
```

```bash
pytest tests/ --cov=. --cov-report=term-missing
```

Tests use mocks for all external calls (GitHub API, git clone, LLM, subprocess). No credentials or network access needed.

**Coverage:** 81% — all core graph logic, tools, and routing covered.

---

## Design Decisions

### Why LangGraph?

LangGraph's `StateGraph` makes the control flow explicit: each node is a pure function `(state) → partial_state`, and edges encode the routing logic separately. This means:
- The debug loop (`run_tests → debug → write_code`) is a first-class graph construct, not an ad-hoc `while` loop buried in business logic.
- Every intermediate state is inspectable.
- The graph can be resumed from any checkpoint (LangGraph supports persistence out of the box).

### Why full file content instead of diffs?

Generating complete file content (rather than unified diffs) is more reliable with LLMs:
- Diffs require exact line-number matching, which LLMs get wrong under context pressure.
- Full content is unambiguous to apply — no patch conflict resolution needed.
- The 200 KB file size cap keeps context usage manageable.

### Reflection loop cap

`MAX_RETRIES=3` is a hard cap on the `debug → write_code` cycle. Without it, a pathological case (e.g. a test that requires external state the agent can't set up) would spin indefinitely. Three attempts matches the observed empirical sweet spot — most real bugs are fixed in 1–2 passes; if three attempts fail, the issue likely needs human intervention.

### Relevant file selection

The agent uses a keyword heuristic (words extracted from the issue title + body) to select ≤20 files. This is intentionally simple:
- Embedding-based semantic search adds latency and cost.
- For the majority of issues, the relevant files contain the same domain words as the issue description.
- The 20-file cap keeps the planning prompt within the model's effective context window.

---

## Limitations

- **Python repos only** for AST symbol extraction (other languages fall back to keyword-only file matching).
- **pytest only** for the test runner — no support for Jest, Go test, etc. yet.
- **No execution sandbox** beyond a subprocess timeout — the agent has full filesystem access inside the cloned repo.
- **Single-repo** — does not handle issues that require changes across multiple repositories.

---

## Roadmap

- [ ] Multi-language test runner (Jest, `go test`, `cargo test`)
- [ ] Embedding-based file retrieval for larger codebases
- [ ] LangGraph checkpoint persistence (resume interrupted runs)
- [ ] Docker-based sandbox for true code isolation
- [ ] GitHub Actions integration (trigger on issue label)
- [ ] Streaming output with live patch preview

---

## License

MIT
