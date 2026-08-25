"""
schemas/validated_brief.py — structured output from the Logos agent.

Captures every field from the Logos SKILL.md brief template plus the
buyer-truth scorecard and compliance gate result.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class Audience(BaseModel):
    segment: str        # named segment, e.g. "BFSI CIOs"
    role: str           # CXO title
    industry: str
    insight: str        # the situation / pressure this segment carries


class BuyerTruth(BaseModel):
    statement: str
    scores: dict[str, int]   # {"true":5, "human":4, "relevant":4, "ownable":4, "actionable":2}
    weighted_total: int       # /100  (true×5 + human×5 + relevant×4 + ownable×4 + actionable×2)
    verdict: str              # "GO" | "SHARPEN" | "REWORK"


class GateFlag(BaseModel):
    area: str                   # "disclosure" | "partner" | "accessibility" | "people"
    status: str                 # "PASS" | "BLOCK"
    element: Optional[str] = None
    rule: Optional[str] = None
    token: Optional[str] = None         # [APPROVED_CLIENT_REF] etc.
    routes_to: Optional[str] = None     # "legal" | "brand_team"


class GateResult(BaseModel):
    overall: str               # "PASS" | "BLOCK"
    flags: list[GateFlag]


class ValidatedBrief(BaseModel):
    campaign_name: str
    brand: str
    sub_brand: str             # "Infosys Topaz" | "Infosys Cobalt" | "Infosys" …
    co_brand: Optional[str] = None
    market: str
    locale: str                # "en-GB"
    objective: str
    kpi: str                   # measurable target with number + timeframe
    audience: Audience
    buyer_truth: BuyerTruth
    proposition: str           # single-minded proposition
    reasons_to_believe: list[str]
    tone: str
    channels: list[str]
    formats: list[str]         # with real specs, e.g. "LinkedIn 1200×627"
    mandatories: list[str]
    timing: str
    budget: str
    success_metric: str
    status: str                # "READY FOR CREATIVE" | "SHARPEN" | "REWORK"
    gate: GateResult
    quiet_period_check: str = ""
    display_brief: str = ""    # full formatted brief in Logos output format
