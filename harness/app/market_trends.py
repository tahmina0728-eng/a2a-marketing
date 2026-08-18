"""
market_trends.py — Live Google Trends signals via pytrends.

Fetches relative search interest (0–100) for brand/product keywords
over the last 3 months. Called by load_brand_context so the briefing
agent receives real market signal context alongside brand guidelines.

Fails silently — if pytrends is rate-limited or unavailable the
briefing pipeline continues normally with zero market trend data.

Results are cached in-process for 1 hour to avoid Google 429s on
repeated briefing runs within the same server session.
"""
from __future__ import annotations

import re
import time
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

# In-process TTL cache: {cache_key: (timestamp, result)}
_cache: dict[tuple, tuple[float, dict]] = {}
_CACHE_TTL = 3600  # seconds — 1 hour


def _geo_code(market: str) -> str:
    market = market.strip().upper()
    _map = {
        # Global / worldwide — Google Trends uses empty string
        "GLOBAL": "", "WORLDWIDE": "", "INTERNATIONAL": "", "ALL": "",
        # Named markets
        "UK": "GB", "UNITED KINGDOM": "GB", "GREAT BRITAIN": "GB",
        "US": "US", "USA": "US", "UNITED STATES": "US",
        "DE": "DE", "GERMANY": "DE",
        "FR": "FR", "FRANCE": "FR",
        "AU": "AU", "AUSTRALIA": "AU",
        "IN": "IN", "INDIA": "IN",
        "SG": "SG", "SINGAPORE": "SG",
        "AE": "AE", "UAE": "AE",
        "JP": "JP", "JAPAN": "JP",
        "CA": "CA", "CANADA": "CA",
        "BR": "BR", "BRAZIL": "BR",
        "ES": "ES", "SPAIN": "ES",
        "IT": "IT", "ITALY": "IT",
        "NL": "NL", "NETHERLANDS": "NL",
        "SE": "SE", "SWEDEN": "SE",
        "NO": "NO", "NORWAY": "NO",
        "CH": "CH", "SWITZERLAND": "CH",
        "PL": "PL", "POLAND": "PL",
        "ZA": "ZA", "SOUTH AFRICA": "ZA",
    }
    if market in _map:
        return _map[market]
    # If it looks like a valid 2-letter ISO code, use it; otherwise fall back to GB
    if len(market) == 2 and market.isalpha():
        return market
    return "GB"


def clean_keyword(text: str, max_words: int = 2) -> str:
    """
    Strip parenthetical content, trailing connectors, and punctuation,
    then take the first max_words words.

    Examples:
        "Barclays Brand & Identity"       → "Barclays Brand"
        "Summer (The Championships, Wimbledon)" → "Summer"
        "Wimbledon Season (Summer)"       → "Wimbledon Season"
    """
    # Remove anything inside parentheses (including the parens)
    text = re.sub(r'\s*\(.*?\)\s*', ' ', text).strip()
    # Split and take first max_words
    words = text.split()[:max_words]
    # Drop a trailing word that is a connector or punctuation-only
    while words and re.fullmatch(r'[&,.\-/\\]|and|or|the|a|an', words[-1], re.I):
        words.pop()
    return " ".join(words).strip()


def get_trends(
    keywords: list[str],
    market:   str = "UK",
    timeframe: str = "today 3-m",
) -> dict[str, Any]:
    """
    Fetch Google Trends interest for up to 5 keywords.

    Returns dict with:
        signals       — number of daily data points returned
        top_keyword   — keyword with highest average interest
        avg_interest  — 0–100 relative interest score for top keyword
        summary       — human-readable string for the briefing agent
        data          — {keyword: avg_score} for all keywords
    """
    keywords = [k.strip() for k in keywords if k and k.strip()][:5]
    if not keywords:
        return _EMPTY

    geo = _geo_code(market)
    cache_key = (tuple(keywords), geo, timeframe)

    # Return cached result if still fresh
    if cache_key in _cache:
        ts, cached = _cache[cache_key]
        if time.time() - ts < _CACHE_TTL:
            logger.info("trends_cache_hit", keywords=keywords, geo=geo)
            return cached

    try:
        from pytrends.request import TrendReq

        pt = TrendReq(
            hl      = "en-GB",
            geo     = geo,
            timeout = (10, 30),
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

        top_keyword  = max(avgs, key=lambda k: avgs[k])
        avg_interest = avgs[top_keyword]

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

        result = {
            "signals":      signals,
            "top_keyword":  top_keyword,
            "avg_interest": avg_interest,
            "summary":      summary,
            "data":         avgs,
        }
        _cache[cache_key] = (time.time(), result)
        return result

    except Exception as exc:
        logger.warning("trends_failed", error=str(exc), geo=geo, keywords=keywords)
        return _EMPTY
