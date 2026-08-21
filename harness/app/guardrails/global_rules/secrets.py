"""
global_rules/secrets.py — Detects API keys, tokens, and credentials in
prompts or outputs. Always BLOCK — secrets must never appear in campaign copy.
"""
from __future__ import annotations

import re
from ..models import GuardrailResult, Flag, Severity, Action
from ..registry import register

_PATTERNS = [
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})", "API key"),
    (r"(?i)(secret|token|password|passwd|pwd)\s*[:=]\s*['\"]?(\S{8,})",  "credential"),
    (r"AIza[0-9A-Za-z\-_]{35}",                                           "GCP API key"),
    (r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*",                             "bearer token"),
    (r"sk-[A-Za-z0-9]{32,}",                                              "OpenAI key"),
    (r"(?i)projects/[^/]+/(?:secrets|serviceAccounts)/\S+",              "GCP resource"),
]


class _SecretsRule:
    name  = "global.secrets"
    stage = "both"
    scope = "global"

    def run(self, payload: dict, context: dict) -> GuardrailResult:
        text = _all_text(payload)
        for pattern, label in _PATTERNS:
            m = re.search(pattern, text)
            if m:
                return GuardrailResult(
                    passed = False,
                    action = Action.BLOCK,
                    flags  = [Flag(
                        rule     = self.name,
                        severity = Severity.BLOCK,
                        message  = f"Secret/credential detected: {label}",
                        span     = m.group(0)[:30] + "…",
                    )],
                )
        return GuardrailResult(passed=True, action=Action.PASS_THROUGH)


def _all_text(payload: dict) -> str:
    parts = []
    for v in payload.values():
        if isinstance(v, str):    parts.append(v)
        elif isinstance(v, list): parts.extend(str(i) for i in v)
    return " ".join(parts)


register(_SecretsRule())
