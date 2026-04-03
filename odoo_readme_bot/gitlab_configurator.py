"""Configure GitLab pipeline schedules via the GitLab REST API.

No extra dependencies — uses only urllib from the standard library.
"""

import json
import logging
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
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _project_id(host: str, token: str, project_path: str) -> int:
    """Resolve a project path like 'Jarsa/starka' to its numeric GitLab ID."""
    encoded = urllib.parse.quote(project_path, safe="")
    project = _api_request(host, token, "GET", f"/projects/{encoded}")
    return project["id"]


def _list_schedules(host: str, token: str, project_id: int) -> list[dict]:
    """Return all existing pipeline schedules for the project."""
    return _api_request(host, token, "GET", f"/projects/{project_id}/pipeline_schedules")


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

    # Delete stale schedule(s) if force or duplicate
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
