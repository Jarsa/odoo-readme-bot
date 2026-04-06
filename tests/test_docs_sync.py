"""Tests for docs_sync — mock Google API service, test document building."""

from unittest.mock import MagicMock, patch

from odoo_readme_bot.docs_sync import build_combined_document, clear_and_update_doc


def _make_service(end_index: int) -> MagicMock:
    """Build a mock Google Docs service that reports *end_index* for the doc body."""
    service = MagicMock()
    doc_response = {"body": {"content": [{"endIndex": end_index}]}}
    service.documents().get().execute.return_value = doc_response
    return service


class TestClearAndUpdateDoc:
    def test_calls_batch_update(self):
        service = _make_service(end_index=100)
        clear_and_update_doc(service, "doc123", "Hello world")
        service.documents().batchUpdate.assert_called_once()

    def test_non_empty_doc_sends_delete_then_insert(self):
        service = _make_service(end_index=100)
        clear_and_update_doc(service, "doc123", "Hello world")

        call_args = service.documents().batchUpdate.call_args
        reqs = call_args.kwargs["body"]["requests"]
        assert len(reqs) == 2
        assert "deleteContentRange" in reqs[0]
        assert "insertText" in reqs[1]

    def test_empty_doc_skips_delete_step(self):
        # endIndex == 1 means completely empty doc
        service = _make_service(end_index=1)
        clear_and_update_doc(service, "doc123", "Hello world")

        call_args = service.documents().batchUpdate.call_args
        reqs = call_args.kwargs["body"]["requests"]
        assert len(reqs) == 1
        assert "insertText" in reqs[0]

    def test_single_char_doc_skips_delete_step(self):
        # endIndex == 2 means one character — delete range [1,1] would be empty, skip it
        service = _make_service(end_index=2)
        clear_and_update_doc(service, "doc123", "Hello world")

        call_args = service.documents().batchUpdate.call_args
        reqs = call_args.kwargs["body"]["requests"]
        assert len(reqs) == 1
        assert "insertText" in reqs[0]

    def test_delete_range_starts_at_index_1(self):
        service = _make_service(end_index=50)
        clear_and_update_doc(service, "doc123", "Content")

        call_args = service.documents().batchUpdate.call_args
        delete_range = call_args.kwargs["body"]["requests"][0]["deleteContentRange"]["range"]
        assert delete_range["startIndex"] == 1
        assert delete_range["endIndex"] == 49  # end_index - 1

    def test_insert_text_at_index_1(self):
        service = _make_service(end_index=10)
        clear_and_update_doc(service, "doc123", "My content")

        call_args = service.documents().batchUpdate.call_args
        insert_req = call_args.kwargs["body"]["requests"][-1]["insertText"]
        assert insert_req["location"]["index"] == 1
        assert "My content" in insert_req["text"]

    def test_content_without_trailing_newline_gets_one_appended(self):
        service = _make_service(end_index=10)
        clear_and_update_doc(service, "doc123", "No newline")

        call_args = service.documents().batchUpdate.call_args
        text = call_args.kwargs["body"]["requests"][-1]["insertText"]["text"]
        assert text.endswith("\n")

    def test_content_with_trailing_newline_not_doubled(self):
        service = _make_service(end_index=10)
        clear_and_update_doc(service, "doc123", "Has newline\n")

        call_args = service.documents().batchUpdate.call_args
        text = call_args.kwargs["body"]["requests"][-1]["insertText"]["text"]
        assert text == "Has newline\n"

    def test_passes_doc_id_to_get(self):
        service = _make_service(end_index=10)
        clear_and_update_doc(service, "my-doc-id", "Content")
        service.documents().get.assert_called_with(documentId="my-doc-id")

    def test_passes_doc_id_to_batch_update(self):
        service = _make_service(end_index=10)
        clear_and_update_doc(service, "my-doc-id", "Content")
        call_args = service.documents().batchUpdate.call_args
        assert call_args.kwargs["documentId"] == "my-doc-id"


class TestBuildCombinedDocument:
    def test_header_contains_client_name(self, tmp_path):
        result = build_combined_document([], str(tmp_path), "AcmeCorp")
        assert "# Documentación Técnica — AcmeCorp" in result

    def test_header_contains_module_count(self, tmp_path):
        result = build_combined_document(["mod_a", "mod_b"], str(tmp_path), "Client")
        assert "Módulos: 2" in result

    def test_header_contains_utc_timestamp(self, tmp_path):
        result = build_combined_document([], str(tmp_path), "Client")
        assert "UTC" in result

    def test_found_readme_included(self, tmp_path):
        mod_dir = tmp_path / "my_module"
        mod_dir.mkdir()
        (mod_dir / "README.md").write_text("# My Module\n\nDescription.", encoding="utf-8")

        result = build_combined_document(["my_module"], str(tmp_path), "Client")

        assert "# MÓDULO: my_module" in result
        assert "# My Module" in result
        assert "Description." in result

    def test_found_rst_readme_included(self, tmp_path):
        mod_dir = tmp_path / "oca_module"
        mod_dir.mkdir()
        (mod_dir / "README.rst").write_text("OCA Module\n==========\n\nDescription.", encoding="utf-8")

        result = build_combined_document(["oca_module"], str(tmp_path), "Client")

        assert "# MÓDULO: oca_module" in result
        assert "OCA Module" in result

    def test_md_takes_precedence_over_rst(self, tmp_path):
        mod_dir = tmp_path / "dual_module"
        mod_dir.mkdir()
        (mod_dir / "README.md").write_text("# MD README", encoding="utf-8")
        (mod_dir / "README.rst").write_text("RST README", encoding="utf-8")

        result = build_combined_document(["dual_module"], str(tmp_path), "Client")

        assert "# MD README" in result
        assert "RST README" not in result

    def test_missing_readme_shows_placeholder(self, tmp_path):
        result = build_combined_document(["missing_module"], str(tmp_path), "Client")

        assert "# MÓDULO: missing_module" in result
        assert "> Sin README disponible." in result

    def test_submodule_path_readme_found(self, tmp_path):
        nested = tmp_path / "addons" / "sub_module"
        nested.mkdir(parents=True)
        (nested / "README.md").write_text("# Sub Module README", encoding="utf-8")

        result = build_combined_document(["sub_module"], str(tmp_path), "Client")

        assert "# MÓDULO: sub_module" in result
        assert "# Sub Module README" in result

    def test_direct_path_takes_precedence_over_submodule(self, tmp_path):
        # Direct path
        direct = tmp_path / "mod"
        direct.mkdir()
        (direct / "README.md").write_text("# Direct README", encoding="utf-8")
        # Also in a subdirectory
        nested = tmp_path / "addons" / "mod"
        nested.mkdir(parents=True)
        (nested / "README.md").write_text("# Nested README", encoding="utf-8")

        result = build_combined_document(["mod"], str(tmp_path), "Client")

        assert "# Direct README" in result
        assert "# Nested README" not in result

    def test_module_sections_separated_by_divider(self, tmp_path):
        result = build_combined_document(["mod_a", "mod_b"], str(tmp_path), "Client")
        assert result.count("---") >= 2

    def test_empty_module_list_returns_only_header(self, tmp_path):
        result = build_combined_document([], str(tmp_path), "Client")
        assert "# Documentación Técnica" in result
        assert "MÓDULO" not in result
