"""
guardrails/registry.py — Rule registry.

Rules register themselves here. The GuardrailService loads rules by
stage (input / output) and scope (global / brand / campaign).
"""
from __future__ import annotations

from typing import Callable, Protocol
from .models import GuardrailResult


class Rule(Protocol):
    name:  str
    stage: str   # "input" | "output" | "both"
    scope: str   # "global" | "brand" | "campaign"

    def run(self, payload: dict, context: dict) -> GuardrailResult: ...


_REGISTRY: dict[str, Rule] = {}


def register(rule: Rule) -> Rule:
    _REGISTRY[rule.name] = rule
    return rule


def get_rules(stage: str, scope: str | None = None) -> list[Rule]:
    out = []
    for r in _REGISTRY.values():
        if r.stage not in (stage, "both"):
            continue
        if scope and r.scope != scope and r.scope != "global":
            continue
        out.append(r)
    return out


def all_rules() -> list[Rule]:
    return list(_REGISTRY.values())
