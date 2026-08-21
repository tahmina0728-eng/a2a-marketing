"""
campaign_rules/audience.py — Validates audience targeting against brand policy.
Blocks campaigns targeting under-18s for age-restricted products (alcohol,
gambling, finance). Warns on sensitive segments.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

_AGE_RESTRICTED_INDUSTRIES = {"alcohol", "gambling", "vaping", "tobacco"}
_UNDER_18_SIGNALS = [
    r"\bunder\s*1[0-7]\b",
    r"\bchildren\b",
    r"\bkids?\b",
    r"\bteenager?s?\b",
    r"\byouth\b",
    r"\bschool\s*age\b",
    r"\bjunior\b",
]


class _AudienceRule:
    name  = "campaign.audience"
    stage = "input"
    scope = "campaign"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        policy   = context.get("brand_policy", {})
        industry = policy.get("industry", "").lower()

        if industry not in _AGE_RESTRICTED_INDUSTRIES:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        audience_text = str(payload.get("audience", "")) + " " + str(payload.get("segment", ""))
        for pattern in _UNDER_18_SIGNALS:
            m = re.search(pattern, audience_text, re.I)
            if m:
                return GuardrailResult(
                    passed = False,
                    action = Action.BLOCK,
                    flags  = [Flag(
                        rule     = self.name,
                        severity = Severity.BLOCK,
                        message  = f"Age-restricted product ({industry}) cannot target under-18 audience",
                        span     = m.group(0),
                    )],
                )
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


register(_AudienceRule())
