"""
tools.py â€” ADK tool definitions for CampaignOS agents.

All data-loading functions (brand assets, search, brand locks) have been
moved to nodes.py as deterministic graph function nodes. This file contains
only tools that require ADK's async ToolContext (artifact service, BigQuery).

Tool list:
  save_brief_output          â€” ADK artifact service + BigQuery audit + session state
  generate_and_save_kv_image â€” Gemini image generation; saves PNG via ADK artifact
                               service (InMemory in dev, GCS in prod â€” zero code change).
                               Passes product photos as multi-modal image inputs so the
                               model sees the actual product photography.
  render_copy_overlay        â€” Pillow flat text overlay; creates a positional reference
                               (kv_ref_{N}.png) showing exactly where headline/brand/
                               tagline copy sits â€” used as stencil for refine_kv_image.
  refine_kv_image            â€” Nano Banana 2 image-to-image; loads the Pillow reference,
                               re-renders the text with scene-integrated lighting/shadows,
                               saves the finished key visual as kv_final_{N}.png.
"""

import json
import structlog

from google.adk.tools import ToolContext
from google.genai import types

from app.config import get_settings
from app.data_loader import log_brief_to_bigquery

logger   = structlog.get_logger()
settings = get_settings()


# â”€â”€ SHARED HELPERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€ PERSISTENCE TOOL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def save_brief_output(
    campaign_id: str,
    machine_brief: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Save the completed machine_brief via the ADK artifact service and log
    it to BigQuery. Also stores the brief in session state so downstream
    agents can access it without reloading.

    In development (adk web) the artifact is stored in-memory and visible
    in the Artifacts panel. In production set ARTIFACT_SERVICE_URI=gs://bucket
    and the same code writes to GCS automatically.

    ALWAYS call this as the FINAL step after the brief is fully validated
    and structured.

    Args:
        campaign_id: Unique campaign identifier e.g. 'summer-drop-a1b2c3d4'
        machine_brief: The complete validated machine_brief dict including
                       all validation results, scores, flags, structured_brief,
                       brand_locks, and handoff_message

    Returns:
        dict with 'status': 'saved', 'artifact_name', and 'campaign_id'
    """
    artifact_name = f"machine_brief_{campaign_id}.json"
    brief_json    = json.dumps(machine_brief, indent=2, default=str)

    # Save via ADK artifact service (InMemory in dev, GCS in prod).
    # - Filename must be flat (no '/') â€” ADK web uses it as a URL path segment.
    # - Must use inline_data (not types.Part(text=...)) â€” ADK artifact spec requires bytes + mime_type.
    try:
        await tool_context.save_artifact(
            filename = artifact_name,
            artifact = types.Part.from_bytes(
                data      = brief_json.encode("utf-8"),
                mime_type = "application/json",
            ),
        )
    except Exception as e:
        logger.warning("artifact_save_failed", campaign_id=campaign_id, error=str(e))

    # BigQuery audit log (non-fatal -- kept separate from artifact storage)
    brief_input = machine_brief.get("structured_brief", {})
    log_brief_to_bigquery(campaign_id, brief_input, machine_brief)

    # Store parsed brief dict in session state for downstream workflow agents.
    # briefing_agent also has output_key="machine_brief" which stores the raw
    # JSON string â€” this overwrites that with the properly parsed dict.
    tool_context.state["machine_brief"] = machine_brief
    tool_context.state["machine_brief_saved"] = True

    logger.info("tool_save_brief_output", campaign_id=campaign_id, artifact=artifact_name)
    return {
        "status":        "saved",
        "artifact_name": artifact_name,
        "campaign_id":   campaign_id,
    }


# â”€â”€ KV IMAGE GENERATION TOOL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    Environment-agnostic: in development (adk web) the image is stored
    in-memory and visible in the Artifacts panel. In production the same code
    writes to the configured GCS bucket â€” no code changes required.

    Artifact key: "kv_image_{generator_id}.png"
    ADK versions artifacts on each save, so reruns create v1, v2, â€¦ of the
    same key â€” no UUID required.

    The artifact key and MIME type are written to session state as
    kv_image_key_{generator_id} so aggregate_kv_concepts and downstream
    agents can reference them without touching GCS URIs directly.

    Non-fatal: if generation or save fails a warning is logged and
    {"status": "failed", "error": "..."} is returned so the pipeline continues.

    Args:
        generator_id: 1â€“4 matching the kv_generator_N that produced the concept
        image_prompt: The detailed image generation prompt from the KVConcept
        concept_id:   The concept_id string from the KVConcept (for logging)

    Returns:
        {"artifact_key": "kv_image_{N}.png", "status": "saved", "version": N}
        or {"status": "failed", "error": "..."}
    """
    artifact_key = f"kv_image_{generator_id}.png"

    try:
        from google import genai as _genai  # lazy â€” heavy dep, avoid import-time cost

        # Prepend a brand-protection prefix to prevent the image model from defaulting
        # to visually similar real-world brands (e.g. rendering "Rnorr" as "Knorr").
        guarded_prompt = (
            "IMPORTANT: This image is for a fictional brand. "
            "Do not render any real-world brand names, logos, or packaging. "
            "Treat all brand names in this prompt as entirely fictional.\n\n"
            + image_prompt
        )

        # Build multi-modal contents â€” product photos first, text prompt last.
        # Passing the actual product photography allows the image model to
        # incorporate the real product into the composition rather than
        # inferring it from the text description alone.
        product_image_map_raw = tool_context.state.get("product_image_map", "{}")
        product_image_map: dict = (
            json.loads(product_image_map_raw)
            if isinstance(product_image_map_raw, str)
            else (product_image_map_raw or {})
        )

        contents: list = []
        for product_name, uri in product_image_map.items():
            img_bytes = _load_asset_bytes(uri)
            if img_bytes:
                contents.append(
                    types.Part.from_bytes(
                        data      = img_bytes,
                        mime_type = _guess_image_mime(uri),
                    )
                )
                logger.info("product_photo_included", product=product_name, uri=uri)
            else:
                logger.warning("product_photo_skipped", product=product_name, uri=uri)

        contents.append(guarded_prompt)  # text prompt always last

        client   = _genai.Client()
        response = client.models.generate_content(
            model    = settings.gemini_model_image,
            contents = contents,
            config   = types.GenerateContentConfig(
                response_modalities = ["IMAGE", "TEXT"],
            ),
        )

        image_data: bytes | None = None
        mime_type = "image/png"
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data is not None:
                image_data = part.inline_data.data
                mime_type  = part.inline_data.mime_type or "image/png"
                break

        if image_data is None:
            raise ValueError("Gemini returned no image data")

        # Save via ADK artifact service â€” InMemory locally, GCS in production.
        # Filename must be flat (no '/') for compatibility with adk web UI.
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


