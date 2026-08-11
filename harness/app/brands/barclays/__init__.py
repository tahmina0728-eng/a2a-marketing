"""
Barclays brand module.

Brand rules, partnership claims, creative concepts, and reel structures are
stored in JSON files in this directory. Edit those files to change brand
behaviour; touch Python only to change rendering logic.

Directory layout:
  brand.json                       — brand constants, fonts, copy rules
  assets.json                      — asset registry (logos, lockups, channels)
  campaigns/wimbledon/
    campaign.json                  — partnership profile + approved claims
    concepts.json                  — 5 creative territories + image prompts
    reel-concepts.json             — 4-beat reel structures per territory
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Load JSON configs at import time ──────────────────────────────────────────

_HERE = Path(__file__).parent


def _load(rel: str) -> dict:
    with open(_HERE / rel, encoding="utf-8") as f:
        return json.load(f)


_brand = _load("brand.json")
_assets = _load("assets.json")
_wimb_campaign = _load("campaigns/wimbledon/campaign.json")
_wimb_concepts = _load("campaigns/wimbledon/concepts.json")
_wimb_reels = _load("campaigns/wimbledon/reel-concepts.json")


# ── Brand constants (derived from brand.json) ─────────────────────────────────

BLUE: tuple = tuple(_brand["colors"]["blue"]["rgb"])
NIGHT: tuple = tuple(_brand["colors"]["night"]["rgb"])
WHITE: tuple = tuple(_brand["colors"]["white"]["rgb"])
BLACK: tuple = (0, 0, 0)
FONTS: list = [_brand["fonts"]["headline"]["stem"], _brand["fonts"]["body"]["stem"]]
PALETTE_LOCK: str = _brand["palette_lock"]
PALETTE_STR: str = _brand["palette_str"]

BRAND_MAGIC: dict = {
    "effects":  _brand["visual"]["effects"],
    "model":    _brand["visual"]["subject"],
    "hair":     "natural, understated — this is a financial services brand, not a beauty campaign",
    "bg":       _brand["visual"]["background"],
    "wardrobe": _brand["visual"]["wardrobe"],
    "energy":   _brand["visual"]["energy"],
}


# ── Asset registry ────────────────────────────────────────────────────────────

def get_asset(asset_type: str, campaign: str = "", channel: str = "") -> str:
    """Return the filename or stem for a given asset_type / campaign / channel.

    asset_type: "reel_logo" | "lockup" | "shield"
    campaign:   "wimbledon" (or empty for default)
    channel:    "instagram" | "linkedin" | etc.
    """
    partnerships = _assets.get("partnerships", {})

    if asset_type == "reel_logo":
        if campaign and campaign in partnerships:
            return partnerships[campaign]["reel_logo_stem"]
        return _assets["channel_logo_stem"].get(channel, _assets["channel_logo_stem"]["default"])

    if asset_type == "lockup":
        if campaign and campaign in partnerships:
            # Return approved_lockup if one exists, otherwise the composite asset
            return partnerships[campaign].get("approved_lockup") or partnerships[campaign]["lockup"]
        return _assets["logos"]["primary_white"]

    if asset_type == "shield":
        if campaign and campaign in partnerships:
            return partnerships[campaign]["shield"]

    return _assets["logos"]["primary_white"]


def reel_logo_hint(is_wimbledon: bool = False) -> str:
    """Return the logo filename stem for reel overlay selection."""
    return get_asset("reel_logo", campaign="wimbledon" if is_wimbledon else "")


# ── Font resolution ───────────────────────────────────────────────────────────

def resolve_font_path(brand_base_dir: "str | Path") -> "str | None":
    """Return the best available Effra font path from the brand base folder."""
    font_dir = Path(brand_base_dir) / "Font"
    for spec in [_brand["fonts"]["headline"], _brand["fonts"]["body"]]:
        for filename in spec["files"]:
            p = font_dir / filename
            if p.exists():
                return str(p)
    return None


# ── Copy agent ────────────────────────────────────────────────────────────────

def _detect_wimbledon(machine_brief: dict) -> bool:
    """Detect Wimbledon campaign from structured field first, then keywords."""
    # 1. Structured field (preferred — set by campaign/brief form)
    campaign_type = (
        machine_brief.get("campaign_type") or
        (machine_brief.get("campaign") or {}).get("property") or
        (machine_brief.get("campaign") or {}).get("id") or ""
    ).lower()
    if "wimbledon" in campaign_type:
        return True

    # 2. Keyword fallback across detection fields
    detection = _wimb_campaign.get("detection", {})
    keywords = detection.get("keywords", ["wimbledon"])
    fields   = detection.get("fields", ["fan_truth"])
    for field in fields:
        val = str(machine_brief.get(field) or "").lower()
        if any(kw in val for kw in keywords):
            return True

    return False


def copy_prompt_block(machine_brief: dict) -> str:
    """Return brand-specific copy rules injected into the copy agent prompt."""
    br = _brand
    rules = br["rules"]
    copy_r = br["copy_rules"]

    no_jargon = ", ".join(f'"{w}"' for w in rules["no_financial_jargon"])
    subline_examples = "\n".join(
        f'  "{ex["headline"]}"\n  → "{ex["subline"]}"'
        for ex in copy_r["subline_examples"]
    )
    cta_options = " / ".join(f'"{c}"' for c in copy_r["cta_options"])
    if _detect_wimbledon(machine_brief):
        wc = _wimb_campaign["copy_rules"]
        directions = " / ".join(wc.get("creative_direction", []))
        avoid      = ", ".join(f'"{a}"' for a in wc.get("avoid", []))
        wimbledon_note = (
            f"\n\nWIMBLEDON PARTNERSHIP ({_wimb_campaign['relationship']['display_name']}):\n"
            f"  Creative direction: {directions}\n"
            f"  Avoid: {avoid}"
        )
    else:
        wimbledon_note = ""

    return f"""

