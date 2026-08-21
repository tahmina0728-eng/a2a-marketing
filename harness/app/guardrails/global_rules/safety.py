"""
global_rules/safety.py — Blocks harmful, violent, or illegal content.
Runs on both input prompts and agent outputs.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

_PATTERNS = [
    # Weapons / explosives
    (r"\bhow to (?:make|build|create|synthesize)\s+(?:a\s+)?(?:bomb|weapon|explosive|grenade|landmine)\b",
     "violence/weapons"),
    (r"\b(?:chemical|biological|radiological|nuclear)\s+(?:weapon|attack|warfare|agent|bomb)\b",
     "WMD content"),

    # Physical harm to others
    (r"\bhow to (?:poison|harm|hurt|injure|kill|murder|attack|assault|stab|shoot)\s+(?:someone|a person|people|an?\s+(?:individual|human))\b",
     "physical harm instructions"),
    (r"\b(?:poison|poisoning)\s+(?:someone|a person|people|(?:the\s+)?(?:food|drink|water supply))\b",
     "poisoning content"),
    (r"\bwrite\s+(?:copy|content|ad|ads|post)\s+about\s+(?:how to\s+)?(?:poison|kill|harm|hurt|murder|attack)\b",
     "harmful content request"),

    # Self-harm
    (r"\b(?:self.harm|suicide method|how to (?:kill|hang|overdose on)\s+(?:myself|yourself))\b",
     "self-harm"),

    # Child safety
    (r"\b(?:child\s+(?:abuse|exploitation|pornography|sexual abuse material|grooming)|CSAM)\b",
     "child safety"),

    # Illegal drug production
    (r"\billegal drug\s+(?:synthesis|manufacture|production|lab)\b",
     "illegal activity"),

    # Explicit sexual content
    (r"\b(?:explicit sex|porn(?:ography)?|nude(?:s)?|naked\s+(?:photo|image|video)|onlyfans|sex tape|adult content)\b",
     "explicit sexual content"),
    (r"\b(?:rape|sexual assault|non.?consensual)\b",
     "sexual violence"),
]


class _SafetyRule:
    name  = "global.safety"
    stage = "both"
    scope = "global"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        text = _extract_text(payload)
        for pattern, category in _PATTERNS:
            m = re.search(pattern, text, re.I)
            if m:
                return GuardrailResult(
                    passed = False,
                    action = Action.BLOCK,
                    flags  = [Flag(
                        rule     = self.name,
                        severity = Severity.BLOCK,
                        message  = f"Harmful content detected: {category}",
                        span     = m.group(0)[:120],
                    )],
                )
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


def _extract_text(payload: dict) -> str:
    parts = []
    for key in ("prompt", "text", "content", "output", "copy", "body", "headline"):
        v = payload.get(key, "")
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_SafetyRule())
