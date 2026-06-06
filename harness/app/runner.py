"""
runner.py â€" ADK Runner + direct Groq fallback.

For Vertex AI: uses ADK Workflow runner normally.
For Groq/LiteLLM: runs load_brand_context via ADK, then calls Groq directly
because LiteLlm agents in ADK Workflows fail silently due to Pydantic
model handoff incompatibility.
"""

import json
import os
import re
import time
import uuid


def _clean_api_key(key: str) -> str:
    """Strip BOM, newlines, carriage returns, null bytes and non-ASCII from API keys."""
    key = key.encode("utf-8").decode("utf-8-sig")  # strip BOM
    key = re.sub(r"[^\x20-\x7E]", "", key)         # keep only printable ASCII
    return key.strip()
import asyncio
import structlog
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk import Agent, Workflow
from google.genai.types import Content, Part

logger = structlog.get_logger()


async def _vertex_generate(client, model: str, prompt: str, temperature: float = 0.5, retries: int = 4) -> str:
    """Call Vertex AI generate_content with exponential backoff on 429."""
    loop = asyncio.get_event_loop()
    for attempt in range(retries):
        try:
            r = await loop.run_in_executor(None, lambda: client.models.generate_content(
                model=model, contents=prompt, config={"temperature": temperature},
            ))
            return r.text.strip()
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = 20 * (2 ** attempt)  # 20s, 40s, 80s
                logger.warning("vertex_rate_limit_retry", attempt=attempt + 1, wait_s=wait, model=model)
                await asyncio.sleep(wait)
            else:
                raise
    return ""

session_service = InMemorySessionService()


def _is_groq_model(agent: Agent | Workflow) -> bool:
    """Check if any agent in the pipeline uses a Groq/LiteLlm model."""
    try:
        from google.adk.models.lite_llm import LiteLlm
        root = agent
        if hasattr(root, "model") and isinstance(root.model, LiteLlm):
            return True
        if hasattr(root, "_agent"):
            return isinstance(root._agent.model, LiteLlm)
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "") != ""


def _needs_groq_fallback(agent: Agent | Workflow) -> bool:
    """
    Returns True only for pipelines where the Groq direct-call fallback is appropriate.
    experiment_pipeline has its OWN agent-level handling â€" don't use briefing fallback.
    """
    if hasattr(agent, "name") and agent.name == "experiment_pipeline":
        return False
    return _is_groq_model(agent)


def _parse_agent_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:]) if len(lines) > 1 else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        try:
            return json.loads(cleaned.strip())
        except Exception:
            return {"raw_output": raw}


