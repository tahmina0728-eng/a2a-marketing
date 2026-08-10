"""Shared utilities for all standalone agent modules."""
from __future__ import annotations

import json
import re
import time

import structlog
from google import genai

from app.config import get_settings
from app.brand_assets import get_asset_loader

logger   = structlog.get_logger()
settings = get_settings()

_client = None


def _genai_client():
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=settings.gcp_project, location=settings.gcp_region)
    return _client


def _brand_guidelines(brand: str) -> str:
    text = get_asset_loader().load_guidelines(brand)
    return text[:6000] if text else "(no brand guidelines on file for this brand — use general best practice)"


def _extract_brand(text: str) -> str | None:
    """Find which known (uploaded) brand is referenced in the free text, preferring the longest match —
    e.g. "UBS Bank for UK market, festive: christmas" -> "UBS Bank", not a shorter coincidental match."""
    known = get_asset_loader().list_brands()
    text_lower = text.lower()
    matches = [b for b in known if b.lower() in text_lower]
    return max(matches, key=len) if matches else None


def _parse_json_loose(text: str) -> dict | None:
    """Pull a JSON object out of a model response that may have wrapping prose/markdown fences."""
    # Strip markdown code fences first
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _extract_language(text: str) -> str:
    """Extract language tag from prompt text, e.g. 'Language: German (de-CH)' -> 'German (de-CH)'."""
    m = re.search(r"[Ll]anguage:\s*([^\.\n,]+)", text)
    return m.group(1).strip() if m else ""


def _generate(persona: str, brand: str, prompt: str, output_instructions: str) -> dict:
    guidelines   = _brand_guidelines(brand)
    full_prompt = (
        f"{persona}\n\n"
        f"BRAND GUIDELINES for {brand}:\n{guidelines}\n\n"
        f"CREATIVE DIRECTION from the user: \"{prompt}\"\n\n"
        f"{output_instructions}"
    )
    for attempt in range(3):
        try:
            resp = _genai_client().models.generate_content(
                model=settings.gemini_model_reasoning, contents=full_prompt,
            )
            raw = (resp.text or "").strip()
            return _parse_json_loose(raw) or {"raw": raw}
        except Exception as _e:
            err = str(_e)
            if "429" in err and attempt < 2:
                wait = 30 * (attempt + 1)
                logger.warning("standalone_generate_429_retry", brand=brand, attempt=attempt + 1, wait=wait)
                time.sleep(wait)
            else:
                logger.warning("standalone_generate_failed", brand=brand, error=err)
                return {"error": err}
    return {"error": "quota exhausted after retries"}
