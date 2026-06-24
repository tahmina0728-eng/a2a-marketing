"""
tools.py — ADK tool definitions for CampaignOS agents.

All data-loading and persistence functions have been moved out of this file:
  - Data loading    → nodes.py (deterministic graph function nodes)
  - State + artifact persistence → nodes.py persist_* function nodes
                                    (InvocationContext-based, deterministic)

This file contains ONLY the image generation tool that requires ADK's async
ToolContext for Gemini image generation + artifact storage.

Tool list:
  generate_and_save_kv_image — Gemini image generation; saves PNG via ADK artifact
                               service (InMemory in dev, GCS in prod — zero code change).
                               Passes product photos as multi-modal image inputs so the
                               model sees the actual product photography.
                               Post-processes the Imagen output with Pillow to composite:
                                 - Campaign headline (from campaign_copy.short.headline)
                                   using the brand's actual TTF font
                                 - Brand logo (from bucket/brands/{brand}/Logos/)
                               This guarantees correct typography regardless of what
                               the image model renders.
"""

import io
import json
import structlog

from google.adk.tools import ToolContext
from google.genai import types

from app.config import get_settings

logger   = structlog.get_logger()
settings = get_settings()


# ── SHARED HELPERS ────────────────────────────────────────────────────────

def _load_asset_bytes(path_or_uri: str) -> bytes | None:
    """
    Load raw bytes from a local file path or a gs:// URI.
    Returns None if the path is empty or the load fails (non-fatal).
    """
    if not path_or_uri:
        return None
    try:
        if path_or_uri.startswith("gs://"):
            from google.cloud import storage as _gcs  # type: ignore
            without_scheme = path_or_uri[5:]
            bucket_name, _, blob_path = without_scheme.partition("/")
            client = _gcs.Client(project=settings.gcp_project)
            return client.bucket(bucket_name).blob(blob_path).download_as_bytes()
        else:
            from pathlib import Path as _Path
            return _Path(path_or_uri).read_bytes()
    except Exception as exc:
        logger.warning("load_asset_bytes_failed", path=path_or_uri, error=str(exc))
        return None


def _guess_image_mime(path_or_uri: str) -> str:
    """Guess image MIME type from file extension."""
    ext = path_or_uri.rsplit(".", 1)[-1].lower() if "." in path_or_uri else ""
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png",  "webp": "image/webp",
    }.get(ext, "image/png")


def _part_for_uri(path_or_uri: str) -> "types.Part | None":
    """
    Return a genai Part for the given image source.
    GCS URIs (gs://…) use Part.from_uri so Gemini fetches directly from GCS.
    Local paths load bytes and use Part.from_bytes.
    Returns None on failure (non-fatal).
    """
    if not path_or_uri:
        return None
    mime = _guess_image_mime(path_or_uri)
    if path_or_uri.startswith("gs://"):
        return types.Part.from_uri(file_uri=path_or_uri, mime_type=mime)
    data = _load_asset_bytes(path_or_uri)
    if data is None:
        return None
    return types.Part.from_bytes(data=data, mime_type=mime)


# ── BRAND ASSET COMPOSITING ───────────────────────────────────────────────

def _pick_primary_logo(logo_paths: list[str]) -> str | None:
    """
    Choose the best logo from the available paths.
    Prefer: PNG with transparency, no colour-variant suffix (green/red/yellow/…).
    Falls back to the first PNG, then the first path of any type.
    """
    if not logo_paths:
        return None
    _colour_suffixes = {"green", "red", "yellow", "orange", "purple", "blue", "white", "black"}
    # Prefer PNG files whose stem doesn't end with a colour variant name
    candidates = [
        p for p in logo_paths
        if p.lower().rsplit(".", 1)[-1] == "png"
        and not any(p.lower().rsplit(".", 1)[0].endswith(s) for s in _colour_suffixes)
    ]
    if candidates:
        return candidates[0]
    pngs = [p for p in logo_paths if p.lower().endswith(".png")]
    return pngs[0] if pngs else logo_paths[0]


