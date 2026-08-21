"""
global_rules/hate_harassment.py — Blocks hate speech, harassment, and discrimination.
Runs on both input and output. Covers attacks on protected characteristics.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

_PROTECTED = [
    "race", "racial", "ethnicity", "ethnic", "nationality",
    "religion", "religious", "muslim", "jewish", "christian", "hindu", "sikh",
    "gender", "sex", "woman", "women", "man", "men", "transgender", "trans",
    "sexuality", "gay", "lesbian", "bisexual", "lgbtq",
    "disability", "disabled", "mental illness",
    "age", "ageism",
]

_ATTACK_PREFIXES = [
    r"all\s+(?:{})\s+(?:are|should|must|deserve|need to)",
    r"(?:{})\s+(?:people\s+)?(?:are inferior|are subhuman|are stupid|are criminals|are terrorists)",
    r"(?:kill|eliminate|remove|deport|ban)\s+(?:all\s+)?(?:{})",
    r"(?:hate|despise)\s+(?:all\s+)?(?:{})\s+people",
    r"(?:{})\s+(?:don't|do not)\s+belong",
]

_SLURS = [
    r"\bchink\b", r"\bspic\b", r"\bwetback\b", r"\bkike\b", r"\bgook\b",
    r"\btranny\b", r"\bretard\b", r"\bcripple\b",
]

_HARASSMENT = [
    r"\b(you\s+(?:should|deserve\s+to)\s+(?:die|kill yourself|be\s+raped))\b",
    r"\b(go\s+(?:kill\s+yourself|hang\s+yourself))\b",
    r"\b(i\s+(?:will|want\s+to)\s+(?:hurt|harm|kill|rape)\s+you)\b",
]


class _HateHarassmentRule:
    name  = "global.hate_harassment"
    stage = "both"
    scope = "global"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        text = _extract_text(payload)

        for slur in _SLURS:
            m = re.search(slur, text, re.I)
            if m:
                return _block(self.name, f"Discriminatory slur detected", m.group(0))

        for harass in _HARASSMENT:
            m = re.search(harass, text, re.I)
            if m:
                return _block(self.name, f"Harassment detected", m.group(0))

        protected_group = "|".join(_PROTECTED)
        for template in _ATTACK_PREFIXES:
            pattern = template.format(protected_group)
            m = re.search(pattern, text, re.I)
            if m:
                return _block(self.name, "Discriminatory attack on protected characteristic", m.group(0))

        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


def _block(rule: str, message: str, span: str) -> GuardrailResult:
    return GuardrailResult(
        passed=False,
        action=Action.BLOCK,
        flags=[Flag(rule=rule, severity=Severity.BLOCK, message=message, span=span[:120])],
    )


def _extract_text(payload: dict) -> str:
    parts = []
    for key in ("prompt", "text", "content", "output", "copy", "body", "headline", "summary"):
        v = payload.get(key, "")
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_HateHarassmentRule())
