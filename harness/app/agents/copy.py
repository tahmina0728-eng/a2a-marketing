from __future__ import annotations
from app._standalone_agents import standalone_copy
from app.agents._utils import _run_adk_sync, _extract_language


def run_copy(brand: str, prompt: str) -> dict:
    lang = _extract_language(prompt)
    # Language override is appended to the user message so the ADK instruction
    # callable (which only reads brand context) doesn't need to know about it.
    if lang:
        user_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL LANGUAGE OVERRIDE: The user has explicitly selected '{lang}' as the output language. "
            f"ALL copy (headline, subline, body, cta) MUST be written entirely in {lang}. "
            f"This overrides any localisation requirements mentioned in the brand guidelines."
        )
    else:
        user_prompt = prompt

    data = _run_adk_sync(standalone_copy, brand, user_prompt)
    return {"agent": "copy", **data}
