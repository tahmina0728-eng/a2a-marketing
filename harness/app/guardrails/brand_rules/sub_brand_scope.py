"""
brand_rules/sub_brand_scope.py — Validates Infosys sub-brand/domain alignment.

Each Infosys sub-brand owns a specific domain:
  Topaz   → AI / cloud / digital / data
  Cobalt  → cybersecurity
  Aster   → healthcare / life sciences
  Finacle → banking / financial services
  McCamish → insurance
  BPM     → business process / managed services

A campaign can use at most one sub-brand. This rule flags two problems:

1. Sub-brand/domain mismatch — the sub-brand name appears in the output but
   the copy's topic domain doesn't align with that sub-brand's allowed domains.
   e.g. "Infosys Cobalt" appears in a healthcare AI campaign → WARN.

2. Multiple sub-brands in the same output — mixing "Infosys Topaz" and
   "Infosys Cobalt" in one piece of copy blurs the portfolio message → WARN.

Scope: brand — only fires when brand_policy contains a "sub_brands" dict.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register


class _SubBrandScopeRule:
    name  = "brand.sub_brand_scope"
    stage = "output"
    scope = "brand"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        policy     = context.get("brand_policy", {})
        sub_brands = policy.get("sub_brands", {})
        if not sub_brands:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        text  = _all_text(payload).lower()
        flags = []

        found_brands: list[str] = []

        for sb_name, sb_config in sub_brands.items():
            # Full lockup match (e.g. "Infosys Topaz") or plain sub-brand name
            lockup  = sb_config.get("lockup_prefix", f"Infosys {sb_name}").lower()
            pattern = rf"\b{re.escape(lockup)}\b|\binfosys\s+{re.escape(sb_name.lower())}\b"
            if re.search(pattern, text, re.I):
                found_brands.append(sb_name)

                # Check domain alignment — at least one domain keyword must appear
                domains = sb_config.get("domains", [])
                domain_hit = any(re.search(rf"\b{re.escape(d)}\b", text, re.I) for d in domains)
                if not domain_hit:
                    flags.append(Flag(
                        rule     = self.name,
                        severity = Severity.WARNING,
                        message  = (
                            f"Sub-brand '{sb_name}' appears but copy contains no "
                            f"{sb_name} domain keywords"
                        ),
                        detail   = (
                            f"'{lockup}' belongs to: {', '.join(domains[:5])}. "
                            f"Verify the correct sub-brand for this campaign topic."
                        ),
                        span     = sb_name,
                    ))

        # Multiple sub-brands in a single output
        if len(found_brands) > 1:
            flags.append(Flag(
                rule     = self.name,
                severity = Severity.WARNING,
                message  = f"Multiple Infosys sub-brands detected: {', '.join(found_brands)}",
                detail   = (
                    "Each campaign should carry a single sub-brand. "
                    "Mixing sub-brands in one execution blurs the portfolio message."
                ),
                span     = ", ".join(found_brands),
            ))

        if not flags:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        return GuardrailResult(passed=False, action=Action.WARN, flags=flags)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_SubBrandScopeRule())
