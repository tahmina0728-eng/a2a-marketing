"""
tools.py â€” ADK tool definitions for CampaignOS agents.

All data-loading and persistence functions have been moved out of this file:
  - Data loading    → nodes.py (deterministic graph function nodes)
  - State + artifact persistence → nodes.py persist_* function nodes
                                    (InvocationContext-based, deterministic)

This file contains ONLY the image generation tool that requires ADK's async
ToolContext for Gemini image generation + artifact storage.

Tool list:
  generate_and_save_kv_image â€” Gemini image generation; saves PNG via ADK artifact
                               service (InMemory in dev, GCS in prod â€” zero code change).
                               Passes product photos as multi-modal image inputs so the
                               model sees the actual product photography.

"""

import json
import structlog

from google.adk.tools import ToolContext
from google.genai import types

from app.config import get_settings

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

        # Only send product photos that the image_prompt explicitly references
        # (e.g. "Product1", "Product3"). Sending every product in the brand
        # folder bloats the request and confuses the model when the brief only
        # calls for one hero product.
        referenced_products = {
            k: v for k, v in product_image_map.items() if k in image_prompt
        }
        # Safety fallback: if the prompt references no ProductN keys at all,
        # send the full map so the model still has something to work with.
        products_to_send = referenced_products or product_image_map

        # Prepend product photos as labelled multimodal inputs.
        # Text labels ("Product1:", "Product2:", ...) must immediately precede
        # each image so the model knows which blob maps to which product key
        # referenced in the image_prompt (e.g. "Reference Product1 above").
        # Without labels the model sees anonymous images and ignores them.
        if products_to_send:
            contents.append(
                "Reference product photography follows. "
                "Each image is labelled by the product key used in the prompt:"
            )
            for product_name, uri in products_to_send.items():
                img_bytes = _load_asset_bytes(uri)
                if img_bytes:
                    contents.append(f"{product_name}:")
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
