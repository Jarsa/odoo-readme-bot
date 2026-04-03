"""Thin wrapper around the `claude` CLI for local usage without ANTHROPIC_API_KEY.

Implements just enough of the anthropic.Anthropic.messages interface so that
analyzer.py and generator.py can use it transparently.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)


class _Content:
    def __init__(self, text: str) -> None:
        self.text = text


class _Message:
    def __init__(self, text: str) -> None:
        self.content = [_Content(text)]


class _Messages:
    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict],
        system: str | None = None,
    ) -> _Message:
        """Call `claude -p` CLI and return a response object."""
        # Build the full prompt: system prefix + user message
        user_text = messages[-1]["content"]
        if system:
            full_prompt = f"{system}\n\n{user_text}"
        else:
            full_prompt = user_text

        cmd = [
            "claude",
            "--model", model,
            "--output-format", "text",
            "-p", full_prompt,
        ]
        logger.debug("Calling claude CLI: model=%s max_tokens=%d", model, max_tokens)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return _Message(result.stdout)


class LocalClaudeClient:
    """Drop-in replacement for anthropic.Anthropic() that uses the claude CLI."""

    def __init__(self) -> None:
        self.messages = _Messages()
