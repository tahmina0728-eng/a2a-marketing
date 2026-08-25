"""
schemas/copy_deck.py — structured output from the Ideon agent.
"""
from __future__ import annotations

from pydantic import BaseModel


class HeadlinePack(BaseModel):
    hero_options: list[str]      # 3 options, ≤7 words each
    support_options: list[str]   # 3 options


class FormatCopy(BaseModel):
    format_name: str             # "LinkedIn 1200×627" | "MPU 300×250" …
    heading: str                 # banner heading (≤18 chars/line, 2 lines for LinkedIn)
    body_copy: str
    cta: str
    alt_text: str                # accessibility alt text for the visual


class ScriptScene(BaseModel):
    time: str                    # "0:00–0:08"
    visual: str                  # [image zone] description
    super: str                   # on-screen text
    vo: str                      # spoken voiceover


class Script(BaseModel):
    format: str                  # "30s social film"
    territory: str
    scenes: list[ScriptScene]
    end_frame: str               # lockup description + hero line SUPER
    legal_supers: list[str]      # [APPROVED_...] tokens shown on-screen


class CopyDeck(BaseModel):
    campaign_name: str
    territory: str               # territory name from Helia
    big_idea_anchor: str         # big idea statement this deck executes
    headlines: HeadlinePack
    body_copy: dict[str, str]    # {"web": "...", "email": "..."}
    banner_copy: dict[str, dict] # {"linkedin_1200x627": {"heading": "...", "cta": "..."}}
    cta_bank: list[str]          # 4–6 specific CTAs
    social_captions: dict[str, str]   # {"linkedin": "...", "x": "..."}
    scripts: list[Script]
    compliance_flags: list[str]
    lead_picks: dict[str, str]   # {"linkedin_banner": "option_1", ...}
    display_deck: str = ""       # full formatted copy deck in Ideon output format
