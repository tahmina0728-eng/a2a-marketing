from __future__ import annotations
from app._standalone_agents import standalone_strategy
from app.agents._utils import _run_adk_sync

_WEIGHTS = {
    "brand_fit":          0.25,
    "audience_relevance": 0.20,
    "originality":        0.20,
    "business_alignment": 0.15,
    "channel_suitability":0.10,
    "historical_evidence":0.10,
}


def run_strategy(brand: str, prompt: str) -> dict:
    enriched = _enrich_prompt(brand, prompt)
    data = _run_adk_sync(standalone_strategy, brand, enriched)
    if data.get("verdict") == "BLOCKED":
        return {"agent": "strategy", **data}

    _compute_territory_scores(data)
    _sort_territories(data)
    return {"agent": "strategy", **data}


def _enrich_prompt(brand: str, prompt: str) -> str:
    """Append live market signals to the brief so the model can cite them as evidence."""
    extra: list[str] = []
    try:
        from app.market_trends import get_trends, clean_keyword
        trends = get_trends(keywords=[brand, clean_keyword(prompt)], market="UK", timeframe="today 3-m")
        if trends.get("signals"):
            extra.append(f"MARKET SIGNALS (Google Trends, last 3 months): {trends['summary']}")
    except Exception:
        pass
    if extra:
        return prompt + "\n\n" + "\n".join(extra)
    return prompt


def _compute_territory_scores(data: dict) -> None:
    """Re-compute the weighted composite score for each territory from its sub-scores."""
    for t in data.get("creative_territories", []):
        scores = t.get("scores", {})
        if not scores:
            continue
        weighted = sum(scores.get(k, 0.0) * w for k, w in _WEIGHTS.items())
        t["score"] = round(weighted, 3)


def _sort_territories(data: dict) -> None:
    """Sort territories best-first by weighted score."""
    territories = data.get("creative_territories")
    if isinstance(territories, list):
        territories.sort(key=lambda t: t.get("score", 0.0), reverse=True)