async def _run_briefing_with_groq(state: dict, brief: dict, cid: str) -> dict:
    """Call Groq directly to generate the machine brief using session state context."""
    import litellm
    from app.instructions import BRIEFING_AGENT_INSTRUCTIONS

    context = {
        "brand_guidelines":    state.get("brand_guidelines", ""),
        "brand_locks":         state.get("brand_locks_json", "{}"),
        "fan_truth_summary":   state.get("fan_truth_summary", ""),
        "campaign_benchmarks": state.get("campaign_benchmarks_summary", ""),
        "channel_benchmarks":  state.get("channel_benchmarks_summary", ""),
        "audience_insights":   state.get("audience_insights", ""),
        "moment_type_rules":   state.get("moment_type_rules_summary", ""),
    }

    # Serialize brief â€" convert enums/Pydantic to plain values BEFORE f-string
    def _safe(v):
        if hasattr(v, "value"):      return v.value
        if hasattr(v, "model_dump"): return v.model_dump()
        return v

    safe_brief = {k: _safe(v) for k, v in brief.items()}

    prompt = f"""{BRIEFING_AGENT_INSTRUCTIONS}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
BRAND CONTEXT
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
Brand Guidelines:
{context['brand_guidelines'][:3000]}

Brand Locks (JSON):
{context['brand_locks'][:1000]}

Fan Truth Guidance:
{context['fan_truth_summary'][:500]}

Campaign Benchmarks:
{context['campaign_benchmarks'][:500]}

Channel Benchmarks:
{context['channel_benchmarks'][:500]}

Customer Audience Intelligence (CDP â€" pgvector):
{context['audience_insights'][:800]}

Moment Type Rules:
{context['moment_type_rules'][:500]}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
CAMPAIGN BRIEF
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{json.dumps(brief, indent=2)}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
TASK
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
Validate the campaign brief above using ALL context provided. Your scoring must be grounded in the data:

1. Fan Truth: Score Specific/Shared/Special (0-100 each). Overall = average of the three.
   Use fan_truth_summary and audience_insights CDP benchmarks to calibrate.
   verdict = "PASS" if overall >= 70, else "FAIL".

2. KPIs: Compare each target to campaign and channel benchmarks.
   flag = "OK" / "AMBITIOUS" / "UNREALISTIC" based on benchmark data.

3. Audience: Cross-check against audience_insights CDP data.
   Flag channel mismatches or segment size issues as brand_warnings.

4. Status â€" apply these rules EXACTLY:
   "READY"        â†' fan_truth overall >= 75 AND zero UNREALISTIC KPI flags AND zero error brand_warnings
   "NEEDS_REVIEW" â†' fan_truth overall >= 60 AND has AMBITIOUS KPIs or minor brand_warnings
   "INCOMPLETE"   â†' fan_truth overall < 60 OR fan_truth verdict is FAIL

Apply brand locks. Return ONLY valid JSON â€" no markdown, no explanation:

{{
  "campaign_id": "{cid}",
  "campaign_name": "<name>",
  "status": "READY or NEEDS_REVIEW or INCOMPLETE",
  "brief_summary": "<2 sentence summary>",
  "fan_truth": {{
    "statement": "<statement>",
    "specific": <0-100>,
    "shared": <0-100>,
    "special": <0-100>,
    "overall": <0-100>,
    "verdict": "PASS or FAIL",
    "notes": "<brief notes>"
  }},
  "kpis": [
    {{"metric": "<name>", "target": "<value>", "flag": "OK or AMBITIOUS or UNREALISTIC", "note": "<why>"}}
  ],
  "brand_locks_applied": ["<lock1>", "<lock2>"],
  "brand_warnings": [],
  "channels": {json.dumps(safe_brief.get("channels", []))},
  "audience": "{safe_brief.get('audience', {}).get('segment', 'General') if isinstance(safe_brief.get('audience'), dict) else safe_brief.get('audience', 'General')}",
  "budget": "{safe_brief.get('budget', '')}",
  "market": "{safe_brief.get('market', 'UK')}",
  "season": "{safe_brief.get('season', '')}",
  "moment_type": "{safe_brief.get('moment_type', 'Day-to-Day')}",
  "validation_notes": "<any concerns or strengths>"
}}
"""

    import google.genai as _genai_brief
    from app.config import get_settings as _gs_brief
    _sb = _gs_brief()
    _gc_brief = _genai_brief.Client(vertexai=True, project=_sb.gcp_project, location=_sb.gcp_region)
    raw = await _vertex_generate(_gc_brief, os.getenv("GEMINI_MODEL_REASONING", "gemini-2.5-flash"), prompt, temperature=0.3)
    return _parse_agent_response(raw)


async def run_agent(
    agent:       Agent | Workflow,
    input_data:  dict,
    campaign_id: str | None = None,
) -> tuple[dict, int]:
    start = time.time()
    cid   = campaign_id or f"run-{str(uuid.uuid4())[:8]}"

    log = logger.bind(agent_name=agent.name, campaign_id=cid)
    log.info("adk_run_start")

    session = await session_service.create_session(
        app_name   = agent.name,
        user_id    = "campaignos",
        session_id = cid,
    )
    session.state["brief_json"] = json.dumps({"campaign_id": cid, **input_data})

    runner = Runner(
        agent           = agent,
        app_name        = agent.name,
        session_service = session_service,
    )

    input_content = Content(
        role  = "user",
        parts = [Part(text=json.dumps({"campaign_id": cid, **input_data}))]
    )

    final_response = None
    async for event in runner.run_async(
        user_id     = "campaignos",
        session_id  = cid,
        new_message = input_content,
    ):
        log.debug("adk_event", is_final=event.is_final_response(),
                  has_content=event.content is not None)
        if event.is_final_response():
            if event.content and event.content.parts:
                part = event.content.parts[0]
                final_response = part.text or None
            break

    # Check session state (output_key agents write here)
    refreshed = await session_service.get_session(
        app_name=agent.name, user_id="campaignos", session_id=cid,
    )
    state = dict(refreshed.state) if refreshed else {}
    log.info("session_state_keys", keys=list(state.keys()))

    # If Groq/LiteLlm and no LLM output yet, call Groq directly
    if not final_response and _needs_groq_fallback(agent):
        log.info("groq_direct_fallback", reason="ADK LiteLlm workflow returned no output")
        result = await _run_briefing_with_groq(state, input_data, cid)
        result.setdefault("campaign_id", cid)
        if state.get("audience_insights"):
            result["audience_insights"] = state["audience_insights"]
        return result, int((time.time() - start) * 1000)

    if not final_response:
        useful = {k: v for k, v in state.items()
                  if k not in ("brief_json",) and not k.startswith("_")}
        if useful:
            useful.setdefault("campaign_id", cid)
            return useful, int((time.time() - start) * 1000)
        raise RuntimeError(f"Agent '{agent.name}' produced no output.")

    result = _parse_agent_response(final_response)
    result.setdefault("campaign_id", cid)
    # Include audience intelligence in result for UI display
    if state.get("audience_insights"):
        result["audience_insights"] = state["audience_insights"]
    ms = int((time.time() - start) * 1000)
    log.info("adk_run_complete", processing_ms=ms)
    return result, ms


