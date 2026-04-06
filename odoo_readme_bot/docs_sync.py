"""Google Docs API integration using a service account."""

import base64
import glob as glob_module
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/documents"]


def build_service(credentials_b64: str) -> Any:
    """
    Build and return a Google Docs API service object.

    credentials_b64: base64-encoded JSON of the service account credentials.
    """
    creds_json = base64.b64decode(credentials_b64).decode("utf-8")
    creds_dict = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=_SCOPES
    )
    return build("docs", "v1", credentials=credentials)


def clear_and_update_doc(service: Any, doc_id: str, content: str) -> None:
    """
    Clear the Google Doc body and replace it with *content*.

    Never deletes index 0. Trailing newline is always preserved.
    """
    doc = service.documents().get(documentId=doc_id).execute()
    body_content = doc.get("body", {}).get("content", [])
    end_index = body_content[-1].get("endIndex", 1) if body_content else 1

    requests_list: list[dict] = []
    if end_index > 2:
        requests_list.append(
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": end_index - 1,
                    }
                }
            }
        )

    if not content.endswith("\n"):
        content += "\n"

    requests_list.append(
        {
            "insertText": {
                "location": {"index": 1},
                "text": content,
            }
        }
    )

    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests_list},
    ).execute()


def build_combined_document(
    module_names: list[str], repo_root: str, client_name: str
) -> str:
    """
    Build a combined markdown document from multiple module READMEs.

    Header includes client name, module count, and UTC timestamp.
    Each module section is separated by `---`.
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    n = len(module_names)

    parts = [
        f"# Documentación Técnica — {client_name}",
        "> Generado automáticamente por odoo-readme-bot",
        f"> Módulos: {n} | Actualizado: {timestamp} UTC",
        "",
    ]

    for module_name in module_names:
        parts.append("---")
        parts.append(f"# MÓDULO: {module_name}")
        parts.append("")

        readme_path = _find_readme(module_name, repo_root)
        if readme_path:
            with open(readme_path, "r", encoding="utf-8") as fh:
                readme_content = fh.read()
            parts.append(readme_content)
        else:
            parts.append("> Sin README disponible.")
            parts.append("")

    return "\n".join(parts)


def _find_readme(module_name: str, repo_root: str) -> str | None:
    """Return the path to the module's README (md or rst), or None if not found."""
    for filename in ("README.md", "README.rst"):
        direct = os.path.join(repo_root, module_name, filename)
        if os.path.isfile(direct):
            return direct

    for filename in ("README.md", "README.rst"):
        pattern = os.path.join(repo_root, "**", module_name, filename)
        matches = glob_module.glob(pattern, recursive=True)
        if matches:
            return matches[0]

    return None
