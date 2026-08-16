"""
Hero template — campaign-style image-led layout.

Structure:
  ┌──────────────────────────────────────┐
  │ BRAND NAME            PARTNER NAME   │  ← dual-brand header (brand color)
  ├──────────────────────────────────────┤
  │                                      │
  │     HEADLINE (ALL CAPS)              │  ← hero text band (gradient, above image)
  │     Tagline / subline                │
  │                                      │
  │         [CAMPAIGN IMAGE]             │  ← full-width image (no padding)
  │                                      │
  ├──────────────────────────────────────┤
  │                                      │
  │ BRAND × PARTNER             (eyebrow)│  ← white body section
  │                                      │
  │ Tagline as headline.                 │  ← body headline (large, dark)
  │                                      │
  │ Paragraph one of body copy...        │  ← body paragraphs
  │ Paragraph two of body copy...        │
  │                                      │
  │        [ DISCOVER MORE ]             │  ← CTA (wide, uppercase)
  │                                      │
  ├──────────────────────────────────────┤
  │ Supporting tagline / brand line      │  ← sub-footer strip (darker brand color)
  ├──────────────────────────────────────┤
  │ Privacy  |  Terms  |  Unsubscribe    │  ← legal footer
  └──────────────────────────────────────┘
"""
from __future__ import annotations
import re
from typing import Any

from ..helpers import escape, darken, text_on
from ..base import (
    dual_brand_header, hero_text_band, body_headline,
    cta_button_wide, sub_footer_strip, footer_simple,
    eyebrow, para_block, table_block, section_divider,
    html_shell,
)


def render(
    slots:       dict[str, Any],
    brand_name:  str  = "",
    brand_color: str  = "#0055A4",
    multi_file:  bool = False,
) -> str:
    subject   = slots.get("subject",   "")
    preheader = slots.get("preheader", "")
    headline  = slots.get("headline",  "")
    subline   = slots.get("subline",   "")
    cta_text  = slots.get("cta",       "")
    images    = slots.get("images",    [])
    sections  = slots.get("_sections", [])
    body_raw  = slots.get("body",      [])

    if not preheader:
        preheader = subline or (body_raw[0][:120] if body_raw else headline)

    # Detect co-brand / partner name from headline (e.g. "Barclays & Wimbledon")
    partner = _extract_partner(headline, brand_name)

    # ── 1. Dual-brand header ─────────────────────────────────────────────────
    rows = dual_brand_header(brand_name, partner, brand_color)

    # ── 2. Hero text band (above image) — headline + tagline ─────────────────
    # The hero section gives the visual statement; body section expands on it.
    if headline or subline:
        rows += hero_text_band(escape(headline), escape(subline), brand_color)

    # ── 3. Campaign image (full-width, no border-radius — bleeds edge to edge) ─
    remaining_images = list(images)
    if remaining_images:
        hero_img = remaining_images.pop(0)
        rows += f"""
        <tr>
          <td style="padding:0;line-height:0;font-size:0;">
            <img src="data:{hero_img['mime']};base64,{hero_img['b64']}"
                 width="600" alt="{escape(brand_name)} campaign image"
                 style="display:block;width:100%;max-width:600px;height:auto;border:0;" />
          </td>
        </tr>"""

    # ── 4. White body section ─────────────────────────────────────────────────
    # Eyebrow: BRAND × PARTNER (or just BRAND)
    eyebrow_text = f"{brand_name} × {partner}" if partner else brand_name
    rows += eyebrow(eyebrow_text, brand_color)

    # Body headline — use subline (the tagline) as the section headline;
    # fall back to the main headline if subline is empty.
    body_hl = subline or headline
    if body_hl:
        rows += body_headline(body_hl)

    # Body paragraphs — rendered as prose (not bullets) for the hero template.
    if multi_file and sections:
        for i, sec in enumerate(sections):
            if i > 0 and sec.get("label"):
                rows += section_divider(sec["label"], brand_color)
            for j, item in enumerate(_clean_body(sec.get("body", []))):
                rows += para_block(item, lead=(i == 0 and j == 0))
            for tbl in sec.get("tables", []):
                rows += table_block(tbl, brand_color)
            # Additional images from subsequent files
            skip = 1 if (i == 0 and images) else 0
            for img in sec.get("images", [])[skip:]:
                rows += _inline_image_full(img)
    else:
        for i, item in enumerate(_clean_body(body_raw)):
            rows += para_block(item, lead=(i == 0))
        for tbl in slots.get("tables", []):
            rows += table_block(tbl, brand_color)
        # Additional images (gallery)
        for img in remaining_images:
            rows += _inline_image_full(img)

    # ── 5. CTA button ─────────────────────────────────────────────────────────
    if cta_text:
        rows += cta_button_wide(cta_text, brand_color)
    else:
        rows += '<tr><td style="height:36px;font-size:0;">&nbsp;</td></tr>'

    # ── 6. Sub-footer strip — supporting / partnership line ───────────────────
    sub_line = _sub_footer_text(slots, brand_name, partner)
    if sub_line:
        rows += sub_footer_strip(sub_line, brand_color)

    # ── 7. Legal footer ───────────────────────────────────────────────────────
    rows += footer_simple(brand_name)

    return html_shell(subject, brand_color, rows, preheader)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_partner(headline: str, brand_name: str) -> str:
    """
    Pull the partner / co-brand name from headlines like:
      "Barclays & Wimbledon", "BARCLAYS × WIMBLEDON", "Barclays and Wimbledon"
    Returns the part that is NOT the brand name, or "" if no pattern found.
    """
    for sep in [" × ", " & ", " and ", " x ", " X ", " + "]:
        if sep.lower() in headline.lower():
            idx = headline.lower().find(sep.lower())
            left  = headline[:idx].strip()
            right = headline[idx + len(sep):].strip()
            # Return the part that doesn't match the brand name
            if brand_name and brand_name.lower() in left.lower():
                return right
            if brand_name and brand_name.lower() in right.lower():
                return left
            # Neither matches cleanly — return the shorter one (likely the event)
            return right if len(right) <= len(left) else left
    return ""


def _clean_body(items: list[str]) -> list[str]:
    """Filter out very short or empty items; strip leading/trailing whitespace."""
    return [s.strip() for s in items if len(s.strip()) > 8]


def _inline_image_full(img: dict) -> str:
    """Render an additional image full-width with slight padding."""
    return (
        f'<tr><td style="padding:16px 0 0;line-height:0;font-size:0;">'
        f'<img src="data:{img["mime"]};base64,{img["b64"]}" alt="" width="600"'
        f' style="display:block;width:100%;max-width:600px;height:auto;border:0;" />'
        f'</td></tr>'
    )


def _sub_footer_text(slots: dict, brand_name: str, partner: str) -> str:
    """
    Build the sub-footer strip text.
    Priority: last body item (if it reads like a tagline) → partnership line → empty.
    """
    body = _clean_body(slots.get("body", []))
    if body:
        last = body[-1]
        # Use as sub-footer only if it's short and punchy (tagline-style)
        if len(last) < 120:
            return last
    if partner:
        return f"Supporting {partner}"
    return ""
