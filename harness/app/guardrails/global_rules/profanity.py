"""
global_rules/profanity.py — Detects profanity in user input and agent outputs.
Action is WARN for mild terms, BLOCK for severe ones.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

# Extend as needed — keep lists in policy/global.json for easy updates
# Stems — matched with \bSTEM\w*\b so derivatives are also caught:
#   fuck → fucking, fucker, fucked  |  shit → shitty  |  etc.
# "ass" kept as exact match to avoid false positives on assign/assert/etc.
_SEVERE_STEMS = ["fuck", "shit", "cunt", "nigger", "faggot"]
_MILD_STEMS   = ["damn", "crap", "bastard", "bitch"]
_MILD_EXACT   = ["ass"]


class _ProfanityRule:
    name  = "global.profanity"
    stage = "both"
    scope = "global"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        text = _all_text(payload)
        for stem in _SEVERE_STEMS:
            if re.search(rf"\b{re.escape(stem)}\w*\b", text, re.I):
                return GuardrailResult(
                    passed = False,
                    action = Action.BLOCK,
                    flags  = [Flag(self.name, Severity.BLOCK,
                                   f"Severe profanity: '{stem}'", span=stem)],
                )
        flags = []
        for stem in _MILD_STEMS:
            if re.search(rf"\b{re.escape(stem)}\w*\b", text, re.I):
                flags.append(Flag(self.name, Severity.WARNING,
                                  f"Mild profanity detected: '{stem}'", span=stem))
        for word in _MILD_EXACT:
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
