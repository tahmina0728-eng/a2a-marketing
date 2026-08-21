"""
campaign_rules/partnership.py — Validates partnership campaign content.
Ensures partner names are used correctly and co-branding guidelines are met.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register


class _PartnershipRule:
    name  = "campaign.partnership"
    stage = "output"
    scope = "campaign"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        policy   = context.get("brand_policy", {})
        partners = policy.get("approved_partners", [])
        moment   = str(context.get("moment_type", "")).lower()

        if "partnership" not in moment or not partners:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        text  = _all_text(payload)
        flags = []

        # Check that at least one approved partner is mentioned
        found = [p for p in partners if re.search(rf"\b{re.escape(p)}\b", text, re.I)]
        if not found:
            flags.append(Flag(
                rule     = self.name,
                severity = Severity.WARNING,
                message  = "Partnership campaign does not mention an approved partner",
                detail   = f"Approved partners: {', '.join(partners)}",
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


register(_PartnershipRule())