# â”€â”€ COPY RENDERER TOOL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def render_copy_overlay(
    generator_id: int,
    tool_context: ToolContext,
) -> dict:
    """
    Load the raw KV background (kv_image_{N}.png) from the artifact service,
    overlay typographic copy (headline, brand name, tagline) as a flat Pillow
    reference layer, and save the result as kv_ref_{N}.png.

    The reference image is intentionally plain â€” it acts as a pixel-precise
    positional stencil for the subsequent refine_kv_image pass, showing the
    image model exactly where each text element sits, at what size, without
    requiring the Pillow layer to look production-quality.

    Brand font is loaded from the brand Font/ directory (GCS or local).
    Falls back to PIL's built-in default font if no brand font is available.

    Reads state:  kv_concept_{N}  â€” KVConcept JSON (title, typography_guidance)
                  brand_name      â€” for font loading and brand name copy
                  brand_locks_json â€” for tagline + primary_colour
    Artifact in:  kv_image_{N}.png
    Artifact out: kv_ref_{N}.png
    State out:    kv_ref_key_{N} = "kv_ref_{N}.png"

    Args:
        generator_id: 1â€“4 matching the concept branch

    Returns:
        {"artifact_key": "kv_ref_{N}.png", "status": "saved", "version": N}
        or {"status": "failed", "error": "..."}
    """
    ref_key = f"kv_ref_{generator_id}.png"
    src_key = f"kv_image_{generator_id}.png"

    try:
        from io import BytesIO
        import os
        import tempfile
        from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

        # â”€â”€ 1. Load the raw background from artifact service â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        src_part = await tool_context.load_artifact(src_key)
        if src_part is None or not src_part.inline_data:
            raise ValueError(f"Artifact {src_key!r} not found or empty")
        img        = Image.open(BytesIO(src_part.inline_data.data)).convert("RGBA")
        width, height = img.size

        # â”€â”€ 2. Read copy text from session state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        concept_raw = tool_context.state.get(f"kv_concept_{generator_id}", "{}")
        try:
            concept = json.loads(concept_raw) if isinstance(concept_raw, str) else concept_raw
        except Exception:
            concept = {}

        headline            = concept.get("title", "")
        if isinstance(headline, dict):
            headline = headline.get("text", "") or headline.get("en", "") or ""
        headline = str(headline)

        brand_name          = tool_context.state.get("brand_name", "")
        try:
            locks = json.loads(tool_context.state.get("brand_locks_json", "{}"))
        except Exception:
            locks = {}

        # tagline and primary_colour may be nested dicts in some brand guidelines schemas
        tagline_raw    = locks.get("tagline") or ""
        tagline        = (
            tagline_raw.get("text", "") if isinstance(tagline_raw, dict) else str(tagline_raw)
        )
        colour_raw     = locks.get("primary_colour") or ""
        primary_colour = (
            colour_raw.get("rnorr_green", "#FFFFFF") if isinstance(colour_raw, dict)
            else (str(colour_raw) if colour_raw else "#FFFFFF")
        )
        # If primary_colour is still a nested structure (e.g. colors.primary dict), fall back
        if not primary_colour.startswith("#"):
            # Try to pull first hex value from a colours dict stored elsewhere in locks
            colours_block = locks.get("colors", {}).get("primary", {})
            first_hex = next(
                (v for v in colours_block.values() if isinstance(v, str) and v.startswith("#")),
                "#FFFFFF",
            )
            primary_colour = first_hex

        # â”€â”€ 3. Load brand font (fallback to PIL built-in) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        headline_size = max(36, height // 14)
        body_size     = max(24, height // 22)

        font_headline: object
        font_body:     object
        try:
            from app.brand_assets import get_asset_loader
            loader     = get_asset_loader()
            font_paths = loader.list_fonts(brand_name) if brand_name else []
            font_bytes = _load_asset_bytes(font_paths[0]) if font_paths else None
            if font_bytes:
                with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmp:
                    tmp.write(font_bytes)
                    tmp_path = tmp.name
                font_headline = ImageFont.truetype(tmp_path, headline_size)
                font_body     = ImageFont.truetype(tmp_path, body_size)
                os.unlink(tmp_path)
            else:
                raise ValueError("no brand font found")
        except Exception:
            font_headline = ImageFont.load_default(size=headline_size)
            font_body     = ImageFont.load_default(size=body_size)

        # â”€â”€ 4. Composite text overlay â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        def _hex_to_rgba(hex_colour: str, alpha: int = 240) -> tuple:
            try:
                h = hex_colour.lstrip("#")
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)
            except Exception:
                return (255, 255, 255, alpha)

        shadow_offset = max(2, height // 300)

        def _draw_shadowed(text: str, pos: tuple, font: object) -> None:
            sx, sy = pos[0] + shadow_offset, pos[1] + shadow_offset
            draw.text((sx, sy), text, font=font, fill=(0, 0, 0, 180))  # type: ignore[arg-type]
            draw.text(pos, text, font=font, fill=_hex_to_rgba(primary_colour))  # type: ignore[arg-type]

        margin = width // 16
        top_y  = height // 12

        # Headline â€” top-centre
        if headline:
            try:
                bbox      = draw.textbbox((0, 0), headline, font=font_headline)  # type: ignore[arg-type]
                text_w    = bbox[2] - bbox[0]
                headline_x = (width - text_w) // 2
            except Exception:
                headline_x = margin
            _draw_shadowed(headline, (headline_x, top_y), font_headline)

        # Brand name â€” bottom-left (honouring token_placement default)
        bottom_y = height - height // 8
        if brand_name:
            _draw_shadowed(brand_name, (margin, bottom_y), font_headline)

        # Tagline â€” one line below brand name
        if tagline:
            tagline_y = bottom_y + headline_size + 8
            _draw_shadowed(tagline, (margin, tagline_y), font_body)

        img_out = Image.alpha_composite(img, overlay)

        out_buf = BytesIO()
        img_out.convert("RGB").save(out_buf, format="PNG")
        ref_bytes = out_buf.getvalue()

        # â”€â”€ 5. Save reference image via ADK artifact service â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        version = await tool_context.save_artifact(
            filename = ref_key,
            artifact = types.Part.from_bytes(data=ref_bytes, mime_type="image/png"),
        )
        tool_context.state[f"kv_ref_key_{generator_id}"] = ref_key

        logger.info("copy_overlay_saved", generator_id=generator_id, size=(width, height), version=version)
        return {"artifact_key": ref_key, "status": "saved", "version": version}

    except Exception as exc:
        logger.warning("copy_overlay_failed", generator_id=generator_id, error=str(exc))
        return {"status": "failed", "error": str(exc)}


