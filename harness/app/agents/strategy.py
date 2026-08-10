from __future__ import annotations
from app.agents._utils import _generate


def run_strategy(brand: str, prompt: str) -> dict:
    data = _generate(
        "You are Helia, the creative strategist for an AI marketing campaign system. "
        "You turn a one-line creative direction into a campaign's Big Idea and strategic framework.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"hero_message": "the Big Idea, one punchy sentence", '
        '"strategic_framework": "2-3 sentences on the strategic approach", '
        '"messaging_pillars": ["pillar 1", "pillar 2", "pillar 3"]}',
    )
    return {"agent": "strategy", **data}
