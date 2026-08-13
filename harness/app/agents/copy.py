from __future__ import annotations
from app.agents._utils import _generate, _extract_language


def run_copy(brand: str, prompt: str) -> dict:
    lang = _extract_language(prompt)
    # Always emit a language rule when the user explicitly selected one — including English.
    # Without this, brand guidelines that mention regional localisation (e.g. Sunrise's
    # "German / French / Italian for Swiss market") override the user's language choice.
    if lang:
        lang_rule = (
            f" CRITICAL LANGUAGE OVERRIDE: The user has explicitly selected '{lang}' as the output language. "
            f"ALL copy (headline, subline, body, cta) MUST be written entirely in {lang}. "
            f"This instruction overrides any localisation requirements mentioned in the brand guidelines. "
            f"Output only the JSON — no preamble, no explanation."
        )
    else:
        lang_rule = " Output only the JSON — no preamble, no explanation."
    data = _generate(
        "You are Ideon, the copywriter for an AI marketing campaign system. "
        "You write campaign headlines and copy that sound like a human wrote them, not corporate marketing-speak.",
        brand, prompt,
        'Respond ONLY with valid JSON, no markdown fences, no commentary:' + lang_rule + ' '
        '{"headline": "...", "subline": "...", "body": "1-2 sentences", "cta": "2-3 words"}',
    )
    return {"agent": "copy", **data}
