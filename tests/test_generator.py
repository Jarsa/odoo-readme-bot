"""Tests for generator — mock Anthropic client, test file reading."""

from unittest.mock import MagicMock

from odoo_readme_bot.generator import generate_readme, read_module_files


class TestReadModuleFiles:
    def test_reads_manifest(self, tmp_path):
        manifest = tmp_path / "__manifest__.py"
        manifest.write_text("{'name': 'Test Module'}", encoding="utf-8")
        result = read_module_files(str(tmp_path))
        assert "__manifest__.py" in result
        assert "Test Module" in result

    def test_reads_model_files(self, tmp_path):
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "sale.py").write_text("class SaleOrder(models.Model):", encoding="utf-8")
        result = read_module_files(str(tmp_path))
        assert "SaleOrder" in result

    def test_each_file_has_separator(self, tmp_path):
        manifest = tmp_path / "__manifest__.py"
        manifest.write_text("{'name': 'X'}", encoding="utf-8")
        result = read_module_files(str(tmp_path))
        assert "===" in result

    def test_truncates_large_files(self, tmp_path):
        manifest = tmp_path / "__manifest__.py"
        # Use distinct marker at position 8001 to detect if truncation happened
        large_content = "a" * 8_000 + "OVERFLOW"
        manifest.write_text(large_content, encoding="utf-8")
        result = read_module_files(str(tmp_path))
        assert "OVERFLOW" not in result

    def test_returns_empty_string_for_empty_module(self, tmp_path):
        result = read_module_files(str(tmp_path))
        assert result == ""


class TestGenerateReadme:
    def _make_client(self, response_text: str) -> MagicMock:
        client = MagicMock()
        message = MagicMock()
        message.content = [MagicMock(text=response_text)]
        client.messages.create.return_value = message
        return client

    def test_returns_readme_content(self, tmp_path):
        expected = "# Generated README\n\nSome content."
        client = self._make_client(expected)
        result = generate_readme(client, str(tmp_path), "Base prompt")
        assert result == expected

    def test_passes_correct_model(self, tmp_path):
        client = self._make_client("# README")
        generate_readme(client, str(tmp_path), "Base prompt")
        call_kwargs = client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-sonnet-4-6"
        assert call_kwargs.kwargs["max_tokens"] == 8_000

    def test_includes_base_prompt_in_request(self, tmp_path):
        client = self._make_client("# README")
        generate_readme(client, str(tmp_path), "MY_BASE_PROMPT")
        call_kwargs = client.messages.create.call_args
        user_content = call_kwargs.kwargs["messages"][0]["content"]
        assert "MY_BASE_PROMPT" in user_content
