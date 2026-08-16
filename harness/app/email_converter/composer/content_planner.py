"""
Content Planner — classifies raw body text into typed content groups
(bullets, paragraphs, subheadings) and decides which items to promote
to headline / subline / preheader if those slots are missing.

This is a rule-based pass that runs BEFORE the LLM composer so the LLM
receives pre-structured content rather than a raw text dump.
"""
from __future__ import annotations
from typing import Any


class ContentPlanner:
    """
    Classify and group body content items.

    Classification rules:
      • item < 4 chars               → skip
      • item ends ":" and < 80 chars → subheading
      • item < 90 chars              → bullet point
      • item >= 90 chars             → paragraph

    Grouping: consecutive bullets are merged into a single bullet group
    so the builder can render them together under one "Key Points" eyebrow.
    """

    BULLET_MAX   = 90    # chars; shorter items become bullets
    SUBHEAD_MAX  = 80    # chars; items ending ":" become subheads if under this
    MIN_LENGTH   = 4     # chars; items shorter than this are skipped

    def classify(self, body: list[str]) -> list[tuple[str, str]]:
        """
        Returns a flat list of (type, text) tuples.
        type is one of: "bullet", "para", "subhead"
        """
        result: list[tuple[str, str]] = []
        for item in body:
            s = item.strip()
            if len(s) < self.MIN_LENGTH:
                continue
            if s.endswith(":") and len(s) < self.SUBHEAD_MAX:
                result.append(("subhead", s.rstrip(":")))
            elif len(s) < self.BULLET_MAX:
                result.append(("bullet", s))
            else:
                result.append(("para", s))
        return result

    def group(self, classified: list[tuple[str, str]]) -> list[tuple[str, list[str]]]:
        """
        Group consecutive same-type items.
        Consecutive bullets → one group; paragraphs and subheads are never grouped.
        Returns list of (type, [text, ...]).
        """
        groups: list[tuple[str, list[str]]] = []
        for (itype, itext) in classified:
            if groups and groups[-1][0] == "bullet" and itype == "bullet":
                groups[-1][1].append(itext)
            else:
                groups.append((itype, [itext]))
        return groups

    def promote_missing_slots(self, slots: dict[str, Any]) -> dict[str, Any]:
        """
        If headline or subline are empty, try to promote from body.
        Mutates and returns the slots dict.
        """
        body = slots.get("body", [])
        if not slots.get("headline") and body:
            # first body item that's reasonably short → headline
            for i, item in enumerate(body):
                if len(item) < 120:
                    slots["headline"] = item
                    slots["body"] = body[:i] + body[i+1:]
                    body = slots["body"]
                    break

        if not slots.get("subline") and body:
            # second body item → subline
            for i, item in enumerate(body):
                if len(item) < 200 and item != slots.get("headline"):
                    slots["subline"] = item
                    slots["body"] = body[:i] + body[i+1:]
                    break

        if not slots.get("subject") and slots.get("headline"):
            slots["subject"] = slots["headline"]

        return slots

    def plan(self, slots: dict[str, Any]) -> dict[str, Any]:
        """
        Full content planning pass:
          1. Promote missing headline/subline from body if empty.
          2. Classify and group body items and store in slots["_content_groups"].
        """
        slots = self.promote_missing_slots(slots)
        classified = self.classify(slots.get("body", []))
        slots["_content_groups"] = self.group(classified)
        return slots
