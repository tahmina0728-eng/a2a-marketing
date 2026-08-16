"""
Layout Planner — decides which email template to use.

Decision order:
  1. If slots already has _template set (e.g. user-chosen), keep it.
  2. Ask TemplateLibrary for a rule-based pick.
  3. (Optional) Override with an LLM-driven pick when use_llm=True.
"""
from __future__ import annotations
from typing import Any

from ..rag.template_library import TemplateLibrary


class LayoutPlanner:
    """
    Selects the best template and stores the choice in slots["_template"].

    Templates:
      hero        — visual-led, single image hero
      text_first  — text-led, gradient banner headline
      product     — 2-column product/image grid
    """

    def __init__(self):
        self._library = TemplateLibrary()

    def plan(
        self,
        slots: dict[str, Any],
        use_llm: bool   = False,
        llm_fn: object  = None,   # callable(slots, candidates) -> str
    ) -> dict[str, Any]:
        """
        Set slots["_template"] and return the updated slots dict.

        Args:
            slots   : ContentSlots dict (after content planning)
            use_llm : if True, call llm_fn to override the rule-based pick
            llm_fn  : optional callable(slots, candidates: list[str]) -> template_name
        """
        # Respect an explicit user/agent choice
        if slots.get("_template") in ("hero", "text_first", "product"):
            return slots

        # Rule-based pick
        template = self._library.select(slots)

        # LLM override
        if use_llm and callable(llm_fn):
            try:
                llm_pick = llm_fn(slots, list(("hero", "text_first", "product")))
                if llm_pick in ("hero", "text_first", "product"):
                    template = llm_pick
            except Exception:
                pass   # fall back to rule-based pick

        slots["_template"] = template
        return slots
