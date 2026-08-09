"""
model_router.py — Three-way image model router for CampaignOS.

Architecture stage:
  Copy Skill → [Model Router] → Gemini | Imagen | GPT Image → Generated Assets

Three routing buckets
─────────────────────
  Gemini   — gemini-2.0-flash-preview-image-generation (or GEMINI_MODEL_IMAGE)
             Best for: FMCG, energy drinks, beauty, telco — vibrant, creative outputs
             Backend: google.genai (Vertex AI)

  Imagen   — imagen-4.0-generate-preview-05-20 (or IMAGEN_MODEL)
             Best for: regulated finance (FCA/FINMA), pharma (MHRA), luxury spirits
             Backend: google.genai (Vertex AI, same client — Imagen is a Vertex model)

  GPT Image — gpt-image-1 or dall-e-3 (or GPT_IMAGE_MODEL)
             Best for: lifestyle, fashion, editorial, human-centric scenes where
             DALL-E/GPT produces more photorealistic human subjects
             Backend: openai Python SDK

Model selection priority (per brand)
──────────────────────────────────────
  1. brand.json → "image_model" key           (explicit override by brand team)
  2. Routing table below                       (industry / regulator classification)
  3. Settings default (GEMINI_MODEL_IMAGE)     (safe fallback)

To activate a bucket, set the corresponding env var in Cloud Run:
  IMAGEN_MODEL=imagen-4.0-generate-preview-05-20
  GPT_IMAGE_MODEL=gpt-image-1
  OPENAI_API_KEY=sk-...

If a bucket's env var is blank, the router falls back to Gemini (no breakage).
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# ── Classification keywords ────────────────────────────────────────────────────
_REGULATED_REGULATORS = ("FCA", "FINMA", "MHRA", "PORTMAN", "BAKOM")
_REGULATED_INDUSTRIES = ("banking", "financial", "insurance", "wealth", "pharma", "health")
_LUXURY_INDUSTRIES    = ("spirits", "luxury", "premium", "whisky", "scotch")
_GPT_INDUSTRIES       = ("lifestyle", "fashion", "apparel", "editorial", "beauty", "personal care")
_FMCG_INDUSTRIES      = ("fmcg", "energy", "food", "beverage", "telecommunications", "telco", "retail")

# Provider detection from model name (used by the image generation dispatcher)
_OPENAI_PREFIXES  = ("gpt-", "dall-e", "dall_e", "o1-", "o3-")
_IMAGEN_PREFIXES  = ("imagen",)


def _is_openai_model(model: str) -> bool:
    m = model.lower()
    return any(m.startswith(p) for p in _OPENAI_PREFIXES)


def _is_imagen_model(model: str) -> bool:
    m = model.lower()
    return any(m.startswith(p) for p in _IMAGEN_PREFIXES)


def route_image_model(
    brand_profile_dict: dict | None,
    gemini_image_model: str,
    imagen_model: str = "",
    gpt_image_model: str = "",
    fallback_image_model: str = "",
) -> tuple[str, str, str]:
    """
    Select the primary and fallback image models for this brand campaign.

    Returns:
        (primary_model, fallback_model, rationale)

    The caller uses the returned model names to dispatch to the correct
    image generation backend — use provider_for_model() to determine which.
    """
    if not brand_profile_dict:
        return gemini_image_model, fallback_image_model, "no brand profile — Gemini default"

    brand_info = brand_profile_dict.get("brand", {})
    regulator  = (brand_info.get("regulator") or "").upper()
    industry   = (brand_info.get("industry")  or "").lower()
    brand_name = brand_info.get("name", "unknown")

    # Brand team override inside brand.json takes precedence over routing table
    if brand_profile_dict.get("image_model"):
        override = brand_profile_dict["image_model"]
        logger.info("model_router_brand_override", brand=brand_name, model=override)
        return override, fallback_image_model, f"brand.json override → {override}"

    is_regulated = (
        any(r in regulator for r in _REGULATED_REGULATORS) or
        any(k in industry  for k in _REGULATED_INDUSTRIES)
    )
    is_luxury  = any(k in industry for k in _LUXURY_INDUSTRIES)
    is_gpt_fit = any(k in industry for k in _GPT_INDUSTRIES)

    # ── Route: Imagen (regulated / luxury) ────────────────────────────────────
    if (is_regulated or is_luxury) and imagen_model and imagen_model != gemini_image_model:
        bucket    = "regulated" if is_regulated else "luxury"
        rationale = (
            f"{bucket} brand ({regulator or industry}) — "
            f"Imagen selected for brand-safe, high-fidelity output"
        )
        primary  = imagen_model
        fallback = gemini_image_model   # Gemini as quota fallback
        logger.info("model_router_decision",
                    brand=brand_name, bucket="imagen",
                    primary=primary, fallback=fallback, rationale=rationale)
        return primary, fallback, rationale

    # ── Route: GPT Image (lifestyle / fashion / human-centric) ────────────────
    if is_gpt_fit and gpt_image_model and not is_regulated:
        rationale = (
            f"lifestyle/fashion brand ({industry}) — "
            f"GPT Image selected for photorealistic human subjects"
        )
        primary  = gpt_image_model
        fallback = gemini_image_model   # Gemini as quota fallback
        logger.info("model_router_decision",
                    brand=brand_name, bucket="gpt_image",
                    primary=primary, fallback=fallback, rationale=rationale)
        return primary, fallback, rationale

    # ── Route: Gemini (FMCG / energy / default) ───────────────────────────────
    rationale = f"creative/FMCG brand ({industry or 'default'}) — Gemini image model"
    logger.info("model_router_decision",
                brand=brand_name, bucket="gemini",
                primary=gemini_image_model, fallback=fallback_image_model,
                rationale=rationale)
    return gemini_image_model, fallback_image_model, rationale


def provider_for_model(model: str) -> str:
    """
    Return the image generation backend provider for a given model name.

    Returns: "openai" | "vertex"

    Used by run_creative_pipeline_direct() to dispatch to the right API client.
    """
    if _is_openai_model(model):
        return "openai"
    return "vertex"   # covers both Gemini and Imagen (same google.genai client)
