from __future__ import annotations
from app._standalone_agents import standalone_culture
from app.agents._utils import _run_adk_sync


def run_culture(brand: str, prompt: str) -> dict:
    data = _run_adk_sync(standalone_culture, brand, prompt)
    return {"agent": "culture", **data}
