"""Configure GitLab pipeline schedules and commit files via the GitLab REST API.

No extra dependencies — uses only urllib from the standard library.
"""

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_DEFAULT_CRON = "0 12 * * 1-5"          # Mon–Fri 6 am Torreón (UTC-6 = 12 UTC)
_DEFAULT_TIMEZONE = "America/Monterrey"
_SCHEDULE_DESCRIPTION = "odoo-readme-bot: auto-update READMEs"


def _api_request(
    host: str,
    token: str,
    method: str,
    path: str,
    body: dict | None = None,
) -> dict:
    """Perform a GitLab API request and return the parsed JSON response."""
    url = f"https://{host}/api/v4{path}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Private-Token": token,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            detail = json.loads(raw)
            msg = detail.get("error_description") or detail.get("message") or raw
        except json.JSONDecodeError:
            msg = raw
        raise RuntimeError(f"GitLab API {exc.code} {exc.reason}: {msg}") from None


def _project_id(host: str, token: str, project_path: str) -> int:
    """Resolve a project path like 'Jarsa/starka' to its numeric GitLab ID."""
    encoded = urllib.parse.quote(project_path, safe="")
    project = _api_request(host, token, "GET", f"/projects/{encoded}")
    return project["id"]


def _list_schedules(host: str, token: str, project_id: int) -> list[dict]:
    """Return all existing pipeline schedules for the project."""
    return _api_request(host, token, "GET", f"/projects/{project_id}/pipeline_schedules")


def _file_exists(host: str, token: str, project_id: int, branch: str, file_path: str) -> bool:
    """Return True if file_path exists in the repo at the given branch."""
    encoded_file = urllib.parse.quote(file_path, safe="")
    encoded_branch = urllib.parse.quote(branch, safe="")
    try:
        _api_request(
            host, token, "GET",
            f"/projects/{project_id}/repository/files/{encoded_file}?ref={encoded_branch}",
        )
        return True
    except RuntimeError:
        return False


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def preflight(host: str, token: str, project_path: str, branch: str) -> int:
    """Verify API credentials and branch existence before generating READMEs.

    Returns the numeric project ID on success.
    Raises RuntimeError with a descriptive message on any failure.
    """
    logger.info("Preflight: verificando acceso a %s / %s (rama: %s)", host, project_path, branch)
    pid = _project_id(host, token, project_path)
    encoded_branch = urllib.parse.quote(branch, safe="")
    _api_request(host, token, "GET", f"/projects/{pid}/repository/branches/{encoded_branch}")
    logger.info("Preflight OK — project_id=%s, rama '%s' encontrada.", pid, branch)
    return pid


# ---------------------------------------------------------------------------
# Commit via API
# ---------------------------------------------------------------------------

def commit_files(
    host: str,
    token: str,
    project_id: int,
    branch: str,
    readme_paths: list[str],
    commit_message: str,
    repo_root: str = ".",
) -> dict:
    """Commit README files to GitLab using the Commits API.

    Uses the GitLab API instead of git push, which works even when HTTP git
    access is disabled on the server (only SSH is allowed).

    readme_paths: list of relative paths like ["module_a/README.md", ...]
    repo_root: local directory where the files are (CI_PROJECT_DIR)

    Returns the commit dict from the GitLab API.
    """
    actions = []
    for rel_path in readme_paths:
        local_path = os.path.join(repo_root, rel_path)
        with open(local_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        action = "update" if _file_exists(host, token, project_id, branch, rel_path) else "create"
        actions.append({
            "action": action,
            "file_path": rel_path,
            "content": content,
            "encoding": "text",
        })
        logger.debug("%s %s", action, rel_path)

    result = _api_request(
        host, token, "POST",
        f"/projects/{project_id}/repository/commits",
        body={
            "branch": branch,
            "commit_message": commit_message,
            "actions": actions,
        },
    )
    logger.info("Commit creado via API: %s", result.get("short_id", result.get("id")))
    return result


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

def configure_schedule(
    host: str,
    token: str,
    project_path: str,
    branch: str = "main",
    cron: str = _DEFAULT_CRON,
    timezone: str = _DEFAULT_TIMEZONE,
    force: bool = False,
) -> dict:
    """Create (or update) the odoo-readme-bot pipeline schedule in a GitLab project.

    If a schedule with our description already exists and force=False, returns it
    unchanged. With force=True, the existing schedule is deleted and recreated.

    Returns the schedule dict as returned by the GitLab API.
    """
    pid = _project_id(host, token, project_path)
    existing = [
        s for s in _list_schedules(host, token, pid)
        if s.get("description") == _SCHEDULE_DESCRIPTION
    ]

    if existing and not force:
        schedule = existing[0]
        logger.info(
            "Schedule ya existe (id=%s) en %s — sin cambios. "
            "Usa --force para recrearlo.",
            schedule["id"],
            project_path,
        )
        return schedule

    for s in existing:
        _api_request(host, token, "DELETE", f"/projects/{pid}/pipeline_schedules/{s['id']}")
        logger.debug("Schedule id=%s eliminado.", s["id"])

    schedule = _api_request(
        host,
        token,
        "POST",
        f"/projects/{pid}/pipeline_schedules",
        body={
            "description": _SCHEDULE_DESCRIPTION,
            "ref": branch,
            "cron": cron,
            "cron_timezone": timezone,
            "active": True,
        },
    )
    logger.info(
        "Schedule creado (id=%s) en %s — cron: %s %s",
        schedule["id"],
        project_path,
        cron,
        timezone,
    )
    return schedule
