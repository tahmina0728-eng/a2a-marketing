"""
validators/handoff.py — Validates agent-to-agent handoff payloads.
Ensures the receiving agent gets all data it needs before execution starts.
"""
from __future__ import annotations

from ..models import GuardrailResult, Flag, Severity, Action

# Map: (from_agent, to_agent) → fields that MUST be present in the handoff
_HANDOFF_REQUIREMENTS: dict[tuple[str, str], list[str]] = {
    ("briefing",  "strategy"):    ["goal", "audience", "market", "fan_truth"],
    ("strategy",  "copy"):        ["campaign_concept", "key_messages", "channels"],
    ("strategy",  "culture"):     ["campaign_concept", "audience", "market"],
    ("copy",      "channel"):     ["headline", "body", "cta"],
    ("briefing",  "morphis"):     ["goal", "audience", "fan_truth"],
    ("strategy",  "kinetik"):     ["campaign_concept", "channels"],
    ("copy",      "performance"): ["headline", "cta", "channels"],
}


def validate_handoff(from_agent: str, to_agent: str, payload: dict) -> GuardrailResult:
    key      = (from_agent, to_agent)
    required = _HANDOFF_REQUIREMENTS.get(key, [])
    missing  = [f for f in required if not payload.get(f)]
    if not missing:
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)
    return GuardrailResult(
        passed = False,
        action = Action.BLOCK,
        flags  = [Flag(
            rule     = "validator.handoff",
            severity = Severity.BLOCK,
            message  = f"Handoff {from_agent}→{to_agent} missing fields: {missing}",
            detail   = "Receiving agent cannot proceed without these fields",
        )],
    )
