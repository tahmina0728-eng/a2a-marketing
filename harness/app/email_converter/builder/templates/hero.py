"""
Hero template — image-led layout.

Structure:
  Brand header  (coloured top bar)
  Hero image    (full-width) + headline in brand-colour strip
  Spacer
  Body          (bullets / paragraphs / subheadings)
  Data tables
  Image gallery (2-col grid for remaining images)
  CTA button
  Footer
"""
from __future__ import annotations
from typing import Any

from ..helpers import escape, darken, text_on
from ..base import (
    brand_header, eyebrow, para_block, subhead_block, bullet_list,
    table_block, section_divider, inline_image, cta_button, footer, html_shell,
)


def render(
    slots: dict[str, Any],
    brand_name:  str = "",
    brand_color: str = "#0055A4",
    multi_file:  bool = False,
) -> str:
    subject  = slots.get("subject",   "")
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

    # Classify body
    groups = _classify_and_group(body_raw)

    # ── Brand header ──
    rows = brand_header(brand_name, brand_color)

    # ── Hero: image + headline in brand strip, or gradient banner ──
    gallery_images = images[:]
    hl_in_hero = False

    if gallery_images:
        hero_img = gallery_images.pop(0)
        rows += f"""
        <tr>
          <td style="padding:0;line-height:0;font-size:0;background:{brand_color};">
            <img src="data:{hero_img['mime']};base64,{hero_img['b64']}"
                 width="600" alt="{escape(brand_name)}"
                 style="display:block;width:100%;max-width:600px;height:auto;border:0;" />
          </td>
        </tr>"""
        if headline:
            rows += f"""
        <tr>
          <td style="background:{brand_color};padding:28px 40px 26px;" class="pad">
            <h1 style="margin:0 0 8px;font-size:32px;font-weight:900;line-height:1.2;
               letter-spacing:-.02em;color:{on_brand};
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">{headline}</h1>"""
            if subline:
                rows += f"""
            <p style="margin:0;font-size:17px;line-height:1.55;color:{on_brand};opacity:.85;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">{subline}</p>"""
            rows += "\n          </td>\n        </tr>"
            hl_in_hero = True
    else:
        # No image — gradient banner
        hl_content = ""
        if headline:
            hl_content += (
                f'<h1 style="margin:0 0 10px;font-size:36px;font-weight:900;line-height:1.18;'
                f'letter-spacing:-.025em;color:{on_brand};'
                f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">{headline}</h1>"
            )
        if subline:
            hl_content += (
                f'<p style="margin:0;font-size:18px;line-height:1.55;color:{on_brand};opacity:.82;'
                f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">{subline}</p>"
            )
        rows += f"""
        <tr>
          <td style="background:linear-gradient(135deg,{brand_color} 0%,{dark_col} 100%);
                     padding:52px 40px 44px;" class="pad">
            {hl_content}
          </td>
        </tr>"""
        hl_in_hero = True

    if headline and not hl_in_hero:
        rows += f"""
        <tr>
          <td style="padding:40px 40px 0;" class="pad">
            <h1 style="margin:0 0 12px;font-size:34px;font-weight:900;line-height:1.2;
               letter-spacing:-.025em;color:#0d0d0d;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">{headline}</h1>
            <div style="width:44px;height:4px;background:{brand_color};border-radius:99px;"></div>
          </td>
        </tr>"""
        if subline:
            rows += f"""
        <tr>
          <td style="padding:14px 40px 0;" class="pad">
            <p style="margin:0;font-size:18px;line-height:1.55;color:#555555;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">{subline}</p>
          </td>
        </tr>"""

    rows += '<tr><td style="height:28px;font-size:0;">&nbsp;</td></tr>'

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
            skip = 1 if (i == 0 and images) else 0
            for img in sec.get("images", [])[skip:]:
                body_html += inline_image(img)
    else:
        body_html += _render_groups(groups, brand_color, lead=True)
        if slots.get("tables"):
            tables_html += eyebrow("Data", brand_color)
            for tbl in slots["tables"]:
                tables_html += table_block(tbl, brand_color)

    rows += body_html + tables_html

    # ── Gallery ──
    if gallery_images and not multi_file:
        pairs = [gallery_images[i:i+2] for i in range(0, len(gallery_images), 2)]
        for pair in pairs:
            left     = pair[0]
            right_td = '<td width="51%">&nbsp;</td>'
            if len(pair) > 1:
                r = pair[1]
                right_td = (
                    f'<td width="2%" style="font-size:0;">&nbsp;</td>'
                    f'<td width="49%" class="col2" valign="top">'
                    f'<img src="data:{r["mime"]};base64,{r["b64"]}" alt="" width="260"'
                    f' style="display:block;width:100%;max-width:260px;height:auto;'
                    f'border-radius:6px;border:1px solid #eeeeee;" /></td>'
                )
            rows += (
                f'<tr><td style="padding:16px 40px 0;" class="pad">'
                f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
                f'<td width="49%" class="col2" valign="top">'
                f'<img src="data:{left["mime"]};base64,{left["b64"]}" alt="" width="260"'
                f' style="display:block;width:100%;max-width:260px;height:auto;'
                f'border-radius:6px;border:1px solid #eeeeee;" /></td>'
                f'{right_td}</tr></table></td></tr>'
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
