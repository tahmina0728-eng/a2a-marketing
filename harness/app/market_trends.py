"""
market_trends.py — Live Google Trends signals via pytrends.

Fetches relative search interest (0–100) for brand/product keywords
over the last 3 months. Called by load_brand_context so the briefing
agent receives real market signal context alongside brand guidelines.

Fails silently — if pytrends is rate-limited or unavailable the
briefing pipeline continues normally with zero market trend data.
"""
from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

_EMPTY: dict[str, Any] = {
    "signals":        0,
    "top_keyword":    "",
    "avg_interest":   0.0,
    "summary":        "",
    "data":           {},
}


def _geo_code(market: str) -> str:
    """Map a market string to a 2-letter Google Trends geo code."""
    market = market.strip().upper()
    _map = {
        "UK": "GB", "UNITED KINGDOM": "GB", "GREAT BRITAIN": "GB",
        "US": "US", "USA": "US", "UNITED STATES": "US",
        "DE": "DE", "GERMANY": "DE",
        "FR": "FR", "FRANCE": "FR",
        "AU": "AU", "AUSTRALIA": "AU",
        "IN": "IN", "INDIA": "IN",
        "SG": "SG", "SINGAPORE": "SG",
        "AE": "AE", "UAE": "AE",
    }
    return _map.get(market, market[:2] if len(market) >= 2 else "GB")


def get_trends(
    keywords: list[str],
    market:   str = "UK",
    timeframe: str = "today 3-m",
) -> dict[str, Any]:
    """
    Fetch Google Trends interest for up to 5 keywords.

    Args:
        keywords:  Search terms (brand name, product, season/moment).
        market:    Market string — mapped to a geo code (e.g. "UK" → "GB").
        timeframe: pytrends timeframe string. Default = last 3 months.

    Returns dict with:
        signals       — number of weekly data points returned (real count)
        top_keyword   — keyword with highest average interest
        avg_interest  — 0–100 relative interest score for top keyword
        summary       — human-readable string for the briefing agent
        data          — {keyword: avg_score} for all keywords
    """
    keywords = [k.strip() for k in keywords if k and k.strip()][:5]
    if not keywords:
        return _EMPTY

    geo = _geo_code(market)

    try:
        from pytrends.request import TrendReq

        pt = TrendReq(
            hl             = "en-GB",
            geo            = geo,
            timeout        = (10, 30),
            retries        = 1,
            backoff_factor = 0.5,
        )
        pt.build_payload(keywords, timeframe=timeframe, geo=geo)
        df = pt.interest_over_time()

        if df is None or df.empty:
            logger.warning("trends_empty", geo=geo, keywords=keywords)
            return _EMPTY

        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])

        avgs    = {col: round(float(df[col].mean()), 1) for col in df.columns}
        signals = len(df)

        top_keyword   = max(avgs, key=lambda k: avgs[k])
        avg_interest  = avgs[top_keyword]

        trend_parts = [
            f"{kw}: {int(score)}/100"
            for kw, score in sorted(avgs.items(), key=lambda x: -x[1])
        ]
        summary = (
            f"Google Trends ({geo}, last 3 months) — "
            + "; ".join(trend_parts)
        )

        logger.info(
            "trends_ok",
            geo          = geo,
            keywords     = keywords,
            signals      = signals,
            top_keyword  = top_keyword,
            avg_interest = avg_interest,
        )

        return {
            "signals":      signals,
            "top_keyword":  top_keyword,
            "avg_interest": avg_interest,
            "summary":      summary,
            "data":         avgs,
        }

    except Exception as exc:
        logger.warning("trends_failed", error=str(exc), geo=geo, keywords=keywords)
        return _EMPTY
