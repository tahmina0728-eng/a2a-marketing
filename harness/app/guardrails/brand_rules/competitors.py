"""
brand_rules/competitors.py — Blocks competitor brand mentions in output copy.
Competitor lists are loaded from policies/brands/<brand>.json.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register


class _CompetitorRule:
    name  = "brand.competitors"
    stage = "output"
    scope = "brand"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        brand       = context.get("brand", "")
        competitors = context.get("brand_policy", {}).get("competitors", [])
        if not competitors:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        text  = _all_text(payload)
        flags = []
        for comp in competitors:
            if re.search(rf"\b{re.escape(comp)}\b", text, re.I):
                flags.append(Flag(
                    rule     = self.name,
                    severity = Severity.BLOCK,
                    message  = f"Competitor brand mentioned: '{comp}'",
                    detail   = f"Brand '{brand}' policy prohibits naming competitors",
                    span     = comp,
                ))
        if flags:
            return GuardrailResult(passed=False, action=Action.BLOCK, flags=flags)
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):    parts.append(v)
        elif isinstance(v, list): parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_CompetitorRule())
