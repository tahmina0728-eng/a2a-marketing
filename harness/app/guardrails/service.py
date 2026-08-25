"""
guardrails/service.py — Central GuardrailService.

Every agent calls:
    gs = GuardrailService(brand="Barclays", context={...})
    result = gs.check_input(payload)   # before LLM call
    result = gs.check_output(payload)  # after LLM call

The service:
  1. Loads the global policy + brand policy JSON
  2. Runs all registered rules for the given stage
  3. Merges results — worst action wins
  4. Routes HITL cases to the review service
  5. Returns a single GuardrailResult the agent acts on
"""
from __future__ import annotations

import json
import os
import structlog

from .models  import GuardrailResult, Action, Flag, Severity
from .registry import get_rules

logger = structlog.get_logger()

_POLICY_DIR = os.path.join(os.path.dirname(__file__), "..", "policies")


def _load_policy(brand: str) -> dict:
    path = os.path.join(_POLICY_DIR, "brands", f"{brand}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_global_policy() -> dict:
    path = os.path.join(_POLICY_DIR, "global.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


class GuardrailService:

    def __init__(self, brand: str = "", agent: str = "", context: dict | None = None):
        self.brand         = brand
        self.agent         = agent
        self.global_policy = _load_global_policy()
        self.brand_policy  = _load_policy(brand) if brand else {}
        self.context: dict = {
            **(context or {}),
            "brand":         brand,
            "agent":         agent,
            "brand_policy":  self.brand_policy,
            "global_policy": self.global_policy,
        }

    def check_input(self, payload: dict) -> GuardrailResult:
        return self._run_rules("input", payload)

    def check_output(self, payload: dict) -> GuardrailResult:
        result = self._run_rules("output", payload)
        if result.action == Action.HITL:
            self._submit_hitl(payload, result)
        return result

    def check_handoff(self, from_agent: str, to_agent: str, payload: dict) -> GuardrailResult:
        from .validators.handoff import validate_handoff
        return validate_handoff(from_agent, to_agent, payload)

    def check_schema(self, payload: dict) -> GuardrailResult:
        from .validators.schema import validate_schema
        return validate_schema(self.agent, payload)

    # ── internals ──────────────────────────────────────────────────────────

    def _run_rules(self, stage: str, payload: dict) -> GuardrailResult:
        # Import rule modules so they self-register
        _ensure_rules_loaded()

        rules = get_rules(stage)
        combined = GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        for rule in rules:
            rule_config = self.global_policy.get("rules", {}).get(rule.name, {})
            if not rule_config.get("enabled", True):
                continue
            try:
                result = rule.run(payload, self.context)
                if not result.passed:
                    logger.warning(
                        "guardrail_flag",
                        rule   = rule.name,
                        agent  = self.agent,
                        brand  = self.brand,
                        action = result.action.value,
                        flags  = [f.message for f in result.flags],
                    )
                combined = combined.merge(result)
            except Exception as exc:
                logger.error("guardrail_rule_error", rule=rule.name, error=str(exc))

        if combined.passed:
            logger.debug("guardrail_passed", stage=stage, agent=self.agent)
        return combined

    def _submit_hitl(self, payload: dict, result: GuardrailResult) -> str:
        from app.hitl.service import submit_for_review
        return submit_for_review(
            agent   = self.agent,
            brand   = self.brand,
            payload = payload,
            flags   = [f.__dict__ for f in result.flags],
            context = {k: v for k, v in self.context.items()
                       if k not in ("brand_policy", "global_policy")},
        )


def _ensure_rules_loaded() -> None:
    """Import all rule modules so they self-register via register()."""
    from .global_rules   import safety, profanity, pii, secrets, prompt_injection, hate_harassment  # noqa
    from .brand_rules    import competitors, tone, claims, terminology, scope       # noqa
    from .brand_rules    import analyst_citations, sub_brand_scope                 # noqa
    from .campaign_rules import audience, approved_claims, partnership              # noqa
