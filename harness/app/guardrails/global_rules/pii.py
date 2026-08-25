"""
global_rules/pii.py — Detects and redacts Personally Identifiable Information.
Covers email addresses, phone numbers, national IDs, credit cards, and names
when paired with an identifier.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

_PATTERNS: list[tuple[str, str, str]] = [
    # ── Universal ──────────────────────────────────────────────────────────────
    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "email address", "redact"),
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",    "credit card",   "block"),

    # ── UK ─────────────────────────────────────────────────────────────────────
    (r"\b(?:\+44|0044|0)7\d{9}\b",                       "UK phone",      "redact"),
    (r"\b[A-Z]{2}\d{6}[A-D]\b",                          "NI number",     "block"),
    (r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b",          "UK postcode",   "warn"),

    # ── US ─────────────────────────────────────────────────────────────────────
    # US SSN — hard block; never appears in marketing copy legitimately
    (r"\b\d{3}-\d{2}-\d{4}\b",                                                   "US SSN",   "block"),
    # US phone (various formats: 555-867-5309, (555) 867-5309, +1 555 867 5309)
    (r"\b(?:\+1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b",                   "US phone", "redact"),

    # ── India ──────────────────────────────────────────────────────────────────
    # Aadhaar — 12-digit national ID in 4-4-4 groups; hard block
    (r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b",                                           "Aadhaar number", "block"),
    # PAN — AAAAA9999A format; hard block
    (r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",                                               "Indian PAN",     "block"),
    # Indian mobile: starts 6-9, 10 digits (may be split 5+5 or 4+6 with separator)
    (r"(?:\+91[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}\b",                               "Indian phone",   "redact"),
]


class _PIIRule:
    name  = "global.pii"
    stage = "both"
    scope = "global"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        text   = _all_text(payload)
        flags  = []
        action = Action.PASS_THROUGH

        for pattern, label, severity in _PATTERNS:
            matches = re.findall(pattern, text)
            if not matches:
                continue
            if severity == "block":
                flags.append(Flag(self.name, Severity.BLOCK,
                                  f"PII detected: {label}", span=matches[0][:40]))
                action = Action.BLOCK
            elif severity == "redact":
                flags.append(Flag(self.name, Severity.WARNING,
                                  f"PII detected and redacted: {label}", span=matches[0][:40]))
                if action not in (Action.BLOCK,):
                    action = Action.REDACT
            else:
                flags.append(Flag(self.name, Severity.INFO,
                                  f"Possible PII: {label}", span=matches[0][:40]))
                if action == Action.PASS_THROUGH:
                    action = Action.WARN

        if not flags:
            return GuardrailResult(passed=True, action=Action.PASS_THROUGH)

        cleaned = _redact(text) if action == Action.REDACT else None
        return GuardrailResult(
            passed = action not in (Action.BLOCK,),
            action = action,
            flags  = flags,
            output = cleaned,
        )


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):    parts.append(v)
        elif isinstance(v, list): parts.extend(str(i) for i in v)
    return " ".join(parts)


def _redact(text: str) -> str:
    text = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL REDACTED]", text)
    text = re.sub(r"\b(?:\+44|0044|0)7\d{9}\b", "[PHONE REDACTED]", text)
    text = re.sub(r"\b(?:\+1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b", "[PHONE REDACTED]", text)
    text = re.sub(r"(?:\+91[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}\b", "[PHONE REDACTED]", text)
    return text


register(_PIIRule())
