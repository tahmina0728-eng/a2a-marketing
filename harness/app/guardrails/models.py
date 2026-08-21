"""
guardrails/models.py — Core data models for the guardrails system.

GuardrailResult is returned by every rule and by the GuardrailService.
Agents inspect .passed and .action to decide whether to proceed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    INFO    = "info"
    WARNING = "warning"
    BLOCK   = "block"   # hard stop — output must not be used


class Action(str, Enum):
    PASS_THROUGH = "pass"       # no issue, continue normally
    WARN         = "warn"       # flag but allow — log for review
    REDACT       = "redact"     # strip the offending content and continue
    BLOCK        = "block"      # stop processing, return error to caller
    HITL         = "hitl"       # pause and route to human reviewer


@dataclass
class Flag:
    rule:     str
    severity: Severity
    message:  str
    detail:   str = ""
    span:     str = ""          # offending text excerpt (truncated)


@dataclass
class GuardrailResult:
    passed:  bool
    action:  Action
    flags:   list[Flag] = field(default_factory=list)
    output:  Any        = None  # cleaned/redacted content if action==REDACT

    @property
    def blocked(self) -> bool:
        return self.action in (Action.BLOCK, Action.HITL)

    def merge(self, other: "GuardrailResult") -> "GuardrailResult":
        """Combine two results — worst action wins."""
        _order = [Action.PASS_THROUGH, Action.WARN, Action.REDACT, Action.HITL, Action.BLOCK]
        worst  = max(self.action, other.action, key=lambda a: _order.index(a))
        return GuardrailResult(
            passed = self.passed and other.passed,
            action = worst,
            flags  = self.flags + other.flags,
            output = other.output if other.output is not None else self.output,
        )

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "action": self.action.value,
            "flags":  [
                {"rule": f.rule, "severity": f.severity.value,
                 "message": f.message, "detail": f.detail, "span": f.span}
                for f in self.flags
            ],
        }