BRAND-SPECIFIC RULES — BARCLAYS (FINANCIAL SERVICES):
This is a regulated financial services brand operating within the FCA framework.
The campaign platform is "{br['campaign_platform']}" — quiet confidence, human truth, never hype.

HEADLINE RULES:
  – Understated, human, emotionally resonant — not a product pitch
  – Never: {no_jargon}
  – Never financial jargon or rate/return claims
  – Must work as a standalone statement at billboard scale

MEDIUM.SUBLINE RULES (THIS IS RENDERED DIRECTLY ON THE CAMPAIGN BANNER):
  – Completes the headline's emotional territory by naming what Barclays does
  – Speaks to the human benefit, not the product feature
  – Feels like a natural continuation of the headline — not a separate thought
  – ≤20 words, no financial jargon

SUBLINE EXAMPLES BY HEADLINE:
{subline_examples}

CTA: {cta_options} — max 3 words, never salesy{wimbledon_note}"""


# ── Wimbledon concept selection ───────────────────────────────────────────────

def _format_direction(concept: dict) -> str:
    """Format a structured creative_direction dict into a text block for the image agent.

    Combines concept title, template, and all creative_direction keys into a
    descriptive brief the LLM can use to produce a detailed image prompt.
    Brand colours are NOT included here — the Brand Skill supplies those.
    """
    d = concept.get("creative_direction", {})
    title    = concept.get("title", "")
    template = concept.get("template", "")

    # Build ordered lines, skipping absent keys
    fields = [
        ("subject",       d.get("subject")),
        ("narrative",     d.get("narrative")),
        ("action",        d.get("action")),
        ("relationship",  d.get("relationship")),
        ("setting",       d.get("setting")),
        ("emotion",       d.get("emotion")),
        ("composition",   d.get("composition")),
        ("lighting",      d.get("lighting")),
        ("photography",   d.get("photography")),
    ]
    parts = [f"{k.capitalize()}: {v}" for k, v in fields if v]
    detail = " ".join(parts)
    return (
        f"Concept — {title} ({template}): {detail}. "
        f"NO logos, NO text, NO brand marks in the generated image."
    )


def select_concepts(
    big_idea_seed: str,
    copy_headline: str,
    fan_truth: str,
    creative_theme: str = "",
) -> tuple:
    """Return (concept_1_direction, concept_2_direction) formatted for the image agent.

    Each value is a text block derived from creative_direction in concepts.json —
    not a stored prompt blob. Brand colours come from the Brand Skill, not here.

    Prefers a structured creative_theme key emitted by the copy/campaign agent.
    Falls back to keyword matching when creative_theme is absent.
    """
    themes = _wimb_concepts["themes"]

    def _pair(theme: dict) -> tuple:
        return (
            _format_direction(theme["concepts"][0]),
            _format_direction(theme["concepts"][1]),
        )

    # 1. Structured theme key (preferred)
    if creative_theme:
        for theme in themes:
            if theme["id"] == creative_theme:
                return _pair(theme)

    # 2. Keyword fallback (POC — replace when copy agent emits creative_theme).
    # Sort all keywords longest-first so "backing progress" matches before "progress".
    seed = " ".join(filter(None, [big_idea_seed, copy_headline, fan_truth])).lower()
    kw_index = [(kw, theme) for theme in themes for kw in theme.get("keywords", [])]
    kw_index.sort(key=lambda p: -len(p[0]))
    for kw, theme in kw_index:
        if kw in seed:
            return _pair(theme)

    # 3. Default theme
    default_id = _wimb_concepts.get("default_theme", "partnership")
    for theme in themes:
        if theme["id"] == default_id:
            return _pair(theme)

    return _pair(themes[0])


def select_concept(
    big_idea_seed: str,
    copy_headline: str,
    fan_truth: str,
    creative_theme: str = "",
    concept_id: str = "",
) -> dict:
    """Return the best-matching concept dict (raw fields, not pre-formatted string).

    Priority:
      1. Exact concept_id match (e.g. "c1_journey")
      2. Structured creative_theme match (e.g. "progress")
      3. Keyword match across prompt + headline + fan_truth
      4. Default theme first concept
    """
    themes = _wimb_concepts["themes"]

    # 1. Exact concept_id
    if concept_id:
        for theme in themes:
            for concept in theme["concepts"]:
                if concept["id"] == concept_id:
                    return concept

    # 2. Structured theme key
    if creative_theme:
        for theme in themes:
            if theme["id"] == creative_theme:
                return theme["concepts"][0]

    # 3. Keyword fallback — longest match first
    seed = " ".join(filter(None, [big_idea_seed, copy_headline, fan_truth])).lower()
    kw_index = [(kw, theme) for theme in themes for kw in theme.get("keywords", [])]
    kw_index.sort(key=lambda p: -len(p[0]))
    for kw, theme in kw_index:
        if kw in seed:
            return theme["concepts"][0]

    # 4. Default
    default_id = _wimb_concepts.get("default_theme", "partnership")
    for theme in themes:
        if theme["id"] == default_id:
            return theme["concepts"][0]

    return themes[0]["concepts"][0]


# ── Reel — scene direction ────────────────────────────────────────────────────

def _pick_reel_concept(big_idea: str, fan_truth: str, copy_headline: str, concept_key: str = "") -> tuple:
    """Return (concept_key, concept_dict) from reel-concepts.json."""
    concepts = _wimb_reels["concepts"]

    if concept_key and concept_key in concepts:
        return concept_key, concepts[concept_key]

    # Sort all keywords longest-first so multi-word phrases match before single words
    seed = " ".join(filter(None, [big_idea, fan_truth, copy_headline])).lower()
    kw_index = [
        (kw, ckey, cdata)
        for ckey, cdata in concepts.items()
        for kw in cdata.get("keywords", [])
    ]
    kw_index.sort(key=lambda p: -len(p[0]))
    for kw, ckey, cdata in kw_index:
        if kw in seed:
            return ckey, cdata

    default = _wimb_reels["default_concept"]
    return default, concepts[default]


def reel_scene(
    big_idea: str,
    fan_truth: str,
    copy_headline: str,
    concept_key: str = "",
) -> str:
    """Return the 4-beat Veo scene description for the matching reel concept."""
    _, concept = _pick_reel_concept(big_idea, fan_truth, copy_headline, concept_key)
    scenes = concept["scenes"]
    beats = " ".join(
        f"Beat {s['scene_id']} ({s['start']}–{s['end']}s): {s['visual']} "
        f"Audio: {s['audio']}."
        for s in scenes
    )
    return f"{concept['title']}. {beats} NO logos, NO text in generated footage."


def reel_storyboard(
    big_idea: str,
    fan_truth: str,
    copy_headline: str = "",
    concept_key: str = "",
) -> dict:
    """Return structured storyboard JSON with full scene schema.

    Scene fields: scene_id, start, end, camera, visual, emotion, audio, transition.
    Copy is separated into copy_slots; use copy_headline to fill the end_frame slot.
    """
    _, concept = _pick_reel_concept(big_idea, fan_truth, copy_headline, concept_key)

    # Fulfill copy slots — copy_headline goes to the end_frame slot
    fulfilled = []
    for slot in concept.get("copy_slots", []):
        entry = dict(slot)
        if copy_headline and slot["id"] == "end_frame":
            entry["copy"] = copy_headline
        fulfilled.append(entry)

    return {
        "concept":        concept["title"],
        "creative_theme": concept.get("creative_theme"),
        "duration":       _wimb_reels["duration_seconds"],
        "format":         _wimb_reels["format"],
        "brand":          "Barclays × Wimbledon",
        "scenes":         [dict(s) for s in concept["scenes"]],
        "copy_slots":     fulfilled,
    }


# ── Reel — Veo config ─────────────────────────────────────────────────────────

def reel_veo_rules() -> str:
    """Return Barclays-specific Veo prompt rules."""
    voiceover = (
        "Subtle ambient sound design — crowd ambience, heartbeat, musical resolve — "
        "no dialogue voiceover unless brand-approved."
    )
    return (
        "- Photorealistic premium UK financial-services advertising quality — NOT FMCG\n"
        f"- Deep Barclays Night (#1A2142) and Barclays Blue (#00AEEF) colour palette\n"
        "- Cinematic, understated, emotionally powerful — sophisticated not flashy\n"
        f"- AUDIO: {voiceover}\n"
        "- NO product packshots, NO bank app screens, NO financial data\n"
        "- NO text or typography in the generated footage — text composited separately\n"
        "- NO logos or brand marks — composited after generation\n"
        "- Wimbledon atmosphere: immaculate grass, English summer light, authentic crowd energy"
    )


def reel_negative_prompt() -> str:
    """Return Veo negative prompt for Barclays reels, sourced from reel-concepts.json."""
    return ", ".join(_wimb_reels["generation"]["negative_prompt"])


# ── Banner overlay ────────────────────────────────────────────────────────────
#
# Wimbledon path — fully deterministic compositor (spec-driven):
#   1. _open_photo()              — load + resize the source image
#   2. _create_canvas()           — Barclays Blue border frame
#   3. _render_border_eagle()     — white eagle in top-right border cell
#   4. _apply_wimbledon_overlay() — ALL brand elements from assets.json overlay spec:
#        headline (Effra Bold, white, responsive, auto-wrap + shrink)
#        subline  (Effra Regular, white, responsive, auto-wrap)
#        CTA      (rounded-rect, #00AEEF bg, #1A2142 text)
#        logo     (approved barclays-wimbledon_wb.png lockup, bottom-right)
#
# Non-Wimbledon path (unchanged):
#   gradient scrim → _render_headline → _render_standard_bottom
#  11. Encode JPEG

def _open_photo(img_data: bytes):
    from PIL import Image
    import io as _io
    Image.MAX_IMAGE_PIXELS = None
    photo = Image.open(_io.BytesIO(img_data)).convert("RGBA")
    if max(photo.size) > 1400:
        _sc = 1400 / max(photo.size)
        photo = photo.resize((int(photo.width * _sc), int(photo.height * _sc)), Image.LANCZOS)
    return photo


def _create_canvas(photo, blue: tuple):
    from PIL import Image
    PW, PH = photo.size
    # Base border on the LONGER side so both 16:9 and 9:16 get the same
    # absolute border thickness (using min gives a 18px floor for 16:9
    # landscape images where height is small, which causes the eagle to
    # bleed into the photo area).
    border = max(28, int(max(PW, PH) * 0.028))
    TW, TH = PW + border * 2, PH + border * 2
    canvas = Image.new("RGBA", (TW, TH), (*blue, 255))
    canvas.alpha_composite(photo, (border, border))
    return canvas, TW, TH, border, border, border  # canvas, TW, TH, border, PX, PY


def _logo_sibling_uris(logo_uri: str) -> list:
    """Return ordered list of sibling logo paths/URIs from assets.json priority."""
    if not logo_uri:
        return []
    names = _assets["sibling_priority"]
    if logo_uri.startswith("gs://"):
        base = logo_uri.rsplit("/", 1)[0]
        return [f"{base}/{n}" for n in names]
    from pathlib import Path as _P
    d = _P(logo_uri).parent
    return [str(d / n) for n in names if (d / n).exists()]


def _load_img_from(uri: str):
    try:
        from app.creative_pipeline import _load_bytes as _clb
        _b = _clb(uri)
        if _b:
            from PIL import Image
            import io as _io
            return Image.open(_io.BytesIO(_b)).convert("RGBA")
    except Exception:
        pass
    return None


def _load_eagle(logo_uri: str):
    """Return (eagle_for_border, eagle_for_watermark) — same source, kept separate."""
    for uri in _logo_sibling_uris(logo_uri):
        img = _load_img_from(uri)
        if img:
            return img, img.copy()
    if logo_uri:
        img = _load_img_from(logo_uri)
        if img:
            return img, img.copy()
    return None, None


def _tint_white(src):
    """Convert a logo to a white silhouette (non-white pixels → opaque white).

    If the source is already a white-on-transparent PNG (all visible pixels
    are white), the algorithm would produce a fully-transparent result.
    Detect that case and return the source unchanged so the white eagle
    remains visible on the blue border.
    """
    from PIL import Image
    pix = src.load()
    alpha = Image.new("L", src.size, 0)
    ap = alpha.load()
    has_visible = False
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = pix[x, y]
            if a > 30 and not (r > 215 and g > 215 and b > 215):
                ap[x, y] = 255
                has_visible = True
    if not has_visible:
        # Already white-on-transparent — use it directly.
        return src.copy()
    wh = Image.new("L", src.size, 255)
    return Image.merge("RGBA", [wh, wh, wh, alpha])


def _tint_color(src, rgb: tuple, alpha_val: int):
    """Tint non-background pixels to rgb at alpha_val opacity."""
    from PIL import Image
    pix = src.load()
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    op = out.load()
    r0, g0, b0 = rgb
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = pix[x, y]
            if a > 30 and not (r > 215 and g > 215 and b > 215):
                op[x, y] = (r0, g0, b0, alpha_val)
    return out


def _render_border_eagle(canvas, eagle_src, border: int, TW: int):
    if not eagle_src:
        return canvas
    from PIL import Image
    eh = max(int(border * 0.72), 16)
    ew = int(eagle_src.width * eh / eagle_src.height)
    # Clamp width so the eagle never bleeds into the photo area.
    if ew > border:
        ew = border
        eh = int(eagle_src.height * ew / eagle_src.width)
    small = eagle_src.resize((ew, eh), Image.LANCZOS)
    white = _tint_white(small)
    # Centre within the right border strip.
    ex = TW - border + (border - ew) // 2
    ey = max(0, (border - eh) // 2)
    canvas.alpha_composite(white, (ex, ey))
    return canvas


def _render_gradient_scrim(canvas, PX: int, PY: int, PW: int, PH: int, TW: int, TH: int):
    from PIL import Image, ImageDraw
    scrim = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    scrim_h = int(PH * 0.62)
    steps = 52
    for s in range(steps):
        y0 = PY + s * scrim_h // steps
        y1 = PY + (s + 1) * scrim_h // steps
        a = int(200 * (1.0 - s / steps) ** 0.52)
        sd.rectangle([PX, y0, PX + PW, y1], fill=(0, 0, 0, a))
    canvas.alpha_composite(scrim)
    return canvas


def _split_headline(headline: str) -> list:
    """Split headline into 2-3 display lines at sentence boundaries."""
    raw = (headline or "MOMENTS OF PROGRESS").split()
    sents, cur = [], []
    for w in raw:
        cur.append(w)
        if w and w[-1] in ".!?,":
            sents.append(" ".join(cur)); cur = []
    if cur:
        sents.append(" ".join(cur))
    if not sents:
        sents = [headline or "MOMENTS OF PROGRESS"]
    if len(sents) > 3:
        n = len(raw)
        sents = [" ".join(raw[:n // 3]), " ".join(raw[n // 3:(n * 2) // 3]), " ".join(raw[(n * 2) // 3:])]
    if len(sents) == 1 and len(raw) >= 3:
        mid = len(raw) // 2
        sents = [" ".join(raw[:mid]), " ".join(raw[mid:])]
    return sents


def _render_headline(draw, headline: str, is_wimbledon: bool, fnt, text_x: int, text_y: int, PW: int, PH: int):
    """Render headline; last line in Barclays Blue for Wimbledon. Returns (draw, bottom_y, head_sz)."""
    _BLUE, _WHITE = BLUE, WHITE
    head_sz = max(28, int(PH * 0.092))
    text_max_w = int(PW * 0.75)
    while head_sz > 14:
        tf = fnt(head_sz)
        words = (headline or "").split()
        test = " ".join(words[:5]) if len(words) > 5 else " ".join(words)
        bb = tf.getbbox(test)
        if (bb[2] - bb[0]) <= text_max_w:
            break
        head_sz -= 2

    sents = _split_headline(headline)
    hf = fnt(head_sz)
    line_h = int(head_sz * 1.20)
    for li, line in enumerate(sents):
        col = _BLUE if (is_wimbledon and li == len(sents) - 1) else _WHITE
        draw.text((text_x, text_y + li * line_h), line, fill=col, font=hf)
    return draw, text_y + len(sents) * line_h, head_sz


def _wrap_text(draw, text: str, font, max_w: int) -> list:
    """Word-wrap text to fit within max_w pixels. Returns list of lines."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _render_subcopy(draw, copy_subline: str, is_wimbledon: bool, fnt, text_x: int, head_bottom: int, head_sz: int, PH: int, PW: int = 0):
    """Render Wimbledon sub-copy + 'Proud partner' line. Returns draw."""
    if not is_wimbledon:
        return draw
    _WHITE = WHITE
    sub_sz  = max(14, int(PH * 0.030))
    sub_fnt = fnt(sub_sz)
    sub_lh  = int(sub_sz * 1.35)

    sub_y = head_bottom + int(head_sz * 0.4)
    sub_text = (copy_subline.strip() if copy_subline and copy_subline.strip()
                else "Behind every champion is support that believes.")

    # Word-wrap to 65% of photo width so text never bleeds off the right edge.
    max_sub_w = int(PW * 0.65) if PW else int(PH * 0.55)
    lines = _wrap_text(draw, sub_text, sub_fnt, max_sub_w)
    for line in lines:
        draw.text((text_x, sub_y), line, fill=_WHITE, font=sub_fnt)
        sub_y += sub_lh

    proud_sz  = max(9, int(PH * 0.019))
    proud_fnt = fnt(proud_sz)
    proud_label = "Proud partner of Wimbledon"
    draw.text((text_x, sub_y + int(proud_sz * 0.3)), proud_label, fill=_WHITE, font=proud_fnt)
    return draw


