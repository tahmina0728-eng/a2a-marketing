"""
global_rules/safety.py — Blocks harmful, violent, or illegal content.
Runs on both input prompts and agent outputs.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

_PATTERNS = [
    (r"\b(how to (?:make|build|create) (?:bomb|weapon|explosive))\b", "violence/weapons"),
    (r"\b(self.harm|suicide method|kill (?:myself|yourself))\b",       "self-harm"),
    (r"\b(child (?:abuse|exploitation|pornography))\b",                "child safety"),
    (r"\b(illegal drug (?:synthesis|manufacture))\b",                  "illegal activity"),
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
