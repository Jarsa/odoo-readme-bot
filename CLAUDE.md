# odoo-readme-bot

## Project Overview

Python package that automatically detects outdated README files in Odoo custom module
repositories and regenerates them using Claude API. Designed to run as a scheduled
GitLab CI job (once per day) on client repositories managed by Jarsa.

**Repository:** `github.com/Jarsa/odoo-readme-bot`
**PyPI package:** `odoo-readme-bot`
**Author:** Jarsa
**License:** MIT

---

## Architecture

```
odoo_readme_bot/
├── __init__.py
├── cli.py              ← Entry point: `odoo-readme-bot run`
├── detector.py         ← Finds Odoo modules with changes since last documented SHA
├── analyzer.py         ← Calls Claude Haiku to decide if README needs update
├── generator.py        ← Calls Claude Sonnet to regenerate the full README
├── git_utils.py        ← git diff, git add, git commit, git push helpers
├── readme_utils.py     ← Read/write the SHA tag embedded in README.md
└── prompt.md           ← Base documentation prompt (bundled with package)
```

### SHA tracking concept

Every README managed by this bot contains an embedded HTML comment as the last line:

```
<!-- odoo-docs: last-commit=abc1234f | updated=2025-04-01 -->
```

This SHA marks the exact commit when the README was last generated. All diffs are
computed from that SHA to HEAD, not HEAD~1. This correctly handles days with multiple
merges (e.g. 6 commits merged during a client on-site visit).

### Two-model strategy (cost optimization)

1. **Claude Haiku** (`claude-haiku-4-5-20251001`) — fast and cheap (~$0.001/call)
   - Receives: git diff since last SHA + first 2000 chars of current README
   - Decides: YES/NO whether the README needs updating
   - Responds: JSON `{"needs_update": bool, "reason": "string in Spanish"}`

2. **Claude Sonnet** (`claude-sonnet-4-6`) — powerful, called only when needed
   - Receives: full module file tree + base prompt
   - Generates: complete bilingual README (English technical + Spanish functional)
   - Only called when Haiku returns `needs_update: true`

---

## Repository Structure

```
odoo-readme-bot/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── CHANGELOG.md
├── .github/
│   └── workflows/
│       └── publish.yml     ← Publishes to PyPI on git tag
├── .gitignore
└── odoo_readme_bot/
    ├── __init__.py          ← version = "X.Y.Z" (single source of truth)
    ├── cli.py
    ├── detector.py
    ├── analyzer.py
    ├── generator.py
    ├── git_utils.py
    ├── readme_utils.py
    └── prompt.md
```

---

## Local Development Setup

**Requirements:** Python 3.10+, pip, git

```bash
# Clone
git clone git@github.com:Jarsa/odoo-readme-bot.git
cd odoo-readme-bot

# Create virtualenv
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify entry point works
odoo-readme-bot --help
```

### Running locally against a client repo

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

# From any Odoo client repo root:
cd ~/proyectos/17.0/cliente-repo
odoo-readme-bot run

# Dry run (analyze only, no file writes, no git operations):
odoo-readme-bot run --dry-run

# Force update all modules regardless of SHA:
odoo-readme-bot run --force

# Single module only:
odoo-readme-bot run --module path/to/module_name
```

---

## pyproject.toml Specification

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "odoo-readme-bot"
dynamic = ["version"]
description = "Automatic README documentation bot for Odoo custom modules"
readme = "README.md"
license = { text = "MIT" }
authors = [{ name = "Jarsa", email = "dev@jarsa.com" }]
requires-python = ">=3.10"
dependencies = [
    "anthropic>=0.30.0",
    "gitpython>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "ruff",
]

[project.scripts]
odoo-readme-bot = "odoo_readme_bot.cli:main"

[tool.hatch.version]
path = "odoo_readme_bot/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["odoo_readme_bot"]
include = ["odoo_readme_bot/prompt.md"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

---

## Module Specifications

### `odoo_readme_bot/__init__.py`

```python
__version__ = "1.0.0"
```

Version is the **single source of truth**. `pyproject.toml` reads it via hatch dynamic.
When bumping version, only edit this file.

---

### `readme_utils.py`

**Purpose:** Read and write the SHA tag embedded in README.md.

```python
SHA_PATTERN = re.compile(
    r"<!--\s*odoo-docs:\s*last-commit=([a-f0-9]+)\s*\|.*?-->"
)

