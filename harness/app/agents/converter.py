"""
converter.py — Document-to-HTML-email converter

Supports: .docx, .doc (try), .pdf, .xlsx/.xls, .csv, .txt,
          .jpg/.jpeg/.png/.gif/.webp (images), .pptx (PowerPoint)

Multiple files are merged into one combined email, with visual
section breaks between each source document.
"""
from __future__ import annotations

import base64
import csv as _csv_mod
import io
import re
from typing import Any


# ── Text utilities ─────────────────────────────────────────────────────────────

def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


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


def _escape(text: str) -> str:
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r, g, b


def _darken(hex_color: str, factor: float = 0.80) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return "#{:02x}{:02x}{:02x}".format(
        int(r * factor), int(g * factor), int(b * factor)
    )


def _text_on(hex_color: str) -> str:
    """Return white or near-black depending on luminance."""
    r, g, b = _hex_to_rgb(hex_color)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return "#ffffff" if lum < 140 else "#0d0d0d"


# ── Format parsers ─────────────────────────────────────────────────────────────

def _parse_docx(content: bytes) -> dict:
    from docx import Document

    doc = Document(io.BytesIO(content))
    blocks: list[dict] = []
    images: list[dict] = []

    for para in doc.paragraphs:
        text = _clean(para.text)
        if not text:
            continue
        style = (para.style.name or "").lower()
        level = 0
        if "heading 1" in style or "title" in style:
            level = 1
        elif "heading 2" in style:
            level = 2
        elif "heading 3" in style:
            level = 3
        blocks.append({"type": "heading" if level else "paragraph", "level": level, "text": text})

    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            try:
                blob = rel.target_part.blob
                mime = rel.target_part.content_type or "image/png"
                images.append({"b64": base64.b64encode(blob).decode(), "mime": mime})
            except Exception:
                pass

    return {"blocks": blocks, "images": images[:6]}


def _parse_pdf(content: bytes) -> dict:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=content, filetype="pdf")
    blocks: list[dict] = []
    images: list[dict] = []

    for page in doc:
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            btype = block.get("type")
            if btype == 0:  # text
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    line_text = _clean(" ".join(s.get("text", "") for s in spans))
                    if not line_text:
                        continue
                    max_size = max((s.get("size", 0) for s in spans), default=0)
                    if max_size >= 18:
                        blocks.append({"type": "heading", "level": 1, "text": line_text})
                    elif max_size >= 14:
                        blocks.append({"type": "heading", "level": 2, "text": line_text})
                    else:
                        blocks.append({"type": "paragraph", "text": line_text})
            elif btype == 1:  # image
                try:
                    xref = block.get("xref", 0)
                    if xref:
                        img_data = doc.extract_image(xref)
                        raw  = img_data.get("image", b"")
                        mime = f"image/{img_data.get('ext', 'jpeg')}"
                    else:
                        raw  = block.get("image", b"")
                        mime = "image/jpeg"
                    if raw:
                        images.append({"b64": base64.b64encode(raw).decode(), "mime": mime})
                except Exception:
                    pass

    doc.close()
    return {"blocks": blocks, "images": images[:6]}


def _parse_xlsx(content: bytes) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    blocks: list[dict] = []
    multi = len(wb.worksheets) > 1

    for sheet in wb.worksheets:
        rows_data: list[list[str]] = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c).strip() if c is not None else "" for c in row]
            cells = [c for c in cells if c]
            if cells:
                rows_data.append(cells)
        if rows_data:
            if multi:
                blocks.append({"type": "heading", "level": 2, "text": sheet.title})
            blocks.append({"type": "table", "headers": rows_data[0], "rows": rows_data[1:]})

    wb.close()
    return {"blocks": blocks, "images": []}


def _parse_csv(content: bytes) -> dict:
    text = content.decode("utf-8-sig", errors="replace")
    reader = _csv_mod.reader(io.StringIO(text))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return {"blocks": [], "images": []}
    return {"blocks": [{"type": "table", "headers": rows[0], "rows": rows[1:]}], "images": []}