# â”€â”€ KV IMAGE REFINEMENT TOOL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def refine_kv_image(
    generator_id:      int,
    refinement_prompt: str,
    tool_context:      ToolContext,
) -> dict:
    """
    Load the Pillow reference image (kv_ref_{N}.png) and run it through Nano
    Banana 2 (Gemini image model) as an image-to-image refinement pass.

    The model sees the reference image â€” with the flat Pillow text as a positional
    stencil â€” and re-renders the text elements so they appear physically integrated
    with the scene: correct lighting, shadows, material reflections, and depth.

    The background is preserved; only the text region is refined.

    Artifact in:  kv_ref_{N}.png
    Artifact out: kv_final_{N}.png
    State out:    kv_final_key_{N} = "kv_final_{N}.png"

    Args:
        generator_id:      1â€“4 matching the concept branch
        refinement_prompt: 80â€“120 word prompt describing how to integrate the
                           text with the scene (composed by kv_swap_agent_N)

    Returns:
        {"artifact_key": "kv_final_{N}.png", "status": "saved", "version": N}
        or {"status": "failed", "error": "..."}
    """
    ref_key   = f"kv_ref_{generator_id}.png"
    final_key = f"kv_final_{generator_id}.png"

    try:
        from google import genai as _genai  # lazy import

        # â”€â”€ 1. Load reference image from artifact service â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ref_part = await tool_context.load_artifact(ref_key)
        if ref_part is None or not ref_part.inline_data:
            raise ValueError(f"Reference artifact {ref_key!r} not found")
        ref_bytes = ref_part.inline_data.data
        ref_mime  = ref_part.inline_data.mime_type or "image/png"

        # â”€â”€ 2. Image-to-image refinement via Nano Banana 2 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Pass the reference image first, then the text instruction.
        # The model treats the image bytes as a visual layout guide and
        # "bakes" the flat Pillow text into the scene lighting.
        client   = _genai.Client()
        response = client.models.generate_content(
            model    = settings.gemini_model_image,
            contents = [
                types.Part.from_bytes(data=ref_bytes, mime_type=ref_mime),
                refinement_prompt,
            ],
            config   = types.GenerateContentConfig(
                response_modalities = ["IMAGE", "TEXT"],
            ),
        )

        image_data: bytes | None = None
        mime_type = "image/png"
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data is not None:
                image_data = part.inline_data.data
                mime_type  = part.inline_data.mime_type or "image/png"
                break

        if image_data is None:
            raise ValueError("Gemini returned no image data on refinement pass")

        # â”€â”€ 3. Save finished KV via ADK artifact service â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        version = await tool_context.save_artifact(
            filename = final_key,
            artifact = types.Part.from_bytes(data=image_data, mime_type=mime_type),
        )
        tool_context.state[f"kv_final_key_{generator_id}"] = final_key

        logger.info("kv_final_saved", generator_id=generator_id, version=version)
        return {"artifact_key": final_key, "status": "saved", "version": version}

    except Exception as exc:
        logger.warning("kv_refine_failed", generator_id=generator_id, error=str(exc))
        return {"status": "failed", "error": str(exc)}
