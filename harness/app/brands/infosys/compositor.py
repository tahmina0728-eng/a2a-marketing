"""
brands/infosys/compositor.py — Infosys LinkedIn KV compositor.

Produces on-brand LinkedIn 1200×627 key visuals by:
1. Selecting the correct template JPG by sub-brand
2. Resizing to output dimensions
3. Clearing the placeholder text zone with the brand background colour
4. Compositing headline / sub-heading / body using Myriad Pro fonts
5. Returning JPEG bytes ready for the API response

Template → sub-brand mapping
  masterbrand / IT Services / Finacle / McCamish / BPM / Cobalt / Topaz
      → Template_Infosys_Linkedin.jpg       (Infosys Blue  #007CC3)
  Aster
      → Template_Inofsys-Aster_Linkedin.jpg (Infosys Blue  #007CC3)
  Topaz + Cobalt co-brand
      → Template_Topaz-Cobalt_Linkedin.jpg  (Purple        #9B2FAC)
  Speaker / thought-leadership
      → Template_ Speaker_Linkedin.jpg      (Amber         #D4880F)
"""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

_BRAND_DIR = Path(__file__).parent          # harness/app/brands/infosys/
_ASSETS    = _BRAND_DIR / "assets"
_FONTS     = _BRAND_DIR / "fonts"

# ── Output dimensions (LinkedIn 1200×627) ─────────────────────────────────────
_W, _H = 1200, 627

# ── Template registry ──────────────────────────────────────────────────────────
_TPL = {
    "default":      _ASSETS / "Template_Infosys_Linkedin.jpg",
    "aster":        _ASSETS / "Template_Inofsys-Aster_Linkedin.jpg",
    "topaz+cobalt": _ASSETS / "Template_Topaz-Cobalt_Linkedin.jpg",
    "speaker":      _ASSETS / "Template_ Speaker_Linkedin.jpg",
}

# Background fill colour per template (covers placeholder text before new text is drawn)
_BG = {
    "default":      (0,   124, 195),   # Infosys Blue #007CC3
    "aster":        (0,   124, 195),
    "topaz+cobalt": (155,  47, 172),   # Purple       #9B2FAC
    "speaker":      (212, 136,  15),   # Amber        #D4880F
}

# ── Text layout at 1200×627 ───────────────────────────────────────────────────
# Per Infosys Type-Reference brand spec + template pixel measurements
# (template 3600×1881 → output 1200×627, scale ÷3):
#   "Heading" zone starts at y≈227, left bars x≈38–58, y≈225–306
#   Headline  → Tungsten Medium 72px  (brand headline font for banners)
#   Sub-line  → Myriad Pro SemiBold 24px
#   CTA       → Myriad Pro Regular 20px
_TEXT_X       = 120    # left edge of text — just past bar 2 (ends x=115)
_TEXT_MAX_W   = 530    # max line width — stays inside left text zone
_HEADING_Y    = 225    # matches template "Heading" zone

# Clear rectangle: covers template placeholder text only.
# Bar 1: x=70..94, Bar 2: x=97..115 — x1=116 preserves both bars completely.
# y: from just above heading zone to well below "Text goes here".
_CLEAR_RECT = (116, 210, 750, 420)   # (x1, y1, x2, y2)

_WHITE = (255, 255, 255)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tpl_key(sub_brand: str) -> str:
    s = sub_brand.lower()
    if "aster" in s:
        return "aster"
    if "topaz" in s and "cobalt" in s:
        return "topaz+cobalt"
    if "speaker" in s or "thought" in s:
        return "speaker"
    return "default"


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = _FONTS / name
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default(size=size)


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = f"{cur} {w}".strip()
        try:
            wide = font.getlength(candidate)
        except Exception:
            wide = len(candidate) * (font.size // 2)
        if wide <= max_w:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ── Public API ────────────────────────────────────────────────────────────────

def generate_kv(
    headline:     str,
    subline:      str = "",
    cta:          str = "",
    sub_brand:    str = "",
    aspect_ratio: str = "16:9",
) -> bytes:
    """
    Composite an Infosys LinkedIn KV from the brand template.
    Returns JPEG bytes at 1200×627.

    Args:
        headline:     Campaign headline (from Ideon copy deck)
        subline:      Sub-heading / support line
        cta:          Short CTA text shown in the lower text zone (≤ 5 words)
        sub_brand:    e.g. "Infosys Aster (Healthcare)", "Infosys Topaz (AI/Cloud)"
        aspect_ratio: Ignored for now (always 16:9 LinkedIn); reserved for future formats
    """
    key      = _tpl_key(sub_brand)
    tpl_path = _TPL.get(key, _TPL["default"])
    bg_rgb   = _BG.get(key, _BG["default"])

    # 1. Load and resize template
    img = Image.open(tpl_path).convert("RGB")
    img = img.resize((_W, _H), Image.LANCZOS)

    draw = ImageDraw.Draw(img)

    # 2. Clear placeholder text zone with the brand background colour
    draw.rectangle(_CLEAR_RECT, fill=bg_rgb)

    # 3. Load fonts per Infosys brand spec
    # Tungsten Medium = brand headline font (online banners)
    # Myriad Pro SemiBold = attribution / standout text
    # Myriad Pro Regular = body / CTA
    f_head = _load_font("Tungsten-Medium.ttf",     72)   # brand headline font
    f_sub  = _load_font("MYRIADPRO-SEMIBOLD.OTF", 24)   # support / attribution
    f_cta  = _load_font("MYRIADPRO-REGULAR.OTF",  20)   # CTA caption

    # 4. Headline — Tungsten Medium, flows from _HEADING_Y, up to 3 lines
    y = _HEADING_Y
    for line in _wrap(headline, f_head, _TEXT_MAX_W)[:3]:
        draw.text((_TEXT_X, y), line, font=f_head, fill=_WHITE)
        y += 80   # 72px + 8px leading

    # 5. Sub-heading — flows immediately below headline, no floor gap
    if subline:
        y += 14   # fixed gap between headline block and sub-heading
        for line in _wrap(subline, f_sub, _TEXT_MAX_W)[:2]:
            draw.text((_TEXT_X, y), line, font=f_sub, fill=_WHITE)
            y += 30   # 24px + 6px leading

    # 6. CTA — flows immediately below sub-heading
    if cta:
        y += 16   # fixed gap between sub-heading and CTA
        draw.text((_TEXT_X, y), cta[:50], font=f_cta, fill=_WHITE)

    # 7. Encode and return
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93, optimize=True)
    return buf.getvalue()
