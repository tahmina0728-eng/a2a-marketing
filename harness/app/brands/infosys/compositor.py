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


def _wrap_balanced(text: str, font: ImageFont.FreeTypeFont, max_w: int, max_lines: int = 3) -> list[str]:
    """Wrap text with balanced line lengths — each line as equal width as possible.

    For a headline that needs 2 lines, finds the word-split that minimises the
    difference between line widths (not greedy first-fit), matching the reference
    KV layout where short headlines split evenly across two compact lines.
    Falls back to greedy _wrap() when the text needs 3+ lines.
    """
    words = text.split()
    if not words:
        return []

    def _w(s: str) -> float:
        try:
            return font.getlength(s)
        except Exception:
            return len(s) * (font.size // 2)

    # Fits on one line — no wrapping needed
    if _w(text) <= max_w:
        return [text]

    # Try balanced 2-line split: pick the split that minimises max(w1, w2)
    best_split: int | None = None
    best_score = float("inf")
    for i in range(1, len(words)):
        l1 = " ".join(words[:i])
        l2 = " ".join(words[i:])
        w1, w2 = _w(l1), _w(l2)
        if w1 <= max_w and w2 <= max_w:
            score = max(w1, w2)          # minimise the longest line
            if score < best_score:
                best_score = score
                best_split = i

    if best_split is not None:
        return [" ".join(words[:best_split]), " ".join(words[best_split:])]

    # Can't fit in 2 balanced lines — greedy wrap at max_w
    return _wrap(text, font, max_w)[:max_lines]


# ── Speaker / executive circle layout constants ───────────────────────────────
_SPK_CX = 870   # circle center x  (right half of 1200px canvas)
_SPK_CY = 270   # circle center y  (vertically centred in 627px canvas)
_SPK_R  = 118   # outer radius including white border
_SPK_BORDER = 6 # white border ring width


def _paste_speaker_circle(
    img: Image.Image,
    image_bytes: bytes,
    name: str,
    title: str,
) -> Image.Image:
    """
    Composite a circular executive headshot onto the right zone of the KV,
    followed by name (bold) and title (regular) centred below the circle.
    Matches the layout used in Campaign4_2/3/4 reference assets.
    """
    inner_r   = _SPK_R - _SPK_BORDER
    inner_d   = inner_r * 2
    outer_d   = _SPK_R * 2

    # Load headshot, centre-crop to square, resize to inner diameter
    headshot = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = headshot.size
    side = min(w, h)
    headshot = headshot.crop(((w - side) // 2, (h - side) // 2,
                               (w + side) // 2, (h + side) // 2))
    headshot = headshot.resize((inner_d, inner_d), Image.LANCZOS)

    # Circular mask for the headshot
    mask = Image.new("L", (inner_d, inner_d), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, inner_d - 1, inner_d - 1), fill=255)
    headshot_rgba = headshot.convert("RGBA")
    headshot_rgba.putalpha(mask)

    # White border disc (full circle, slightly larger)
    border_disc = Image.new("RGBA", (outer_d, outer_d), (0, 0, 0, 0))
    ImageDraw.Draw(border_disc).ellipse((0, 0, outer_d - 1, outer_d - 1),
                                        fill=(255, 255, 255, 255))

    # Composite: paste border disc, then headshot centred inside it
    img_rgba = img.convert("RGBA")
    bx = _SPK_CX - _SPK_R
    by = _SPK_CY - _SPK_R
    img_rgba.paste(border_disc, (bx, by), border_disc)
    img_rgba.paste(headshot_rgba, (bx + _SPK_BORDER, by + _SPK_BORDER), headshot_rgba)
    img = img_rgba.convert("RGB")

    # Name + title below circle
    f_name  = _load_font("MYRIADPRO-BOLD.OTF",    26)
    f_title = _load_font("MYRIADPRO-REGULAR.OTF", 20)
    draw = ImageDraw.Draw(img)

    name_y  = _SPK_CY + _SPK_R + 18
    title_y = name_y + 34

    try:
        name_w  = f_name.getlength(name)
        title_w = f_title.getlength(title) if title else 0
    except Exception:
        name_w  = len(name)  * 13
        title_w = len(title) * 10

    draw.text((_SPK_CX - name_w  // 2, name_y),  name,  font=f_name,  fill=_WHITE)
    if title:
        draw.text((_SPK_CX - title_w // 2, title_y), title, font=f_title, fill=_WHITE)

    return img


# ── Public API ────────────────────────────────────────────────────────────────

def generate_kv(
    headline:            str,
    subline:             str = "",
    cta:                 str = "",
    sub_brand:           str = "",
    aspect_ratio:        str = "16:9",
    color_theme:         str = "blue",
    speaker_image_b64:   str = "",
    speaker_name:        str = "",
    speaker_title:       str = "",
    content_type_badge:  str = "",
) -> bytes:
    """
    Composite an Infosys LinkedIn KV from the brand template.
    Returns JPEG bytes at 1200×627.

    Args:
        headline:           Campaign headline (from Ideon copy deck)
        subline:            Sub-heading / support line
        cta:                Short CTA text shown in the lower text zone (≤ 5 words)
        sub_brand:          e.g. "Infosys Aster (Healthcare)", "Infosys Topaz (AI/Cloud)"
        aspect_ratio:       Ignored for now (always 16:9 LinkedIn); reserved for future formats
        color_theme:        IT Services color variant: "blue" | "purple" | "amber" | "deep-purple"
        speaker_image_b64:  Base-64 JPEG/PNG of executive headshot — triggers circle layout
        speaker_name:       Executive name shown below circle, e.g. "Salil Parekh"
        speaker_title:      Role/company line, e.g. "CEO & MD, Infosys"
        content_type_badge: Optional label above headline, e.g. "BYLINE" or "MEDIA ARTICLE"
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

    # 1. Load and resize template
    img = Image.open(tpl_path).convert("RGB")
    img = img.resize((_W, _H), Image.LANCZOS)

    # 2. Flood the placeholder text zone with solid source blue BEFORE recoloring.
    # Pixel-threshold detection can't reliably separate JPEG anti-aliasing halos
    # from grid texture — both sit in the same 0–18 unit range from source blue.
    # A solid fill is 100% reliable: the recolor step then maps the flat blue to
    # the target color, and the text zone ends up clean on all 4 themes.
    x1, y1, x2, y2 = _CLEAR_RECT
    img.paste(Image.new("RGB", (x2 - x1, y2 - y1), _BLUE_SRC), (x1, y1))

    # 3. Apply color theme — run for ALL colors.
    # Blue→blue is a no-op on hue, but amplify=3.0 brings up the subtle blue grid
    # to the same perceptual contrast level as amber/purple (which naturally have
    # high contrast because their small B-channel amplifies the same +10 pixel offset).
    amp = 3.0 if color_theme == "blue" else 1.0
    img = _recolor_bg(img, bg_rgb, amplify=amp)

    draw = ImageDraw.Draw(img)

    # 4. Load fonts per Infosys brand spec
    f_head  = _load_font("MYRIADPRO-BOLD.OTF",     48)
    f_sub   = _load_font("MYRIADPRO-SEMIBOLD.OTF", 26)
    f_cta   = _load_font("MYRIADPRO-REGULAR.OTF",  20)
    f_badge = _load_font("MYRIADPRO-BOLD.OTF",     18)

    # 5. Optional content-type badge (BYLINE / MEDIA ARTICLE) above headline
    y = _HEADING_Y
    if content_type_badge:
        badge_text = content_type_badge.upper()
        try:
            badge_w = f_badge.getlength(badge_text)
        except Exception:
            badge_w = len(badge_text) * 9
        pad_x, pad_y = 10, 5
        bx2 = _TEXT_X + int(badge_w) + pad_x * 2
        by2 = y + 28
        draw.rectangle((_TEXT_X, y, bx2, by2), outline=_WHITE, width=2)
        draw.text((_TEXT_X + pad_x, y + pad_y), badge_text, font=f_badge, fill=_WHITE)
        y = by2 + 18   # shift headline below badge

    # 6. Headline — Myriad Pro Bold, balanced split, tight leading (no gap between lines)
    head_lines = _wrap_balanced(headline, f_head, _TEXT_MAX_W, max_lines=3)
    for line in head_lines:
        draw.text((_TEXT_X, y), line, font=f_head, fill=_WHITE)
        y += 50   # 48px font + 2px — tight, no visible gap between lines

    # 7. Sub-heading — gap after headline block, then tight leading between sub lines
    if subline:
        y += 14   # gap between headline block and subheading
        sub_lines = _wrap_balanced(subline, f_sub, _TEXT_MAX_W, max_lines=2)
        for line in sub_lines:
            draw.text((_TEXT_X, y), line, font=f_sub, fill=_WHITE)
            y += 28   # 26px font + 2px — tight

    # 8. CTA — flows immediately below sub-heading
    if cta:
        y += 16
        draw.text((_TEXT_X, y), cta[:50], font=f_cta, fill=_WHITE)

    # 9. Speaker circle — composited last so it sits on top
    if speaker_image_b64 and speaker_name:
        import base64
        try:
            img_bytes = base64.b64decode(speaker_image_b64)
            img = _paste_speaker_circle(img, img_bytes, speaker_name, speaker_title)
        except Exception:
            pass  # silently skip if decode/composite fails

    # 10. Encode and return
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93, optimize=True)
    return buf.getvalue()
