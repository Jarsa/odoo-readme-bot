"""Tests for detector — mock git output, test module detection."""

from unittest.mock import patch

from odoo_readme_bot import detector


class TestGetModulesNeedingReview:
    def test_returns_empty_when_no_modules(self):
        with patch("odoo_readme_bot.detector.git_utils.get_all_modules", return_value=[]):
            result = detector.get_modules_needing_review()
            assert result == []

    def test_excludes_modules_without_changes(self):
        with (
            patch("odoo_readme_bot.detector.git_utils.get_all_modules", return_value=["mod_a"]),
            patch("odoo_readme_bot.detector.readme_utils.get_documented_sha", return_value="abc1234"),
            patch("odoo_readme_bot.detector.git_utils.has_changes_since", return_value=False),
        ):
            result = detector.get_modules_needing_review()
            assert result == []

    def test_includes_modules_with_changes(self):
        with (
            patch("odoo_readme_bot.detector.git_utils.get_all_modules", return_value=["mod_a"]),
            patch("odoo_readme_bot.detector.readme_utils.get_documented_sha", return_value="abc1234"),
            patch("odoo_readme_bot.detector.git_utils.has_changes_since", return_value=True),
            patch("odoo_readme_bot.detector._get_changed_files", return_value=["models/sale.py"]),
        ):
            result = detector.get_modules_needing_review()
            assert len(result) == 1
            assert result[0]["path"] == "mod_a"
            assert result[0]["last_sha"] == "abc1234"
            assert "models/sale.py" in result[0]["changed_files"]

    def test_never_documented_module_always_included(self):
        with (
            patch("odoo_readme_bot.detector.git_utils.get_all_modules", return_value=["new_mod"]),
            patch("odoo_readme_bot.detector.readme_utils.get_documented_sha", return_value=None),
            patch("odoo_readme_bot.detector.git_utils.has_changes_since", return_value=True),
            patch("odoo_readme_bot.detector._get_changed_files", return_value=[]),
        ):
            result = detector.get_modules_needing_review()
            assert len(result) == 1
            assert result[0]["last_sha"] is None
