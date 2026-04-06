"""Tests for odoo_client — mock requests.post, test module list extraction."""

from unittest.mock import MagicMock, patch

import requests

from odoo_readme_bot.odoo_client import get_installed_custom_modules


def _make_response(result: dict) -> MagicMock:
    """Build a mock response that returns the given result dict."""
    response = MagicMock()
    response.json.return_value = {"result": result}
    response.raise_for_status = MagicMock()
    return response


class TestGetInstalledCustomModules:
    def test_happy_path_returns_module_list(self):
        mock_response = _make_response({"module_a": {}, "module_b": {}})
        with patch("odoo_readme_bot.odoo_client.requests.post", return_value=mock_response):
            result = get_installed_custom_modules("http://example.com")
        assert set(result) == {"module_a", "module_b"}

    def test_happy_path_posts_to_correct_url(self):
        mock_response = _make_response({"mod": {}})
        with patch("odoo_readme_bot.odoo_client.requests.post", return_value=mock_response) as mock_post:
            get_installed_custom_modules("http://example.com")
        mock_post.assert_called_once()
        called_url = mock_post.call_args.args[0]
        assert called_url == "http://example.com/odoo_cloc/webhook/"

    def test_trailing_slash_in_url_not_duplicated(self):
        mock_response = _make_response({"mod": {}})
        with patch("odoo_readme_bot.odoo_client.requests.post", return_value=mock_response) as mock_post:
            get_installed_custom_modules("http://example.com/")
        called_url = mock_post.call_args.args[0]
        assert called_url == "http://example.com/odoo_cloc/webhook/"

    def test_connection_error_returns_empty(self):
        with patch(
            "odoo_readme_bot.odoo_client.requests.post",
            side_effect=requests.ConnectionError("refused"),
        ):
            result = get_installed_custom_modules("http://example.com")
        assert result == []

    def test_timeout_returns_empty(self):
        with patch(
            "odoo_readme_bot.odoo_client.requests.post",
            side_effect=requests.Timeout("timed out"),
        ):
            result = get_installed_custom_modules("http://example.com")
        assert result == []

    def test_malformed_json_no_result_key_returns_empty(self):
        response = MagicMock()
        response.json.return_value = {"error": "not found"}
        response.raise_for_status = MagicMock()
        with patch("odoo_readme_bot.odoo_client.requests.post", return_value=response):
            result = get_installed_custom_modules("http://example.com")
        assert result == []

    def test_http_error_returns_empty(self):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("500")
        with patch("odoo_readme_bot.odoo_client.requests.post", return_value=response):
            result = get_installed_custom_modules("http://example.com")
        assert result == []
