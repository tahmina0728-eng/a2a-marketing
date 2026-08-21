"""
brand_rules/claims.py — Detects unsubstantiated superlatives and claims
that require legal sign-off (e.g. "#1", "best in class", "clinically proven").
HITL for regulated industries (pharma, finance, alcohol).
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

_SUPERLATIVES = [
    r"\bworld'?s?\s+(?:best|leading|first|only|largest|fastest)\b",
    r"\b#1\b",
    r"\bnumber\s+one\b",
    r"\bclinically\s+(?:proven|tested|validated)\b",
    r"\bguaranteed\b",
    r"\b100%\s+(?:safe|effective|natural|organic)\b",
    r"\bno\s+(?:side effects|risk|downsides)\b",
]

_REGULATED_INDUSTRIES = {"pharma", "healthcare", "finance", "banking", "alcohol", "gambling"}


class _ClaimsRule:
    name  = "brand.claims"
    stage = "output"
    scope = "brand"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        text     = _all_text(payload)
        industry = context.get("brand_policy", {}).get("industry", "").lower()
        flags    = []

        for pattern in _SUPERLATIVES:
            m = re.search(pattern, text, re.I)
            if m:
                flags.append(Flag(
                    rule     = self.name,
                    severity = Severity.WARNING,
                    message  = "Unsubstantiated claim detected",
                    detail   = "Requires legal review before publication",
                    span     = m.group(0)[:80],
                ))

        if not flags:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        # Regulated industries → route to human reviewer
        action = Action.HITL if industry in _REGULATED_INDUSTRIES else Action.WARN
        return GuardrailResult(passed=False, action=action, flags=flags)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):    parts.append(v)
        elif isinstance(v, list): parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_ClaimsRule())
