from __future__ import annotations
from app.agents._utils import _generate


def run_culture(brand: str, prompt: str) -> dict:
    data = _generate(
        "You are Aether, the cultural intelligence researcher for an AI marketing campaign system. "
        "You identify cultural trends, moments, and audience behaviours relevant to a campaign.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"summary": "3-4 sentences of cultural insight relevant to this market and moment", '
        '"recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"]}',
    )
    return {"agent": "culture", **data}