def _render_eagle_watermark(canvas, eagle_orig, PX: int, PY: int, PW: int, PH: int):
    """Render large Barclays Blue eagle watermark bottom-right (Wimbledon only)."""
    if not eagle_orig:
        return canvas
    try:
        from PIL import Image
        wm_w = int(PW * 0.38)
        wm_h = int(eagle_orig.height * wm_w / eagle_orig.width)
        wm = eagle_orig.resize((wm_w, wm_h), Image.LANCZOS)
        tinted = _tint_color(wm, BLUE, 90)
        wx0 = PX + PW - int(wm_w * 0.78)
        wy0 = PY + PH - int(wm_h * 0.85)
        canvas.alpha_composite(tinted, (wx0, wy0))
    except Exception:
        pass
    return canvas


def _render_bottom_bar(canvas, PX: int, PY: int, PW: int, PH: int, TW: int, TH: int, is_wimbledon: bool):
    """Render the dark semi-transparent bottom bar. Returns (canvas, bar_y, bar_h)."""
    from PIL import Image, ImageDraw
    bar_h = int(PH * 0.22)
    bar_y = PY + PH - bar_h
    bar_alpha = 105 if is_wimbledon else 155
    layer = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([PX, bar_y, PX + PW, PY + PH], fill=(*BLACK, bar_alpha))
    canvas.alpha_composite(layer)
    return canvas, bar_y, bar_h


