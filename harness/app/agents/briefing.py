from __future__ import annotations
from app.agents._utils import _generate


def run_briefing(brand: str, prompt: str) -> dict:
    data = _generate(
        "You are Logos, the briefing agent for an AI marketing campaign system. "
        "You validate a campaign idea against brand guidelines and give a quick quality read.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"goal": "...", "product": "...", "fan_truth": "the human insight behind this, one sentence", '
        '"audience": "who this is for, one phrase", "market": "...", "season": "...", '
        '"score": <integer 0-100>, "verdict": "PASS or NEEDS WORK", '
        '"summary": "1-2 sentence rationale for the score"}',
    )
    return {"agent": "briefing", **data}
