"""
Text-first template — copy-led layout, no hero image.

Best for: B2B emails, newsletters, press releases, informational updates.

Structure:
  Brand header
  Gradient headline banner (full-width, no image)
  Lead paragraph (larger, heavier)
  Remaining body (bullets / paragraphs)
  Data tables
  Optional single image (centred)
  CTA button
  Footer
"""
from __future__ import annotations
from typing import Any

from ..helpers import escape, darken, text_on
from ..base import (
    brand_header, eyebrow, para_block, subhead_block, bullet_list,
    table_block, section_divider, cta_button, footer, html_shell,
)


def render(
    slots: dict[str, Any],
    brand_name:  str = "",
    brand_color: str = "#0055A4",
    multi_file:  bool = False,
) -> str:
    subject   = slots.get("subject",   "")
    preheader = slots.get("preheader", "")
    headline  = escape(slots.get("headline", ""))
    subline   = escape(slots.get("subline",  ""))
    cta       = slots.get("cta",      "")
    images    = slots.get("images",   [])
    sections  = slots.get("_sections", [])
    body_raw  = slots.get("body",     [])
    on_brand  = text_on(brand_color)
    dark_col  = darken(brand_color, 0.82)

    if not preheader:
        preheader = (body_raw[0][:120] if body_raw else "") or slots.get("headline", "")

    groups = _classify_and_group(body_raw)

    # ── Brand header ──
    rows = brand_header(brand_name, brand_color)

    # ── Gradient headline banner (text-first has no hero image) ──
    hl_content = ""
    if headline:
        hl_content += (
            f'<h1 style="margin:0 0 12px;font-size:38px;font-weight:900;line-height:1.15;'
            f'letter-spacing:-.03em;color:{on_brand};'
            f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">{headline}</h1>"
        )
    if subline:
        hl_content += (
            f'<p style="margin:0;font-size:19px;line-height:1.55;color:{on_brand};opacity:.82;'
            f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">{subline}</p>"
        )
    if hl_content:
        rows += f"""
        <tr>
          <td style="background:linear-gradient(135deg,{brand_color} 0%,{dark_col} 100%);
                     padding:48px 40px 42px;" class="pad">
            {hl_content}
          </td>
        </tr>"""

    rows += '<tr><td style="height:32px;font-size:0;">&nbsp;</td></tr>'

    # ── Body ──
    body_html   = ""
    tables_html = ""

    if multi_file and sections:
        for i, sec in enumerate(sections):
            if i > 0 and sec.get("label"):
                body_html += section_divider(sec["label"], brand_color)
            body_html += _render_groups(
                _classify_and_group(sec.get("body", [])),
                brand_color, lead=(i == 0),
            )
            for tbl in sec.get("tables", []):
                tables_html += table_block(tbl, brand_color)
    else:
        body_html += _render_groups(groups, brand_color, lead=True)
        if slots.get("tables"):
            tables_html += eyebrow("Data", brand_color)
            for tbl in slots["tables"]:
                tables_html += table_block(tbl, brand_color)

    rows += body_html + tables_html

    # ── Single centred image (if present) ──
    if images:
        img = images[0]
        rows += (
            f'<tr><td style="padding:20px 40px 0;" class="pad">'
            f'<img src="data:{img["mime"]};base64,{img["b64"]}" alt="" width="520"'
            f' style="display:block;width:100%;max-width:520px;height:auto;margin:0 auto;'
            f'border-radius:8px;border:1px solid #eeeeee;" /></td></tr>'
        )

    rows += cta_button(cta, brand_color) if cta else '<tr><td style="height:36px;font-size:0;">&nbsp;</td></tr>'
    rows += footer(brand_name)

    return html_shell(subject, brand_color, rows, preheader)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _classify_and_group(body: list[str]) -> list[tuple[str, list[str]]]:
    classified: list[tuple[str, str]] = []
    for item in body:
        s = item.strip()
        if len(s) < 4: continue
        if s.endswith(":") and len(s) < 80:
            classified.append(("subhead", s.rstrip(":")))
        elif len(s) < 90:
            classified.append(("bullet", s))
        else:
            classified.append(("para", s))
    groups: list[tuple[str, list[str]]] = []
    for (itype, itext) in classified:
        if groups and groups[-1][0] == "bullet" and itype == "bullet":
            groups[-1][1].append(itext)
        else:
            groups.append((itype, [itext]))
    return groups


def _render_groups(
    groups: list[tuple[str, list[str]]],
    brand_color: str,
    lead: bool = True,
) -> str:
    html        = ""
    bullet_done = False
    first_para  = lead
    for (gtype, gitems) in groups:
        if gtype == "para":
            html      += para_block(gitems[0], lead=first_para)
            first_para = False
        elif gtype == "subhead":
            html += subhead_block(gitems[0], brand_color)
        elif gtype == "bullet":
            if not bullet_done:
                html += eyebrow("Key Points", brand_color)
                bullet_done = True
            html += bullet_list(gitems, brand_color)
    return html
