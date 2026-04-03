"""Call Claude Sonnet to generate the full bilingual README."""

import glob
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

_SONNET_MODEL = "claude-sonnet-4-6"
_MAX_FILE_CHARS = 8_000
_MAX_TOKENS = 8_000

_FILE_PATTERNS = [
    "**/__manifest__.py",
    "**/models/*.py",
    "**/wizards/*.py",
    "**/views/*.xml",
    "**/security/*.xml",
    "**/security/*.csv",
    "**/data/*.xml",
    "**/report/*.xml",
    "**/controllers/*.py",
]


def read_module_files(module_path: str) -> str:
    """Read all relevant Odoo module files as a single concatenated string.

    Files are separated by === filename === headers.
    Each file is truncated to 8000 chars to avoid context overflow.
    """
    seen: set[str] = set()
    sections: list[str] = []

    for pattern in _FILE_PATTERNS:
        full_pattern = os.path.join(module_path, pattern)
        for filepath in sorted(glob.glob(full_pattern, recursive=True)):
            abs_path = os.path.abspath(filepath)
            if abs_path in seen:
                continue
            seen.add(abs_path)
            rel = os.path.relpath(filepath, module_path)
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                sections.append(f"=== {rel} ===\n{content[:_MAX_FILE_CHARS]}")
            except OSError as exc:
                logger.warning("Could not read %s: %s", filepath, exc)

    return "\n\n".join(sections)


def generate_readme(
    client: anthropic.Anthropic,
    module_path: str,
    base_prompt: str,
) -> str:
    """Call claude-sonnet-4-6 to generate the full bilingual README.

    Returns raw markdown string (the complete README content).
    Output: ONLY markdown, no explanations before or after.
    """
    module_context = read_module_files(module_path)
    user_content = (
        "IMPORTANT: Respond with ONLY the raw markdown content of the README. "
        "Do not use any tools. Do not ask for permissions. Do not explain what you will do. "
        "Output the markdown directly and nothing else.\n\n"
        f"{base_prompt}\n\n"
        "---\n\n"
        "## Module files\n\n"
        f"{module_context}"
    )
    response = client.messages.create(
        model=_SONNET_MODEL,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text
