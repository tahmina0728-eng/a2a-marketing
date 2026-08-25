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

# Background fill colour per sub-brand template (non-default templates)
_BG = {
    "aster":        (0,   124, 195),   # Infosys Blue #007CC3
    "topaz+cobalt": (155,  47, 172),   # Purple       #9B2FAC
    "speaker":      (212, 136,  15),   # Amber        #D4880F
}

# IT Services color themes — 4 variants of the default blue template
_THEMES: dict[str, tuple[int, int, int]] = {
    "blue":        (0,   124, 195),   # Infosys Blue (default)
    "purple":      (155,  53, 181),   # Light Purple
    "amber":       (212, 136,  15),   # Gold/Amber
    "deep-purple": (107,  47, 160),   # Deep Purple
}
_BLUE_SRC = (0, 124, 195)  # source blue pixels to recolor in template


def _recolor_bg(
    img: Image.Image,
    tgt: tuple[int, int, int],
    tol: int = 55,
    amplify: float = 1.0,
) -> Image.Image:
    """Recolor blue background to target color, preserving the template grid texture.

    Each blue-ish pixel keeps its relative lightness offset from the source blue
    and that offset is applied (optionally amplified) to the target color:
        new_pixel = target + (old_pixel - source_blue) * amplify

    amplify > 1.0 makes the grid more visible — needed for blue→blue because
    blue-on-blue grid contrast is perceptually much lower than amber/purple-on-self.
    """
    import numpy as np
    arr  = np.array(img, dtype=np.float32)
    src  = np.array(_BLUE_SRC, dtype=np.float32)
    tgt_f = np.array(tgt, dtype=np.float32)

    diff = arr - src                            # signed per-pixel offset from source blue
    mask = np.abs(diff).max(axis=2) < tol      # pixels close enough to source blue

    new_arr = arr.copy()
    for c in range(3):
        new_arr[:, :, c] = np.where(
            mask,
            np.clip(tgt_f[c] + diff[:, :, c] * amplify, 0, 255),
            arr[:, :, c],
        )
    return Image.fromarray(new_arr.astype(np.uint8))

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
_CLEAR_RECT = (116, 200, 780, 470)   # (x1, y1, x2, y2) — wide enough to cover all placeholder text rows

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
    color_theme:  str = "blue",
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
        color_theme:  IT Services color variant: "blue" | "purple" | "amber" | "deep-purple"
    """
    headline = headline.replace(".", "").rstrip(" ,;:!?")
    subline  = subline.replace(".", "").rstrip(" ,;:!?")
    cta      = cta.replace(".", "").rstrip(" ,;:!?")

    key      = _tpl_key(sub_brand)
    tpl_path = _TPL.get(key, _TPL["default"])

    if key == "default":
        # IT Services: color theme controls background; recolor template if needed
        bg_rgb = _THEMES.get(color_theme, _THEMES["blue"])
    else:
        # Sub-brand template: use its own background color, no recoloring
        bg_rgb = _BG.get(key, _THEMES["blue"])
        color_theme = "blue"  # suppress recolor for sub-brand templates

    import numpy as np
    # 1. Load and resize template
    img = Image.open(tpl_path).convert("RGB")
    img = img.resize((_W, _H), Image.LANCZOS)

    # 2. Clean placeholder text BEFORE recoloring.
    # The template has white text ("Heading", "Sub headings", "Text") with JPEG
    # anti-aliasing edges whose pixel values range from ~50 to ~220 — far above
    # the background grid (which stays within ±15 units of source blue).
    # Replacing them NOW (before recolor) means the cleaned zone gets mapped
    # cleanly to the target colour with no ghost text in any of the 4 themes.
    x1, y1, x2, y2 = _CLEAR_RECT
    patch_orig = np.array(img.crop((x1, y1, x2, y2)), dtype=np.float32)
    src_f = np.array(_BLUE_SRC, dtype=np.float32)
    # Any pixel whose max-channel diff from source blue exceeds 18 is text/JPEG edge.
    # Background grid pixels vary by ≤15 units; threshold of 18 gives 3 units of buffer
    # while catching the faint anti-aliasing halos that the previous threshold missed.
    not_bg = np.abs(patch_orig - src_f).max(axis=2) > 18
    for c in range(3):
        patch_orig[:, :, c] = np.where(not_bg, src_f[c], patch_orig[:, :, c])
    img.paste(Image.fromarray(patch_orig.astype(np.uint8)), (x1, y1))

    # 3. Apply color theme — run for ALL colors.
    # Blue→blue is a no-op on hue, but amplify=3.0 brings up the subtle blue grid
    # to the same perceptual contrast level as amber/purple (which naturally have
    # high contrast because their small B-channel amplifies the same +10 pixel offset).
    amp = 3.0 if color_theme == "blue" else 1.0
    img = _recolor_bg(img, bg_rgb, amplify=amp)

    draw = ImageDraw.Draw(img)

    # 4. Load fonts per Infosys brand spec
    # Myriad Pro Bold = headline (matches template "Heading" — broad, heavy, non-condensed)
    # Myriad Pro SemiBold = sub-heading / attribution
    # Myriad Pro Regular = CTA
    f_head = _load_font("MYRIADPRO-BOLD.OTF",     48)   # headline — matches Campaign2_1 weight
    f_sub  = _load_font("MYRIADPRO-SEMIBOLD.OTF", 26)   # sub-heading
    f_cta  = _load_font("MYRIADPRO-REGULAR.OTF",  20)   # CTA caption

    # 5. Headline — Myriad Pro Bold, flows from _HEADING_Y, up to 3 lines
    y = _HEADING_Y
    for line in _wrap(headline, f_head, _TEXT_MAX_W)[:3]:
        draw.text((_TEXT_X, y), line, font=f_head, fill=_WHITE)
        y += 58   # 48px + 10px leading

    # 6. Sub-heading — flows immediately below headline, no floor gap
    if subline:
        y += 14   # fixed gap between headline block and sub-heading
        for line in _wrap(subline, f_sub, _TEXT_MAX_W)[:2]:
            draw.text((_TEXT_X, y), line, font=f_sub, fill=_WHITE)
            y += 32   # 26px + 6px leading

    # 7. CTA — flows immediately below sub-heading
    if cta:
        y += 16   # fixed gap between sub-heading and CTA
        draw.text((_TEXT_X, y), cta[:50], font=f_cta, fill=_WHITE)

    # 8. Encode and return
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93, optimize=True)
    return buf.getvalue()
