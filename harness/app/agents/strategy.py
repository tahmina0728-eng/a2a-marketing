from __future__ import annotations
from app._standalone_agents import standalone_strategy
from app.agents._utils import _run_adk_sync


def run_strategy(brand: str, prompt: str) -> dict:
    data = _run_adk_sync(standalone_strategy, brand, prompt)
    return {"agent": "strategy", **data}
