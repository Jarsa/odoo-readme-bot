"""Call Claude Haiku to decide if a README update is warranted."""

import json
import logging

import anthropic

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = (
    "You are a technical documentation assistant. "
    "Analyze the provided git diff and README preview for an Odoo module. "
    "Respond ONLY with valid JSON, no markdown fences, no preamble."
)

_USER_TEMPLATE = """\
Git diff since last documentation:
{diff}

Current README (first 2000 chars):
{readme_preview}

Based on the diff above, does this module's README need to be updated?
Respond with JSON only:
{{"needs_update": true|false, "reason": "explanation in Spanish"}}
"""


def should_update(
    client: anthropic.Anthropic,
    diff: str,
    readme_preview: str,
) -> dict:
    """Call claude-haiku to decide if the README needs updating.

    Returns:
        {
            "needs_update": bool,
            "reason": "string in Spanish explaining the decision"
        }

    On JSON parse failure returns {"needs_update": True, "reason": "Error al analizar..."}.
    Never raises — always returns a safe default.
    """
    user_content = _USER_TEMPLATE.format(
        diff=diff or "(sin cambios detectados)",
        readme_preview=readme_preview[:2000],
    )
    try:
        response = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=150,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse Haiku JSON response: %s", exc)
        return {"needs_update": True, "reason": "Error al analizar la respuesta del modelo."}
    except Exception as exc:  # noqa: BLE001
        logger.error("Haiku API call failed: %s", exc)
        return {"needs_update": True, "reason": f"Error en la llamada al modelo: {exc}"}
