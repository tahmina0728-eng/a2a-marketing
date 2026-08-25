"""
brand_rules/analyst_citations.py — Blocks unprotected analyst firm citations.

Infosys legal policy: no analyst firm name (Gartner, Forrester, IDC, etc.) may
appear in published copy without a corresponding [APPROVED_ANALYST_CITATION] token
from the Analyst Relations team. Without it the claim is unverified and cannot be
used in marketing materials.

Rule behaviour:
  - Scans output for any string that names an analyst firm from the brand policy
  - If found AND no [APPROVED_ANALYST_CITATION] token appears in the same output →
    Action.HITL (routes to Analyst Relations + Legal for sign-off)
  - If the token IS present → pass (the claim has been approved for use)

Scope: brand — only fires when brand_policy contains an "analyst_firms" list,
so it is effectively Infosys-only unless another brand adds that key.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register


_CITATION_TOKEN = "[APPROVED_ANALYST_CITATION]"


class _AnalystCitationsRule:
    name  = "brand.analyst_citations"
    stage = "output"
    scope = "brand"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        policy        = context.get("brand_policy", {})
        analyst_firms = policy.get("analyst_firms", [])
        if not analyst_firms:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        text  = _all_text(payload)
        token_present = _CITATION_TOKEN in text

        flags = []
        for firm in analyst_firms:
            if re.search(rf"\b{re.escape(firm)}\b", text, re.I) and not token_present:
                flags.append(Flag(
                    rule     = self.name,
                    severity = Severity.BLOCK,
                    message  = f"Analyst firm '{firm}' cited without approval token",
                    detail   = (
                        f"Add {_CITATION_TOKEN} adjacent to this citation, or remove the "
                        f"firm name and use the approved claim token only. "
                        f"Route to Analyst Relations + Legal before publishing."
                    ),
                    span     = firm,
                ))

        if not flags:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        # HITL — the content needs human sign-off; it is not outright blocked
        # (the analyst citation may be valid but just missing the token) so we
        # route for review rather than discarding the output entirely.
        return GuardrailResult(passed=False, action=Action.HITL, flags=flags)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_AnalystCitationsRule())