def _pick_display_font(font_paths: list[str]) -> str | None:
    """
    Pick the best display/headline TTF or OTF from available font paths.
    Prefers non-italic, non-bold variants (variable fonts cover weight via axis).
    """
    if not font_paths:
        return None
    usable = [p for p in font_paths if p.lower().endswith((".ttf", ".otf"))]
    if not usable:
        return None
    # Prefer paths that do NOT contain 'italic' or 'bold' in the filename
    regular = [p for p in usable if "italic" not in p.lower() and "bold" not in p.lower()]
    return (regular or usable)[0]


def _parse_hex_color(hex_str: str | None) -> tuple[int, int, int] | None:
    """Parse '#RRGGBB' → (R, G, B) int tuple. Returns None on failure."""
    if not hex_str:
        return None
    h = hex_str.lstrip("#")
    if len(h) == 6:
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except ValueError:
            pass
    return None


def _extract_primary_color(brand_locks: dict) -> tuple[int, int, int]:
    """
    Extract the primary brand color from brand_locks, handling both:
      - Flat BrandLocks field: brand_locks["primary_colour"] = "#RRGGBB"
      - Nested YAML structure: brand_locks["colors"]["primary"]["rnorr_green"] = "#008641"
                               brand_locks["colors"]["master"]["sunglow_magenta"] = "#B00064"
    Falls back to near-black if nothing is parseable.
    """
    # 1. Standard BrandLocks field
    c = _parse_hex_color(brand_locks.get("primary_colour"))
    if c:
        return c

    # 2. Nested YAML colour sections (parsed from brand guidelines YAML block)
    colors_section = brand_locks.get("colors", {})
    if isinstance(colors_section, dict):
        for section_name in ("primary", "master", "brand", "core"):
            section = colors_section.get(section_name, {})
            if isinstance(section, dict):
                for val in section.values():
                    if isinstance(val, str):
                        c = _parse_hex_color(val)
                        if c:
                            return c
        # Also try direct color values at the top level of colors dict
        for val in colors_section.values():
            if isinstance(val, str):
                c = _parse_hex_color(val)
                if c:
                    return c

    return (20, 20, 20)  # dark fallback


def _contrast_text_color(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    """
    Return white or near-black depending on background luminance.
    Uses WCAG relative luminance formula.
    """
    def _lin(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    lum = 0.2126 * _lin(bg[0]) + 0.7152 * _lin(bg[1]) + 0.0722 * _lin(bg[2])
    return (255, 255, 255) if lum < 0.179 else (20, 20, 20)


def _shadow_text(
    draw:   "ImageDraw.ImageDraw",
    xy:     tuple[int, int],
    text:   str,
    font:   "ImageFont.FreeTypeFont | ImageFont.ImageFont",
    fill:   tuple[int, int, int, int],
    offset: int = 2,
) -> None:
    """Draw text with a dark drop-shadow for legibility on any background."""
    x, y = xy
    draw.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0, 140))
    draw.text((x, y), text, font=font, fill=fill)


