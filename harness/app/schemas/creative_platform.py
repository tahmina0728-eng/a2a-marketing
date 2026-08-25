"""
schemas/creative_platform.py — structured output from the Helia agent.
"""
from __future__ import annotations

from pydantic import BaseModel


class BigIdea(BaseModel):
    statement: str          # one sentence — the organising creative thought
    what_it_unlocks: str    # short paragraph on what it enables creatively
    scores: dict[str, int]  # {"rooted":5, "single_minded":5, "ownable":4, "elastic":4, "inspiring":2}
    weighted_total: int     # /100
    verdict: str            # "proceed" | "sharpen" | "rework"


class HeroMessage(BaseModel):
    hero_line: str
    hero_line_char_count: int
    fits_banner_column: bool    # fits 546px column at 48px — ≤18 chars/line, 2 lines max
    support_line: str
    reason_to_believe: str      # may contain [APPROVED_...] tokens
    cta: str


class Territory(BaseModel):
    name: str
    premise: str
    feeling: str
    verbal_tone: str
    visual_cues: str            # colour set, ground hex + contrast ratio, template modules
    story_spine: str            # tension → stake → navigable path → Infosys → outcome
    sample_execution: str
    extends: str                # how it scales across formats, industries, time


class CreativePlatform(BaseModel):
    campaign_name: str
    brief_summary: str          # one-paragraph restatement of objective + truth + proposition
    big_idea: BigIdea
    hero_message: HeroMessage
    territories: list[Territory]     # 2–3 distinct worlds
    recommended_territory: str       # name of recommended territory
    recommendation_reason: str
    dos: list[str]                   # 3–4 execution dos
    donts: list[str]                 # 3–4 execution don'ts
    compliance_flags: list[str]      # BLOCK items with token and routing
    display_platform: str = ""       # full formatted creative platform in Helia format