async def run_strategy_with_groq(machine_brief: dict, brand_guidelines: str, brand_locks: str) -> dict:
    """Generate creative strategy from validated machine brief."""
    import litellm
    from app.instructions import STRATEGY_AGENT_INSTRUCTIONS

    prompt = f"""{STRATEGY_AGENT_INSTRUCTIONS}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
MACHINE BRIEF (validated):
{json.dumps(machine_brief, indent=2)[:3000]}

BRAND GUIDELINES:
{brand_guidelines[:4000]}

BRAND LOCKS:
{brand_locks[:500]}
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

Produce a creative strategy as valid JSON only â€" no markdown, no explanation:
{{
  "campaign_id": "{machine_brief.get('campaign_id', '')}",
  "big_idea": "<6 words max â€" the campaign world>",
  "tagline": "<campaign tagline>",
  "strategic_framework": "<2-3 sentences â€" the overarching approach>",
  "hero_message": "<â‰¤8 words, Fan-to-Fan voice>",
  "tone_of_voice": "<brand voice for this campaign>",
  "channel_priorities": [{{"channel": "<name>", "priority": <1-10>, "rationale": "<why>"}}],
  "messaging_pillars": ["<pillar 1>", "<pillar 2>", "<pillar 3>"],
  "culture_context": "<1 sentence â€" the cultural insight driving the idea>",
  "handoff_message": "<2-3 sentences briefing the creative team>"
}}"""

    import google.genai as _g
    from app.config import get_settings as _gs
    _ss = _gs()
    _gc = _g.Client(vertexai=True, project=_ss.gcp_project, location=_ss.gcp_region)
    raw = await _vertex_generate(_gc, os.getenv('CREATIVE_MODEL', 'gemini-2.5-flash'), prompt, temperature=0.5)
    return _parse_agent_response(raw)


async def run_copy_with_groq(machine_brief: dict, strategy: dict, brand_locks: str) -> dict:
    """Generate campaign copy from brief and strategy."""
    import litellm
    from app.instructions import COPY_AGENT_INSTRUCTIONS

    prompt = f"""{COPY_AGENT_INSTRUCTIONS}

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
CREATIVE STRATEGY:
{json.dumps(strategy, indent=2)[:2000]}

BRAND LOCKS:
{brand_locks[:500]}

CAMPAIGN BRIEF:
{json.dumps(machine_brief, indent=2)[:1500]}
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

Produce campaign copy as valid JSON only â€" no markdown, no explanation:
{{
  "campaign_id": "{machine_brief.get('campaign_id', '')}",
  "short": {{
    "headline": "<â‰¤6 words, billboard-ready>",
    "subline": null
  }},
  "medium": {{
    "headline": "<â‰¤10 words>",
    "subline": "<â‰¤20 words>"
  }},
  "long": {{
    "headline": "<headline>",
    "subline": "<optional bridge>",
    "body": "<â‰¤60 words, present tense, sensory, no bullets>"
  }},
  "cta": "<â‰¤3 words, verb-led>",
  "instagram_caption": "<platform caption with relevant hashtags>",
  "tiktok_hook": "<first 3 seconds â€" what makes someone stop scrolling>"
}}"""

    import google.genai as _g2
    from app.config import get_settings as _gs2
    _ss2 = _gs2()
    _gc2 = _g2.Client(vertexai=True, project=_ss2.gcp_project, location=_ss2.gcp_region)
    raw2 = await _vertex_generate(_gc2, os.getenv('CREATIVE_MODEL', 'gemini-2.5-flash'), prompt, temperature=0.7)
    return _parse_agent_response(raw2)


