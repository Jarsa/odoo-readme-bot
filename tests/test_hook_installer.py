"""Tests for hook_installer — install/uninstall post-commit hook."""

import os
import stat
import subprocess

from odoo_readme_bot.hook_installer import _HOOK_MARKER, install, is_installed, uninstall


def _make_git_repo(tmp_path):
    """Create a minimal git repo for testing."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    return str(tmp_path)


class TestIsInstalled:
    def test_returns_false_when_no_hook(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        assert is_installed(repo) is False

    def test_returns_false_when_hook_without_marker(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/bash\necho hello\n")
        assert is_installed(repo) is False

    def test_returns_true_after_install(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        install(repo)
        assert is_installed(repo) is True


class TestInstall:
    def test_creates_hook_file(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        install(repo)
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        assert hook.exists()

    def test_hook_is_executable(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        install(repo)
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        mode = os.stat(str(hook)).st_mode
        assert mode & stat.S_IXUSR

    def test_hook_contains_marker(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        install(repo)
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        assert _HOOK_MARKER in hook.read_text()

    def test_install_twice_is_idempotent(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        install(repo)
        install(repo)
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        content = hook.read_text()
        assert content.count(_HOOK_MARKER) == 1

    def test_preserves_existing_hook_content(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/bash\necho existing-hook\n")
        install(repo)
        content = hook.read_text()
        assert "existing-hook" in content
        assert _HOOK_MARKER in content

    def test_raises_when_not_a_git_repo(self, tmp_path):
        import pytest
        with pytest.raises(ValueError, match="no es un repositorio git"):
            install(str(tmp_path))


class TestUninstall:
    def test_removes_file_when_only_our_hook(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        install(repo)
        uninstall(repo)
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        assert not hook.exists()

    def test_preserves_other_content_on_uninstall(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook = tmp_path / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/bash\necho existing-hook\n")
        install(repo)
        uninstall(repo)
        assert hook.exists()
        content = hook.read_text()
        assert "existing-hook" in content
        assert _HOOK_MARKER not in content

    def test_uninstall_when_not_installed_is_safe(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        uninstall(repo)  # Should not raise
