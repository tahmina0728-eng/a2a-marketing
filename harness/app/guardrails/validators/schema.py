"""
validators/schema.py — Validates agent output against the expected schema
for each agent type. Blocks handoffs with missing required fields.
"""
from __future__ import annotations

from ..models import GuardrailResult, Flag, Severity, Action

_REQUIRED_FIELDS: dict[str, list[str]] = {
    "briefing":     ["goal", "audience", "market", "fan_truth", "verdict"],
    "strategy":     ["campaign_concept", "key_messages", "channels"],
    "copy":         ["headline", "body", "cta"],
    "culture":      ["summary", "recommendations"],
    "channel":      ["channels", "rationale"],
    "performance":  ["kpis"],
}


def validate_schema(agent: str, payload: dict) -> GuardrailResult:
    required = _REQUIRED_FIELDS.get(agent, [])
    missing  = [f for f in required if not payload.get(f)]
    if not missing:
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)
    return GuardrailResult(
        passed = False,
        action = Action.BLOCK,
        flags  = [Flag(
            rule     = "validator.schema",
            severity = Severity.BLOCK,
            message  = f"Agent '{agent}' output missing required fields: {missing}",
        )],
    )
