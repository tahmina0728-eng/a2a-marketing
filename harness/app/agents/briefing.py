from __future__ import annotations
from app.agents._utils import _generate


def run_briefing(brand: str, prompt: str) -> dict:
    data = _generate(
        "You are Logos, the briefing agent for an AI marketing campaign system. "
        "You validate a campaign idea against brand guidelines and give a quick quality read.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"goal": "...", "product": "...", "fan_truth": "the human insight behind this, one sentence", '
        '"audience": "who this is for, one phrase", "market": "...", "season": "...", '
        '"score": <integer 0-100>, "verdict": "PASS or NEEDS WORK", '
        '"summary": "1-2 sentence rationale for the score"}',
    )

    # Enrich with real data-source stats for the briefing dashboard
    source_stats = _get_source_stats(brand, data)
    return {"agent": "briefing", **data, **source_stats}


def _get_source_stats(brand: str, data: dict) -> dict:
    """Fetch real data-source counts: Google Trends, Vertex AI Search, GCS product files."""
    from app.config import get_settings
    settings = get_settings()
    stats: dict = {}

    # Google Trends — market signals
    try:
        from app.market_trends import get_trends
        market = data.get("market", "UK") or "UK"
        trends = get_trends(
            keywords  = [kw for kw in [brand, data.get("product", ""), data.get("season", "")] if kw],
            market    = market,
            timeframe = "today 3-m",
        )
        if trends["signals"]:
            stats["_market_signals"]      = trends["signals"]
            stats["_market_top_keyword"]  = trends["top_keyword"]
            stats["_market_avg_interest"] = trends["avg_interest"]
            stats["_market_summary"]      = trends["summary"]
    except Exception:
        pass

    # Vertex AI Search — brand guidelines chunks
    try:
        if settings.search_mode == "live":
            from app.search_client import get_search_client
            sc = get_search_client()
            brand_result = sc.get_brand_rules(product_category="", channels=[])
            if brand_result.results:
                stats["_chunks"] = len(brand_result.results)
    except Exception:
        pass

    # GCS product catalogue — actual file count
    try:
        from app.brand_assets import get_asset_loader
        product_paths = get_asset_loader().list_products(brand)
        if product_paths:
            stats["_product_skus"] = len(product_paths)
    except Exception:
        pass

    return stats
