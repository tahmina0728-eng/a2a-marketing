"""
converter.py — Document-to-HTML-email converter

Supports: .docx (Word), .pdf, .xlsx / .xls (Excel), .csv
No AI generation — faithful format conversion of client-supplied content.
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
    """Return a slot name if the line begins with a recognised field label."""
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

    return {"blocks": blocks, "images": images[:3]}


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
                    raw = block.get("image", b"")
                    if raw:
                        images.append({"b64": base64.b64encode(raw).decode(), "mime": "image/jpeg"})
                except Exception:
                    pass

    doc.close()
    return {"blocks": blocks, "images": images[:3]}


def _parse_xlsx(content: bytes) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    blocks: list[dict] = []

    for sheet in wb.worksheets:
        rows_data: list[list[str]] = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c).strip() if c is not None else "" for c in row]
            cells = [c for c in cells if c]
            if cells:
                rows_data.append(cells)
        if rows_data:
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


# ── Slot mapping ───────────────────────────────────────────────────────────────

def _map_slots(parsed: dict) -> dict[str, Any]:
    slots: dict[str, Any] = {
        "subject": "",
        "preheader": "",
        "headline": "",
        "subline": "",
        "body": [],
        "cta": "",
        "tables": [],
        "images": parsed.get("images", []),
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


# ── HTML email renderer ────────────────────────────────────────────────────────

def _render_email(slots: dict, brand_name: str = "", brand_color: str = "#0055A4") -> str:
    subject   = _escape(slots.get("subject", ""))
    headline  = _escape(slots.get("headline", ""))
    subline   = _escape(slots.get("subline", ""))
    body_list = [_escape(p) for p in slots.get("body", [])]
    cta       = _escape(slots.get("cta", ""))
    tables    = slots.get("tables", [])
    images    = slots.get("images", [])

    # ── Hero image ──
    hero_html = ""
    if images:
        img = images[0]
        b64  = img.get("b64", "")
        mime = img.get("mime", "image/jpeg")
        hero_html = f"""
      <tr>
        <td style="padding:0;">
          <img src="data:{mime};base64,{b64}" width="600" alt=""
               style="display:block;width:100%;max-width:600px;height:auto;border:0;" />
        </td>
      </tr>"""

    # ── Brand header strip ──
    brand_html = ""
    if brand_name:
        brand_html = f"""
      <tr>
        <td style="background:{brand_color};padding:16px 40px;">
          <p style="margin:0;font-size:13px;font-weight:700;letter-spacing:.08em;
             text-transform:uppercase;color:#ffffff;
             font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
            {_escape(brand_name)}
          </p>
        </td>
      </tr>"""

    # ── Headline ──
    hl_html = ""
    if headline:
        hl_html = f"""
      <tr>
        <td style="padding:32px 40px 0;">
          <h1 style="margin:0;font-size:28px;font-weight:800;line-height:1.25;
             letter-spacing:-.02em;color:#111111;
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
        <td style="padding:10px 40px 20px;">
          <p style="margin:0;font-size:18px;line-height:1.5;color:#555555;
             font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
            {subline}
          </p>
        </td>
      </tr>"""

    # ── Body paragraphs ──
    body_html = "".join(f"""
      <tr>
        <td style="padding:0 40px 16px;">
          <p style="margin:0;font-size:16px;line-height:1.75;color:#444444;
             font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
            {p}
          </p>
        </td>
      </tr>""" for p in body_list)

    # ── Data tables ──
    tables_html = ""
    for tbl in tables:
        headers = tbl.get("headers", [])
        rows    = tbl.get("rows", [])
        th_row  = "".join(
            f'<th style="background:{brand_color};color:#fff;padding:10px 14px;'
            f'text-align:left;font-size:13px;font-weight:600;white-space:nowrap;">'
            f'{_escape(str(h))}</th>' for h in headers
        )
        tbody = ""
        for i, row in enumerate(rows):
            bg = "#f8f8f8" if i % 2 == 0 else "#ffffff"
            tds = "".join(
                f'<td style="padding:9px 14px;font-size:13px;color:#444444;'
                f'border-bottom:1px solid #eeeeee;">{_escape(str(c))}</td>'
                for c in row
            )
            tbody += f'<tr style="background:{bg};">{tds}</tr>'
        tables_html += f"""
      <tr>
        <td style="padding:0 40px 24px;">
          <table width="100%" cellpadding="0" cellspacing="0"
            style="border-collapse:collapse;border-radius:6px;
                   border:1px solid #eeeeee;overflow:hidden;">
            <thead><tr>{th_row}</tr></thead>
            <tbody>{tbody}</tbody>
          </table>
        </td>
      </tr>"""

    # ── CTA button ──
    cta_html = ""
    if cta:
        cta_html = f"""
      <tr>
        <td align="center" style="padding:8px 40px 36px;">
          <a href="#" style="display:inline-block;background:{brand_color};color:#ffffff;
             font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
             font-size:15px;font-weight:700;text-decoration:none;
             padding:14px 40px;border-radius:6px;letter-spacing:.03em;">
            {cta}
          </a>
        </td>
      </tr>"""

    footer_brand = _escape(brand_name) if brand_name else "CampaignOS"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <title>{subject}</title>
  <style>
    body{{margin:0;padding:0;background:#f0f0f0;-webkit-text-size-adjust:100%;}}
    img{{border:0;outline:none;text-decoration:none;display:block;}}
    table{{border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;}}
    a{{color:#0055A4;}}
    @media only screen and (max-width:640px){{
      .wrap{{width:100%!important;}}
      td.pad{{padding-left:20px!important;padding-right:20px!important;}}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f0f0f0;">
<table width="100%" cellpadding="0" cellspacing="0"
  style="background:#f0f0f0;min-width:280px;">
  <tr>
    <td align="center" style="padding:24px 16px;">
      <table class="wrap" width="600" cellpadding="0" cellspacing="0"
        style="background:#ffffff;border-radius:10px;overflow:hidden;
               box-shadow:0 2px 24px rgba(0,0,0,.10);">
        {brand_html}
        {hero_html}
        {hl_html}
        {sl_html}
        {body_html}
        {tables_html}
        {cta_html}
        <!-- footer -->
        <tr>
          <td style="padding:24px 40px;border-top:1px solid #eeeeee;">
            <p style="margin:0;font-size:12px;color:#999999;text-align:center;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;line-height:1.6;">
              Converted by CampaignOS &mdash; &copy; 2026 {footer_brand}.<br>
              <a href="#" style="color:#999999;">Unsubscribe</a>
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


# ── Public entry point ─────────────────────────────────────────────────────────

_PARSERS = {
    "docx": _parse_docx,
    "pdf":  _parse_pdf,
    "xlsx": _parse_xlsx,
    "xls":  _parse_xlsx,
    "csv":  _parse_csv,
}


def convert_document(
    content: bytes,
    filename: str,
    brand_name: str = "",
    brand_color: str = "#0055A4",
) -> dict:
    """
    Parse *content* (raw bytes of the uploaded file) and return:
      {html, slots, image_count, filename}

    Raises ValueError for unsupported file types.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    parser = _PARSERS.get(ext)
    if not parser:
        raise ValueError(f"Unsupported file type: .{ext}  (supported: docx, pdf, xlsx, csv)")

    parsed = parser(content)
    slots  = _map_slots(parsed)
    html   = _render_email(slots, brand_name=brand_name, brand_color=brand_color)

    public_slots = {k: v for k, v in slots.items() if k != "images"}

    return {
        "html":        html,
        "slots":       public_slots,
        "image_count": len(slots.get("images", [])),
        "filename":    filename,
    }
