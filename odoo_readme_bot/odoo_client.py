"""Odoo webhook client for querying installed custom modules."""

import logging

import requests

TIMEOUT_SECONDS = 30
logger = logging.getLogger(__name__)


def get_installed_custom_modules(odoo_url: str) -> list[str]:
    """
    Call the odoo_cloc webhook and return the list of installed custom module names.

    Returns [] on any error (connection failure, timeout, bad response) — never raises.
    """
    url = f"{odoo_url.rstrip('/')}/odoo_cloc/webhook/"
    payload = {"jsonrpc": "2.0", "method": "call", "params": {}}
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        result = data["result"]
        return list(result.keys())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error al consultar odoo_cloc webhook (%s): %s", url, exc)
        return []
