"""
Product showcase template — 2-column image+copy rows.

Best for: e-commerce, multi-product promotions, catalogues.

Structure:
  Brand header
  Headline strip (gradient, no image hero)
  Product rows: [image | copy] alternating per row, driven by tables
  Body text bullets below (if any)
  CTA button
  Footer

Product rows are built from tables: each data row becomes a product card.
  Column 0 → product name (heading)
  Column 1 → description  (body paragraph)
  Column 2 → price / metric (badge)
  Images are paired with rows in order.
"""
from __future__ import annotations
from typing import Any

from ..helpers import escape, darken, text_on
from ..base import (
    brand_header, eyebrow, para_block, bullet_list,
    cta_button, footer, html_shell,
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
    body_raw  = slots.get("body",     [])
    tables    = slots.get("tables",   [])
    on_brand  = text_on(brand_color)
    dark_col  = darken(brand_color, 0.82)

    if not preheader:
        preheader = (body_raw[0][:120] if body_raw else "") or slots.get("headline", "")

    # ── Brand header ──
    rows = brand_header(brand_name, brand_color)

    # ── Headline banner ──
    hl_content = ""
    if headline:
        hl_content += (
            f'<h1 style="margin:0 0 10px;font-size:34px;font-weight:900;line-height:1.2;'
            f'letter-spacing:-.025em;color:{on_brand};'
            f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">{headline}</h1>"
        )
    if subline:
        hl_content += (
            f'<p style="margin:0;font-size:17px;line-height:1.55;color:{on_brand};opacity:.82;'
            f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">{subline}</p>"
        )
    if hl_content:
        rows += f"""
        <tr>
          <td style="background:linear-gradient(135deg,{brand_color} 0%,{dark_col} 100%);
                     padding:44px 40px 38px;" class="pad">
            {hl_content}
          </td>
        </tr>"""

    rows += '<tr><td style="height:24px;font-size:0;">&nbsp;</td></tr>'

    # ── Product rows (from first table) ──
    if tables:
        tbl    = tables[0]
        t_rows = tbl.get("rows", [])
        img_idx = 0
        for i, row in enumerate(t_rows[:12]):   # cap at 12 products
            name  = escape(str(row[0])) if len(row) > 0 else ""
            desc  = escape(str(row[1])) if len(row) > 1 else ""
            badge = escape(str(row[2])) if len(row) > 2 else ""
            flip  = "row-reverse" if i % 2 == 1 else "row"   # alternate image side

            img_td = '<td width="40%" class="col2">&nbsp;</td>'
            if img_idx < len(images):
                img = images[img_idx]
                img_td = (
                    f'<td width="40%" class="col2" valign="top">'
                    f'<img src="data:{img["mime"]};base64,{img["b64"]}" alt="{name}"'
                    f' width="220" style="display:block;width:100%;max-width:220px;'
                    f'height:auto;border-radius:8px;border:1px solid #eeeeee;" /></td>'
                )
                img_idx += 1

            copy_td = (
                f'<td width="55%" class="col2" valign="top" style="padding-left:20px;">'
                f'<p style="margin:0 0 6px;font-size:18px;font-weight:800;color:#111111;'
                f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">{name}</p>"
                + (
                    f'<p style="margin:0 0 10px;font-size:14px;line-height:1.7;color:#555555;'
                    f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">{desc}</p>"
                    if desc else ""
                )
                + (
                    f'<span style="display:inline-block;background:{brand_color};'
                    f'color:{on_brand};font-size:13px;font-weight:700;'
                    f'padding:5px 14px;border-radius:99px;">{badge}</span>'
                    if badge else ""
                )
                + '</td>'
            )

            # Alternate: even rows image-left, odd rows image-right
            left_td, right_td = (img_td, copy_td) if i % 2 == 0 else (copy_td, img_td)
            gap_td = '<td width="5%" style="font-size:0;">&nbsp;</td>'

            rows += (
                f'<tr><td style="padding:16px 40px;" class="pad">'
                f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
                f'{left_td}{gap_td}{right_td}</tr></table></td></tr>'
            )

    # ── Any body bullets below product grid ──
    bullets = [s.strip() for s in body_raw if 4 <= len(s.strip()) < 90]
    if bullets:
        rows += eyebrow("More Details", brand_color)
        rows += bullet_list(bullets, brand_color)

    rows += cta_button(cta, brand_color) if cta else '<tr><td style="height:36px;font-size:0;">&nbsp;</td></tr>'
    rows += footer(brand_name)

    return html_shell(subject, brand_color, rows, preheader)
