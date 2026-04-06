"""Tests for readme_utils — SHA read/write and tag pattern matching."""

import os
import tempfile

from odoo_readme_bot.readme_utils import SHA_PATTERN, get_documented_sha, write_sha_to_readme


class TestShaPattern:
    def test_matches_standard_tag(self):
        tag = "<!-- odoo-docs: last-commit=abc1234f | updated=2025-04-01 -->"
        match = SHA_PATTERN.search(tag)
        assert match is not None
        assert match.group(1) == "abc1234f"

    def test_matches_full_sha(self):
        tag = "<!-- odoo-docs: last-commit=abcdef1234567890abcdef1234567890abcdef12 | updated=2025-04-01 -->"
        match = SHA_PATTERN.search(tag)
        assert match is not None
        assert match.group(1) == "abcdef1234567890abcdef1234567890abcdef12"

    def test_no_match_on_plain_text(self):
        assert SHA_PATTERN.search("# Some README content") is None

    def test_matches_within_larger_document(self):
        content = "# Module\n\nSome content.\n\n<!-- odoo-docs: last-commit=deadbeef | updated=2025-01-15 -->\n"
        match = SHA_PATTERN.search(content)
        assert match is not None
        assert match.group(1) == "deadbeef"


class TestGetDocumentedSha:
    def test_returns_none_when_readme_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_documented_sha(tmpdir)
            assert result is None

    def test_returns_none_when_no_tag_in_readme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            readme = os.path.join(tmpdir, "README.md")
            with open(readme, "w") as fh:
                fh.write("# Module\n\nNo SHA tag here.\n")
            result = get_documented_sha(tmpdir)
            assert result is None

    def test_returns_sha_when_tag_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            readme = os.path.join(tmpdir, "README.md")
            with open(readme, "w") as fh:
                fh.write("# Module\n\n<!-- odoo-docs: last-commit=cafe1234 | updated=2025-04-01 -->\n")
            result = get_documented_sha(tmpdir)
            assert result == "cafe1234"


class TestWriteShaToReadme:
    def test_appends_tag_when_none_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = "# Module\n\nSome content.\n"
            write_sha_to_readme(tmpdir, "abc12345", content)
            readme = os.path.join(tmpdir, "README.md")
            with open(readme) as fh:
                result = fh.read()
            assert "abc12345" in result
            assert "odoo-docs:" in result

    def test_replaces_existing_tag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = "# Module\n\n<!-- odoo-docs: last-commit=aabbcc00 | updated=2024-01-01 -->\n"
            write_sha_to_readme(tmpdir, "ddeeff11", content)
            result = get_documented_sha(tmpdir)
            assert result == "ddeeff11"

    def test_tag_is_last_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = "# Module\n\nContent here.\n"
            write_sha_to_readme(tmpdir, "abc12345", content)
            readme = os.path.join(tmpdir, "README.md")
            with open(readme) as fh:
                lines = fh.read().splitlines()
            last_non_empty = [line for line in lines if line.strip()][-1]
            assert "odoo-docs:" in last_non_empty
