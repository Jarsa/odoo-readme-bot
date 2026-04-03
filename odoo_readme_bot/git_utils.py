"""All subprocess git operations for odoo-readme-bot."""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def run(cmd: list[str], cwd: str = ".") -> str:
    """Run a git command and return stdout. Raises on non-zero exit."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command {' '.join(cmd)} failed (exit {result.returncode}):\n{result.stderr}"
        )
    return result.stdout.strip()


def get_current_sha(cwd: str = ".") -> str:
    """Return the full SHA of HEAD."""
    return run(["git", "rev-parse", "HEAD"], cwd=cwd)


def get_diff_since(sha: str, module_path: str, max_chars: int = 20_000) -> str:
    """Return git diff from {sha} to HEAD for the given module_path.

    Excludes README.md from the diff to avoid confusing the model.
    Truncates to max_chars to control token usage.
    """
    cmd = [
        "git",
        "diff",
        sha,
        "HEAD",
        "--",
        module_path,
        ":(exclude)**/README.md",
    ]
    try:
        diff = run(cmd)
    except RuntimeError:
        # sha might not exist (shallow clone, etc.) — return empty diff
        logger.warning("Could not compute diff from %s for %s", sha, module_path)
        return ""
    return diff[:max_chars]


def has_changes_since(sha: str | None, module_path: str) -> bool:
    """Return True if any non-README file in module_path changed since sha.

    If sha is None, always returns True (module was never documented).
    """
    if sha is None:
        return True
    cmd = [
        "git",
        "diff",
        "--name-only",
        sha,
        "HEAD",
        "--",
        module_path,
        ":(exclude)**/README.md",
    ]
    try:
        output = run(cmd)
    except RuntimeError:
        logger.warning("Could not check changes for %s since %s", module_path, sha)
        return True
    return bool(output.strip())


def get_all_modules(repo_root: str = ".") -> list[str]:
    """Recursively find all directories containing __manifest__.py.

    Returns a list of relative paths from repo_root.
    """
    modules = []
    for dirpath, _dirnames, filenames in os.walk(repo_root):
        if "__manifest__.py" in filenames:
            rel = os.path.relpath(dirpath, repo_root)
            modules.append(rel)
    return sorted(modules)


def configure_git(name: str, email: str, cwd: str = ".") -> None:
    """Set git user.name and user.email for the current repo."""
    run(["git", "config", "user.name", name], cwd=cwd)
    run(["git", "config", "user.email", email], cwd=cwd)
    logger.debug("Configured git user: %s <%s>", name, email)


def commit_and_push(
    branch: str,
    modules_updated: list[str],
    sha_short: str,
    cwd: str = ".",
) -> None:
    """Stage all README.md files, commit with [skip ci], and push.

    Commit message format:
        docs: auto-update README(s) [skip ci]

        Modules: module_a, module_b
        Triggered by: {sha_short}
    """
    for module_path in modules_updated:
        readme = os.path.join(module_path, "README.md")
        run(["git", "add", readme], cwd=cwd)

    modules_str = ", ".join(modules_updated)
    message = (
        f"docs: auto-update README(s) [skip ci]\n\n"
        f"Modules: {modules_str}\n"
        f"Triggered by: {sha_short}"
    )
    run(["git", "commit", "-m", message], cwd=cwd)
    run(["git", "push", "origin", branch], cwd=cwd)
    logger.info("Pushed updated READMEs to origin/%s", branch)