def get_documented_sha(module_path: str) -> str | None:
    """
    Returns the SHA stored in the README tag.
    Returns None if README does not exist or has no tag (treat as never documented).
    """

def write_sha_to_readme(module_path: str, sha: str, content: str) -> None:
    """
    Writes the README content with the SHA tag updated/appended.
    Tag format: <!-- odoo-docs: last-commit={sha} | updated={YYYY-MM-DD} -->
    If tag already exists, replaces it. If not, appends it as the last line.
    """
```

---

### `git_utils.py`

**Purpose:** All subprocess git operations. No GitPython ORM — use subprocess directly
for predictability in CI environments.

```python
def run(cmd: list[str], cwd: str = ".") -> str:
    """Runs a git command, returns stdout. Raises on non-zero exit."""

def get_current_sha() -> str:
    """Returns full SHA of HEAD."""

def get_diff_since(sha: str, module_path: str, max_chars: int = 20_000) -> str:
    """
    Returns git diff from {sha} to HEAD for the given module_path.
    Excludes README.md from the diff to avoid confusing the model.
    Truncates to max_chars to control token usage.
    """

def has_changes_since(sha: str | None, module_path: str) -> bool:
    """
    Returns True if any non-README file in module_path changed since sha.
    If sha is None, always returns True (module was never documented).
    """

def get_all_modules(repo_root: str = ".") -> list[str]:
    """
    Recursively finds all directories containing __manifest__.py.
    Returns list of relative paths from repo_root.
    """

def configure_git(name: str, email: str) -> None:
    """Sets git user.name and user.email for the current repo."""

def commit_and_push(branch: str, modules_updated: list[str], sha_short: str) -> None:
    """
    Stages all README.md files in updated modules,
    creates a commit with [skip ci] tag,
    and pushes to origin/{branch}.

    Commit message format:
    docs: auto-update README(s) [skip ci]

    Modules: module_a, module_b
    Triggered by: {sha_short}
    """
```

---

### `detector.py`

**Purpose:** Identify which modules need README review.

```python
def get_modules_needing_review(repo_root: str = ".") -> list[dict]:
    """
    For each module in the repo:
    1. Get SHA from README tag
    2. Check if there are technical changes since that SHA
    3. Return modules that have changes

    Returns list of dicts:
    [
        {
            "path": "relative/path/to/module",
            "last_sha": "abc1234f" | None,
            "changed_files": ["models/sale.py", "views/sale_view.xml"],
        },
        ...
    ]
    """
```

---

### `analyzer.py`

**Purpose:** Call Haiku to decide if a README update is warranted.

```python
def should_update(
    client: anthropic.Anthropic,
    diff: str,
    readme_preview: str,
) -> dict:
    """
    Calls claude-haiku-4-5-20251001 with the diff and README preview.

    Returns:
    {
        "needs_update": bool,
        "reason": "string in Spanish explaining the decision"
    }

    On JSON parse failure: returns {"needs_update": True, "reason": "Error al analizar..."}
    Never raises — always returns a safe default.
    """
```

**Haiku prompt rules:**
- Respond ONLY with valid JSON, no markdown fences, no preamble
- `max_tokens: 150` (response is tiny)
- Temperature: default (no override needed)

---

### `generator.py`

**Purpose:** Call Sonnet to generate the full bilingual README.

```python
def read_module_files(module_path: str) -> str:
    """
    Reads all relevant Odoo module files and returns them as a single
    concatenated string with === filename === separators.

    Patterns scanned (in this order):
    - **/__manifest__.py
    - **/models/*.py
    - **/wizards/*.py
    - **/views/*.xml
    - **/security/*.xml
    - **/security/*.csv
    - **/data/*.xml
    - **/report/*.xml
    - **/controllers/*.py

    Each file is truncated to 8000 chars to avoid context overflow.
    """

