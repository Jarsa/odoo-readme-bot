"""Tests for gitlab_configurator — mock urllib, test schedule creation."""

import json
from unittest.mock import MagicMock, patch

from odoo_readme_bot.gitlab_configurator import commit_files, configure_schedule, preflight


def _mock_response(data: dict, status: int = 200):
    """Create a mock urllib response."""
    body = json.dumps(data).encode()
    mock = MagicMock()
    mock.read.return_value = body
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _patch_urlopen(responses: list[dict]):
    """Patch urllib.request.urlopen to return a sequence of responses."""
    mocks = [_mock_response(r) for r in responses]
    return patch("odoo_readme_bot.gitlab_configurator.urllib.request.urlopen", side_effect=mocks)


class TestConfigureSchedule:
    def test_creates_schedule_when_none_exists(self):
        project = {"id": 42}
        schedules = []
        new_schedule = {
            "id": 99,
            "description": "odoo-readme-bot: auto-update READMEs",
            "ref": "main",
            "cron": "0 12 * * 1-5",
            "cron_timezone": "America/Monterrey",
            "active": True,
        }
        with _patch_urlopen([project, schedules, new_schedule]):
            result = configure_schedule(
                host="gitlab.com",
                token="glpat-test",
                project_path="Jarsa/starka",
            )
        assert result["id"] == 99
        assert result["active"] is True

    def test_returns_existing_schedule_without_force(self):
        project = {"id": 42}
        existing = [
            {
                "id": 77,
                "description": "odoo-readme-bot: auto-update READMEs",
                "ref": "main",
                "cron": "0 12 * * 1-5",
                "cron_timezone": "America/Monterrey",
                "active": True,
            }
        ]
        with _patch_urlopen([project, existing]):
            result = configure_schedule(
                host="gitlab.com",
                token="glpat-test",
                project_path="Jarsa/starka",
                force=False,
            )
        assert result["id"] == 77

    def test_recreates_schedule_with_force(self):
        project = {"id": 42}
        existing = [
            {
                "id": 77,
                "description": "odoo-readme-bot: auto-update READMEs",
                "ref": "main",
                "cron": "0 12 * * 1-5",
                "cron_timezone": "America/Monterrey",
                "active": True,
            }
        ]
        deleted = {}
        new_schedule = {
            "id": 88,
            "description": "odoo-readme-bot: auto-update READMEs",
            "ref": "main",
            "cron": "0 12 * * 1-5",
            "cron_timezone": "America/Monterrey",
            "active": True,
        }
        with _patch_urlopen([project, existing, deleted, new_schedule]):
            result = configure_schedule(
                host="gitlab.com",
                token="glpat-test",
                project_path="Jarsa/starka",
                force=True,
            )
        assert result["id"] == 88

    def test_uses_custom_cron_and_branch(self):
        project = {"id": 42}
        schedules = []
        new_schedule = {
            "id": 55,
            "description": "odoo-readme-bot: auto-update READMEs",
            "ref": "17.0",
            "cron": "0 8 * * 1-5",
            "cron_timezone": "America/Monterrey",
            "active": True,
        }
        with _patch_urlopen([project, schedules, new_schedule]) as mock_open:
            configure_schedule(
                host="git.jarsa.com",
                token="glpat-test",
                project_path="Jarsa/cliente",
                branch="17.0",
                cron="0 8 * * 1-5",
            )
        # Verify the POST body contained correct branch and cron
        post_call = mock_open.call_args_list[2]
        req = post_call.args[0]
        body = json.loads(req.data.decode())
        assert body["ref"] == "17.0"
        assert body["cron"] == "0 8 * * 1-5"


class TestPreflight:
    def test_returns_project_id_on_success(self):
        project = {"id": 42}
        branch_info = {"name": "17.0"}
        with _patch_urlopen([project, branch_info]):
            pid = preflight("git.jarsa.com", "glpat-test", "Jarsa/starka", "17.0")
        assert pid == 42

    def test_raises_on_invalid_token(self):
        import pytest
        import urllib.error

        def raise_401(*args, **kwargs):
            err = urllib.error.HTTPError(
                url="", code=401, msg="Unauthorized",
                hdrs=None, fp=None,
            )
            err.read = lambda: b'{"message":"401 Unauthorized"}'
            raise err

        with patch("odoo_readme_bot.gitlab_configurator.urllib.request.urlopen", side_effect=raise_401):
            with pytest.raises(RuntimeError, match="401"):
                preflight("git.jarsa.com", "bad-token", "Jarsa/starka", "17.0")

    def test_raises_on_branch_not_found(self):
        import pytest
        import urllib.error

        err_404 = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs=None, fp=None,
        )
        err_404.read = lambda: b'{"message":"404 Branch Not Found"}'

        with patch(
            "odoo_readme_bot.gitlab_configurator.urllib.request.urlopen",
            side_effect=[_mock_response({"id": 42}), err_404],
        ):
            with pytest.raises(RuntimeError, match="404"):
                preflight("git.jarsa.com", "glpat-test", "Jarsa/starka", "nonexistent")


class TestCommitFiles:
    def test_creates_commit_with_correct_actions(self, tmp_path):
        # Write a fake README file
        readme = tmp_path / "my_module" / "README.md"
        readme.parent.mkdir()
        readme.write_text("# My Module\n")

        # file_exists check returns False (create action)
        file_not_found = {"message": "404 Not Found"}
        commit_result = {"id": "abc123def456", "short_id": "abc123de"}

        import urllib.error

        def urlopen_side_effect(req):
            url = req.full_url
            if "/repository/files/" in url:
                err = urllib.error.HTTPError(
                    url=url, code=404, msg="Not Found", hdrs=None, fp=None,
                )
                err.read = lambda: json.dumps(file_not_found).encode()
                raise err
            return _mock_response(commit_result)

        with patch(
            "odoo_readme_bot.gitlab_configurator.urllib.request.urlopen",
            side_effect=urlopen_side_effect,
        ) as mock_open:
            result = commit_files(
                host="git.jarsa.com",
                token="glpat-test",
                project_id=42,
                branch="17.0",
                readme_paths=["my_module/README.md"],
                commit_message="docs: update README",
                repo_root=str(tmp_path),
            )

        assert result["short_id"] == "abc123de"
        # Verify the commit POST body
        post_call = mock_open.call_args_list[-1]
        req = post_call.args[0]
        body = json.loads(req.data.decode())
        assert body["branch"] == "17.0"
        assert body["actions"][0]["action"] == "create"
        assert body["actions"][0]["file_path"] == "my_module/README.md"
        assert "# My Module" in body["actions"][0]["content"]
