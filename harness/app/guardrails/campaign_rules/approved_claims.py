"""
campaign_rules/approved_claims.py — Verifies that factual claims in outputs
appear in the brand's approved-claims list (loaded from brand policy JSON).
Unapproved claims in regulated industries trigger HITL.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

_REGULATED = {"pharma", "healthcare", "finance", "banking", "alcohol"}


class _ApprovedClaimsRule:
    name  = "campaign.approved_claims"
    stage = "output"
    scope = "campaign"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        policy         = context.get("brand_policy", {})
        approved       = policy.get("approved_claims", [])
        industry       = policy.get("industry", "").lower()

        if not approved:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        text  = _all_text(payload)
        flags = []

        # Flag sentences containing claim-like language not in approved list
        claim_sentences = re.findall(r"[^.!?]*(?:proven|guaranteed|certified|endorsed|#1|award)[^.!?]*[.!?]?", text, re.I)
        for sentence in claim_sentences:
            sentence = sentence.strip()
            if not any(a.lower() in sentence.lower() for a in approved):
                flags.append(Flag(
                    rule     = self.name,
                    severity = Severity.WARNING,
                    message  = "Claim not found in approved-claims list",
                    detail   = sentence[:120],
                    span     = sentence[:60],
                ))

        if not flags:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        action = Action.HITL if industry in _REGULATED else Action.WARN
        return GuardrailResult(passed=False, action=action, flags=flags)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):    parts.append(v)
        elif isinstance(v, list): parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_ApprovedClaimsRule())
