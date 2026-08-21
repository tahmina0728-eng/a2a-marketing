"""
brand_rules/tone.py — Checks output copy against brand tone-of-voice rules.
Flags banned words/phrases and warns on required tone attributes.
Banned phrases come from policies/brands/<brand>.json.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register


class _ToneRule:
    name  = "brand.tone"
    stage = "output"
    scope = "brand"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        policy      = context.get("brand_policy", {})
        banned      = policy.get("banned_phrases", [])
        if not banned:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        text  = _all_text(payload)
        flags = []
        for phrase in banned:
            if re.search(rf"\b{re.escape(phrase)}\b", text, re.I):
                flags.append(Flag(
                    rule     = self.name,
                    severity = Severity.WARNING,
                    message  = f"Banned phrase detected: '{phrase}'",
                    detail   = "Off-brand language for this brand's tone of voice",
                    span     = phrase,
                ))
        if flags:
            return GuardrailResult(passed=False, action=Action.WARN, flags=flags)
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):    parts.append(v)
        elif isinstance(v, list): parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_ToneRule())
