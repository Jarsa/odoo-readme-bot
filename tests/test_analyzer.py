"""Tests for analyzer — mock Anthropic client, test JSON parsing + fallback."""

import json
from unittest.mock import MagicMock

import pytest

from odoo_readme_bot.analyzer import should_update


def _make_client(response_text: str) -> MagicMock:
    """Create a mock Anthropic client that returns the given response text."""
    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = message
    return client


class TestShouldUpdate:
    def test_returns_needs_update_true(self):
        payload = json.dumps({"needs_update": True, "reason": "Se agregaron nuevos campos."})
        client = _make_client(payload)
        result = should_update(client, "some diff", "# README")
        assert result["needs_update"] is True
        assert "campos" in result["reason"]

    def test_returns_needs_update_false(self):
        payload = json.dumps({"needs_update": False, "reason": "Sin cambios relevantes."})
        client = _make_client(payload)
        result = should_update(client, "", "# README")
        assert result["needs_update"] is False

    def test_fallback_on_invalid_json(self):
        client = _make_client("not valid json at all")
        result = should_update(client, "diff", "readme")
        assert result["needs_update"] is True
        assert "Error" in result["reason"]

    def test_fallback_on_api_exception(self):
        client = MagicMock()
        client.messages.create.side_effect = Exception("network error")
        result = should_update(client, "diff", "readme")
        assert result["needs_update"] is True
        assert "Error" in result["reason"]

    def test_passes_correct_model_to_api(self):
        payload = json.dumps({"needs_update": False, "reason": "OK"})
        client = _make_client(payload)
        should_update(client, "diff", "readme")
        call_kwargs = client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-haiku-4-5-20251001"
        assert call_kwargs.kwargs["max_tokens"] == 150

    def test_readme_preview_truncated_to_2000(self):
        payload = json.dumps({"needs_update": False, "reason": "OK"})
        client = _make_client(payload)
        long_readme = "x" * 5_000
        should_update(client, "diff", long_readme)
        call_kwargs = client.messages.create.call_args
        user_content = call_kwargs.kwargs["messages"][0]["content"]
        # The preview passed to the prompt should be at most 2000 chars of the readme
        assert long_readme[2000:] not in user_content
