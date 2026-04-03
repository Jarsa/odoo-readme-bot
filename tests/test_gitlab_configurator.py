"""Tests for gitlab_configurator — mock urllib, test schedule creation."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from odoo_readme_bot.gitlab_configurator import configure_schedule


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
