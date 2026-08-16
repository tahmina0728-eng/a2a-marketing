"""Typed schema for the structured content slots used throughout the pipeline."""
from __future__ import annotations
from typing import Any, TypedDict


class TableSlot(TypedDict):
    headers: list[str]
    rows:    list[list[str]]


class ImageSlot(TypedDict):
    b64:  str   # base64-encoded image bytes
    mime: str   # e.g. "image/jpeg"


class SectionSlot(TypedDict):
    label:  str
    body:   list[str]
    tables: list[TableSlot]
    images: list[ImageSlot]


class ContentSlots(TypedDict, total=False):
    subject:   str
    preheader: str
    headline:  str
    subline:   str
    body:      list[str]
    cta:       str
    tables:    list[TableSlot]
    images:    list[ImageSlot]
    _sections: list[SectionSlot]   # multi-file mode only
    _template: str                  # set by LayoutPlanner: "hero" | "text_first" | "product"
    _vision:   dict[str, Any]       # raw Gemini Vision response, if available
