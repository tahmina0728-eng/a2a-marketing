"""
agent_standalone.py — Thin dispatcher: detects brand from the free-text prompt
and routes to the appropriate per-agent module under app/agents/.
"""
from __future__ import annotations

import os

import structlog

from app.agents import (
    run_briefing, run_strategy, run_copy, run_culture,
    run_channel, run_kv, run_tvc, run_reel, run_email_templates,
    get_standalone_page,
)
from app.agents._utils import _extract_brand
from app.agents.channel import _standalone_channel_data

logger = structlog.get_logger()

# Re-export so callers that imported get_standalone_page from here still work.
__all__ = ["get_standalone_page", "publish_standalone_channel", "run_agent_standalone"]


def publish_standalone_channel(
    page_id: str, channel: str, to_email: str = "",
    override_subject: str = "", override_headline: str = "", override_body: str = "",
) -> dict:
    """
    Act on what a standalone Poly run already generated — real actions, same
    underlying functions as the full pipeline's /publish route, just scoped
    to a standalone (non-campaign) run:
      "landing_page" -> confirm the already-generated preview URL
      "email"        -> actually send a branded email via SMTP
      "google_ads"   -> generate the same mocked Google Ads preview

    override_* params carry the user's edits from the email preview modal
    and take priority over the originally generated copy.
    """
    data = _standalone_channel_data.get(page_id)
    if not data:
        raise ValueError("Run Poly first — no generated content found for this preview.")

    harness_base = os.getenv("HARNESS_URL", "http://localhost:8000").rstrip("/")
    brand    = data["brand"]
    headline = override_headline or data.get("headline", "")
    body     = override_body     or data.get("body", "")
    subject  = override_subject  or data.get("email_subject", "") or headline
    cta      = data.get("cta", "") or "Learn More"

    if channel == "landing_page":
        return {"status": "live", "url": f"/agents/landing/{page_id}",
                "public_url": f"{harness_base}/agents/landing/{page_id}"}

    if channel == "email":
        if not to_email:
            return {"status": "skipped", "reason": "Enter a recipient email first."}
        from app.publisher import send_campaign_email
        return send_campaign_email(
            to_email       = to_email,
            brand          = brand,
            hero_message   = headline,
            short_headline = headline,
            cta            = cta,
            landing_url    = f"{harness_base}/agents/landing/{page_id}",
            logo_url       = f"{harness_base}/brand-logo/{brand}",
            email_subject  = subject,
            body_copy      = body,
        )

    if channel == "google_ads":
        from app.publisher import publish_google_ads
        return publish_google_ads(
            campaign_id     = f"standalone-{page_id}",
            brand           = brand,
            short_headline  = headline,
            medium_headline = headline,
            cta             = cta,
            body            = body,
        )

    raise ValueError(f"Unknown or unsupported channel '{channel}' for standalone runs.")


_RUNNERS = {
    "briefing":        run_briefing,
    "strategy":        run_strategy,
    "copy":            run_copy,
    "culture":         run_culture,
    "channel":         run_channel,
    "kv":              run_kv,
    "reel":            run_reel,
    "tvc":             run_tvc,
    "email_templates": run_email_templates,
}


def run_agent_standalone(
    agent_key: str,
    text: str,
    duration: int = 30,
    image_b64: str = "",
    product_name: str = "",
    market: str = "",
    audience: str = "",
    copy_headline: str = "",
    campaign_type: str = "",
) -> dict:
    """text is the whole free-text prompt, e.g. "UBS Bank for UK market, festive: christmas" —
    the brand is detected from it automatically rather than passed separately."""
    runner = _RUNNERS.get(agent_key)
    if not runner:
        raise ValueError(f"No standalone runner for agent '{agent_key}'.")
    brand = _extract_brand(text)
    if not brand:
        raise ValueError(
            "Couldn't tell which brand this is for — mention an uploaded brand's name in your prompt "
            '(e.g. "UBS Bank for UK market, festive: christmas").'
        )
    logger.info("agent_standalone_run", agent=agent_key, brand=brand)
    if agent_key == "tvc":
        return runner(brand, text, duration)
    if agent_key == "channel" and image_b64:
        return runner(brand, text, image_b64)
    if agent_key == "kv":
        return runner(brand, text, product_name=product_name, market=market,
                      audience=audience, copy_headline=copy_headline, campaign_type=campaign_type)
    return runner(brand, text)
