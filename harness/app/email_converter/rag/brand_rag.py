"""
Brand RAG — reads brand guidelines from the GCS bucket (or local bucket/ fallback).

Bucket: dauntless-karma-497108-b0-campaignos
Path:   brands/{brand}/
  brand.json                      ← structured profile: tone, colors, rules, compliance
  Guidelines/brand_guidelines.md  ← full markdown guidelines text
  Guidelines/brand_guidelines.txt ← fallback plain-text guidelines

Uses BrandAssetLoader which handles GCS vs local mode transparently via
the BRAND_ASSETS_MODE env var. No Firestore dependency.

Returned dict shape (same interface as before):
  tone_of_voice   : str   — e.g. "trusted, clear, scientifically grounded"
  do_say          : list  — phrases / requirements to include
  dont_say        : list  — phrases / claims to avoid
  brand_colors    : list  — primary hex colours, e.g. ["#007A33", "#FFFFFF"]
  guidelines_text : str   — full markdown guidelines (capped at 8 000 chars)
  font_family     : str   — web-safe font stack
  email_footer    : str   — footer override (empty unless set in brand.json)
"""
from __future__ import annotations
from typing import Any

import structlog

logger = structlog.get_logger()

_DEFAULT: dict[str, Any] = {
    "tone_of_voice":   "",
    "do_say":          [],
    "dont_say":        [],
    "brand_colors":    [],
    "guidelines_text": "",
    "font_family":     "'Helvetica Neue', Helvetica, Arial, sans-serif",
    "email_footer":    "",
}


class BrandRAG:
    """
    Retrieves brand guidelines from the GCS bucket for a given brand name.

    Two data sources are combined per brand:
      1. brand.json       — structured: tone, avoid/require lists, primary colours
      2. brand_guidelines.md / .txt — full markdown text for the LLM composer

    The BrandAssetLoader (app.brand_assets) is the single source of truth
    and handles both GCS and local bucket/ modes automatically.

    Usage:
        rag = BrandRAG()
        ctx = rag.search("Haleon")
        # ctx = { tone_of_voice, do_say, dont_say, brand_colors, guidelines_text }

        # Async callers:
        ctx = await rag.async_search("Haleon")
    """

    def __init__(self):
        self._loader = None   # lazy — avoids import-time GCS connection

    def _get_loader(self):
        if self._loader is None:
            from app.brand_assets import get_asset_loader
            self._loader = get_asset_loader()
        return self._loader

    def search(self, brand_name: str) -> dict[str, Any]:
        """
        Return brand context dict for brand_name from GCS bucket.
        Never raises — always returns a usable dict (defaults on any error).
        """
        if not brand_name:
            return dict(_DEFAULT)

        result = dict(_DEFAULT)

        try:
            loader = self._get_loader()

            # ── 1. Structured profile from brand.json ─────────────────────
            profile = loader.load_brand_profile(brand_name)
            if profile:
                vi = profile.get("visual_identity", {})
                cr = profile.get("creative_rules",  {})
                co = profile.get("compliance",       {})

                # Combine tone + visual style into one sentence
                tone  = cr.get("tone",  "").strip()
                style = vi.get("style", "").strip()
                result["tone_of_voice"] = " — ".join(filter(None, [tone, style]))

                # do_say: explicit requirements from creative rules
                result["do_say"] = list(cr.get("require", []))

                # dont_say: creative avoids + compliance prohibited phrases
                result["dont_say"] = list(cr.get("avoid", [])) + list(co.get("prohibited_phrases", []))

                # Primary brand colours
                result["brand_colors"] = list(vi.get("primary_colors", []))

                # Optional email footer override
                result["email_footer"] = cr.get("email_footer", "") or ""

            # ── 2. Full markdown guidelines text ──────────────────────────
            text = loader.load_guidelines(brand_name)
            if text:
                result["guidelines_text"] = text[:8000]   # cap to avoid token bloat

            logger.info(
                "brand_rag_search_ok",
                brand       = brand_name,
                has_profile = bool(profile if 'profile' in dir() else None),
                colors      = result["brand_colors"],
                guidelines_chars = len(result["guidelines_text"]),
            )

        except Exception as exc:
            logger.warning("brand_rag_search_failed", brand=brand_name, error=str(exc))

        return result

    async def async_search(self, brand_name: str) -> dict[str, Any]:
        """Async wrapper — BrandAssetLoader is sync; this satisfies async callers."""
        return self.search(brand_name)