def _load_logo_file(logo_uri: str, names: list):
    """Load the first matching logo file from the same folder as logo_uri."""
    from pathlib import Path as _P
    if logo_uri and not logo_uri.startswith("gs://"):
        d = _P(logo_uri).parent
        for n in names:
            if (d / n).exists():
                img = _load_img_from(str(d / n))
                if img:
                    return img
    elif logo_uri and logo_uri.startswith("gs://"):
        base = logo_uri.rsplit("/", 1)[0]
        for n in names:
            img = _load_img_from(f"{base}/{n}")
            if img:
                return img
    return None


def _render_wimbledon_lockup(canvas, draw, bar_y: int, bar_h: int, PX: int, PW: int, text_x: int, margin: int, logo_uri: str, fnt):
    """Render the Wimbledon bottom bar.

    Layout matches real Barclays × Wimbledon ads:
      [Wimbledon badge]  OFFICIAL BANK        [Barclays eagle + wordmark]
                         OF WIMBLEDON

    The Wimbledon badge PNG already carries its own circular white background —
    no additional white pill is added (which was causing the "sticker" look).
    """
    from PIL import Image, ImageDraw as _ID
    _WHITE = WHITE
    partner_assets = _assets["partnerships"]["wimbledon"]

    shield_right = text_x  # tracks where badge ends so text can start after it

    # Left: Wimbledon shield — render directly; badge PNG has its own white circle
    shield = _load_logo_file(logo_uri, [partner_assets["shield"], partner_assets["lockup"]])
    if shield:
        sh  = max(24, int(bar_h * 0.62))
        sw  = int(shield.width * sh / shield.height)
        shield = shield.resize((sw, sh), Image.LANCZOS)
        sly = bar_y + (bar_h - sh) // 2
        canvas.alpha_composite(shield, (text_x, sly))
        shield_right = text_x + sw + max(10, int(bar_h * 0.14))
        draw = _ID.Draw(canvas)

    # ── Pre-calculate right lockup width so center text never overlaps it ────
    sym = _load_logo_file(logo_uri, [_assets["logos"]["symbol_white"]])
    sym_h = sym_w = bk_w = bk_h = gap = bk_fnt = bk_bb = 0
    if sym:
        sym_h  = max(22, int(bar_h * 0.50))
        sym_w  = int(sym.width * sym_h / sym.height)
        sym    = sym.resize((sym_w, sym_h), Image.LANCZOS)
        sym    = _tint_white(sym)
        bk_sz  = max(12, int(sym_h * 0.58))
        bk_fnt = fnt(bk_sz)
        bk_bb  = draw.textbbox((0, 0), "BARCLAYS", font=bk_fnt)
        bk_w   = bk_bb[2] - bk_bb[0]
        bk_h   = bk_bb[3] - bk_bb[1]
        gap    = max(5, int(sym_h * 0.15))
    right_lockup_w   = sym_w + gap + bk_w if sym_w else 0
    right_lockup_left = PX + PW - right_lockup_w - margin  # where right section starts

    # Centre: "OFFICIAL BANK / OF WIMBLEDON" in white — matches real ad lockup
    _label = _wimb_campaign["relationship"].get(
        "bar_label",
        _wimb_campaign["relationship"]["short_display_name"],
    ).upper()
    if " OF " in _label:
        _idx  = _label.index(" OF ")
        lines = [_label[:_idx], "OF " + _label[_idx + 4:]]
    else:
        lines = [_label]
    ct_sz    = max(8, int(bar_h * 0.17))
    ct_fnt   = fnt(ct_sz)
    ct_lh    = int(ct_sz * 1.30)
    ct_total = len(lines) * ct_lh
    ct_y     = bar_y + (bar_h - ct_total) // 2
    ct_gap   = max(10, int(bar_h * 0.12))
    ct_max_x = right_lockup_left - ct_gap   # hard stop before right section
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=ct_fnt)
        line_w = bb[2] - bb[0]
        # Truncate line if it would collide with the right lockup
        while line_w > (ct_max_x - shield_right) and len(line) > 4:
            line = line[:-1]
            bb = draw.textbbox((0, 0), line + "…", font=ct_fnt)
            line_w = bb[2] - bb[0]
        draw.text((shield_right, ct_y), line, fill=_WHITE, font=ct_fnt)
        ct_y += ct_lh

    # Right: Barclays horizontal lockup — eagle symbol LEFT + "BARCLAYS" text RIGHT
    if sym is not None and sym_w:
        sym_x = right_lockup_left
        sym_y = bar_y + (bar_h - sym_h) // 2
        canvas.alpha_composite(sym, (sym_x, sym_y))
        draw = _ID.Draw(canvas)

        text_bx = sym_x + sym_w + gap
        text_by = bar_y + (bar_h - bk_h) // 2 - bk_bb[1]
        draw.text((text_bx, text_by), "BARCLAYS", fill=_WHITE, font=bk_fnt)
    else:
        # fallback: prefer horizontal wordmark_white over stacked primary_white
        bk = _load_logo_file(logo_uri, [_assets["logos"]["wordmark_white"], _assets["logos"]["primary_white"]])
        if bk:
            lh = max(22, int(bar_h * 0.50))
            lw = int(bk.width * lh / bk.height)
            bk = bk.resize((lw, lh), Image.LANCZOS)
            canvas.alpha_composite(bk, (PX + PW - lw - margin, bar_y + (bar_h - lh) // 2))

    return canvas


def _render_standard_bottom(canvas, draw, bar_y: int, bar_h: int, PX: int, PW: int, text_x: int, margin: int, logo_uri: str, copy_cta: str, fnt):
    """Render standard bottom bar: CTA text left + Barclays wordmark pill right."""
    from PIL import Image
    _WHITE = WHITE
    sub_sz  = max(10, int(bar_h * 0.22 * 0.022 * 6))
    sub_fnt = fnt(sub_sz)
    cta = copy_cta.strip() if copy_cta and copy_cta.strip() else "Here for your every goal."
    draw.text((text_x, bar_y + int(bar_h * 0.30)), cta, fill=_WHITE, font=sub_fnt)

    lockup = _load_logo_file(logo_uri, [_assets["logos"]["primary_white"], _assets["logos"]["wordmark_white"]])
    if lockup:
        lh = max(26, int(bar_h * 0.48))
        lw = int(lockup.width * lh / lockup.height)
        lockup = lockup.resize((lw, lh), Image.LANCZOS)
        pad = 8
        pill = Image.new("RGBA", (lw + pad * 2, lh + pad * 2), (*_WHITE, 255))
        lf = Image.new("RGBA", lockup.size, (*_WHITE, 255))
        lf.alpha_composite(lockup)
        pill.paste(lf, (pad, pad))
        canvas.alpha_composite(pill, (PX + PW - lw - pad * 2 - margin, bar_y + (bar_h - lh - pad * 2) // 2))

    return canvas


# ── Deterministic compositor helpers ─────────────────────────────────────────

def _responsive_font_size(image_width: int, ratio: float, min_size: int, max_size: int) -> int:
    return max(min_size, min(max_size, int(image_width * ratio)))


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _draw_cta_button(draw, text: str, font, x: int, y: int,
                     pad_x: int, pad_y: int, radius: int,
                     bg: tuple, fg: tuple):
    """Rounded-rect Barclays Blue CTA button."""
    bb     = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=radius, fill=(*bg, 255))
    draw.text((x + pad_x, y + pad_y - bb[1]), text, fill=(*fg, 255), font=font)
    return bw, bh


def _apply_wimbledon_overlay(
    canvas, draw, PX: int, PY: int, PW: int, PH: int,
    font_dir: "str | None",
    logo_uri: str,
    headline: str,
    copy_subline: str,
    copy_cta: str,
):
    """
    Fully deterministic Wimbledon brand compositor driven by assets.json overlay spec.

    Responsibility boundary:
      Gemini  → photography, people, environment, lighting, atmosphere
      This fn → headline, subline, CTA, logo lockup, safe areas, typography scale
    """
    from PIL import Image, ImageDraw as _ID, ImageFont

    spec      = _assets.get("overlay", {})
    safe      = spec.get("safe_area", {"left": 0.07, "right": 0.07, "top": 0.07, "bottom": 0.07})
    copy_spec = spec.get("copy", {})
    logo_spec = spec.get("logos", {})

    safe_left = PX + int(PW * safe["left"])
    safe_top  = PY + int(PH * safe["top"])

    # ── Font loader (tries named Effra files in font_dir, falls back to default) ──
    def _fnt(filename: str, size: int):
        if font_dir:
            from pathlib import Path as _P
            for name in [filename, filename.replace(".ttf", ".otf")]:
                p = _P(font_dir) / name
                if p.exists():
                    try:
                        return ImageFont.truetype(str(p), size)
                    except Exception:
                        pass
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()

    def bold(sz):    return _fnt("Effra_Bd.ttf", sz)
    def regular(sz): return _fnt("Effra_Rg.ttf", sz)

    draw = _ID.Draw(canvas)

    # ── Headline ──────────────────────────────────────────────────────────────
    hl_cfg      = copy_spec.get("headline", {})
    hl_size     = _responsive_font_size(PW, hl_cfg.get("size_ratio", 0.060),
                                        hl_cfg.get("min_size", 42), hl_cfg.get("max_size", 96))
    hl_max_w    = int(PW * copy_spec.get("headline_width", 0.38))
    hl_max_ln   = hl_cfg.get("max_lines", 3)
    hl_text     = (headline or "").strip()
    hl_font     = bold(hl_size)
    hl_lines    = _wrap_text(draw, hl_text, hl_font, hl_max_w)
    # Auto-shrink until ≤ max_lines
    while len(hl_lines) > hl_max_ln and hl_size > hl_cfg.get("min_size", 42):
        hl_size -= 2
        hl_font  = bold(hl_size)
        hl_lines = _wrap_text(draw, hl_text, hl_font, hl_max_w)
    hl_lh = int(hl_size * hl_cfg.get("line_spacing", 1.10))

    # ── Subline ───────────────────────────────────────────────────────────────
    sl_cfg   = copy_spec.get("subline", {})
    sl_size  = _responsive_font_size(PW, sl_cfg.get("size_ratio", 0.024),
                                     sl_cfg.get("min_size", 18), sl_cfg.get("max_size", 36))
    sl_max_w = int(PW * copy_spec.get("subline_width", 0.32))
    sl_text  = (copy_subline.strip() if copy_subline and copy_subline.strip()
                else "Behind every champion is support that believes.")
    sl_font  = regular(sl_size)
    sl_lines = _wrap_text(draw, sl_text, sl_font, sl_max_w)[:sl_cfg.get("max_lines", 3)]
    sl_lh    = int(sl_size * sl_cfg.get("line_spacing", 1.20))

    # ── CTA ───────────────────────────────────────────────────────────────────
    cta_cfg    = copy_spec.get("cta", {})
    cta_size   = _responsive_font_size(PW, cta_cfg.get("size_ratio", 0.020),
                                       cta_cfg.get("min_size", 16), cta_cfg.get("max_size", 30))
    cta_font   = bold(cta_size)
    cta_text   = (copy_cta.strip() if copy_cta and copy_cta.strip() else "Discover more")
    cta_bg     = _hex_to_rgb(cta_cfg.get("background_color", "#00AEEF"))
    cta_fg     = _hex_to_rgb(cta_cfg.get("text_color", "#1A2142"))
    cta_pad_x  = int(PW * cta_cfg.get("padding_x", 0.018))
    cta_pad_y  = int(PH * cta_cfg.get("padding_y", 0.010))
    cta_radius = max(4, int(PH * cta_cfg.get("radius", 0.006)))

    # ── Vertical layout ───────────────────────────────────────────────────────
    y = safe_top

    # Headline — all white (never Barclays Blue on dark photo)
    for line in hl_lines:
        draw.text((safe_left, y), line, fill=WHITE, font=hl_font)
        y += hl_lh
    y += int(hl_size * 0.50)   # gap: headline → subline

    # Subline — white, regular weight
    for line in sl_lines:
        draw.text((safe_left, y), line, fill=WHITE, font=sl_font)
        y += sl_lh
    y += int(sl_size * 0.80)   # gap: subline → CTA

    # CTA button
    _draw_cta_button(draw, cta_text, cta_font, safe_left, y,
                     cta_pad_x, cta_pad_y, cta_radius, cta_bg, cta_fg)

    # ── Logo lockup (bottom-right) ────────────────────────────────────────────
    # Point 8: prefer the single approved lockup asset over separate logos.
    bottom_m = int(PH * logo_spec.get("bottom", 0.055))
    right_m  = int(PW * logo_spec.get("right", 0.055))

    lockup_name = _assets["partnerships"]["wimbledon"]["lockup"]   # barclays-wimbledon_wb.png
    lockup_img  = _load_logo_file(logo_uri, [lockup_name])

    if lockup_img:
        lk_w  = int(PW * logo_spec.get("lockup_width", 0.22))
        lk_h  = int(lockup_img.height * lk_w / lockup_img.width)
        lockup_img = lockup_img.resize((lk_w, lk_h), Image.LANCZOS)
        lk_x  = PX + PW - lk_w - right_m
        lk_y  = PY + PH - lk_h - bottom_m
        canvas.alpha_composite(lockup_img, (lk_x, lk_y))
        draw = _ID.Draw(canvas)
    else:
        # Fallback: Wimbledon badge + eagle + BARCLAYS text (deterministic sizing)
        gap_logos = int(PW * 0.018)
        lh = max(28, int(PH * logo_spec.get("bottom", 0.055) * 1.8))

        # Wimbledon badge
        shield = _load_logo_file(logo_uri, [_assets["partnerships"]["wimbledon"]["shield"]])
        if shield:
            sw = int(shield.width * lh / shield.height)
            shield = shield.resize((sw, lh), Image.LANCZOS)

        # Barclays eagle symbol (white silhouette)
        sym = _load_logo_file(logo_uri, [_assets["logos"]["symbol_white"]])
        if sym:
            ew = int(sym.width * lh / sym.height)
            sym = sym.resize((ew, lh), Image.LANCZOS)
            sym = _tint_white(sym)

        # BARCLAYS text
        bk_sz  = max(12, int(lh * 0.58))
        bk_fnt = bold(bk_sz)
        draw_m = _ID.Draw(canvas)
        bk_bb  = draw_m.textbbox((0, 0), "BARCLAYS", font=bk_fnt)
        bk_w, bk_h = bk_bb[2] - bk_bb[0], bk_bb[3] - bk_bb[1]

        sw_val = shield.width if shield else 0
        ew_val = sym.width    if sym    else 0
        total  = sw_val + (gap_logos if sw_val else 0) + ew_val + gap_logos + bk_w
        lx     = PX + PW - total - right_m
        ly_c   = PY + PH - lh - bottom_m

        if shield:
            canvas.alpha_composite(shield, (lx, ly_c))
            lx += sw_val + gap_logos
        if sym:
            canvas.alpha_composite(sym, (lx, ly_c))
            lx += ew_val + gap_logos
        draw_m = _ID.Draw(canvas)
        draw_m.text((lx, ly_c + (lh - bk_h) // 2 - bk_bb[1]), "BARCLAYS",
                    fill=WHITE, font=bk_fnt)

    return canvas


def apply_overlay(
    img_data:     bytes,
    headline:     str,
    logo_uri:     str = "",
    is_wimbledon: bool = False,
    font_path:    "str | None" = None,
    copy_subline: str = "",
    copy_cta:     str = "",
) -> bytes:
    """
    Barclays brand compositor.

    Responsibility boundary:
      Gemini  → photography only (no text, no logos, no brand marks)
      This fn → 100% of the visual system: typography, CTA, logo lockup, safe areas
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io as _io

        def fnt(size: int):
            if font_path:
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    pass
            try:
                return ImageFont.load_default(size=size)
            except Exception:
                return ImageFont.load_default()

        # 1. Load photo
        photo = _open_photo(img_data)
        PW, PH = photo.size

        # 2. Blue border canvas
        canvas, TW, TH, border, PX, PY = _create_canvas(photo, BLUE)

        # 3. Border eagle (top-right blue border cell)
        eagle_src, _ = _load_eagle(logo_uri)
        canvas = _render_border_eagle(canvas, eagle_src, border, TW)

        if is_wimbledon:
            # Fully deterministic spec-driven compositor
            font_dir = str(Path(font_path).parent) if font_path else None
            canvas = _apply_wimbledon_overlay(
                canvas, ImageDraw.Draw(canvas), PX, PY, PW, PH,
                font_dir, logo_uri, headline, copy_subline, copy_cta,
            )
        else:
            # Non-Wimbledon: gradient scrim + headline + standard bottom bar
            canvas = _render_gradient_scrim(canvas, PX, PY, PW, PH, TW, TH)
            margin = max(16, int(PW * 0.055))
            text_x, text_y = PX + margin, PY + margin
            draw = ImageDraw.Draw(canvas)
            draw, head_bottom, head_sz = _render_headline(draw, headline, False, fnt, text_x, text_y, PW, PH)
            draw = _render_subcopy(draw, copy_subline, False, fnt, text_x, head_bottom, head_sz, PH, PW)
            canvas, bar_y, bar_h = _render_bottom_bar(canvas, PX, PY, PW, PH, TW, TH, False)
            draw = ImageDraw.Draw(canvas)
            canvas = _render_standard_bottom(canvas, draw, bar_y, bar_h, PX, PW, text_x, margin, logo_uri, copy_cta, fnt)

        # 11. Encode
        buf = _io.BytesIO()
        canvas.convert("RGB").save(buf, format="JPEG", quality=93)
        return buf.getvalue()

    except Exception as e:
        logger.warning("barclays_overlay_failed", error=str(e))
        return img_data


# ── Brand guidelines text (for asset loader fallback) ─────────────────────────

def brand_guidelines_text() -> str:
    """Return a markdown brand guidelines summary assembled from the JSON configs.

    Called by BrandAssetLoader when no brand_guidelines.md exists in GCS.
    Keeps all agents (KV, strategy, copy) in sync with the structured data.
    """
    br    = _brand
    rules = br["rules"]
    copy_r = br["copy_rules"]
    rel   = _wimb_campaign["relationship"]

    forbidden = ", ".join(f'"{w}"' for w in rules["no_financial_jargon"])
    headline_rules = "\n".join(f"  - {r}" for r in copy_r["headline_rules"])
    subline_rules  = "\n".join(f"  - {r}" for r in copy_r["subline_rules"])
    subline_ex = "\n".join(
        f'  "{ex["headline"]}"\n  → "{ex["subline"]}"'
        for ex in copy_r["subline_examples"]
    )
    cta_opts = " / ".join(f'"{c}"' for c in copy_r["cta_options"])
    wimb_directions = " / ".join(_wimb_campaign["copy_rules"]["creative_direction"])
    wimb_avoid      = ", ".join(_wimb_campaign["copy_rules"]["avoid"])
    allowed_themes  = ", ".join(_wimb_campaign["allowed_themes"])

    return f"""# Barclays Brand Guidelines

## Brand Identity
- **Sector**: Financial services (FCA-regulated)
- **Market**: UK
- **Campaign platform**: {br["campaign_platform"]}
- **Tone**: {", ".join(br["tone"])}

## Colour Palette
- **Barclays Blue** `#00AEEF` — fill and device use ONLY; never as text on white
- **Barclays Night** `#1A2142` — primary dark ground, reversed layouts, default text
- **White** `#FFFFFF` — reversed type on dark

## Typography
- **Headline**: Effra Bold (Effra_Bd)
- **Body**: Effra Regular (Effra_Rg)

## Visual Style
- **Lighting**: {br["visual"]["effects"]}
- **Subject**: {br["visual"]["subject"]}
- **Background**: {br["visual"]["background"]}
- **Wardrobe**: {br["visual"]["wardrobe"]}
- **Energy**: {br["visual"]["energy"]}

## Mandatory Visual Rules
- No product packshots
- No app screenshots
- No financial data or rate displays
- Upper-left quadrant kept as clean negative space for copy overlay

## Copy Rules

### Headline
{headline_rules}
- Forbidden words: {forbidden}

### Subline
{subline_rules}

### CTA options
{cta_opts}

### Subline examples by headline
{subline_ex}

## Wimbledon Partnership
- **Relationship**: {rel["display_name"]}
- **Short name**: {rel["short_display_name"]}
- **Verified from**: {rel["announced_from_year"]}
- **Creative themes**: {allowed_themes}
- **Creative direction**: {wimb_directions}
- **Avoid**: {wimb_avoid}
- Partnership wording comes from approved asset images only — never generated from text strings
"""