def _parse_txt(content: bytes) -> dict:
    """Plain text: split on blank lines into paragraphs."""
    text = content.decode("utf-8-sig", errors="replace")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    blocks: list[dict] = []
    for i, para in enumerate(paras):
        lines = [l.strip() for l in para.splitlines() if l.strip()]
        if not lines:
            continue
        first = lines[0]
        rest  = " ".join(lines[1:])
        if i == 0 and len(first) < 120:
            blocks.append({"type": "heading", "level": 1, "text": first})
            if rest:
                blocks.append({"type": "paragraph", "text": rest})
        else:
            blocks.append({"type": "paragraph", "text": " ".join(lines)})
    return {"blocks": blocks, "images": []}


def _parse_image(content: bytes, filename: str, mime: str) -> dict:
    """Treat the uploaded image file itself as a content image."""
    b64  = base64.b64encode(content).decode()
    name = re.sub(r"[-_]+", " ", filename.rsplit(".", 1)[0]).strip().title()
    return {
        "blocks": [{"type": "heading", "level": 1, "text": name}],
        "images": [{"b64": b64, "mime": mime}],
    }


def _parse_pptx(content: bytes) -> dict:
    try:
        from pptx import Presentation
    except ImportError:
        raise ValueError(
            "python-pptx is required for .pptx files. "
            "Install it: pip install python-pptx"
        )
    prs = Presentation(io.BytesIO(content))
    blocks: list[dict] = []
    images: list[dict] = []

    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                ph_idx = None
                if hasattr(shape, "placeholder_format") and shape.placeholder_format:
                    ph_idx = shape.placeholder_format.idx
                for i, para in enumerate(shape.text_frame.paragraphs):
                    text = _clean(para.text)
                    if not text:
                        continue
                    if ph_idx == 0 and i == 0:
                        blocks.append({"type": "heading", "level": 2, "text": text})
                    else:
                        blocks.append({"type": "paragraph", "text": text})
            if hasattr(shape, "image"):
                try:
                    img  = shape.image
                    b64  = base64.b64encode(img.blob).decode()
                    mime = img.content_type or "image/png"
                    images.append({"b64": b64, "mime": mime})
                except Exception:
                    pass

    return {"blocks": blocks, "images": images[:6]}


# ── Slot mapping ───────────────────────────────────────────────────────────────

def _map_slots(parsed: dict) -> dict[str, Any]:
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
            slots["tables"].append({"headers": block.get("headers", []), "rows": block.get("rows", [])})
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


def _merge_slots_list(slots_list: list[dict], filenames: list[str]) -> dict[str, Any]:
    """Merge multiple per-file slot dicts into one combined set."""
    if not slots_list:
        return _map_slots({"blocks": [], "images": []})
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

    # First file as section 0
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


# ── HTML email renderer ────────────────────────────────────────────────────────

