from __future__ import annotations
from app._standalone_agents import standalone_briefing
from app.agents._utils import _run_adk_sync


def run_briefing(brand: str, prompt: str) -> dict:
    data = _run_adk_sync(standalone_briefing, brand, prompt)

    if data.get("verdict") == "BLOCKED":
        return {"agent": "briefing", **data}

    source_stats = _get_source_stats(brand, data)
    return {"agent": "briefing", **data, **source_stats}


def _get_source_stats(brand: str, data: dict) -> dict:
    """Fetch real data-source counts: Google Trends, Vertex AI Search, GCS product files."""
    from app.config import get_settings
    settings = get_settings()
    stats: dict = {}

    try:
        from app.market_trends import get_trends, clean_keyword
        market = data.get("market", "UK") or "UK"
        raw_keywords = [
            brand,
            clean_keyword(data.get("product", "") or ""),
            clean_keyword(data.get("season", "") or ""),
        ]
        trends = get_trends(
            keywords  = [kw for kw in raw_keywords if kw],
            market    = market,
            timeframe = "today 3-m",
        )
        if trends["signals"]:
            stats["_market_signals"]      = trends["signals"]
            stats["_market_top_keyword"]  = trends["top_keyword"]
            stats["_market_avg_interest"] = trends["avg_interest"]
            stats["_market_summary"]      = trends["summary"]
            stats["_market_data"]         = trends["data"]
    except Exception:
        pass

    try:
        if settings.search_mode == "live":
            from app.search_client import get_search_client
            sc = get_search_client()
            brand_result = sc.get_brand_rules(product_category="", channels=[])
            if brand_result.results:
                stats["_chunks"] = len(brand_result.results)
    except Exception:
        pass

    try:
        from app.brand_assets import get_asset_loader
        product_paths = get_asset_loader().list_products(brand)
        if product_paths:
            stats["_product_skus"] = len(product_paths)
    except Exception:
        pass

    return stats