def generate_readme(
    client: anthropic.Anthropic,
    module_path: str,
    base_prompt: str,
) -> str:
    """
    Calls claude-sonnet-4-6 with the full module context and base prompt.
    Returns raw markdown string (the complete README content).
    max_tokens: 8000
    Output: ONLY markdown, no explanations before or after.
    """
```

---

### `cli.py`

**Purpose:** Entry point. Orchestrates the full pipeline.

**Environment variables read:**

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Claude API key |
| `GITLAB_TOKEN` | CI only | — | For git push in CI |
| `CI_DEFAULT_BRANCH` | CI only | `main` | Branch to push to |
| `CI_SERVER_HOST` | CI only | `gitlab.com` | GitLab host |
| `CI_PROJECT_PATH` | CI only | — | e.g. `Jarsa/cliente-repo` |
| `CI_PROJECT_DIR` | CI only | `.` | Repo root path |
| `BOT_NAME` | No | `Jarsa Docs Bot` | Git commit author name |
| `BOT_EMAIL` | No | `docs-bot@jarsa.com` | Git commit author email |

**CLI flags:**

```
odoo-readme-bot run [--dry-run] [--force] [--module PATH]

--dry-run    Analyze and print results but do not write files or push
--force      Skip SHA check and regenerate all module READMEs
--module     Only process this specific module path
```

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Success, no changes needed |
| 42 | Success, one or more READMEs were updated and pushed |
| 1 | Unrecoverable error (missing API key, git failure, etc.) |

**Pipeline flow:**

```
1. Read env vars, configure git if GITLAB_TOKEN present
2. get_all_modules() → full list
3. get_modules_needing_review() → filtered list with changes
4. For each module:
   a. get_diff_since(last_sha, module_path)
   b. should_update(client, diff, readme_preview)  ← Haiku
   c. If needs_update:
      - generate_readme(client, module_path, base_prompt)  ← Sonnet
      - write_sha_to_readme(module_path, current_sha, content)
      - append module to `updated` list
5. If updated and GITLAB_TOKEN present:
   - commit_and_push(branch, updated, sha_short)
6. Print summary
7. sys.exit(42) if updated else sys.exit(0)
```

---

### `prompt.md`

Contains the full bilingual README generation prompt defined for the
`~/.claude/skills/document-odoo-module/SKILL.md`.

This file is **bundled with the wheel** (see `pyproject.toml` include).
When the prompt needs updating, edit this file, bump the version, and publish.

---

## GitHub Actions — Auto-publish to PyPI on tag

Uses **Trusted Publisher (OIDC)** via `pypa/gh-action-pypi-publish` — no tokens
to store or rotate. GitHub Actions is a supported OIDC provider by PyPI since 2023,
stable and available without any manual onboarding.

Already configured on PyPI under:
Publisher `GitHub` / Owner `Jarsa` / Repo `odoo-readme-bot` /
Workflow `publish.yml` / Environment `pypi`.

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*.*.*"   # triggers on v1.0.0, v1.2.3, etc.

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff -q
      - run: ruff check odoo_readme_bot/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]" -q
      - run: pytest tests/ --cov=odoo_readme_bot --cov-report=term-missing

  publish:
    needs: [lint, test]
    runs-on: ubuntu-latest
    environment: pypi          # Must match the environment name set in PyPI
    permissions:
      id-token: write          # Required for OIDC token generation
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install build -q
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
        # No token needed — OIDC handles authentication automatically
```

### Release workflow

```bash
# 1. Edit odoo_readme_bot/__init__.py → bump __version__
# 2. Update CHANGELOG.md
# 3. Commit
git add odoo_readme_bot/__init__.py CHANGELOG.md
git commit -m "chore: release v1.2.0"
git push origin main

# 4. Create and push the tag → triggers GitHub Actions automatically
git tag v1.2.0
git push origin v1.2.0
```

