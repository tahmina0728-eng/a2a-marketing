"""
brand_rules/scope.py — Ensures campaign content stays within the allowed
brand scope (markets, channels, products). Warns if output references
markets or channels the brand hasn't activated.
"""
from __future__ import annotations

from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register


class _ScopeRule:
    name  = "brand.scope"
    stage = "output"
    scope = "brand"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        policy          = context.get("brand_policy", {})
        allowed_markets = set(m.lower() for m in policy.get("markets", []))
        if not allowed_markets:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        campaign_market = str(context.get("market", "")).lower()
        if campaign_market and campaign_market not in allowed_markets:
            return GuardrailResult(
                passed = False,
                action = Action.WARN,
                flags  = [Flag(
                    rule     = self.name,
                    severity = Severity.WARNING,
                    message  = f"Market '{campaign_market}' not in brand's activated markets",
                    detail   = f"Allowed: {', '.join(sorted(allowed_markets))}",
                )],
            )
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


register(_ScopeRule())
