"""
Content normaliser — maps raw parsed blocks into structured ContentSlots,
and merges multiple per-file slot dicts into one combined set.
"""
from __future__ import annotations
import re
from typing import Any


def _detect_slot(text: str) -> str | None:
    lower = text.lower().strip()
    for kw in ("subject:", "email subject:", "subject line:"):
        if lower.startswith(kw): return "subject"
    for kw in ("preheader:", "preview text:", "preview:"):
        if lower.startswith(kw): return "preheader"
    for kw in ("headline:", "header:", "title:", "h1:"):
        if lower.startswith(kw): return "headline"
    for kw in ("subline:", "subtitle:", "subheading:", "sub-headline:", "tagline:"):
        if lower.startswith(kw): return "subline"
    for kw in ("cta:", "call to action:", "button:", "action:"):
        if lower.startswith(kw): return "cta"
    return None


def _strip_label(text: str) -> str:
    idx = text.find(":")
    return text[idx + 1:].strip() if idx != -1 else text.strip()


def map_slots(parsed: dict) -> dict[str, Any]:
    """
    Convert raw { blocks, images } from a parser into a ContentSlots dict.

    Slot detection rules:
      • Lines starting with "Subject:", "Headline:", "CTA:", etc. are extracted
        directly into their named slot.
      • Heading level-1 → headline (first one), body thereafter.
      • Heading level-2/3 → subline (first after headline), body thereafter.
      • Plain paragraphs → body list.
      • Tables → tables list.
    """
    slots: dict[str, Any] = {
        "subject":   "",
        "preheader": "",
        "headline":  "",
        "subline":   "",
        "body":      [],
        "cta":       "",
        "tables":    [],
        "images":    parsed.get("images", []),
    }

    for block in parsed.get("blocks", []):
        btype = block.get("type")

        if btype == "table":
            slots["tables"].append({
                "headers": block.get("headers", []),
                "rows":    block.get("rows", []),
            })
            continue

        text = block.get("text", "").strip()
        if not text:
            continue

        slot = _detect_slot(text)
        if slot:
            slots[slot] = _strip_label(text)
            continue

        level = block.get("level", 0)
        if btype == "heading" and level == 1:
            if not slots["headline"]:
                slots["headline"] = text
            else:
                slots["body"].append(text)
        elif btype == "heading":
            if slots["headline"] and not slots["subline"] and len(text) < 160:
                slots["subline"] = text
            else:
                slots["body"].append(text)
        else:
            slots["body"].append(text)

    if not slots["subject"] and slots["headline"]:
        slots["subject"] = slots["headline"]

    return slots


def merge_slots_list(slots_list: list[dict], filenames: list[str]) -> dict[str, Any]:
    """
    Merge multiple per-file slot dicts into one combined ContentSlots dict.

    The first file provides the primary subject / headline / brand signals.
    Subsequent files are appended as `_sections` with their filename as label,
    so the builder can render them with visual dividers.
    """
    if not slots_list:
        return map_slots({"blocks": [], "images": []})
    if len(slots_list) == 1:
        return slots_list[0]

    first  = slots_list[0]
    merged: dict[str, Any] = {
        "subject":   first.get("subject", ""),
        "preheader": first.get("preheader", ""),
        "headline":  first.get("headline", ""),
        "subline":   first.get("subline", ""),
        "cta":       first.get("cta", ""),
        "body":      list(first.get("body", [])),
        "tables":    list(first.get("tables", [])),
        "images":    list(first.get("images", [])),
        "_sections": [],
    }

    merged["_sections"].append({
        "label":  filenames[0] if filenames else "",
        "body":   list(first.get("body", [])),
        "tables": list(first.get("tables", [])),
        "images": list(first.get("images", [])),
    })

    for slots, fname in zip(slots_list[1:], filenames[1:]):
        merged["_sections"].append({
            "label":  fname,
            "body":   list(slots.get("body", [])),
            "tables": list(slots.get("tables", [])),
            "images": list(slots.get("images", [])),
        })
        merged["body"].extend(slots.get("body", []))
        merged["tables"].extend(slots.get("tables", []))
        merged["images"].extend(slots.get("images", []))
        if not merged["cta"] and slots.get("cta"):
            merged["cta"] = slots["cta"]
        if not merged["subject"] and slots.get("subject"):
            merged["subject"] = slots["subject"]
        if not merged["headline"] and slots.get("headline"):
            merged["headline"] = slots["headline"]

    if not merged["subject"] and merged["headline"]:
        merged["subject"] = merged["headline"]

    merged["images"] = merged["images"][:10]
    return merged
