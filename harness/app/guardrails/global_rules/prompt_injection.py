"""
global_rules/prompt_injection.py — Detects prompt injection attempts in
user-supplied inputs (brief text, audience fields, product names, etc.).
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

# Patterns that indicate an attempt to override system instructions
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(your\s+)?(previous\s+)?instructions?",
    r"forget\s+(everything|all)\s+(you\s+)?(were\s+)?told",
    r"you are now\s+(?!Logos|Stratos|Verba|Pulse|Morphis|Kinetik)",
    r"act\s+as\s+(?:DAN|jailbreak|unrestricted)",
    r"bypass\s+(safety|content|guardrail|filter)",
    r"do\s+not\s+follow\s+(your\s+)?(?:guidelines|rules|policy)",
    r"system\s*prompt\s*[:=]",
    r"<\s*(?:system|instruction|prompt)\s*>",
    r"###\s*(?:SYSTEM|NEW INSTRUCTIONS|OVERRIDE)",
]


class _PromptInjectionRule:
    name  = "global.prompt_injection"
    stage = "input"
    scope = "global"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        text = _all_text(payload)
        for pattern in _INJECTION_PATTERNS:
            m = re.search(pattern, text, re.I)
            if m:
                return GuardrailResult(
                    passed = False,
                    action = Action.BLOCK,
                    flags  = [Flag(
                        rule     = self.name,
                        severity = Severity.BLOCK,
                        message  = "Prompt injection attempt detected",
                        span     = m.group(0)[:120],
                    )],
                )
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):    parts.append(v)
        elif isinstance(v, list): parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_PromptInjectionRule())
