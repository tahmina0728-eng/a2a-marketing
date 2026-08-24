from __future__ import annotations
from app._standalone_agents import standalone_copy
from app.agents._utils import _run_adk_sync, _extract_language

_WEIGHTS = {
    "brand_voice":       0.25,
    "strategy_alignment":0.20,
    "message_clarity":   0.15,
    "audience_relevance":0.15,
    "originality":       0.10,
    "channel_suitability":0.10,
    "grammar_readability":0.05,
}


def run_copy(brand: str, prompt: str) -> dict:
    lang = _extract_language(prompt)
    user_prompt = prompt
    if lang:
        user_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL LANGUAGE OVERRIDE: The user has explicitly selected '{lang}' as the output language. "
            f"ALL copy (headline, subheadline, body, cta) MUST be written entirely in {lang}. "
            f"This overrides any localisation requirements mentioned in the brand guidelines."
        )

    data = _run_adk_sync(standalone_copy, brand, user_prompt)
    if data.get("verdict") == "BLOCKED":
        return {"agent": "copy", **data}

    _compute_variant_scores(data)
    _sort_variants(data)
    return {"agent": "copy", **data}


def _compute_variant_scores(data: dict) -> None:
    """Re-compute weighted quality_score for each variant from its sub-scores."""
    for v in data.get("variants", []):
        scores = v.get("scores", {})
        if not scores:
            continue
        weighted = sum(scores.get(k, 0.0) * w for k, w in _WEIGHTS.items())
        v["quality_score"] = round(weighted, 3)


def _sort_variants(data: dict) -> None:
    """Sort variants best-first by quality_score and update recommended_variant index."""
    variants = data.get("variants")
    if not isinstance(variants, list) or len(variants) < 2:
        return
    variants.sort(key=lambda v: v.get("quality_score", 0.0), reverse=True)
    data["recommended_variant"] = 0  # best is always index 0 after sort
