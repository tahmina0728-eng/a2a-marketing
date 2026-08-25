"""
brands/infosys.py — Infosys LinkedIn KV compositor.

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

_BRAND_DIR = Path(__file__).parent / "infosys"
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
# Derived from template at 3600×1881 → ÷3
_TEXT_X       = 85     # left edge of text block (after the white vertical bar)
_TEXT_MAX_W   = 530    # max text zone width (~left 48% of canvas)
_HEADING_Y    = 155    # top of headline
_SUBHEAD_Y    = 220    # top of sub-heading
_BODY_Y       = 285    # top of body text

# Clear rectangle that covers the placeholder "Heading / Sub Heading / Text goes here"
_CLEAR_RECT = (68, 140, 680, 340)   # (x1, y1, x2, y2)

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
    body:         str = "",
    sub_brand:    str = "",
    aspect_ratio: str = "16:9",
) -> bytes:
    """
    Composite an Infosys LinkedIn KV from the brand template.
    Returns JPEG bytes at 1200×627.

    Args:
        headline:     Campaign headline (from Ideon copy deck)
        subline:      Sub-heading / support line
        body:         First sentence of body copy (truncated if long)
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

    # 3. Load Myriad Pro fonts
    f_head = _load_font("MYRIADPRO-BOLD.OTF",     44)
    f_sub  = _load_font("MYRIADPRO-SEMIBOLD.OTF", 30)
    f_body = _load_font("MYRIADPRO-REGULAR.OTF",  23)

    # 4. Headline — up to 2 lines, sentence-case preserved
    y = _HEADING_Y
    for line in _wrap(headline, f_head, _TEXT_MAX_W)[:2]:
        draw.text((_TEXT_X, y), line, font=f_head, fill=_WHITE)
        y += 52

    # 5. Sub-heading — up to 2 lines
    if subline:
        y = max(y + 6, _SUBHEAD_Y)
        for line in _wrap(subline, f_sub, _TEXT_MAX_W)[:2]:
            draw.text((_TEXT_X, y), line, font=f_sub, fill=_WHITE)
            y += 36

    # 6. Body — first sentence only, up to 2 lines
    if body:
        first_sentence = (body.split(".")[0] + ".").strip()
        if len(first_sentence) > 140:
            first_sentence = first_sentence[:137] + "…"
        y = max(y + 10, _BODY_Y)
        for line in _wrap(first_sentence, f_body, _TEXT_MAX_W)[:2]:
            draw.text((_TEXT_X, y), line, font=f_body, fill=_WHITE)
            y += 28

    # 7. Encode and return
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93, optimize=True)
    return buf.getvalue()
