"""
agent_standalone.py — Thin dispatcher: detects brand from the free-text prompt
and routes to the appropriate per-agent module under app/agents/.
"""
from __future__ import annotations

import os

import structlog

from app.agents import (
    run_briefing, run_strategy, run_copy, run_culture,
    run_channel, run_kv, run_tvc, run_reel,
    run_email_templates, run_email_converter,
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


def _pick_best_ideon_copy(ideon_content: dict) -> dict:
    """
    Given the full Ideon artifact content, return a copy of the dict where
    banner_copy.linkedin_1200x627 is overwritten with the recommended/highest-scoring
    variant's copy so Morphis always receives a single, unambiguous copy to work from.
    """
    import copy as _copy
    out = _copy.deepcopy(ideon_content)

    variants: list = out.get("variants", [])
    if not variants:
        return out

    # Use recommended_variant index if valid, otherwise pick by highest quality_score
    rec_idx = out.get("recommended_variant", 0)
    if not (isinstance(rec_idx, int) and 0 <= rec_idx < len(variants)):
        rec_idx = max(range(len(variants)),
                      key=lambda i: variants[i].get("quality_score", 0))

    best = variants[rec_idx]

    # Overwrite banner_copy with the best variant's copy so Morphis has no ambiguity
    out.setdefault("banner_copy", {})
    out["banner_copy"]["linkedin_1200x627"] = {
        "heading":    best.get("headline", ""),
        "subheading": best.get("subheadline", ""),
        "cta":        best.get("cta", ""),
    }
    # Expose selected_copy so Morphis LLM can reference it directly
    out["selected_copy"] = {
        "variant_index": rec_idx,
        "tone":          best.get("tone", ""),
        "headline":      best.get("headline", ""),
        "subheadline":   best.get("subheadline", ""),
        "body":          best.get("body", ""),
        "cta":           best.get("cta", ""),
        "quality_score": best.get("quality_score", 0),
    }
    return out


def _extract_prompt_headline(text: str) -> str:
    # Extract an explicitly stated headline/slogan from the user prompt.
    # Handles: slogan 'Don't Navigate AI Alone'  /  headline: "AI you can answer for"
    import re
    _TRIGGER = r"(?:slogan|headline|heading|tagline|called|titled)\s*[:\-]?\s*"
    # Double-quoted match
    m = re.search(_TRIGGER + r'"([^"]{3,80})"', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Single-quoted — allow contractions (apostrophe + lowercase) inside the string
    m = re.search(
        _TRIGGER + r"'((?:[^']|'(?=[a-z])){3,80})'",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return ""


def _infosys_morphis_with_copy(
    brief: dict,
    copy_headline: str,
    copy_subline: str,
    copy_cta: str,
    color_theme: str = "blue",
    sub_brand: str = "",
    speaker_image_b64: str = "",
    speaker_name: str = "",
    speaker_title: str = "",
    content_type_badge: str = "",
) -> dict:
    """
    Run Morphis using pre-supplied copy (from a previous Ideon run).
    Skips the internal Logos→Helia→Ideon pipeline and goes straight to:
      1. Morphis visual spec (for layout / image-prompt details)
      2. KV compositor (generates the actual image with the supplied copy)
    Returns a dict with image_b64, headline, brand, and Morphis spec fields.
    """
    import base64
    from app.agents.infosys.logos import LogosAgent
    from app.agents.infosys.helia import HeliaAgent
    from app.agents.infosys.morphis import MorphisAgent
    from app.schemas.common import AgentResponse, Artifact, AgentInfo, JobInfo
    from app.brands.infosys.compositor import generate_kv

    # Still need Logos+Helia for creative territory context (fast — no copy generation)
    logos = LogosAgent().run(brief)
    helia = HeliaAgent().run(logos)

    # Build a synthetic Ideon copy_deck from the supplied copy
    synthetic_copy = {
        "campaign_name": brief.get("campaign_name", "Infosys Campaign"),
        "selected_copy": {
            "headline":    copy_headline,
            "subheadline": copy_subline,
            "cta":         copy_cta,
        },
        "banner_copy": {
            "linkedin_1200x627": {
                "heading":    copy_headline,
                "subheading": copy_subline,
                "cta":        copy_cta,
            }
        },
    }
    synthetic_ideon = AgentResponse(
        agent    = AgentInfo(name="ideon"),
        job      = JobInfo(campaign_name=brief.get("campaign_name", "")),
        status   = "completed",
        artifact = Artifact(type="copy_deck", content=synthetic_copy),
    )

    # Run Morphis for visual spec
    morphis_r = MorphisAgent().run({"creative_platform": helia, "copy_deck": synthetic_ideon})
    spec = morphis_r.artifact.content if morphis_r and morphis_r.artifact else {}

    # Generate the actual KV image with the compositor
    img_bytes = generate_kv(
        headline            = copy_headline,
        subline             = copy_subline,
        cta                 = copy_cta,
        sub_brand           = sub_brand,
        aspect_ratio        = "16:9",
        color_theme         = color_theme,
        speaker_image_b64   = speaker_image_b64,
        speaker_name        = speaker_name,
        speaker_title       = speaker_title,
        content_type_badge  = content_type_badge,
    )

    return {
        "image_b64": base64.b64encode(img_bytes).decode(),
        "brand":     "Infosys",
        "headline":  copy_headline,
        "subline":   copy_subline,
        "cta":       copy_cta,
        "color_theme": color_theme,
        "morphis_spec": spec,
    }


def _infosys_runner(agent_key: str, text: str, **kwargs) -> dict:
    """
    Thin runner for individual Infosys A2A agents called from the standalone sidebar.

    The user's free-text prompt is treated as the campaign brief objective if it
    cannot be parsed as JSON.  Each agent returns an AgentResponse whose .artifact.content
    dict is what the UI renders.
    """
    import asyncio, json as _json

    # Accept JSON brief or natural-language text.
    # The Campaign wizard prefixes the JSON with "Infosys — " — strip any non-JSON
    # preamble before the first "{" so the structured brief is always parsed correctly.
    _brace = text.find("{")
    _parse_text = text[_brace:] if _brace >= 0 else text
    try:
        brief: dict = _json.loads(_parse_text)
    except Exception:
        brief = {"campaign_name": "Infosys Campaign", "objective": text,
                 "channels": ["LinkedIn"], "market": "UK"}

    if agent_key == "infosys_logos":
        from app.agents.infosys.logos import LogosAgent
        r = LogosAgent().run(brief)
    elif agent_key == "infosys_helia":
        from app.agents.infosys.logos import LogosAgent
        from app.agents.infosys.helia import HeliaAgent
        logos = LogosAgent().run(brief)
        r = HeliaAgent().run(logos)
    elif agent_key == "infosys_ideon":
        from app.agents.infosys.logos import LogosAgent
        from app.agents.infosys.helia import HeliaAgent
        from app.agents.infosys.ideon import IdeonAgent
        # Capture any slogan from the raw brief BEFORE Logos rewrites the objective.
        # We check the raw objective text and the original free-text prompt because
        # Logos transforms the objective field and the slogan would be lost otherwise.
        _raw_objective = brief.get("objective", "") or brief.get("campaign_name", "") or text
        _pinned_headline = _extract_prompt_headline(_raw_objective)
        logos = LogosAgent().run(brief)
        # Inject the pinned headline into the Logos output so Ideon can read it directly.
        if _pinned_headline and logos and logos.artifact:
            logos.artifact.content["preferred_headline"] = _pinned_headline
        helia = HeliaAgent().run(logos)
        r = IdeonAgent().run({"brief": logos, "creative_platform": helia})
    elif agent_key == "infosys_aether":
        from app.agents.infosys.aether import AetherAgent
        scope = {**brief, "segment": brief.get("audience", ""), "brand": "Infosys"}
        r = AetherAgent().run(scope)
    elif agent_key == "infosys_morphis":
        copy_headline      = kwargs.get("copy_headline",      "")
        copy_subline       = kwargs.get("copy_subline",       "")
        copy_cta           = kwargs.get("copy_cta",           "")
        color_theme        = kwargs.get("color_theme",        "blue")
        speaker_image_b64  = kwargs.get("speaker_image_b64",  "")
        speaker_name       = kwargs.get("speaker_name",       "")
        speaker_title      = kwargs.get("speaker_title",      "")
        content_type_badge = kwargs.get("content_type_badge", "")
        _spk = dict(
            speaker_image_b64=speaker_image_b64, speaker_name=speaker_name,
            speaker_title=speaker_title, content_type_badge=content_type_badge,
        )
        # If the user stated a headline/slogan directly in the prompt, use it.
        if not copy_headline:
            copy_headline = _extract_prompt_headline(text)

        if copy_headline:
            # Honour explicit copy — either from a previous Ideon run or stated in the prompt.
            return _infosys_morphis_with_copy(
                brief, copy_headline, copy_subline, copy_cta,
                color_theme=color_theme,
                sub_brand=brief.get("sub_brand", ""),
                **_spk,
            )
        # No copy found anywhere: run full Logos→Helia→Ideon pipeline,
        # auto-select the best copy variant, then generate the KV image.
        from app.agents.infosys.logos import LogosAgent
        from app.agents.infosys.helia import HeliaAgent
        from app.agents.infosys.ideon import IdeonAgent
        from app.schemas.common import AgentResponse, AgentInfo, JobInfo, Artifact
        logos = LogosAgent().run(brief)
        helia = HeliaAgent().run(logos)
        ideon = IdeonAgent().run({"brief": logos, "creative_platform": helia})
        best_content = (
            _pick_best_ideon_copy(ideon.artifact.content)
            if ideon and ideon.artifact else {}
        )
        best = best_content.get("selected_copy", {})
        # Use the AI-generated copy — never fall back to the raw user prompt
        auto_headline = best.get("headline", "")
        auto_subline  = best.get("subheadline", "")
        auto_cta      = best.get("cta", "")
        if auto_headline:
            return _infosys_morphis_with_copy(
                brief, auto_headline, auto_subline, auto_cta,
                color_theme=color_theme,
                sub_brand=brief.get("sub_brand", ""),
                **_spk,
            )
        # Last resort: return Morphis visual spec when image generation isn't possible
        from app.agents.infosys.morphis import MorphisAgent
        ideon_resp = AgentResponse(
            agent=ideon.agent, job=ideon.job, status=ideon.status,
            artifact=Artifact(type=ideon.artifact.type, content=best_content),
        ) if ideon and ideon.artifact else ideon
        r = MorphisAgent().run({"creative_platform": helia, "copy_deck": ideon_resp})
    elif agent_key == "infosys_kinetik":
        from app.agents.infosys.logos import LogosAgent
        from app.agents.infosys.helia import HeliaAgent
        from app.agents.infosys.ideon import IdeonAgent
        from app.agents.infosys.kinetik import KinetikAgent
        from app.schemas.common import AgentResponse, AgentInfo, JobInfo, Artifact
        logos = LogosAgent().run(brief)
        helia = HeliaAgent().run(logos)
        ideon = IdeonAgent().run({"brief": logos, "creative_platform": helia})
        # Auto-select the best-scoring copy variant
        if ideon and ideon.artifact:
            best_content = _pick_best_ideon_copy(ideon.artifact.content)
            ideon = AgentResponse(
                agent=ideon.agent, job=ideon.job, status=ideon.status,
                artifact=Artifact(type=ideon.artifact.type, content=best_content),
            )
        r = KinetikAgent().run({"creative_platform": helia, "copy_deck": ideon})
    elif agent_key == "infosys":
        # Full pipeline
        from app.agents.infosys.orchestrator import CampaignOrchestrator
        return asyncio.run(CampaignOrchestrator().run_async(brief))
    else:
        raise ValueError(f"Unknown Infosys agent key: '{agent_key}'")

    return r.artifact.content if r and r.artifact else r.qa if r else {}


_RUNNERS = {
    "briefing":         run_briefing,
    "strategy":         run_strategy,
    "copy":             run_copy,
    "culture":          run_culture,
    "channel":          run_channel,
    "kv":               run_kv,
    "reel":             run_reel,
    "tvc":              run_tvc,
    "email_templates":  run_email_templates,
    "email_converter":  run_email_converter,
    # ── Infosys A2A agents — kwargs forwarded from run_agent_standalone ────────
    "infosys":          lambda brand, text, **kw: _infosys_runner("infosys", text, **kw),
    "infosys_logos":    lambda brand, text, **kw: _infosys_runner("infosys_logos", text, **kw),
    "infosys_helia":    lambda brand, text, **kw: _infosys_runner("infosys_helia", text, **kw),
    "infosys_ideon":    lambda brand, text, **kw: _infosys_runner("infosys_ideon", text, **kw),
    "infosys_aether":   lambda brand, text, **kw: _infosys_runner("infosys_aether", text, **kw),
    "infosys_morphis":  lambda brand, text, **kw: _infosys_runner("infosys_morphis", text, **kw),
    "infosys_kinetik":  lambda brand, text, **kw: _infosys_runner("infosys_kinetik", text, **kw),
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
    copy_subline: str = "",
    copy_body: str = "",
    copy_cta: str = "",
    campaign_type: str = "",
    campaign_id: str = "",
    concept_id: str = "",
    aspect_ratio: str = "16:9",
    color_theme: str = "blue",
    speaker_image_b64: str = "",
    speaker_name: str = "",
    speaker_title: str = "",
    content_type_badge: str = "",
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
        return runner(
            brand, text,
            product_name=product_name, market=market,
            audience=audience, copy_headline=copy_headline,
            copy_subline=copy_subline, copy_body=copy_body, copy_cta=copy_cta,
            campaign_type=campaign_type, campaign_id=campaign_id,
            concept_id=concept_id, aspect_ratio=aspect_ratio,
            color_theme=color_theme,
            speaker_image_b64=speaker_image_b64, speaker_name=speaker_name,
            speaker_title=speaker_title, content_type_badge=content_type_badge,
        )
    if agent_key == "reel":
        return runner(brand, text, campaign_type=campaign_type, copy_headline=copy_headline)
    # Infosys A2A agents — forward copy fields and color_theme so Morphis/Kinetik
    # can use a previously-generated Ideon copy without re-running the full pipeline.
    if agent_key.startswith("infosys"):
        return runner(
            brand, text,
            copy_headline=copy_headline, copy_subline=copy_subline,
            copy_cta=copy_cta, color_theme=color_theme,
            speaker_image_b64=speaker_image_b64, speaker_name=speaker_name,
            speaker_title=speaker_title, content_type_badge=content_type_badge,
        )
    return runner(brand, text)
