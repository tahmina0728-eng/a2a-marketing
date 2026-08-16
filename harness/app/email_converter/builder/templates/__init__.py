"""Template dispatcher — routes slots to the correct layout renderer."""
from __future__ import annotations
from typing import Any

from . import hero, text_first, product

_RENDERERS = {
    "hero":       hero.render,
    "text_first": text_first.render,
    "product":    product.render,
}


def render(
    slots: dict[str, Any],
    brand_name:  str = "",
    brand_color: str = "#0055A4",
    multi_file:  bool = False,
) -> str:
    """
    Render slots to a complete HTML email string using the template
    stored in slots["_template"] (default: "hero").
    """
    template = slots.get("_template", "hero")
    renderer = _RENDERERS.get(template, hero.render)
    return renderer(slots, brand_name=brand_name, brand_color=brand_color, multi_file=multi_file)


__all__ = ["render"]