def _render_email(
    slots: dict,
    brand_name: str  = "",
    brand_color: str = "#0055A4",
    multi_file: bool = False,
) -> str:
    subject   = _escape(slots.get("subject", ""))
    preheader = slots.get("preheader", "")
    headline  = _escape(slots.get("headline", ""))
    subline   = _escape(slots.get("subline", ""))
    cta       = _escape(slots.get("cta", ""))
    images    = slots.get("images", [])
    sections  = slots.get("_sections", [])
    on_brand  = _text_on(brand_color)
    dark_col  = _darken(brand_color, 0.82)

    # Preheader: use explicit preheader, or first body sentence, or headline
    _ph = preheader or (slots.get("body") or [""])[0][:120] or slots.get("headline", "")
    preheader_html = (
        f'<div style="display:none;max-height:0;overflow:hidden;'
        f'mso-hide:all;font-size:1px;color:#fefefe;line-height:1px;">'
        f'{_escape(_ph)}&nbsp;' + '&#847;&nbsp;' * 80 + '</div>'
        if _ph else ""
    )

    # ── Brand header ──
    brand_label = _escape(brand_name) if brand_name else "CampaignOS"
    brand_html = f"""
        <tr>
          <td style="background:{brand_color};padding:0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:18px 40px;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <p style="margin:0;font-size:17px;font-weight:900;
                           letter-spacing:.08em;text-transform:uppercase;
                           color:{on_brand};
                           font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
                          {brand_label}
                        </p>
                      </td>
                      <td align="right">
                        <p style="margin:0;font-size:11px;color:{on_brand};opacity:.65;
                           font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                           letter-spacing:.05em;text-transform:uppercase;">
                          Campaign&nbsp;Email
                        </p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="height:4px;background:{dark_col};font-size:0;">&nbsp;</td>
              </tr>
            </table>
          </td>
        </tr>"""

    # ── Hero image (first image) ──
    hero_html = ""
    gallery_images = images[:]
    if gallery_images:
        hero = gallery_images.pop(0)
        hero_html = f"""
        <tr>
          <td style="padding:0;line-height:0;font-size:0;">
            <img src="data:{hero['mime']};base64,{hero['b64']}"
                 width="600" alt="{brand_label} visual"
                 style="display:block;width:100%;max-width:600px;height:auto;border:0;" />
          </td>
        </tr>"""

    # ── Headline ──
    hl_html = ""
    if headline:
        hl_html = f"""
        <tr>
          <td style="padding:40px 40px 0;" class="pad">
            <h1 style="margin:0;font-size:32px;font-weight:900;line-height:1.2;
               letter-spacing:-.025em;color:#0d0d0d;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
              {headline}
            </h1>
          </td>
        </tr>"""

    # ── Subline ──
    sl_html = ""
    if subline:
        sl_html = f"""
        <tr>
          <td style="padding:12px 40px 0;" class="pad">
            <p style="margin:0;font-size:19px;line-height:1.55;color:#555555;
               font-weight:400;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
              {subline}
            </p>
          </td>
        </tr>"""

    # ── Divider after headline block ──
    divider_html = """
        <tr>
          <td style="padding:24px 40px 0;" class="pad">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr><td style="border-top:1px solid #e8e8e8;font-size:0;">&nbsp;</td></tr>
            </table>
          </td>
        </tr>""" if (headline or subline) else ""

    # ── Body / sections ──
    def _section_break(label: str) -> str:
        return f"""
        <tr>
          <td style="padding:28px 40px 0;" class="pad">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#f5f6fb;border-radius:5px;
                    padding:9px 16px;border-left:3px solid {brand_color};">
                  <p style="margin:0;font-size:10.5px;font-weight:800;
                     letter-spacing:.10em;text-transform:uppercase;color:#888888;
                     font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
                    {_escape(label)}
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    def _para(text: str) -> str:
        return f"""
        <tr>
          <td style="padding:16px 40px 0;" class="pad">
            <p style="margin:0;font-size:16px;line-height:1.75;color:#444444;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
              {_escape(text)}
            </p>
          </td>
        </tr>"""

    def _table_block(tbl: dict) -> str:
        headers = tbl.get("headers", [])
        rows    = tbl.get("rows", [])
        if not headers and not rows:
            return ""
        th_cells = "".join(
            f'<th style="background:{brand_color};color:{on_brand};padding:10px 14px;'
            f'text-align:left;font-size:12px;font-weight:700;white-space:nowrap;'
            f'font-family:Helvetica,Arial,sans-serif;">'
            f'{_escape(str(h))}</th>'
            for h in headers
        )
        tbody_rows = ""
        for i, row in enumerate(rows[:50]):  # cap at 50 rows per table
            bg = "#f7f8fc" if i % 2 == 0 else "#ffffff"
            tds = "".join(
                f'<td style="padding:9px 14px;font-size:12.5px;color:#444444;'
                f'border-bottom:1px solid #eeeeee;'
                f'font-family:Helvetica,Arial,sans-serif;">'
                f'{_escape(str(c))}</td>'
                for c in row
            )
            tbody_rows += f'<tr style="background:{bg};">{tds}</tr>'
        overflow_note = ""
        if len(rows) > 50:
            overflow_note = (
                f'<p style="margin:6px 0 0;font-size:11px;color:#999999;'
                f'font-family:Helvetica,Arial,sans-serif;">'
                f'Showing 50 of {len(rows)} rows.</p>'
            )
        return f"""
        <tr>
          <td style="padding:20px 40px 0;" class="pad">
            <div style="overflow-x:auto;">
            <table width="100%" cellpadding="0" cellspacing="0"
              style="border-collapse:collapse;border-radius:6px;
                     border:1px solid #e8e8e8;overflow:hidden;min-width:300px;">
              <thead><tr>{th_cells}</tr></thead>
              <tbody>{tbody_rows}</tbody>
            </table>
            </div>
            {overflow_note}
          </td>
        </tr>"""

    # Build body HTML — sections mode (multi-file) or flat mode (single file)
    body_html = ""
    if sections and multi_file:
        for i, sec in enumerate(sections):
            if i > 0 and sec["label"]:
                body_html += _section_break(sec["label"])
            for p in sec.get("body", []):
                body_html += _para(p)
            for tbl in sec.get("tables", []):
                body_html += _table_block(tbl)
            # Section images (not the hero — already used)
            sec_imgs = sec.get("images", [])
            if i == 0:
                sec_imgs = sec_imgs[1:] if images else sec_imgs  # skip hero from first section
            for img in sec_imgs:
                body_html += f"""
        <tr>
          <td style="padding:20px 40px 0;" class="pad">
            <img src="data:{img['mime']};base64,{img['b64']}"
                 width="520" alt=""
                 style="display:block;width:100%;max-width:520px;height:auto;
                        border-radius:6px;border:1px solid #eeeeee;" />
          </td>
        </tr>"""
    else:
        for p in slots.get("body", []):
            body_html += _para(p)
        for tbl in slots.get("tables", []):
            body_html += _table_block(tbl)

    # ── Gallery (remaining images, 2-col grid) ──
    gallery_html = ""
    if gallery_images and not multi_file:
        # pair up
        pairs = [gallery_images[i:i+2] for i in range(0, len(gallery_images), 2)]
        for pair in pairs:
            left = pair[0]
            right_html = ""
            if len(pair) > 1:
                right = pair[1]
                right_html = f"""
                  <td width="2%" style="font-size:0;">&nbsp;</td>
                  <td width="49%" class="col2" valign="top">
                    <img src="data:{right['mime']};base64,{right['b64']}"
                         alt="" width="260"
                         style="display:block;width:100%;max-width:260px;height:auto;
                                border-radius:5px;border:1px solid #eeeeee;" />
                  </td>"""
            else:
                right_html = '<td width="51%">&nbsp;</td>'

            gallery_html += f"""
        <tr>
          <td style="padding:16px 40px 0;" class="pad">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="49%" class="col2" valign="top">
                  <img src="data:{left['mime']};base64,{left['b64']}"
                       alt="" width="260"
                       style="display:block;width:100%;max-width:260px;height:auto;
                              border-radius:5px;border:1px solid #eeeeee;" />
                </td>
                {right_html}
              </tr>
            </table>
          </td>
        </tr>"""

    # ── CTA button ──
    cta_html = ""
    if cta:
        cta_html = f"""
        <tr>
          <td align="center" style="padding:32px 40px;">
            <!--[if mso]>
            <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
              href="#" style="height:50px;v-text-anchor:middle;width:220px;"
              arcsize="10%" stroke="f" fillcolor="{brand_color}">
            <w:anchorlock/>
            <center><![endif]-->
            <a href="#"
               style="display:inline-block;background:{brand_color};color:{on_brand};
                      font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                      font-size:15px;font-weight:800;text-decoration:none;
                      padding:15px 44px;border-radius:8px;
                      letter-spacing:.03em;mso-padding-alt:0;
                      -webkit-text-size-adjust:none;">
              {cta} &rarr;
            </a>
            <!--[if mso]></center></v:roundrect><![endif]-->
          </td>
        </tr>"""
    else:
        # Spacer if no CTA
        cta_html = '<tr><td style="height:32px;font-size:0;">&nbsp;</td></tr>'

    # ── Footer ──
    footer_brand = _escape(brand_name) if brand_name else "CampaignOS"
    footer_html = f"""
        <tr>
          <td style="border-top:1px solid #e8e8e8;padding:28px 40px 36px;">
            <p style="margin:0 0 8px;font-size:12px;color:#aaaaaa;text-align:center;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;line-height:1.7;">
              You're receiving this because you subscribed to {footer_brand} updates.
            </p>
            <p style="margin:0 0 12px;font-size:12px;color:#aaaaaa;text-align:center;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
              <a href="#" style="color:#aaaaaa;text-decoration:underline;">Unsubscribe</a>
              &nbsp;&middot;&nbsp;
              <a href="#" style="color:#aaaaaa;text-decoration:underline;">Privacy&nbsp;Policy</a>
              &nbsp;&middot;&nbsp;
              <a href="#" style="color:#aaaaaa;text-decoration:underline;">View&nbsp;in&nbsp;browser</a>
            </p>
            <p style="margin:0;font-size:11px;color:#cccccc;text-align:center;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
              &copy; 2026 {footer_brand}. Powered by CampaignOS.
            </p>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>{subject}</title>
  <!--[if mso]>
  <noscript>
    <xml><o:OfficeDocumentSettings>
      <o:PixelsPerInch>96</o:PixelsPerInch>
    </o:OfficeDocumentSettings></xml>
  </noscript>
  <![endif]-->
  <style>
    body{{margin:0;padding:0;background:#efefef;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}}
    img{{border:0;outline:none;text-decoration:none;display:block;}}
    table{{border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;}}
    td,th{{font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;}}
    a{{color:{brand_color};}}
    @media only screen and (max-width:640px){{
      .wrap{{width:100%!important;max-width:100%!important;}}
      .pad{{padding-left:24px!important;padding-right:24px!important;}}
      h1{{font-size:26px!important;}}
      .col2{{display:block!important;width:100%!important;max-width:100%!important;}}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#efefef;">
{preheader_html}
<table width="100%" cellpadding="0" cellspacing="0"
  style="background:#efefef;min-width:280px;" role="presentation">
  <tr>
    <td align="center" style="padding:32px 16px 48px;">
      <table class="wrap" width="600" cellpadding="0" cellspacing="0"
        style="background:#ffffff;border-radius:12px;overflow:hidden;
               box-shadow:0 6px 40px rgba(0,0,0,.13);" role="presentation">
        {brand_html}
        {hero_html}
        {hl_html}
        {sl_html}
        {divider_html}
        {body_html}
        {gallery_html}
        {cta_html}
        {footer_html}
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


# ── Parser registry ────────────────────────────────────────────────────────────

_PARSERS: dict[str, Any] = {
    "docx": _parse_docx,
    "doc":  _parse_docx,     # try python-docx; will fail on true binary .doc
    "pdf":  _parse_pdf,
    "xlsx": _parse_xlsx,
    "xls":  _parse_xlsx,
    "csv":  _parse_csv,
    "txt":  _parse_txt,
    "pptx": _parse_pptx,
    "jpg":  None,            # handled via _parse_image
    "jpeg": None,
    "png":  None,
    "gif":  None,
    "webp": None,
}

_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}

_EXT_MIME: dict[str, str] = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png",  "gif": "image/gif",
    "webp": "image/webp",
}


def _parse_one(content: bytes, filename: str) -> dict:
    """Parse a single file. Returns {blocks, images}."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in _IMAGE_EXTS:
        mime = _EXT_MIME.get(ext, "image/jpeg")
        return _parse_image(content, filename, mime)
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(
            f"Unsupported file type: .{ext}  "
            f"(supported: docx, pdf, xlsx, xls, csv, txt, pptx, jpg, jpeg, png, gif, webp)"
        )
    return parser(content)


# ── Public entry points ────────────────────────────────────────────────────────

def convert_documents(
    files: list[tuple[bytes, str]],
    brand_name: str  = "",
    brand_color: str = "#0055A4",
) -> dict:
    """
    Convert one or more (content_bytes, filename) pairs into a single HTML email.

    Returns:
      { html, slots, image_count, filename, file_count }
    """
    if not files:
        raise ValueError("No files provided.")

    slots_list: list[dict] = []
    filenames: list[str]   = []

    for content, filename in files:
        try:
            parsed = _parse_one(content, filename)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Could not parse {filename}: {exc}") from exc
        slots_list.append(_map_slots(parsed))
        filenames.append(filename)

    multi = len(slots_list) > 1
    merged = _merge_slots_list(slots_list, filenames) if multi else slots_list[0]

    html = _render_email(
        merged,
        brand_name=brand_name,
        brand_color=brand_color,
        multi_file=multi,
    )

    # Public slots (strip internal _sections and raw image bytes)
    public_slots = {
        k: v for k, v in merged.items()
        if k not in ("images", "_sections")
    }

    combined_name = (
        filenames[0] if not multi
        else f"Combined ({len(filenames)} files)"
    )

    return {
        "html":        html,
        "slots":       public_slots,
        "image_count": len(merged.get("images", [])),
        "filename":    combined_name,
        "file_count":  len(files),
    }


def convert_document(
    content: bytes,
    filename: str,
    brand_name: str  = "",
    brand_color: str = "#0055A4",
) -> dict:
    """Single-file convenience wrapper — backward compatible."""
    return convert_documents([(content, filename)], brand_name=brand_name, brand_color=brand_color)
