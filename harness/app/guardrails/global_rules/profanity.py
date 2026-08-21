"""
global_rules/profanity.py — Detects profanity in campaign outputs.
Action is REDACT for mild terms, BLOCK for severe ones.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

# Extend as needed — keep lists in policy/global.json for easy updates
_SEVERE = ["fuck", "shit", "cunt", "nigger", "faggot"]
_MILD   = ["damn", "crap", "bastard", "ass", "bitch"]


class _ProfanityRule:
    name  = "global.profanity"
    stage = "output"
    scope = "global"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        text = _all_text(payload)
        for word in _SEVERE:
            if re.search(rf"\b{re.escape(word)}\b", text, re.I):
                return GuardrailResult(
                    passed = False,
                    action = Action.BLOCK,
                    flags  = [Flag(self.name, Severity.BLOCK,
                                   f"Severe profanity: '{word}'", span=word)],
                )
        flags = []
        for word in _MILD:
            if re.search(rf"\b{re.escape(word)}\b", text, re.I):
                flags.append(Flag(self.name, Severity.WARNING,
                                  f"Mild profanity detected: '{word}'", span=word))
        if flags:
            return GuardrailResult(passed=False, action=Action.WARN, flags=flags)
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):   parts.append(v)
        elif isinstance(v, list): parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_ProfanityRule())
