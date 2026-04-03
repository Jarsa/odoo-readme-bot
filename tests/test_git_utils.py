"""Tests for git_utils — mock subprocess, test diff parsing."""

from unittest.mock import MagicMock, patch

import pytest

from odoo_readme_bot import git_utils


class TestRun:
    def test_returns_stdout_on_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")
            result = git_utils.run(["git", "rev-parse", "HEAD"])
            assert result == "abc1234"

    def test_raises_on_nonzero_exit(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repo")
            with pytest.raises(RuntimeError, match="fatal: not a git repo"):
                git_utils.run(["git", "status"])


class TestGetCurrentSha:
    def test_returns_full_sha(self):
        with patch("odoo_readme_bot.git_utils.run") as mock_run:
            mock_run.return_value = "abcdef1234567890abcdef1234567890abcdef12"
            sha = git_utils.get_current_sha()
            assert sha == "abcdef1234567890abcdef1234567890abcdef12"


class TestHasChangesSince:
    def test_returns_true_when_sha_is_none(self):
        assert git_utils.has_changes_since(None, "some/module") is True

    def test_returns_true_when_diff_has_output(self):
        with patch("odoo_readme_bot.git_utils.run") as mock_run:
            mock_run.return_value = "some/module/models/sale.py"
            assert git_utils.has_changes_since("abc1234", "some/module") is True

    def test_returns_false_when_no_diff(self):
        with patch("odoo_readme_bot.git_utils.run") as mock_run:
            mock_run.return_value = ""
            assert git_utils.has_changes_since("abc1234", "some/module") is False

    def test_returns_true_on_run_failure(self):
        with patch("odoo_readme_bot.git_utils.run") as mock_run:
            mock_run.side_effect = RuntimeError("git error")
            assert git_utils.has_changes_since("abc1234", "some/module") is True


class TestGetDiffSince:
    def test_returns_truncated_diff(self):
        long_diff = "x" * 30_000
        with patch("odoo_readme_bot.git_utils.run") as mock_run:
            mock_run.return_value = long_diff
            result = git_utils.get_diff_since("abc1234", "module/path")
            assert len(result) == 20_000

    def test_returns_empty_string_on_failure(self):
        with patch("odoo_readme_bot.git_utils.run") as mock_run:
            mock_run.side_effect = RuntimeError("shallow clone")
            result = git_utils.get_diff_since("abc1234", "module/path")
            assert result == ""


class TestGetAllModules:
    def test_finds_manifest_directories(self, tmp_path):
        mod_a = tmp_path / "addons" / "module_a"
        mod_a.mkdir(parents=True)
        (mod_a / "__manifest__.py").touch()

        mod_b = tmp_path / "addons" / "module_b"
        mod_b.mkdir(parents=True)
        (mod_b / "__manifest__.py").touch()

        # Directory without manifest — should be excluded
        no_mod = tmp_path / "addons" / "not_a_module"
        no_mod.mkdir(parents=True)

        result = git_utils.get_all_modules(str(tmp_path))
        assert len(result) == 2
        assert any("module_a" in r for r in result)
        assert any("module_b" in r for r in result)
