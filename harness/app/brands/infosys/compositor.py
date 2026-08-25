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
# Per Infosys Type-Reference brand spec:
#   Headline  → Tungsten Medium 72px  (online banners: bold condensed headline font)
#   Sub-line  → Myriad Pro SemiBold 24px  (attribution / standout text)
#   CTA       → Myriad Pro Regular 20px   (body / caption weight)
# Left white bars: x≈18–62 → text starts at x=90 (safe margin past bars)
_TEXT_X       = 90     # left edge of text (right of white vertical bars)
_TEXT_MAX_W   = 570    # max line width (~left 48% of 1200px canvas)
_HEADING_Y    = 155    # top of headline (Tungsten starts higher for visual balance)
_SUBHEAD_Y    = 400    # top of sub-heading (after up to 3 Tungsten lines at 80px)
_BODY_Y       = 460    # top of CTA line

# Clear rectangle: covers ALL template placeholder text.
# x1=80 keeps both left white bars visible (bars end at x≈62).
# y extends to 540 to cover 3 Tungsten lines + subline + CTA.
_CLEAR_RECT = (80, 140, 750, 540)   # (x1, y1, x2, y2)

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

    # 4. Headline — Tungsten Medium, up to 3 lines (condensed so fits more)
    y = _HEADING_Y
    for line in _wrap(headline, f_head, _TEXT_MAX_W)[:3]:
        draw.text((_TEXT_X, y), line, font=f_head, fill=_WHITE)
        y += 80   # 72px + 8px leading

    # 5. Sub-heading — up to 2 lines, semi-bold
    if subline:
        y = max(y + 10, _SUBHEAD_Y)
        for line in _wrap(subline, f_sub, _TEXT_MAX_W)[:2]:
            draw.text((_TEXT_X, y), line, font=f_sub, fill=_WHITE)
            y += 30   # 24px + 6px leading

    # 6. CTA — single line, regular weight
    if cta:
        y = max(y + 14, _BODY_Y)
        draw.text((_TEXT_X, y), cta[:50], font=f_cta, fill=_WHITE)

    # 7. Encode and return
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93, optimize=True)
    return buf.getvalue()
