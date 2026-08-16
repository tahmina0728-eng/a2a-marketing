"""
Template Library — selects the best email layout template based on content signals.

Templates:
  hero        — Image-led. Full-width hero image with headline over brand colour strip.
                Best for: brand announcements, lifestyle campaigns, event invitations.
  text_first  — Text-led. No hero image; headline in gradient banner; dense copy.
                Best for: B2B, newsletters, press releases, informational updates.
  product     — 2-column product grid. Image left, copy right per row.
                Best for: e-commerce, multi-product promotions, catalogues.
"""
from __future__ import annotations
from typing import Any


TEMPLATES = ("hero", "text_first", "product")


class TemplateLibrary:
    """
    Rule-based template selector (no LLM required).

    Selection logic:
      • product   if tables > 0 AND images >= 2 (product data + images)
      • hero      if images >= 1 (visual-led content)
      • text_first otherwise (copy-heavy, no visuals)

    The composer's LayoutPlanner can override this with an LLM-driven pick.
    """

    def select(self, slots: dict[str, Any]) -> str:
        images  = slots.get("images", [])
        tables  = slots.get("tables", [])
        body    = slots.get("body", [])

        if tables and len(images) >= 2:
            return "product"
        if images:
            return "hero"
        return "text_first"

    def describe(self, template: str) -> str:
        descriptions = {
            "hero": (
                "Image-led hero layout. Full-width image at top, "
                "headline in brand-colour strip, bullets + paragraphs below."
            ),
            "text_first": (
                "Text-first layout. Gradient headline banner (no image hero), "
                "lead paragraph, then bullets and data tables."
            ),
            "product": (
                "Product showcase. 2-column rows pairing product images with "
                "description copy and a price/CTA per row."
            ),
        }
        return descriptions.get(template, "")
