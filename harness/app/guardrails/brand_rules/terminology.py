"""
brand_rules/terminology.py — Enforces brand-specific terminology.
e.g. Haleon uses "consumer" not "patient"; Barclays uses "colleague" not "employee".
Term mappings loaded from brand policy JSON.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register


class _TerminologyRule:
    name  = "brand.terminology"
    stage = "output"
    scope = "brand"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        policy  = context.get("brand_policy", {})
        avoid   = policy.get("avoid_terms", {})   # {"patient": "consumer", ...}
        if not avoid:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        text  = _all_text(payload)
        flags = []
        for wrong, correct in avoid.items():
            if re.search(rf"\b{re.escape(wrong)}\b", text, re.I):
                flags.append(Flag(
                    rule     = self.name,
                    severity = Severity.WARNING,
                    message  = f"Non-standard term: '{wrong}' — use '{correct}'",
                    span     = wrong,
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


register(_TerminologyRule())
