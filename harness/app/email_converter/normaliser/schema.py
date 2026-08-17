from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedImage(BaseModel):

    mime: str
    b64: str

    filename: str = ""

    semantic_title: str = ""

    semantic_tagline: str = ""

    description: str = ""

    contains_prominent_text: bool = False


class ContentSlots(BaseModel):

    subject: str = ""

    preheader: str = ""

    partner_name: str = ""

    headline: str = ""

    subline: str = ""

    intro: str = ""

    body: list[str] = Field(
        default_factory=list
    )

    highlights: list[str] = Field(
        default_factory=list
    )

    cta: str = ""

    legal_copy: str = ""

    hero_contains_text: bool = False

    images: list[dict] = Field(
        default_factory=list
    )

    tables: list[dict] = Field(
        default_factory=list
    )