"""
agent_standalone.py — Run a single creative agent in isolation, given just
a brand and one free-text creative-direction prompt (no upstream pipeline
context required).

Unlike the full pipeline (run_creative_pipeline_direct / briefing_pipeline),
these are lightweight, single Gemini-call generations meant for quickly
exploring what one agent would produce for a brand + a one-line idea —
NOT the same depth/consistency as the full multi-agent chain, since each
call has no visibility into what the other agents would have produced.
"""

from __future__ import annotations

import json
import re

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
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _generate(persona: str, brand: str, prompt: str, output_instructions: str) -> dict:
    guidelines   = _brand_guidelines(brand)
    full_prompt = (
        f"{persona}\n\n"
        f"BRAND GUIDELINES for {brand}:\n{guidelines}\n\n"
        f"CREATIVE DIRECTION from the user: \"{prompt}\"\n\n"
        f"{output_instructions}"
    )
    resp = _genai_client().models.generate_content(
        model=settings.gemini_model_reasoning, contents=full_prompt,
    )
    raw = (resp.text or "").strip()
    return _parse_json_loose(raw) or {"raw": raw}


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
    return {"agent": "briefing", **data}


def run_strategy(brand: str, prompt: str) -> dict:
    data = _generate(
        "You are Helia, the creative strategist for an AI marketing campaign system. "
        "You turn a one-line creative direction into a campaign's Big Idea and strategic framework.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"hero_message": "the Big Idea, one punchy sentence", '
        '"strategic_framework": "2-3 sentences on the strategic approach", '
        '"messaging_pillars": ["pillar 1", "pillar 2", "pillar 3"]}',
    )
    return {"agent": "strategy", **data}


def run_copy(brand: str, prompt: str) -> dict:
    data = _generate(
        "You are Ideon, the copywriter for an AI marketing campaign system. "
        "You write campaign headlines and copy that sound like a human wrote them, not corporate marketing-speak.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"headline": "...", "subline": "...", "body": "1-2 sentences", "cta": "2-3 words"}',
    )
    return {"agent": "copy", **data}


def run_culture(brand: str, prompt: str) -> dict:
    data = _generate(
        "You are Aether, the cultural intelligence researcher for an AI marketing campaign system. "
        "You identify cultural trends, moments, and audience behaviours relevant to a campaign.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"summary": "3-4 sentences of cultural insight relevant to this market and moment", '
        '"recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"]}',
    )
    return {"agent": "culture", **data}


def run_channel(brand: str, prompt: str) -> dict:
    data = _generate(
        "You are Poly, the channel adaptation agent for an AI marketing campaign system. "
        "You adapt a campaign idea into platform-specific captions for different channels.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"instagram": "caption text", "tiktok": "caption text", '
        '"email_subject": "subject line", "ooh": "short outdoor billboard line"}',
    )
    return {"agent": "channel", **data}


_RUNNERS = {
    "briefing": run_briefing,
    "strategy": run_strategy,
    "copy":     run_copy,
    "culture":  run_culture,
    "channel":  run_channel,
}


def run_agent_standalone(agent_key: str, text: str) -> dict:
    """text is the whole free-text prompt, e.g. "UBS Bank for UK market, festive: christmas" —
    the brand is detected from it automatically rather than passed separately."""
    runner = _RUNNERS.get(agent_key)
    if not runner:
        raise ValueError(
            f"No standalone runner for agent '{agent_key}' yet "
            "(Morphis/kv and Kinetik/reel are image/video — a separate follow-up)."
        )
    brand = _extract_brand(text)
    if not brand:
        raise ValueError(
            "Couldn't tell which brand this is for — mention an uploaded brand's name in your prompt "
            '(e.g. "UBS Bank for UK market, festive: christmas").'
        )
    logger.info("agent_standalone_run", agent=agent_key, brand=brand)
    return runner(brand, text)