GitHub Actions detects the `v1.2.0` tag pattern, runs lint + test, and if both
pass publishes to PyPI via OIDC. No secrets to manage.

---

## Tests

```
tests/
├── __init__.py
├── test_readme_utils.py    ← SHA read/write, tag pattern matching
├── test_git_utils.py       ← Mock subprocess, test diff parsing
├── test_detector.py        ← Mock git output, test module detection
├── test_analyzer.py        ← Mock Anthropic client, test JSON parsing + fallback
└── test_generator.py       ← Mock Anthropic client, test file reading
```

**Run tests:**

```bash
pytest tests/ -v
pytest tests/ --cov=odoo_readme_bot --cov-report=term-missing
```

**Coverage target:** 80% minimum.

Use `unittest.mock.patch` to mock `anthropic.Anthropic` and subprocess calls.
Never make real API calls in tests.

---

## How client repos use this package

The `.gitlab-ci.yml` in every client repo is minimal:

```yaml
# Client repo .gitlab-ci.yml (only the docs stage shown)
auto-update-readme:
  stage: auto-docs
  image: python:3.11-slim
  script:
    - pip install odoo-readme-bot -q
    - odoo-readme-bot run
  rules:
    - if: '$CI_PIPELINE_SOURCE == "schedule"'
  allow_failure: true
```

**Required CI/CD variables in client repo (or GitLab group):**

```
ANTHROPIC_API_KEY   → sk-ant-...     (protected, masked)
GITLAB_TOKEN        → glpat-...      (protected, masked) — needs write_repository
```

**GitLab Schedule configuration:**
- Cron: `0 6 * * 1-5` (Monday–Friday 6am Torreón time, UTC-6 = `0 12 * * 1-5`)
- Target branch: `main` (or the client's production branch)

---

## Coding Standards

- All code in **English** (variables, methods, comments, docstrings)
- User-facing messages and `reason` fields in **Spanish**
- Type hints required on all function signatures
- Docstrings on all public functions
- No `print()` in library modules — use `logging`; `print()` only in `cli.py`
- `ruff` for linting (configured in pyproject.toml)
- No external dependencies beyond `anthropic` and `gitpython`

---

## CHANGELOG.md Format

```markdown
# Changelog

## [1.0.0] - 2025-04-02
### Added
- Initial release
- SHA-based diff tracking
- Haiku analyzer + Sonnet generator pipeline
- CLI with --dry-run, --force, --module flags
- GitLab CI auto-publish on tag
```

---

## Initial Setup Checklist

- [ ] Create repo at `github.com/Jarsa/odoo-readme-bot` (public)
- [ ] Set default branch to `main`
- [ ] Create GitHub environment `pypi`:
      Settings → Environments → New environment → name: `pypi`
- [ ] Restrict `pypi` environment to tag rules only:
      Edit environment → Deployment branches and tags →
      Add rule: Tag pattern `v*`
- [ ] Configure Trusted Publisher on PyPI (already done ✅):
      Publisher: GitHub / Owner: Jarsa / Repo: odoo-readme-bot /
      Workflow: `publish.yml` / Environment: `pypi`
- [ ] First publish to PyPI (one-time, creates the package name):
      ```bash
      pip install build twine
      python -m build
      twine upload dist/*   # uses PyPI username + password, only this once
      ```
      After this, all subsequent releases go through GitHub Actions automatically.
- [ ] Add group-level CI/CD variables in `git.jarsa.com/Jarsa` (for client repos):
      - `BOT_NAME`          → `Jarsa Docs Bot`
      - `BOT_EMAIL`         → `docs-bot@jarsa.com`
      - `ANTHROPIC_API_KEY` → `sk-ant-...` (protected, masked)
      - `GITLAB_TOKEN`      → `glpat-...` (protected, masked, needs `write_repository`)
      All client repos inherit these without per-repo configuration.