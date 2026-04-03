"""Identify which Odoo modules need README review."""

import logging

from . import git_utils, readme_utils

logger = logging.getLogger(__name__)


def get_modules_needing_review(repo_root: str = ".") -> list[dict]:
    """Return modules that have technical changes since their last documented SHA.

    For each module in the repo:
    1. Get SHA from README tag
    2. Check if there are technical changes since that SHA
    3. Return modules that have changes

    Returns a list of dicts:
    [
        {
            "path": "relative/path/to/module",
            "last_sha": "abc1234f" | None,
            "changed_files": ["models/sale.py", "views/sale_view.xml"],
        },
        ...
    ]
    """
    all_modules = git_utils.get_all_modules(repo_root)
    logger.info("Found %d module(s) in repo", len(all_modules))

    needs_review = []
    for module_path in all_modules:
        last_sha = readme_utils.get_documented_sha(module_path)
        if not git_utils.has_changes_since(last_sha, module_path):
            logger.debug("No changes in %s since %s — skipping", module_path, last_sha)
            continue

        changed_files = _get_changed_files(last_sha, module_path)
        logger.debug(
            "Module %s has %d changed file(s) since %s",
            module_path,
            len(changed_files),
            last_sha,
        )
        needs_review.append(
            {
                "path": module_path,
                "last_sha": last_sha,
                "changed_files": changed_files,
            }
        )

    return needs_review


def _get_changed_files(sha: str | None, module_path: str) -> list[str]:
    """Return list of changed files in module_path since sha."""
    if sha is None:
        return []
    try:
        output = git_utils.run(
            [
                "git",
                "diff",
                "--name-only",
                sha,
                "HEAD",
                "--",
                module_path,
                ":(exclude)**/README.md",
            ]
        )
        return [f for f in output.splitlines() if f]
    except RuntimeError:
        return []