def _extract_headline(big_idea: str) -> str:
    """Extract the short headline from the Big Idea text."""
    for line in big_idea.split("\n"):
        line = line.strip().strip("*").strip("#").strip()
        if line and len(line) > 3 and len(line) < 60:
            return line
    return big_idea[:50].strip()


def _create_channel_adaptation(img_data: bytes, ratio_w: int, ratio_h: int,
                                label: str, brand: str) -> str:
    """Smart-crop the KV image for a specific channel aspect ratio. Returns base64 JPEG."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io as _io, base64 as _b64

        img = Image.open(_io.BytesIO(img_data)).convert("RGB")
        W, H = img.size
        target_ratio = ratio_w / ratio_h
        current_ratio = W / H

        if current_ratio > target_ratio:
            # Image wider than target — crop sides
            new_w = int(H * target_ratio)
            left = (W - new_w) // 2
            img = img.crop((left, 0, left + new_w, H))
        else:
            # Image taller than target — crop bottom (keep top, where subject usually is)
            new_h = int(W / target_ratio)
            img = img.crop((0, 0, W, new_h))

        # Resize to standard output size
        if ratio_w >= ratio_h:
            out_w, out_h = 960, int(960 * ratio_h / ratio_w)
        else:
            out_w, out_h = int(960 * ratio_w / ratio_h), 960
        img = img.resize((out_w, out_h), Image.LANCZOS)

        # Add channel label chip in bottom-left corner
        try:
            draw = ImageDraw.Draw(img)
            chip_text = f"  {label}  "
            font = ImageFont.load_default(size=14)
            bb = draw.textbbox((0, 0), chip_text, font=font)
            tw = bb[2] - bb[0] + 4
            draw.rectangle([(8, out_h - 28), (8 + tw, out_h - 8)],
                           fill=(0, 0, 0, 160))
            draw.text((10, out_h - 26), chip_text, fill="white", font=font)
        except Exception:
            pass

        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        return _b64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        import structlog as _sl
        _sl.get_logger().debug("channel_adaptation_failed", label=label, error=str(e))
        return ""


# Channel format specs: (ratio_w, ratio_h, label, channel_key)
_CHANNEL_FORMATS = [
    (1,  1,  "Instagram Feed",    "instagram_feed"),
    (9,  16, "Instagram Stories", "instagram_stories"),
    (9,  16, "TikTok",            "tiktok"),
    (16, 9,  "Google Ads",        "google_ads"),
    (3,  1,  "Email Banner",      "email"),
    (4,  1,  "OOH / Billboard",   "ooh"),
]


def _apply_brand_overlay(img_data: bytes, brand: str, headline: str, product_uris: list) -> bytes:
    """
    Overlay brand headline + logo area on the generated image using Pillow.
    Uses brand font (.ttf) and brand colors from local bucket.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        import io
        from pathlib import Path

        # Load generated image
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        W, H = img.size

        # â"€â"€ Load brand font â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
        # Preferred brand fonts per guidelines:
        #   Sunglow → Alatsi-Regular.ttf
        #   Rnorr   → Antonio (display) or Rubik
        #   Boozt   → Rubik (bold italic for headlines)
        BRAND_FONT_PREFS = {
            "Sunglow": ["Alatsi"],
            "Rnorr":   ["Antonio", "Rubik"],
            "Boozt":   ["Rubik"],
        }
        prefs = BRAND_FONT_PREFS.get(brand, [])

        font_path = None
        local_font_dir = Path(__file__).parent.parent / "bucket" / "brands" / brand / "Font"
        # Try preferred fonts first
        for pref in prefs:
            for f in local_font_dir.glob("*.ttf"):
                if pref.lower() in f.name.lower():
                    font_path = str(f)
                    break
            if font_path:
                break
        # Fall back to any font in the folder
        if not font_path:
            for ext in ["*.ttf", "*.otf"]:
                fonts = list(local_font_dir.glob(ext))
                if fonts:
                    bold = [f for f in fonts if "bold" in f.name.lower() or "italic" in f.name.lower()]
                    font_path = str(bold[0] if bold else fonts[0])
                    break

        # â"€â"€ Brand colors from brand locks â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
        # Colors sourced from official brand guidelines
        BRAND_COLORS = {
            "Sunglow": {"text": "#FFFFFF", "bar": "#B00064", "accent": "#FFC72C"},  # Magenta + Sunshine Yellow
            "Rnorr":   {"text": "#FFFFFF", "bar": "#008641", "accent": "#FFDE00"},  # Rnorr Green + Yellow
            "Boozt":   {"text": "#FFFFFF", "bar": "#0E105E", "accent": "#0086FE"},  # Midnight + Boozt Blue
        }
        colors = BRAND_COLORS.get(brand, {"text": "#FFFFFF", "bar": "#1a1a2e", "accent": "#0055A4"})

        def hex_to_rgba(h: str, a: int = 255):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (a,)

        # â"€â"€ Create overlay canvas â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        # ── Top bar: semi-transparent brand colour panel at the top ──────────
        bar_h     = int(H * 0.22)
        bar_color = hex_to_rgba(colors["bar"], 200)
        draw.rectangle([(0, 0), (W, bar_h)], fill=bar_color)
        # Fade out at bottom of bar
        for i in range(40):
            alpha = int(200 * (1 - i / 40))
            draw.rectangle([(0, bar_h - 40 + i), (W, bar_h - 39 + i)],
                            fill=(*hex_to_rgba(colors["bar"])[:3], alpha))

        # ── Fonts ─────────────────────────────────────────────────────────────
        headline_size = max(30, W // 19)
        brand_size    = max(16, W // 36)
        try:
            font_headline = ImageFont.truetype(font_path, headline_size) if font_path else ImageFont.load_default(size=headline_size)
            font_brand    = ImageFont.truetype(font_path, brand_size)    if font_path else ImageFont.load_default(size=brand_size)
        except Exception:
            font_headline = ImageFont.load_default()
            font_brand    = ImageFont.load_default()

        # ── Headline: word-wrap, centred in top bar ───────────────────────────
        text_color   = hex_to_rgba(colors["text"])
        accent_color = hex_to_rgba(colors["accent"])
        words = headline.split()
        lines, cur = [], []
        for w in words:
            test = " ".join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=font_headline)
            if bb[2] - bb[0] > W * 0.82 and cur:
                lines.append(" ".join(cur)); cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(" ".join(cur))

        line_h  = headline_size + 8
        total_h = len(lines) * line_h + brand_size + 10
        y = max(8, (bar_h - total_h) // 2)

        for line in lines:
            bb = draw.textbbox((0, 0), line, font=font_headline)
            draw.text(((W - (bb[2]-bb[0])) // 2, y), line, fill=text_color, font=font_headline)
            y += line_h

        # ── Brand name: accent colour, same style as logo, below headline ─────
        y += 2
        # Thin accent line separator
        draw.rectangle([(W // 2 - 36, y), (W // 2 + 36, y + 2)], fill=accent_color)
        y += 6
        brand_text = brand.upper()
        bb = draw.textbbox((0, 0), brand_text, font=font_brand)
        draw.text(((W - (bb[2]-bb[0])) // 2, y), brand_text, fill=accent_color, font=font_brand)

        # ── Brand logo (top-left corner) ──────────────────────────────────────
        # ── Brand logo (top-left corner) ──────────────────────────────────────
        try:
            from app.brand_assets import get_asset_loader as _gal_ov
            _logos = _gal_ov().list_logos(brand)
            if _logos:
                from app.creative_pipeline import _load_bytes as _lb_ov
                _logo_data = _lb_ov(_logos[0])
                if _logo_data:
                    _logo = Image.open(io.BytesIO(_logo_data)).convert("RGBA")
                    _lw, _lh = _logo.size
                    _scale = min(120 / _lw, 50 / _lh, 1.0)
                    _logo = _logo.resize((int(_lw * _scale), int(_lh * _scale)), Image.LANCZOS)
                    _pad = 10
                    _lbg = Image.new("RGBA", (_logo.width + _pad*2, _logo.height + _pad*2),
                                     (*hex_to_rgba(colors["bar"])[:3], 200))
                    if _logo.mode == "RGBA":
                        _lbg.paste(_logo, (_pad, _pad), _logo)
                    else:
                        _lbg.paste(_logo, (_pad, _pad))
                    overlay.paste(_lbg, (16, 16), _lbg)
        except Exception as _le:
            logger.debug("logo_overlay_skipped", error=str(_le))

        # ── Composite and return ──────────────────────────────────────────────
        result = Image.alpha_composite(img, overlay).convert("RGB")
        buf    = io.BytesIO()
        result.save(buf, format="JPEG", quality=92)
        return buf.getvalue()

    except Exception as e:
        logger.warning("brand_overlay_failed", error=str(e))
        return img_data  # return original if overlay fails


async def run_creative_pipeline_direct(
    brand: str,
    audience: str,
    product_uris: list,
    asset_uris: list,
    logo_uri: str,
    brand_guidelines: str,
    big_idea_seed: str = "",
    campaign_id: str = "",
    progress_cb=None,
) -> dict:
    """
    Directly orchestrate the creative pipeline stages using Groq for text
    and Google AI for image generation â€" bypasses ADK Workflow DAG.

    Stages:
      1. Culture researcher  â†' cultural intelligence brief
      2. Brand summariser    â†' 5 brand locks
      3. Creative director   â†' Big Idea + creative strategy
      4. Prompt agent        â†' Gemini image generation prompt
      5. Image generator     â†' key visual (base64 PNG via Google AI)
    """
    log = logger.bind(campaign_id=campaign_id)

    async def _emit(agent: str, status: str, message: str):
        if progress_cb:
            await progress_cb(agent, status, message)

    # Use Gemini via Vertex AI (no daily token limit, uses GCP billing credits)
    import google.genai as _genai
    from app.config import get_settings as _get_settings
    _s = _get_settings()
    _gemini = _genai.Client(vertexai=True, project=_s.gcp_project, location=_s.gcp_region)
    _text_model = os.getenv("CREATIVE_MODEL", "gemini-2.5-flash")

    async def _llm(prompt: str, temp: float = 0.5, retries: int = 3,
                   with_brand_imgs: bool = False) -> str:
        """Call creative model via Vertex AI. Passes brand images when model supports vision."""
        import asyncio
        loop = asyncio.get_event_loop()
        is_vision = any(x in _text_model.lower() for x in ["image", "vision", "pro"])
        contents = [prompt] + (_brand_img_parts[:6] if with_brand_imgs and is_vision and _brand_img_parts else [])
        for attempt in range(retries):
            try:
                r = await loop.run_in_executor(None, lambda: _gemini.models.generate_content(
                    model    = _text_model,
                    contents = contents,
                    config   = {"temperature": temp},
                ))
                # Extract text — vision models may return mixed parts
                txt = ""
                try:
                    for _p in (r.candidates[0].content.parts if r.candidates else []):
                        if hasattr(_p, "text") and _p.text:
                            txt += _p.text
                except Exception:
                    pass
                return (txt or r.text or "").strip()
            except Exception as e:
                if "429" in str(e) and attempt < retries - 1:
                    wait = 30 * (attempt + 1)
                    log.warning("gemini_rate_limit_retry", attempt=attempt+1, wait=wait)
                    await asyncio.sleep(wait)
                else:
                    raise
        return ""

    import asyncio as _asyncio

    # Stage 1: Culture research
    log.info("p2_culture_researcher_start")
    await _emit("culture", "running", f"Researching cultural trends for {brand} audience…")
    culture = await _llm(f"""You are a cultural intelligence researcher.

Brand: {brand}
Target audience: {audience}

Write a concise cultural intelligence brief (max 300 words):
- What is this audience feeling and experiencing right now?
- What cultural tensions or trends are relevant to them?
- What insight could {brand} genuinely tap into?
- One sharp "tension" sentence for the creative brief.

Be specific, avoid generic boilerplate.""")
    log.info("p2_culture_researcher_done")
    await _emit("culture", "done", "Cultural intelligence ready ✓")
    import json as _json
    await _emit("culture", "milestone", _json.dumps({"brief": culture[:600]}))
    await _asyncio.sleep(10)

    # Stage 2: Brand summariser
    log.info("p2_brand_summariser_start")
    await _emit("kv", "running", f"Extracting {brand} brand locks & creative rules…")
    _BRAND_PALETTE_LOCK = {
        "Sunglow": "primary #B00064 Magenta, accent #FFC72C Sunshine Yellow, base #F9F9F9 Off-White, font Alatsi",
        "Rnorr":   "primary #008641 Rnorr Green, accent #FFDE00 Yellow, base #FFFFFF White, fonts Antonio + Rubik",
        "Boozt":   "primary #0E105E Midnight, accent #0086FE Boozt Blue, highlight #00BFFE Sky, base #FFFFFF White, font Rubik",
    }
    _palette_lock = _BRAND_PALETTE_LOCK.get(brand, "use brand primary colours")

    brand_summary = await _llm(f"""You are a brand strategist. You can see the brand logo, colour swatches, and product imagery in the images provided. Use them to extract the exact visual identity.

Brand: {brand}
Official colour palette: {_palette_lock}

Brand guidelines:
{brand_guidelines[:3500]}

Distil into exactly 5 numbered brand lock points any creative execution MUST honour.
Include the exact HEX colours ({_palette_lock}) in lock 1.
Cover: colours (with HEX), typography/font, logo rules, tone, forbidden treatments.""")
    log.info("p2_brand_summariser_done")
    import json as _json2
    await _emit("kv", "step_data", _json2.dumps({"brand_locks": brand_summary[:500]}))
    await _emit("kv", "running", "Brand locks extracted — building Big Idea…")
    await _asyncio.sleep(10)

    # Stage 3: Creative director → Big Idea
    log.info("p2_creative_director_start")
    big_idea = await _llm(f"""You are a Creative Director.

Brand: {brand}
Audience: {audience}
Cultural intelligence: {culture}
Brand locks: {brand_summary}
{f'Seed idea: {big_idea_seed}' if big_idea_seed else ''}

Create a Big Idea for this campaign. Output:
- Big Idea title (â‰¤6 words, memorable)
- Visual world (2-3 sentences â€" what the campaign looks and feels like)
- Hero message (â‰¤8 words, Fan-to-Fan voice)
- Creative tension (1 sentence â€" the cultural hook)""", temp=0.7)
    log.info("p2_creative_director_done")
    await _emit("kv", "step_data", _json2.dumps({"big_idea": big_idea[:400]}))
    await _emit("kv", "running", "Big Idea ready — crafting image prompt…")
    await _asyncio.sleep(10)

    # Stage 4: Prompt agent → image generation prompt
    log.info("p2_prompt_agent_start")
    await _emit("kv", "running", "Crafting Imagen 4 prompt from Big Idea…")
    # Inject exact brand colors so Imagen 4 generates on-brand visuals
    _BRAND_PALETTE = {
        "Sunglow": "primary Magenta #B00064, accent Sunshine Yellow #FFC72C, base Off-White #F9F9F9",
        "Rnorr":   "primary Rnorr Green #008641, accent Yellow #FFDE00, base White #FFFFFF",
        "Boozt":   "primary Midnight #0E105E, accent Boozt Blue #0086FE, Sky #00BFFE, base White #FFFFFF",
    }
    _brand_palette_str = _BRAND_PALETTE.get(brand, "brand primary colour, accent colour, white base")

    image_prompt = await _llm(f"""You are a senior creative director writing Gemini 3 Pro Image prompts for premium advertising campaigns.

Brand: {brand}
Brand colour palette: {_brand_palette_str}
Campaign Big Idea: {big_idea}
Brand locks: {brand_summary}

Write a Gemini 3 Pro Image generation prompt that produces a PREMIUM ADVERTISING KEY VISUAL.

The prompt must describe:
1. PHOTOGRAPHY STYLE: Professional advertising photography, DSLR shot, shallow depth of field (f/1.8-f/2.8), editorial quality, award-winning campaign imagery
2. SCENE: A specific, cinematic lifestyle moment that connects emotionally with the audience. Show a real person in a real moment — not a product still life
3. LIGHTING: Specific lighting setup (e.g. "golden hour natural light", "soft studio diffused light", "warm candlelit") that flatters the scene
4. COMPOSITION: Rule of thirds, clear hero subject, intentional negative space for the brand mark
5. COLOUR GRADING: The brand palette ({_brand_palette_str}) must be woven into the scene through props, wardrobe, environment — not as flat overlays
6. MOOD: The emotional feeling the viewer should experience

STRICT RULES:
- NO text, letters, words, brand names, logos, watermarks, or typography anywhere in the image
- NO product packaging shown prominently — product appears naturally in context
- Photorealistic, not illustrated or animated
- Be 180-240 words

Output only the prompt text, nothing else.""", temp=0.7)
    log.info("p2_prompt_agent_done")
    await _emit("kv", "step_data", _json2.dumps({"image_prompt": image_prompt[:350]}))
    await _emit("kv", "running", "Generating key visual with Gemini 3 Pro Image…")

    # Stage 5: Image generation via Google AI
    image_b64 = None
    image_error = None
    channel_adaptations: dict = {}
    try:
        import google.genai as genai
        import base64

        # Use Vertex AI for image generation
        from app.config import get_settings as _get_settings
        from google.genai import types as _gtypes
        _settings = _get_settings()
        client = genai.Client(
            vertexai = True,
            project  = _settings.gcp_project,
            location = _settings.gcp_region,
        )

        # â"€â"€ Step A: Analyze existing brand campaign banners (reference ads) â"€â"€
        # Load asset images from GCS and ask Gemini Vision to extract visual style
        from app.creative_pipeline import _load_bytes, _mime_for
        SUPPORTED_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        ref_parts = []
        for uri in (asset_uris or [])[:4]:
            mime = _mime_for(uri)
            if mime not in SUPPORTED_MIME:
                log.debug("p2_asset_skipped", uri=uri, mime=mime)
                continue
            data = _load_bytes(uri)
            if data and len(data) > 1024:  # skip empty/corrupt files
                ref_parts.append(_gtypes.Part.from_bytes(data=data, mime_type=mime))

        style_analysis = ""
        if ref_parts:
            log.info("p2_analyze_brand_assets", n_refs=len(ref_parts))
            await _emit("kv", "running", f"Analyzing {len(ref_parts)} brand reference images…")
            try:
                vision_contents = [
                    "These are existing campaign images for this brand. Analyze them and describe in 3-4 sentences: "
                    "the photography style, color palette, mood, lighting, composition, and the type of subjects/scenes used. "
                    "This will guide generating a NEW campaign image consistent with this brand's visual identity.",
                    *ref_parts,
                ]
                vision_resp = client.models.generate_content(
                    model    = "gemini-2.5-flash",
                    contents = vision_contents,
                )
                style_analysis = vision_resp.text.strip()
                log.info("p2_brand_style_extracted", style=style_analysis[:120])
            except Exception as vision_err:
                log.warning("p2_brand_style_failed", error=str(vision_err),
                            note="skipping style analysis, Imagen 4 will use prompt only")

        # â"€â"€ Step B: Enrich image prompt with brand visual style â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
        enriched_prompt = image_prompt
        if style_analysis:
            enriched_prompt = (
                f"{image_prompt}\n\n"
                f"BRAND VISUAL STYLE (derived from existing campaign imagery - match this aesthetic):\n"
                f"{style_analysis}"
            )

        # -- Step C: Generate key visual with Imagen 4 --------------------------------
        image_model = _get_settings().gemini_model_image
        headline_text = big_idea_seed if big_idea_seed else _extract_headline(big_idea)
        log.info("p2_generate_image_start", model=image_model, has_style_ref=bool(style_analysis))
        await _emit("kv", "running", f"Generating key visual with {image_model}...")

        response = client.models.generate_images(
            model=image_model,
            prompt=enriched_prompt,
            config={"number_of_images": 1, "aspect_ratio": "1:1"},
        )
        if not response.generated_images:
            raise ValueError("Imagen 4 returned no images")
        img_data = response.generated_images[0].image.image_bytes

        img_data = _apply_brand_overlay(
            img_data     = img_data,
            brand        = brand,
            headline     = headline_text,
            product_uris = product_uris,
        )

        image_b64 = base64.b64encode(img_data).decode("utf-8")
        log.info("p2_generate_image_done", size_kb=len(img_data) // 1024)

        # Generate channel adaptations (smart crops for different aspect ratios)
        channel_adaptations: dict = {}
        for rw, rh, label, key in _CHANNEL_FORMATS:
            adapted = _create_channel_adaptation(img_data, rw, rh, label, brand)
            if adapted:
                channel_adaptations[key] = {"label": label, "image_b64": adapted,
                                            "ratio": f"{rw}:{rh}"}
        log.info("p2_channel_adaptations_done", count=len(channel_adaptations))

        # Push main image + adaptations as step_data
        await _emit("kv", "step_data", _json2.dumps({"image_b64": image_b64}))
        await _asyncio.sleep(5)  # Let UI display image before channel agent
        await _emit("kv", "done", "Key visual generated ✓")
    except Exception as e:
        image_error = str(e)
        log.warning("p2_generate_image_failed", error=image_error)
        await _emit("kv", "error", f"Image generation failed: {image_error[:80]}")

    return {
        "campaign_id":          campaign_id,
        "culture_brief":        culture,
        "brand_summary":        brand_summary,
        "big_idea":             big_idea,
        "image_prompt":         image_prompt,
        "image_b64":            image_b64,
        "image_error":          image_error,
        "channel_adaptations":  channel_adaptations,
    }