def _fit_text(
    draw:      "ImageDraw.ImageDraw",
    text:      str,
    font:      "ImageFont.FreeTypeFont | ImageFont.ImageFont",
    max_width: int,
) -> str:
    """Truncate text with ellipsis if it exceeds max_width pixels."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text
    while text:
        text = text[:-1]
        bbox = draw.textbbox((0, 0), text + "…", font=font)
        if bbox[2] - bbox[0] <= max_width:
            return text + "…"
    return ""


def _composite_brand_assets(
    image_data:         bytes,
    brand:              str,
    brand_locks:        dict,
    campaign_copy_json: str,
    product_name:       str = "",
) -> bytes:
    """
    Post-process the Imagen output to overlay branded elements using Pillow.

    Layout (bottom panel):
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │           [IMAGEN PHOTOGRAPHIC SCENE]           │
    │                                                 │
    ├─[gradient fade]─────────────────────────────────┤
    │ [LOGO]  BRAND NAME        ← large, brand font   │
    │         Product Name      ← medium subtitle     │
    │         "Campaign headline…"  ← small tagline  │
    └─────────────────────────────────────────────────┘

    Assets loaded from bucket/brands/{brand}/:
      Logos/   → brand logo (PNG with transparency)
      Font/    → display TTF used for all three text rows
    Colors from brand_locks → brand primary used for panel background.
    Headline from campaign_copy.short.headline (copy agent output).
    Product from product_name (brief product field).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError:
        logger.warning("pillow_not_available", msg="pip install pillow to enable brand compositing")
        return image_data

    try:
        from app.brand_assets import get_asset_loader
        loader = get_asset_loader()

        # ── Base image ─────────────────────────────────────────────────────
        Image.MAX_IMAGE_PIXELS = None  # AI-generated images can exceed PIL's default bomb limit
        img = Image.open(io.BytesIO(image_data)).convert("RGBA")
        if max(img.size) > 2048:
            scale = 2048 / max(img.size)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        w, h = img.size
        margin = max(16, int(w * 0.025))

        # ── Brand color & text contrast ────────────────────────────────────
        primary_rgb = _extract_primary_color(brand_locks)
        r, g, b     = primary_rgb
        text_color  = _contrast_text_color(primary_rgb) + (255,)   # RGBA full opacity
        # Dimmed version for product name and headline rows
        dim_color   = text_color[:3] + (200,)

        # ── Load brand font bytes once ─────────────────────────────────────
        font_paths      = loader.list_fonts(brand)
        display_fp      = _pick_display_font(font_paths)
        font_bytes_data = _load_asset_bytes(display_fp) if display_fp else None

        def _make_font(size: int) -> "ImageFont.FreeTypeFont | ImageFont.ImageFont":
            if font_bytes_data:
                try:
                    return ImageFont.truetype(io.BytesIO(font_bytes_data), size=size)
                except Exception:
                    pass
            try:
                return ImageFont.load_default(size=size)
            except Exception:
                return ImageFont.load_default()

        # ── Parse campaign copy headline ───────────────────────────────────
        headline = ""
        try:
            copy_dict = json.loads(campaign_copy_json) if campaign_copy_json else {}
            headline  = copy_dict.get("short", {}).get("headline", "")
        except Exception:
            pass

        # ── Load brand logo ────────────────────────────────────────────────
        logo_img: "Image.Image | None" = None
        logo_path = _pick_primary_logo(loader.list_logos(brand))
        if logo_path:
            logo_bytes = _load_asset_bytes(logo_path)
            if logo_bytes:
                try:
                    logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
                except Exception as e:
                    logger.warning("logo_open_failed", brand=brand, error=str(e))

        # ── Panel dimensions ───────────────────────────────────────────────
        # Panel occupies bottom 26 % of the image, min 90 px
        panel_h = max(90, int(h * 0.26))
        panel_y = h - panel_h

        # ── 1. Draw solid brand-color panel with top gradient fade ─────────
        panel = Image.new("RGBA", (w, panel_h), (0, 0, 0, 0))
        draw_p = ImageDraw.Draw(panel)

        solid_start = int(panel_h * 0.20)        # gradient for first 20 % of panel height
        # Solid portion
        draw_p.rectangle([0, solid_start, w, panel_h], fill=(r, g, b, 230))
        # Gradient fade from transparent → solid at top of panel
        for row in range(solid_start):
            a = int(230 * (row / solid_start))
            draw_p.line([(0, row), (w, row)], fill=(r, g, b, a))

        img.paste(panel, (0, panel_y), panel)
        draw = ImageDraw.Draw(img)

        # ── 2. Brand logo (left side, vertically centred in panel) ─────────
        logo_zone_w = 0
        if logo_img is not None:
            max_logo_h = int(panel_h * 0.68)
            max_logo_w = int(w * 0.18)
            scale      = min(max_logo_h / logo_img.height, max_logo_w / logo_img.width)
            lw         = max(40, int(logo_img.width  * scale))
            lh_s       = max(40, int(logo_img.height * scale))
            logo_r     = logo_img.resize((lw, lh_s), Image.LANCZOS)
            lx         = margin
            ly         = panel_y + (panel_h - lh_s) // 2
            img.paste(logo_r, (lx, ly), logo_r)
            logo_zone_w = lw + margin          # text starts after logo + gap
            logger.info("logo_composited", brand=brand, size=(lw, lh_s))

        # ── 3. Text stack (brand name / product / headline) ────────────────
        text_x     = margin + logo_zone_w
        text_max_w = w - text_x - margin       # available text width

        # Font sizes relative to panel height
        fs_brand    = max(32, int(panel_h * 0.36))
        fs_product  = max(18, int(panel_h * 0.22))
        fs_headline = max(14, int(panel_h * 0.15))

        f_brand    = _make_font(fs_brand)
        f_product  = _make_font(fs_product)
        f_headline = _make_font(fs_headline)

        # Measure each row
        def _row_h(text: str, font: object) -> int:
            bb = draw.textbbox((0, 0), text, font=font)
            return max(1, bb[3] - bb[1])

        brand_label   = brand.upper()
        product_label = _fit_text(draw, product_name, f_product, text_max_w) if product_name else ""
        hl_label      = _fit_text(draw, f'"{headline}"', f_headline, text_max_w) if headline else ""

        row_gap = max(4, int(panel_h * 0.05))

        bh  = _row_h(brand_label, f_brand)
        ph  = _row_h(product_label,  f_product)  if product_label else 0
        hlh = _row_h(hl_label,    f_headline) if hl_label    else 0

        total_h = bh + (row_gap + ph if ph else 0) + (row_gap + hlh if hlh else 0)

        # Vertically centre the text stack inside the solid part of the panel
        solid_panel_y = panel_y + int(panel_h * 0.20)
        solid_h       = panel_h - int(panel_h * 0.20)
        ty            = solid_panel_y + max(0, (solid_h - total_h) // 2)

        # Brand name — full opacity, largest size
        _shadow_text(draw, (text_x, ty), brand_label, f_brand, text_color)
        ty += bh

        # Product name — slightly dimmed
        if product_label:
            ty += row_gap
            _shadow_text(draw, (text_x, ty), product_label, f_product, dim_color)
            ty += ph

        # Campaign headline — dimmed, italic feel via smaller size
        if hl_label:
            ty += row_gap
            _shadow_text(draw, (text_x, ty), hl_label, f_headline, dim_color)

        logger.info("brand_composite_done", brand=brand, product=product_name,
                    headline=headline, size=(w, h))

        # ── Output ─────────────────────────────────────────────────────────
        out = io.BytesIO()
        img.convert("RGB").save(out, format="JPEG", quality=95)
        return out.getvalue()

    except Exception as exc:
        logger.warning("brand_composite_error", brand=brand, error=str(exc))
        return image_data  # non-fatal: return raw Imagen output


# ── KV IMAGE GENERATION TOOL ──────────────────────────────────────────────

async def generate_and_save_kv_image(
    generator_id: int,
    image_prompt: str,
    concept_id:   str,
    tool_context: ToolContext,
) -> dict:
    """
    Generate a hero image for one KV concept using the Gemini image model and
    save it via the ADK artifact service.

    Product photos are loaded from session state (product_image_map) and
    passed as multi-modal image inputs alongside the text prompt, so the model
    sees the actual product photography rather than inferring from text alone.

    After generation, the raw Imagen output is post-processed with Pillow:
      - Campaign headline (from campaign_copy.short.headline in session state)
        is overlaid using the brand's actual TTF font from the bucket
      - Brand logo (from bucket/brands/{brand}/Logos/) is composited
      - Brand primary colour is used for the headline strip background

    Environment-agnostic: in development (adk web) the image is stored
    in-memory and visible in the Artifacts panel. In production the same code
    writes to the configured GCS bucket — no code changes required.

    Non-fatal: if generation or save fails a warning is logged and
    {"status": "failed", "error": "..."} is returned so the pipeline continues.

    Args:
        generator_id: 1–4 matching the kv_generator_N that produced the concept
        image_prompt: The detailed image generation prompt from the KVConcept
        concept_id:   The concept_id string from the KVConcept (for logging)

    Returns:
        {"artifact_key": "kv_image_{N}.png", "status": "saved", "version": N}
        or {"status": "failed", "error": "..."}
    """
    artifact_key = f"kv_image_{generator_id}.png"

    try:
        from google import genai as _genai  # lazy — heavy dep, avoid import-time cost
        from app.brand_assets import get_asset_loader as _get_loader

        brand = tool_context.state.get("brand_name", "")

        # Extract brand colors from brand_locks for explicit palette guidance in the prompt.
        brand_locks: dict = {}
        try:
            brand_locks = json.loads(tool_context.state.get("brand_locks_json", "{}"))
        except Exception:
            pass

        color_lines: list[str] = []
        for field, label in [("primary_colour", "primary"), ("accent_colour", "accent"), ("secondary_colour", "secondary")]:
            val = brand_locks.get(field)
            if isinstance(val, str) and val.startswith("#"):
                color_lines.append(f"  {label}: {val}")
        colors_section = brand_locks.get("colors", {})
        if isinstance(colors_section, dict):
            for section_name, section in colors_section.items():
                if isinstance(section, dict):
                    for name, val in section.items():
                        if isinstance(val, str) and val.startswith("#"):
                            color_lines.append(f"  {section_name}/{name}: {val}")
                elif isinstance(section, str) and section.startswith("#"):
                    color_lines.append(f"  {section_name}: {section}")

        brand_color_block = (
            "BRAND COLOR PALETTE — use these exact hex codes for all flat panels, "
            "graphic elements, backgrounds, and color blocks in the composition:\n"
            + "\n".join(color_lines)
            + "\n\n"
        ) if color_lines else ""

        # Typography note: Gemini does not render text (suppressed below), but the
        # layout should leave clean flat-color zones at the intended text placement
        # positions that match the brand palette — Pillow compositing will apply the
        # brand font on top in post-processing.
        typography_note = (
            "TYPOGRAPHY STYLE: Do not render any text, letters, or numbers anywhere. "
            "Instead, reserve a clean graphic panel at the bottom of the image using the "
            "brand primary color as a flat background — this area will receive the brand "
            "name, product name, and campaign headline in post-production using the brand's "
            "official typeface. The panel should feel consistent with the typographic style "
            "visible in the brand reference images above.\n\n"
        )

        # Prepend a brand-protection prefix to prevent the image model from defaulting
        # to visually similar real-world brands (e.g. rendering "Rnorr" as "Knorr").
        guarded_prompt = (
            "IMPORTANT: This image is for a fictional brand. "
            "Do not render any real-world brand names, logos, or packaging. "
            "Treat all brand names in this prompt as entirely fictional.\n\n"
            + brand_color_block
            + typography_note
            + image_prompt
        )

        product_image_map_raw = tool_context.state.get("product_image_map", "{}")
        product_image_map: dict = (
            json.loads(product_image_map_raw)
            if isinstance(product_image_map_raw, str)
            else (product_image_map_raw or {})
        )

        # Only send product photos that the image_prompt explicitly references.
        referenced_products = {
            k: v for k, v in product_image_map.items() if k in image_prompt
        }
        products_to_send = referenced_products or product_image_map

        contents: list = []

        # ── 1. Brand style reference images (Assets/) — earliest = strongest influence ──
        loader      = _get_loader()
        asset_paths = loader.list_assets(brand)[:2]  # cap at 2 style refs
        if asset_paths:
            contents.append(
                "BRAND VISUAL STYLE REFERENCE: The following image(s) show this brand's "
                "established visual language — color palette, compositional style, mood, "
                "typographic layout, and graphic treatment. Your generated image MUST align "
                "with this visual identity in every detail."
            )
            for ap in asset_paths:
                part = _part_for_uri(ap)
                if part:
                    contents.append(part)
                    logger.info("style_ref_included", uri=ap)

        # ── 2. Brand colour swatches — palette lock ───────────────────────────────────
        colour_paths = loader.list_colours(brand)[:3]  # cap at 3 swatches
        if colour_paths:
            contents.append(
                "BRAND COLOR PALETTE REFERENCE: The following swatch image(s) show the "
                "official brand colors. Use ONLY these colors for all flat panels, graphic "
                "elements, backgrounds, and color blocks — no off-brand tones."
            )
            for cp in colour_paths:
                part = _part_for_uri(cp)
                if part:
                    contents.append(part)
                    logger.info("colour_swatch_included", uri=cp)

        # ── 4. Brand logo — colour/style reference only; NOT reproduced in image ────
        logo_paths   = loader.list_logos(brand)
        primary_logo = _pick_primary_logo(logo_paths)
        if primary_logo:
            contents.append(
                "BRAND IDENTITY REFERENCE: This is the official brand logo. "
                "DO NOT render or place this logo anywhere in the generated image — "
                "it will be composited programmatically after generation. "
                "Use it ONLY as a reference for the brand's color palette and graphic style."
            )
            part = _part_for_uri(primary_logo)
            if part:
                contents.append(part)
                logger.info("logo_ref_included", uri=primary_logo)

        # ── 5. Product photos — subject reference ─────────────────────────────────────
        if products_to_send:
            contents.append(
                "PRODUCT REFERENCE: The following image(s) show the exact product to feature. "
                "Match its shape, packaging, colors, and materials precisely — "
                "do not invent or substitute a generic product."
            )
            for product_name, uri in products_to_send.items():
                part = _part_for_uri(uri)
                if part:
                    contents.append(f"{product_name}:")
                    contents.append(part)
                    logger.info("product_photo_included", product=product_name, uri=uri)
                else:
                    logger.warning("product_photo_skipped", product=product_name, uri=uri)

        # ── 6. Text prompt — always last ──────────────────────────────────────────────
        contents.append(guarded_prompt)

        client   = _genai.Client()
        response = client.models.generate_content(
            model    = settings.gemini_model_image,
            contents = contents,
            config   = types.GenerateContentConfig(
                response_modalities = ["IMAGE", "TEXT"],
            ),
        )

        image_data: bytes | None = None
        mime_type = "image/jpeg"
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data is not None:
                image_data = part.inline_data.data
                mime_type  = part.inline_data.mime_type or "image/jpeg"
                break

        if image_data is None:
            raise ValueError("Gemini returned no image data")

        # ── Post-process: composite brand panel (logo + name + product + headline) ──
        product_name = tool_context.state.get("product_name", "")
        brand_locks  = {}
        try:
            brand_locks = json.loads(tool_context.state.get("brand_locks_json", "{}"))
        except Exception:
            pass
        campaign_copy_json = tool_context.state.get("campaign_copy", "{}")

        image_data = _composite_brand_assets(
            image_data         = image_data,
            brand              = brand,
            brand_locks        = brand_locks,
            campaign_copy_json = campaign_copy_json,
            product_name       = product_name,
        )
        mime_type = "image/jpeg"  # always JPEG after compositing

        # Save via ADK artifact service — InMemory locally, GCS in production.
        version = await tool_context.save_artifact(
            filename = artifact_key,
            artifact = types.Part.from_bytes(
                data      = image_data,
                mime_type = mime_type,
            ),
        )

        # Write artifact key to session state for downstream access
        tool_context.state[f"kv_image_key_{generator_id}"] = artifact_key

        logger.info(
            "kv_image_saved",
            generator_id = generator_id,
            concept_id   = concept_id,
            artifact_key = artifact_key,
            version      = version,
            brand        = brand,
        )
        return {
            "artifact_key": artifact_key,
            "status":       "saved",
            "version":      version,
        }

    except Exception as exc:
        logger.warning(
            "kv_image_failed",
            generator_id = generator_id,
            concept_id   = concept_id,
            error        = str(exc),
        )
        return {"status": "failed", "error": str(exc)}
