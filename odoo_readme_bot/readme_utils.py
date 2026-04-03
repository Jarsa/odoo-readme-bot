"""Read and write the SHA tag embedded in README.md files."""

import logging
import os
import re
from datetime import date

logger = logging.getLogger(__name__)

SHA_PATTERN = re.compile(
    r"<!--\s*odoo-docs:\s*last-commit=([a-f0-9]+)\s*\|.*?-->"
)


def get_documented_sha(module_path: str) -> str | None:
    """Return the SHA stored in the README tag.

    Returns None if README does not exist or has no tag
    (treat as never documented).
    """
    readme_path = os.path.join(module_path, "README.md")
    if not os.path.isfile(readme_path):
        return None
    with open(readme_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    match = SHA_PATTERN.search(content)
    if match:
        return match.group(1)
    return None


def write_sha_to_readme(module_path: str, sha: str, content: str) -> None:
    """Write README content with the SHA tag updated or appended.

    Tag format: <!-- odoo-docs: last-commit={sha} | updated={YYYY-MM-DD} -->
    If the tag already exists, replaces it. If not, appends it as the last line.
    """
    today = date.today().isoformat()
    tag = f"<!-- odoo-docs: last-commit={sha} | updated={today} -->"

    if SHA_PATTERN.search(content):
        new_content = SHA_PATTERN.sub(tag, content)
    else:
        new_content = content.rstrip("\n") + "\n" + tag + "\n"

    readme_path = os.path.join(module_path, "README.md")
    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(new_content)
    logger.debug("Wrote SHA tag to %s", readme_path)
