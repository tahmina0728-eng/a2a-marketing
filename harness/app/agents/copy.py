from __future__ import annotations
from app.agents._utils import _generate, _extract_language


def run_copy(brand: str, prompt: str) -> dict:
    lang = _extract_language(prompt)
    lang_rule = (
        f" CRITICAL: ALL copy (headline, subline, body, cta) MUST be written in {lang}. "
        f"Do not write any English. Output only the JSON — no preamble, no explanation."
        if lang and lang.lower() != "english" else
        " Output only the JSON — no preamble, no explanation."
    )
    data = _generate(
        "You are Ideon, the copywriter for an AI marketing campaign system. "
        "You write campaign headlines and copy that sound like a human wrote them, not corporate marketing-speak.",
        brand, prompt,
        'Respond ONLY with valid JSON, no markdown fences, no commentary:' + lang_rule + ' '
        '{"headline": "...", "subline": "...", "body": "1-2 sentences", "cta": "2-3 words"}',
    )
    return {"agent": "copy", **data}
