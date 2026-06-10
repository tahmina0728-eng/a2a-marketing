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


async def _vertex_generate(client, model: str, prompt: str, retries: int = 3) -> str:
    """Call Vertex AI generate_content with backoff on 429, auto-fallback to cheaper model."""
    import os as _os
    _fallback = _os.getenv("FALLBACK_CREATIVE_MODEL", "gemini-2.0-flash")
    loop = asyncio.get_event_loop()
    for _model in ([model, _fallback] if _fallback and _fallback != model else [model]):
        for attempt in range(retries):
            try:
                r = await loop.run_in_executor(None, lambda m=_model: client.models.generate_content(
                    model=m, contents=prompt,
                ))
                return r.text.strip()
            except Exception as e:
                if "429" in str(e) and attempt < retries - 1:
                    wait = 8 * (2 ** attempt)   # 8s, 16s — shorter initial wait
                    logger.warning("vertex_rate_limit_retry", attempt=attempt+1, wait_s=wait, model=_model)
                    await asyncio.sleep(wait)
                elif "429" in str(e):
                    logger.warning("vertex_quota_exhausted_switching", from_model=_model, to_model=_fallback)
                    break   # try fallback model
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
    raw = await _vertex_generate(_gc_brief, os.getenv("GEMINI_MODEL_REASONING", "gemini-3.5-flash"), prompt)
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
    raw = await _vertex_generate(_gc, os.getenv('CREATIVE_MODEL', 'gemini-3.5-flash'), prompt)
    return _parse_agent_response(raw)


_CHANNEL_COPY_SPEC: dict = {
    "instagram":  {"key": "instagram_caption", "desc": "Instagram caption max 150 chars with 3-5 hashtags"},
    "tiktok":     {"key": "tiktok_hook",        "desc": "TikTok hook - first 3 seconds that stops the scroll (max 15 words)"},
    "youtube":    {"key": "youtube_script",     "desc": "YouTube pre-roll opening before skip (max 20 words)"},
    "google ads": {"key": "google_headline",    "desc": "Google Search headline max 30 chars, keyword-rich"},
    "google_ads": {"key": "google_headline",    "desc": "Google Search headline max 30 chars, keyword-rich"},
    "meta ads":   {"key": "meta_caption",       "desc": "Meta/Facebook ad primary text max 125 chars"},
    "meta_ads":   {"key": "meta_caption",       "desc": "Meta/Facebook ad primary text max 125 chars"},
    "ooh":        {"key": "ooh_headline",       "desc": "OOH billboard copy max 6 words, readable at speed"},
    "website":    {"key": "web_headline",       "desc": "Website hero headline max 8 words"},
    "email":      {"key": "email_subject",      "desc": "Email subject line max 50 chars, curiosity-driving"},
}


async def run_copy_agent(machine_brief: dict, strategy: dict, brand_locks: str,
                         channels: list = None) -> dict:
    """Generate copy scoped to selected channels using Vertex AI."""
    from app.instructions import COPY_AGENT_INSTRUCTIONS
    import google.genai as _g2
    from app.config import get_settings as _gs2
    _ss2 = _gs2()
    _gc2 = _g2.Client(vertexai=True, project=_ss2.gcp_project, location=_ss2.gcp_region)

    selected = [c.lower().strip() for c in (channels or [])]
    seen_keys: set = set()
    channel_fields: list = []
    for ch in selected:
        spec = _CHANNEL_COPY_SPEC.get(ch)
        if spec and spec["key"] not in seen_keys:
            channel_fields.append((spec["key"], spec["desc"]))
            seen_keys.add(spec["key"])

    channel_json_lines = "\n".join(
        f'  "{key}": "<{desc}>",' for key, desc in channel_fields
    )

    prompt = f"""{COPY_AGENT_INSTRUCTIONS}

CREATIVE STRATEGY:
{json.dumps(strategy, indent=2)[:2000]}

BRAND LOCKS:
{brand_locks[:500]}

CAMPAIGN BRIEF:
{json.dumps(machine_brief, indent=2)[:1500]}

Produce campaign copy as valid JSON only - no markdown, no explanation.
Only include the channel fields listed below.

{{
  "campaign_id": "{machine_brief.get('campaign_id', '')}",
  "short": {{"headline": "<max 6 words, billboard-ready>", "subline": null}},
  "medium": {{"headline": "<max 10 words>", "subline": "<max 20 words>"}},
  "long": {{"headline": "<headline>", "subline": "<optional>", "body": "<max 60 words, present tense, sensory>"}},
  "cta": "<max 3 words, verb-led>",
{channel_json_lines}
}}"""

    raw = await _vertex_generate(_gc2, os.getenv("CREATIVE_MODEL", "gemini-3.5-flash"), prompt)
    result = _parse_agent_response(raw)
    result["_channel_keys"] = [k for k, _ in channel_fields]
    return result

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
    raw2 = await _vertex_generate(_gc2, os.getenv('CREATIVE_MODEL', 'gemini-3.5-flash'), prompt)
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

        Image.MAX_IMAGE_PIXELS = None   # allow large Imagen 4 outputs
        img = Image.open(_io.BytesIO(img_data)).convert("RGB")
        # Cap at 2048px before cropping/adapting
        if max(img.size) > 2048:
            scale = 2048 / max(img.size)
            img   = img.resize((int(img.width * scale), int(img.height * scale)),
                               Image.LANCZOS)
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
    (16, 9,  "YouTube",           "youtube"),
    (16, 9,  "Google Ads",        "google_ads"),
    (1,  1,  "Meta Ads",          "meta_ads"),
    (16, 9,  "Website Banner",    "website"),
    (3,  1,  "Email Banner",      "email"),
    (4,  1,  "OOH / Billboard",   "ooh"),
]

_CHANNEL_KEY_MAP: dict = {
    "instagram":  ["instagram_feed", "instagram_stories"],
    "tiktok":     ["tiktok"],
    "youtube":    ["youtube"],
    "google ads": ["google_ads"],
    "google_ads": ["google_ads"],
    "meta ads":   ["meta_ads"],
    "meta_ads":   ["meta_ads"],
    "ooh":        ["ooh"],
    "website":    ["website"],
    "email":      ["email"],
}


def _apply_brand_overlay(
    img_data:     bytes,
    brand:        str,
    headline:     str,
    product_uris: list,
    product_name: str = "",
) -> bytes:
    """
    Full-bleed advertising overlay — no split panel.

    Design: billboard text floats over the full image with a natural dark
    gradient vignette behind it (left edge darkens gently to transparent),
    so text reads on any photo. Logo top-right. Inspired by Sunsilk, Knorr,
    Pantene full-bleed FMCG ads.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        import io
        from pathlib import Path as _P

        Image.MAX_IMAGE_PIXELS = None
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        if max(img.size) > 1536:
            scale = 1536 / max(img.size)
            img   = img.resize((int(img.width * scale), int(img.height * scale)),
                               Image.LANCZOS)
        W, H = img.size
        margin = max(24, int(W * 0.035))

        # ── Brand font ────────────────────────────────────────────────────────
        BRAND_FONT_PREFS = {
            "Sunglow": ["Alatsi"],
            "Rnorr":   ["Antonio", "Rubik"],
            "Boozt":   ["Rubik"],
        }
        font_dir  = _P(__file__).parent.parent / "bucket" / "brands" / brand / "Font"
        font_path = None
        for pref in BRAND_FONT_PREFS.get(brand, []):
            for f in sorted(font_dir.glob("*.ttf")):
                if pref.lower() in f.name.lower() and "italic" not in f.name.lower():
                    font_path = str(f); break
            if font_path:
                break
        if not font_path:
            hits = [f for f in sorted(font_dir.glob("*.ttf")) if "italic" not in f.name.lower()]
            font_path = str(hits[0]) if hits else None

        def _font(size: int):
            if font_path:
                try: return ImageFont.truetype(font_path, size)
                except Exception: pass
            try: return ImageFont.load_default(size=size)
            except Exception: return ImageFont.load_default()

        # ── Brand accent colour ───────────────────────────────────────────────
        BRAND_ACCENT = {
            "Sunglow": (255, 199,  44),
            "Rnorr":   (255, 222,   0),
            "Boozt":   (  0, 134, 254),
        }
        accent_rgb = BRAND_ACCENT.get(brand, (255, 255, 255))

        # ── 1. Split headline into words — billboard stacked layout ───────────
        words = [w.strip() for w in (headline or "").split() if w.strip()]
        if not words:
            words = [brand.upper()]

        n = len(words)
        def _word_size(i: int) -> int:
            if n == 1: return max(70, W // 10)
            if n == 2: return max(48, W // 14) if i == 0 else max(70, W // 9)
            if n == 3:
                return [max(30, W // 28), max(72, W // 10), max(36, W // 20)][i]
            if i == 0:   return max(26, W // 30)
            elif i <= n // 2: return max(64, W // 12)
            else:        return max(32, W // 22)

        lines_spec = [(w.upper(), _word_size(i), _font(_word_size(i))) for i, w in enumerate(words)]

        _tmp = Image.new("RGBA", (W, 4))
        _td  = ImageDraw.Draw(_tmp)

        def _build_line_data(spec):
            data = []
            for word, sz, fnt in spec:
                bb = _td.textbbox((0, 0), word, font=fnt)
                tw, th = bb[2] - bb[0], bb[3] - bb[1]
                # 125% leading — standard typographic line advance, no overlap
                lh = max(th + max(12, int(sz * 0.25)), int(sz * 1.25))
                data.append((word, fnt, lh, tw))
            return data

        line_data = _build_line_data(lines_spec)
        block_h = sum(ld[2] for ld in line_data)

        # If block overflows 85% of image height, scale all font sizes down to fit
        max_block_h = int(H * 0.70)
        if block_h > max_block_h:
            scale = max_block_h / block_h
            lines_spec = [(w, max(18, int(sz * scale)), _font(max(18, int(sz * scale))))
                          for w, sz, _ in lines_spec]
            line_data = _build_line_data(lines_spec)
            block_h = sum(ld[2] for ld in line_data)

        block_w = max(ld[3] for ld in line_data)

        # Place text vertically centred, left-aligned with margin
        text_y_start = max(margin, (H - block_h) // 2)
        text_x       = margin

        # ── 2. No vignette ────────────────────────────────────────────────────

        # ── 3. Billboard text — full-bleed, tight outline only ───────────────
        draw = ImageDraw.Draw(img)
        y = text_y_start
        for i, (word, fnt, lh, tw) in enumerate(line_data):
            # Tight 1px outline shadow — low opacity to avoid dark blotch
            for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1),(0,2),(2,0)]:
                draw.text((text_x+dx, y+dy), word, font=fnt, fill=(0,0,0,80))
            color = (*accent_rgb, 255) if i == 0 and len(line_data) > 1 else (255, 255, 255, 255)
            draw.text((text_x, y), word, font=fnt, fill=color)
            y += lh

        # ── 4. Brand logo — top-right ─────────────────────────────────────────
        try:
            from app.brand_assets import get_asset_loader as _gal
            _logos = _gal().list_logos(brand)
            _sfx   = {"green","red","yellow","orange","purple","blue"}
            _primary = next(
                (p for p in _logos if p.lower().endswith(".png")
                 and not any(p.lower().rsplit(".",1)[0].endswith(s) for s in _sfx)),
                _logos[0] if _logos else None,
            )
            if _primary:
                _logo_bytes = None
                if not _primary.startswith("gs://"):
                    _logo_bytes = _P(_primary).read_bytes()
                else:
                    try:
                        from app.creative_pipeline import _load_bytes as _clb
                        _logo_bytes = _clb(_primary)
                    except Exception: pass
                if _logo_bytes:
                    _logo = Image.open(io.BytesIO(_logo_bytes)).convert("RGBA")
                    max_lw = int(W * 0.14)
                    max_lh = int(H * 0.10)
                    sc  = min(max_lw / max(1, _logo.width), max_lh / max(1, _logo.height), 1.0)
                    lw  = max(32, int(_logo.width * sc))
                    lh2 = max(32, int(_logo.height * sc))
                    _logo = _logo.resize((lw, lh2), Image.LANCZOS)
                    gr   = max(6, int(lw * 0.25))
                    glow = Image.new("RGBA", (lw + gr*2, lh2 + gr*2), (0,0,0,0))
                    gd   = ImageDraw.Draw(glow)
                    gd.ellipse([gr//2, gr//2, lw+gr+gr//2, lh2+gr+gr//2], fill=(255,255,255,60))
                    glow = glow.filter(ImageFilter.GaussianBlur(radius=gr))
                    lx = W - lw - margin
                    ly = margin
                    img.paste(glow, (lx-gr, ly-gr), glow)
                    img.paste(_logo, (lx, ly), _logo)
        except Exception as _le:
            logger.debug("logo_skipped", brand=brand, error=str(_le))

        # ── 5. Product label stamp — brand + product name in product zone ────────
        # Placed bottom-right where products sit; guarantees brand name is readable
        # even if the AI model rendered wrong/no text on the packaging.
        try:
            _LABEL_COLORS = {
                "Sunglow": {"bg": (176, 0, 100, 220),   "text": (255, 255, 255), "accent": (255, 199, 44)},
                "Rnorr":   {"bg": (0, 86, 41, 220),     "text": (255, 255, 255), "accent": (255, 222, 0)},
                "Boozt":   {"bg": (14, 16, 94, 220),    "text": (255, 255, 255), "accent": (0, 186, 254)},
            }
            _lc = _LABEL_COLORS.get(brand, {"bg": (20, 20, 20, 200), "text": (255, 255, 255), "accent": (255, 200, 0)})
            _sw = int(W * 0.17)
            _sh = int(H * 0.11)
            _sx = W - _sw - margin
            _sy = H - _sh - int(H * 0.14)  # lower-right, above crop safe zone

            _stamp = Image.new("RGBA", (_sw, _sh), (0, 0, 0, 0))
            _sdrw  = ImageDraw.Draw(_stamp)
            _cr    = max(8, _sh // 5)

            # Main background pill
            _sdrw.rounded_rectangle([0, 0, _sw, _sh], radius=_cr, fill=_lc["bg"])
            # Accent strip at top (brand colour bar)
            _sdrw.rounded_rectangle([0, 0, _sw, _sh // 3], radius=_cr,
                                     fill=(*_lc["accent"], 255))
            _sdrw.rectangle([0, _sh // 4, _sw, _sh // 3], fill=(*_lc["accent"], 255))

            # Brand name — large, centred
            _bf_sz  = max(14, int(_sh * 0.40))
            _bf     = _font(_bf_sz)
            _bb     = _sdrw.textbbox((0, 0), brand.upper(), font=_bf)
            _bx     = (_sw - (_bb[2] - _bb[0])) // 2
            _by     = _sh // 3 + max(3, int(_sh * 0.05))
            _sdrw.text((_bx + 1, _by + 1), brand.upper(), font=_bf, fill=(0, 0, 0, 90))
            _sdrw.text((_bx, _by), brand.upper(), font=_bf, fill=(*_lc["text"], 255))

            # Product name — smaller, below brand
            if product_name:
                _pf_sz = max(9, int(_sh * 0.20))
                _pf    = _font(_pf_sz)
                _plbl  = product_name[:22].upper()
                _pb    = _sdrw.textbbox((0, 0), _plbl, font=_pf)
                _px    = (_sw - (_pb[2] - _pb[0])) // 2
                _py    = _by + (_bb[3] - _bb[1]) + max(2, int(_sh * 0.04))
                _sdrw.text((_px, _py), _plbl, font=_pf, fill=(*_lc["accent"], 230))

            img.paste(_stamp, (_sx, _sy), _stamp)
        except Exception as _stamp_err:
            logger.debug("product_stamp_skipped", brand=brand, error=str(_stamp_err))

        result = img.convert("RGB")
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=93)
        logger.info("brand_overlay_applied", brand=brand, words=words, W=W, H=H)
        return buf.getvalue()

    except Exception as e:
        logger.warning("brand_overlay_failed", brand=brand, error=str(e))
        return img_data



async def generate_campaign_reel(
    brand: str,
    big_idea: str,
    fan_truth: str,
    season: str,
    product_name: str,
    audience: str,
    gcs_bucket: str,
    gcp_project: str,
    gcp_region: str,
    campaign_id: str,
    copy_headline: str = "",
    reasoning_model: str = "gemini-3.5-flash",
) -> tuple[str, str]:
    """
    Generate a 6-second campaign reel using Veo via Vertex AI.
    Returns (video_b64, gcs_uri) — video_b64 is empty on failure.
    """
    import asyncio, base64, time
    import google.genai as _veo_genai
    from google.genai.types import GenerateVideosConfig

    log = logger.bind(campaign_id=campaign_id)
    output_uri = f"gs://{gcs_bucket}/outputs/{campaign_id}/reel.mp4"

    # ── Product-aware brand scene directions ─────────────────────────────────
    _prod = product_name or f"{brand} product"

    def _sunglow_scene(p: str) -> str:
        if any(x in p.lower() for x in ["serum", "oil", "scalp", "treat"]):
            return (
                f"Close-up slow-motion of a woman applying {p} drops onto her fingertips, "
                f"then running them through her hair as golden light particles trail behind. "
                f"The {p} bottle gleams in warm studio light in the foreground. "
                f"Magenta-pink and sunshine yellow brand colours. Warm glowing bokeh."
            )
        elif any(x in p.lower() for x in ["conditioner", "mask", "repair"]):
            return (
                f"A woman applying {p} through her hair in a bright studio, smiling confidently "
                f"as her hair transforms into glossy, flowing locks in slow motion. "
                f"The {p} tube displayed on a clean white surface. Sunglow magenta-pink and sunshine yellow palette."
            )
        else:  # shampoo, default
            return (
                f"A beautiful woman doing a slow-motion hair flip after washing with {p}, "
                f"her incredibly shiny hair cascading through golden light particles and warm bokeh. "
                f"The {p} bottle visible in foreground catching the light. "
                f"Magenta-pink and sunshine yellow brand colours, dramatic rim lighting."
            )

    def _rnorr_scene(p: str) -> str:
        if any(x in p.lower() for x in ["gravy", "sauce", "cook-in", "liquid"]):
            return (
                f"A home cook pouring rich golden {p} over a sizzling pan of vegetables, "
                f"dramatic steam and golden sauce trails catching warm kitchen light. "
                f"The {p} bottle/pack on the counter, deep green and yellow brand accents."
            )
        elif any(x in p.lower() for x in ["bouillon", "powder", "seasoning"]):
            return (
                f"A close-up of {p} being sprinkled into a bubbling pot, golden powder "
                f"dissolving into rich broth with cinematic steam wisps rising. "
                f"Rnorr {p} pack beside fresh herbs. Deep forest green and yellow palette."
            )
        else:  # stock cubes, stock pots, default
            return (
                f"A home cook dropping a {p} into a steaming pot, watching it dissolve "
                f"into rich golden broth — steam rising dramatically in warm amber kitchen light. "
                f"The {p} box/jar on the counter beside fresh vegetables. "
                f"Deep forest green and sunshine yellow brand colours."
            )

    def _boozt_scene(p: str) -> str:
        if any(x in p.lower() for x in ["sport", "hydration", "zero", "sugar"]):
            return (
                f"An athlete in peak condition opening a can of {p} post-workout, electrolyte "
                f"droplets catching electric blue studio light in slow motion. "
                f"The {p} can gleams in the foreground against a high-contrast navy background. "
                f"Deep midnight navy and electric cobalt blue brand colours, energy arcs and neon trails."
            )
        else:  # Original Energy, default
            return (
                f"A confident person cracking open a can of {p} in a charged urban environment, "
                f"electric blue light spilling out as the can opens, energy radiating outward. "
                f"The {p} can displayed dramatically in foreground catching cobalt studio light. "
                f"Deep midnight navy and electric cobalt blue brand colours, high-voltage energy arcs."
            )

    _BRAND_SCENE_FN = {
        "Sunglow": _sunglow_scene,
        "Rnorr":   _rnorr_scene,
        "Boozt":   _boozt_scene,
    }
    brand_scene = _BRAND_SCENE_FN[brand](_prod) if brand in _BRAND_SCENE_FN \
        else f"A premium advertising scene featuring {_prod} with dynamic energy and brand colours."

    _gc = _veo_genai.Client(vertexai=True, project=gcp_project, location=gcp_region)
    _voiceover_line = (
        f'A warm confident voiceover says: "{copy_headline}"' if copy_headline
        else "A warm confident voiceover narrates the campaign tagline."
    )
    video_prompt = await asyncio.get_event_loop().run_in_executor(None, lambda: _gc.models.generate_content(
        model=reasoning_model,
        contents=f"""Write a single cinematic video+audio generation prompt (80-100 words) for a 6-second {brand} campaign reel with voiceover.

Brand: {brand}
Product: {product_name}
Campaign Big Idea: {big_idea}
Fan Truth: {fan_truth}
Season: {season}
Audience: {audience}
Campaign Headline (voiceover text): "{copy_headline or big_idea}"

Base visual direction: {brand_scene}

Rules:
- Photorealistic, premium FMCG ad quality, dynamic motion, brand colours prominent
- AUDIO: upbeat brand-appropriate background music + {_voiceover_line}
- The voiceover should be delivered confidently and warmly over the music
- No text or typography in the image
Output the prompt only.""",
    ))
    final_prompt = video_prompt.text.strip()
    log.info("veo_prompt_ready", prompt=final_prompt[:120])

    # ── Call Veo ──────────────────────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    try:
        veo_model = os.getenv("VEO_MODEL", "veo-3.1-generate-001")
        operation = await loop.run_in_executor(None, lambda: _gc.models.generate_videos(
            model=veo_model,
            prompt=final_prompt,
            config=GenerateVideosConfig(
                aspect_ratio="16:9",
                duration_seconds=6,
                output_gcs_uri=output_uri,
                number_of_videos=1,
                generate_audio=True,
            ),
        ))
        log.info("veo_operation_started", name=getattr(operation, "name", "unknown"))

        # Poll until complete (max 8 min)
        deadline = time.time() + 480
        while not operation.done:
            if time.time() > deadline:
                log.warning("veo_timeout")
                return "", ""
            await asyncio.sleep(20)
            operation = await loop.run_in_executor(None, lambda: _gc.operations.get(operation))

        if not operation.result or not operation.result.generated_videos:
            log.warning("veo_no_videos_returned")
            return "", ""

        video_gcs = operation.result.generated_videos[0].video.uri
        log.info("veo_done", uri=video_gcs)

        # ── Download from GCS and return as base64 ────────────────────────────
        from google.cloud import storage as _gcs
        without = video_gcs[5:]  # strip gs://
        bucket_name, _, blob_path = without.partition("/")
        video_bytes = await loop.run_in_executor(
            None,
            lambda: _gcs.Client().bucket(bucket_name).blob(blob_path).download_as_bytes()
        )
        return base64.b64encode(video_bytes).decode("utf-8"), video_gcs

    except Exception as e:
        log.warning("veo_failed", error=str(e))
        return "", ""


async def run_creative_pipeline_direct(
    brand: str,
    audience: str,
    product_uris: list,
    asset_uris: list,
    logo_uri: str,
    brand_guidelines: str,
    big_idea_seed: str = "",
    copy_headline: str = "",
    product_name: str = "",
    fan_truth: str = "",
    season: str = "",
    market: str = "",
    channels: list = None,
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
    _text_model = os.getenv("CREATIVE_MODEL", "gemini-3.5-flash")

    _fallback_text_model = os.getenv("FALLBACK_CREATIVE_MODEL", "gemini-2.0-flash")

    async def _llm(prompt: str, temp: float = 0.5, retries: int = 3,
                   with_brand_imgs: bool = False) -> str:
        """Call creative model via Vertex AI with backoff + fallback model on quota errors."""
        import asyncio
        loop = asyncio.get_event_loop()
        _models = ([_text_model, _fallback_text_model]
                   if _fallback_text_model and _fallback_text_model != _text_model
                   else [_text_model])
        for _m in _models:
            is_vision = any(x in _m.lower() for x in ["image", "vision", "pro"])
            contents = [prompt] + (_brand_img_parts[:6] if with_brand_imgs and is_vision and _brand_img_parts else [])
            for attempt in range(retries):
                try:
                    r = await loop.run_in_executor(None, lambda m=_m: _gemini.models.generate_content(
                        model=m, contents=contents,
                    ))
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
                        wait = 8 * (2 ** attempt)   # 8s, 16s
                        log.warning("gemini_rate_limit_retry", attempt=attempt+1, wait=wait, model=_m)
                        await asyncio.sleep(wait)
                    elif "429" in str(e):
                        log.warning("gemini_quota_exhausted_switching", from_model=_m, to_model=_fallback_text_model)
                        break
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
    await _asyncio.sleep(0.5)

    # Stage 2: Brand summariser
    log.info("p2_brand_summariser_start")
    await _emit("kv", "running", f"Extracting {brand} brand locks & creative rules…")
    _BRAND_PALETTE_LOCK = {
        "Sunglow": "primary #B00064 Magenta, accent #FFC72C Sunshine Yellow, base #F9F9F9 Off-White, font Alatsi",
        "Rnorr":   "primary #008641 Rnorr Green, accent #FFDE00 Yellow, base #FFFFFF White, fonts Antonio + Rubik",
        "Boozt":   "primary #0E105E Midnight, accent #0086FE Boozt Blue, highlight #00BFFE Sky, base #FFFFFF White, font Rubik — energy drink brand",
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
    await _asyncio.sleep(0.5)

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
    await _asyncio.sleep(0.5)

    # Stage 4: Generate 5 distinct scene concept prompts from brief context
    log.info("p2_prompt_agent_start")
    await _emit("kv", "running", "Crafting 2 scene concepts from your brief…")
    _BRAND_PALETTE = {
        "Sunglow": "hot magenta pink, sunshine yellow, off-white cream",
        "Rnorr":   "deep forest green, bright sunshine yellow, white",
        "Boozt":   "deep midnight navy, electric cobalt blue, sky blue, white — energy drink can with condensation",
    }
    _brand_palette_str = _BRAND_PALETTE.get(brand, "brand primary colour, accent colour, white")

    # ── Brief context strings ─────────────────────────────────────────────────
    _season_ctx  = season  or "year-round"
    _market_ctx  = market  or "UK"
    _product_ctx = product_name or f"{brand} product range"
    _ft_ctx      = fan_truth or "people love this brand"
    _aud_ctx     = audience or "adults 25-45"

    # ── Brand-specific magic elements ────────────────────────────────────────
    _BRAND_MAGIC = {
        "Sunglow": {
            "effects":  "floating golden light particles, warm bokeh orbs, soft lens flare, shimmering hair highlights catching studio rim light",
            "model":    "beautiful woman, age 22-35, ECSTATIC expression, head tilted back mid-laugh OR doing a dramatic hair-flip, hair FLYING and catching the light — ethnicity matches the selected market",
            "hair":     "hair is the ABSOLUTE HERO — impossibly shiny, flowing, volumised, cascading waves or sleek blowout, lit from behind with golden rim light creating a halo glow",
            "bg":       "rich magenta-pink to warm golden gradient, glowing from centre, deep and saturated",
            "wardrobe": "magenta, hot pink, or sunshine yellow outfit matching brand palette",
            "energy":   "euphoric, empowered, like the best hair day of her life",
        },
        "Rnorr": {
            "effects":  "photorealistic steam wisps rising dramatically, golden food particles suspended mid-air, warm amber bokeh, rich aromatic atmosphere",
            "model":    "warm relatable home cook (woman OR man, age 28-45), genuinely delighted expression, caught in a moment of tasting or stirring — ethnicity and look authentic to the selected market",
            "hair":     "natural, realistic — face and personality are the hero, not hair",
            "bg":       "deep forest green to warm golden-yellow gradient, rich and appetising, warm kitchen ambient light",
            "wardrobe": "warm earthy tones, apron, casual and real",
            "energy":   "joy, pride, the magic of effortless delicious cooking",
        },
        "Boozt": {
            "effects":  "electric cobalt blue light trails, neon energy arcs, fizzing bubbles and condensation droplets catching studio strobes, high-voltage energy sparks",
            "model":    "confident person age 18-35, POWERFUL pose — can in hand raised to lips, or mid-action in urban or sport context — ethnicity matches the selected market",
            "product":  "Boozt drink can PROMINENTLY featured — glistening with condensation, electric blue label under dramatic rim light",
            "bg":       "deep midnight navy to electric cobalt blue gradient, dramatic studio lighting, high-contrast",
            "wardrobe": "electric blue, cobalt, or sharp white outfit — bold and graphic",
            "energy":   "power, unstoppable momentum, pure charged confidence",
        },
    }
    _magic = _BRAND_MAGIC.get(brand, {
        "effects":  "sparkling light particles, soft bokeh, premium studio lighting",
        "model":    "attractive confident person, dynamic pose, genuine emotion",
        "hair":     "natural and beautiful",
        "bg":       f"{_brand_palette_str} gradient, bold and saturated",
        "wardrobe": f"colours matching {_brand_palette_str}",
        "energy":   "aspiration and confidence",
    })

    # ── Audience-driven persona override ─────────────────────────────────────
    # Keys match EXACT UI interest strings (lowercase) per brand.
    # Rnorr:   Home cooks | Families | Students | Budget shoppers | Food lovers | Meal preppers | Time-poor professionals
    # Sunglow: Natural hair community | Protective styles | Wash day routines | Scalp health | Curl definition | Black hair care | Beauty enthusiasts
    # Boozt:   Athletes & gym-goers | Students | Festival-goers | Gamers | Young professionals | Outdoor adventurers
    _AUDIENCE_PERSONAS = {
        # ── Rnorr ─────────────────────────────────────────────────────────────
        "home cooks": {
            "person":   "passionate home cook (any gender, any ethnicity, 28-50), fully absorbed in making something delicious from scratch",
            "setting":  "well-loved home kitchen, pots and fresh ingredients everywhere, steam rising",
            "energy":   "creative, proud, completely in their element — this is their happy place",
            "wardrobe": "casual home clothes, colourful apron, real and relaxed",
        },
        "families": {
            "person":   "young parent (late 20s–30s) with one or two children aged 4-10, all laughing and cooking together",
            "setting":  "warm bright family kitchen, kids helping at the counter, wholesome meal in progress",
            "energy":   "warm, loving, joyful family togetherness around food",
            "wardrobe": "relaxed home clothes, bright and approachable colours",
        },
        "students": {
            "person":   "university student (any ethnicity), casual and resourceful, cooking a quick flavourful meal",
            "setting":  "compact student apartment kitchen — minimal but cosy, practical and lived-in",
            "energy":   "resourceful, carefree, discovering the joy of cooking independently",
            "wardrobe": "casual streetwear — hoodie, jeans, relaxed student aesthetic",
        },
        "budget shoppers": {
            "person":   "savvy everyday shopper (25-45, any ethnicity), proud of making great meals affordably",
            "setting":  "cheerful everyday kitchen, practical ingredients, satisfied smile at an incredible result",
            "energy":   "empowered, smart — incredible flavour without breaking the bank",
            "wardrobe": "everyday casual, practical and approachable",
        },
        "food lovers": {
            "person":   "food-obsessed enthusiast (25-45), eyes wide with delight, completely absorbed in aromas and flavours",
            "setting":  "beautiful home kitchen, artisan cookware, quality fresh ingredients, food-photography aesthetic",
            "energy":   "passionate, sensory, joyful — food is an experience and an art form",
            "wardrobe": "stylish casual or a beautiful apron, food-influencer aesthetic",
        },
        "meal preppers": {
            "person":   "organised home cook (25-45), confidently batch-cooking multiple dishes at once, totally in control",
            "setting":  "tidy organised kitchen, multiple pots on the go, glass containers lined up and ready",
            "energy":   "efficient, satisfyingly productive — Sunday prep is a weekly ritual",
            "wardrobe": "practical casual, sleeves rolled up, ready to work",
        },
        "time-poor professionals": {
            "person":   "busy professional (28-45), smart-casual, cooking a quick impressive meal straight after work",
            "setting":  "sleek modern kitchen, minimal clutter, quick prep underway, laptop bag still on the chair",
            "energy":   "efficient, accomplished — turning 15 minutes into something that tastes like hours",
            "wardrobe": "work smart-casual — shirt sleeves rolled up, transitioning from office to kitchen",
        },
        # ── Sunglow ───────────────────────────────────────────────────────────
        "natural hair community": {
            "person":   "Black woman (20-40) with stunning natural hair — 4C coils, full afro, or defined curls — radiantly and unapologetically confident",
            "setting":  "bright outdoor or studio setting, golden rim light crowning her natural hair like a halo",
            "energy":   "deeply confident, joyful, unapologetically herself — natural hair is her crown",
            "wardrobe": "vibrant outfit in brand palette, celebrating natural identity",
        },
        "protective styles": {
            "person":   "Black woman (18-38) showcasing gorgeous protective styling — box braids, twists, or locs — looking powerful and intentional",
            "setting":  "golden-lit studio, intricate protective style catching every ray of light beautifully",
            "energy":   "powerful, intentional, celebrating the artistry and heritage of protective styling",
            "wardrobe": "bold colourful outfit, accessories that complement the hairstyle",
        },
        "wash day routines": {
            "person":   "Black woman (20-40) mid wash-day ritual — fresh out of shower, product in hair, glowing and relaxed",
            "setting":  "luxurious bathroom with warm steam, golden light, self-care sanctuary atmosphere",
            "energy":   "self-loving, indulgent — wash day is a ritual of celebration and self-care",
            "wardrobe": "beautiful robe or cosy comfort wear, wash-day energy",
        },
        "scalp health": {
            "person":   "Woman (20-45) massaging product into scalp with eyes closed in pleasure, visibly healthy radiant scalp",
            "setting":  "bright clean bathroom, warm clinical-beautiful aesthetic with golden accent light",
            "energy":   "nurturing, deeply satisfied — healthy hair starts at the scalp",
            "wardrobe": "white or cream tones, clean fresh health-focused aesthetic",
        },
        "curl definition": {
            "person":   "Woman (18-38) with perfectly defined, bouncy, glistening curls — any curl type 2B to 4C, absolutely stunning",
            "setting":  "bright studio or outdoor with dappled light making every curl spring and shine",
            "energy":   "euphoric — curls are perfectly popped, springy, and absolutely stunning today",
            "wardrobe": "vibrant or white outfit to contrast and showcase the curl perfection",
        },
        "black hair care": {
            "person":   "Black woman (18-50), any texture from 3A to 4C, glowing with deep healthy-hair confidence",
            "setting":  "premium beauty setting with rich dramatic lighting that reveals every strand's texture and sheen",
            "energy":   "confident, celebratory — Black hair is powerful, diverse, and endlessly beautiful",
            "wardrobe": "bold statement outfit in brand palette, sophisticated and expressive",
        },
        "beauty enthusiasts": {
            "person":   "beauty-obsessed woman (20-38), immaculate grooming, polished and styled, radiating confidence",
            "setting":  "beautiful aesthetic vanity or chic studio environment, aspirational beauty-influencer vibe",
            "energy":   "glamorous, self-expressive — beauty is a lifestyle and a passion",
            "wardrobe": "on-trend fashion-forward outfit, beauty-influencer aesthetic",
        },
        # ── Boozt ─────────────────────────────────────────────────────────────
        "athletes & gym-goers": {
            "person":   "athletic person (18-35, any gender) in peak condition — mid-workout or immediately post-workout, holding a Boozt can with fierce determination",
            "setting":  "premium gym or outdoor track, dramatic electric blue rim lighting, power and performance atmosphere",
            "energy":   "relentless drive, peak performance — this is what being at your best feels like",
            "wardrobe": "performance sportswear — bold electric blue or sharp white, athletic and powerful",
        },
        "students": {
            "person":   "university student (18-24, any ethnicity) buzzing with late-night energy — laptop open, Boozt can in hand, fully in the zone",
            "setting":  "campus study space or urban apartment at night, electric blue accent lighting, productive and alive",
            "energy":   "focused, switched-on — deadlines don't stand a chance when you have this energy",
            "wardrobe": "casual student streetwear — hoodie, jeans, relaxed but sharp",
        },
        "festival-goers": {
            "person":   "person (18-30, any gender) in full festival mode — Boozt can raised high, electric with energy, crowd behind them",
            "setting":  "festival at night — LED lights, smoke machines, stage glow, pulsing crowd energy",
            "energy":   "euphoric, unstoppable, living in the moment — Boozt is the fuel of the night",
            "wardrobe": "bold festival fashion — electric colours, glitter, expressive and loud",
        },
        "gamers": {
            "person":   "confident gamer (18-30, any gender) lit by monitor glow — Boozt can beside the keyboard, fully locked in",
            "setting":  "high-end gaming setup, RGB lighting, electric blue glow, late night immersive atmosphere",
            "energy":   "hyper-focused, unbeatable reaction time — Boozt is the ultimate gaming fuel",
            "wardrobe": "gaming hoodie or casual streetwear, bold and graphic",
        },
        "young professionals": {
            "person":   "young professional (22-35) moving fast through an urban environment — Boozt can in hand, sharp and purposeful",
            "setting":  "city streets or modern office lobby, electric blue neon reflections, fast-paced urban energy",
            "energy":   "driven, ambitious — Boozt keeps you sharp when the world demands your best",
            "wardrobe": "smart-casual urban style — bold blazer or clean streetwear, confident and polished",
        },
        "outdoor adventurers": {
            "person":   "adventurous person (20-40, any gender) in a stunning outdoor setting — Boozt can in hand, conquering the landscape",
            "setting":  "dramatic outdoor vista — mountain peak, cliffside, or urban rooftop at golden hour",
            "energy":   "free, powerful, fearless — Boozt fuels the people who push further",
            "wardrobe": "outdoor/adventure gear — technical, bold, built for performance",
        },
    }
    _AGE_OVERRIDES = {
        "13-17": "specifically a teenager aged 13-17, youthful, relatable and authentic",
        "13–17": "specifically a teenager aged 13-17, youthful, relatable and authentic",
        "18-24": "specifically aged 18-24, young adult face and fresh vibrant energy",
        "18–24": "specifically aged 18-24, young adult face and fresh vibrant energy",
        "25-34": "specifically aged 25-34, young professional energy and confidence",
        "25–34": "specifically aged 25-34, young professional energy and confidence",
        "35-44": "specifically aged 35-44, established mid-life confidence and warmth",
        "35–44": "specifically aged 35-44, established mid-life confidence and warmth",
        "45-54": "specifically aged 45-54, mature, vibrant and powerfully confident",
        "45–54": "specifically aged 45-54, mature, vibrant and powerfully confident",
        "55+":   "specifically aged 55+, distinguished, experienced and warmly radiant",
    }
    # Market drives ethnicity/cultural representation — model should look like they belong there
    _MARKET_DEMOGRAPHICS = {
        "united kingdom": "British — reflect the UK's diverse multicultural population (White British, South Asian, Black British, mixed heritage — vary naturally)",
        "australia":      "Australian — reflect Australia's diverse population (Anglo-Australian, East Asian, South Asian, Aboriginal, Pacific Islander — vary naturally)",
        "united states":  "American — reflect the USA's diverse population (White American, Black American, Hispanic/Latino, East Asian, South Asian — vary naturally)",
        "new zealand":    "New Zealand — reflect NZ's diverse population including Māori, Pākehā, Pacific Islander, and Asian New Zealanders",
        "sea":            "Southeast Asian — specifically Filipino, Indonesian, Thai, Malaysian, or Vietnamese appearance, authentic SEA cultural context",
        "global":         "globally diverse — any ethnicity, universally relatable, celebrate diversity",
    }
    # Sunglow interests that are specifically about Black/textured hair — retain cultural context but market-anchor
    _SUNGLOW_BLACK_HAIR_INTERESTS = {
        "natural hair community", "protective styles", "wash day routines",
        "scalp health", "curl definition", "black hair care",
    }
    _market_lower = (_market_ctx or "").lower()
    _market_demo  = next((v for k, v in _MARKET_DEMOGRAPHICS.items() if k in _market_lower), "")
    # Brand expression/pose always preserved — audience changes WHO, brand DNA stays HOW
    _BRAND_EXPRESSION = {
        "Sunglow": "ECSTATIC expression, dramatic hair-flip or head thrown back mid-laugh, hair FLYING and catching golden light — hair is always the ABSOLUTE HERO",
        "Rnorr":   "genuinely delighted expression, caught mid-moment of cooking — tasting, stirring, or reacting to the aroma with pure joy",
        "Boozt":   "POWERFUL pose — Boozt can raised, mid-drink or thrust forward toward camera, radiating unstoppable electric charged energy",
    }
    # Brand-specific settings anchored to product world — keyed to exact UI interest strings
    _BRAND_SETTING = {
        "Sunglow": {
            "natural hair community": "bright outdoor or studio, golden rim light crowning the natural hair",
            "protective styles":      "golden-lit studio, intricate style catching the light beautifully",
            "wash day routines":      "luxury bathroom, steam and warm golden light, self-care sanctuary",
            "scalp health":           "clean bright bathroom, clinical-beautiful aesthetic, warm accent light",
            "curl definition":        "bright studio or outdoor dappled light making curls spring and shine",
            "black hair care":        "premium beauty setting, rich dramatic lighting on hair texture",
            "beauty enthusiasts":     "chic studio or beauty-influencer environment, aspirational aesthetic",
            "students":               "bright campus bathroom or dorm, golden rim light on hair",
            "families":               "warm family bathroom, morning golden light on hair",
            "default":                "studio with golden hour rim light, hair as the centrepiece",
        },
        "Rnorr": {
            "home cooks":              "well-loved home kitchen, pots on the stove, fresh ingredients, steam rising",
            "families":                "warm family kitchen, kids at the counter, wholesome meal in progress",
            "students":                "compact student apartment kitchen, lived-in and cosy",
            "budget shoppers":         "cheerful everyday kitchen, practical and satisfying",
            "food lovers":             "beautiful home kitchen, artisan cookware, quality fresh ingredients",
            "meal preppers":           "tidy organised kitchen, multiple pots on the go, glass containers ready",
            "time-poor professionals": "sleek modern kitchen, quick prep underway after a long work day",
            "default":                 "warm home kitchen, aromatic cooking atmosphere",
        },
        "Boozt": {
            "athletes & gym-goers": "premium gym or outdoor track, electric blue rim lighting, power and performance",
            "students":             "campus or urban apartment at night, electric blue accent lighting",
            "festival-goers":       "festival at night, LED lights, smoke machines, pulsing crowd energy",
            "gamers":               "high-end gaming setup, RGB lighting, electric blue glow, late night",
            "young professionals":  "city streets or modern office lobby, electric blue neon reflections",
            "outdoor adventurers":  "dramatic outdoor vista — mountain, cliffside, or urban rooftop at golden hour",
            "default":              "dramatic studio with electric cobalt lighting, high-contrast, can centre-stage",
        },
    }

    _aud_lower = (_aud_ctx or "").lower()
    _matched_persona = None
    for _seg_key, _persona in _AUDIENCE_PERSONAS.items():
        if _seg_key in _aud_lower:
            _matched_persona = _persona
            break
    _age_note = next((desc for key, desc in _AGE_OVERRIDES.items() if key in _aud_ctx), "")
    _brand_expr = _BRAND_EXPRESSION.get(brand, "confident genuine expression, dynamic and engaging")

    if _matched_persona:
        # Resolve brand-aware setting for this persona
        _brand_settings = _BRAND_SETTING.get(brand, {})
        _resolved_setting = next(
            (_brand_settings[k] for k in _brand_settings if k in _aud_lower),
            _brand_settings.get("default", _matched_persona["setting"])
        )
        # Market fully drives ethnicity — no exceptions
        _ethnicity_note = _market_demo

        _magic["model"] = (
            f"{_matched_persona['person']}"
            f"{', ' + _age_note if _age_note else ''}. "
            f"{_ethnicity_note + '. ' if _ethnicity_note else ''}"
            f"{_brand_expr}. "
            f"Setting: {_resolved_setting}"
        )
        # Preserve brand effects/hair/bg — only blend energy and wardrobe
        _magic["energy"]   = f"{_matched_persona['energy']} — {_magic['energy']}"
        _magic["wardrobe"] = f"{_matched_persona['wardrobe']}, colours drawn from brand palette: {_brand_palette_str}"
    elif _age_note or _market_demo:
        # No matching segment — still apply age + market demographic to brand default
        _magic["model"] = (
            _magic["model"]
            + (f" — {_age_note}" if _age_note else "")
            + (f". Market: {_market_demo}" if _market_demo else "")
        )

    scene_concepts_raw = await _llm(f"""You are a world-class FMCG advertising creative director.
Study these reference ad styles: Sunsilk (dynamic hair, sparkles, vibrant energy), Pantene (cinematic hair movement, golden glow), Knorr (warm kitchen magic, steam, real moments), L'Oréal (empowered model, bold colour, premium feel).

Generate 2 DISTINCT, MAGICAL, HIGH-ENERGY advertising key visual prompts for this campaign.

═══ CAMPAIGN BRIEF ═══
Brand: {brand}
Product: {_product_ctx}
Big Idea: {big_idea}
Fan Truth: {_ft_ctx}
Audience: {_aud_ctx}
Season: {_season_ctx} — reflect in lighting, atmosphere, wardrobe
Market: {_market_ctx} — reflect in model authenticity

═══ BRAND VISUAL DNA ═══
Background: {_magic['bg']}
Model: {_magic['model']}
Hair/Focus: {_magic['hair']}
Magic Effects: {_magic['effects']}
Wardrobe: {_magic['wardrobe']}
Emotional Energy: {_magic['energy']}
Colours: {_brand_palette_str}

═══ PRODUCT REFERENCE ═══
Selected product: {_product_ctx}
I am providing reference images of the actual {brand} {_product_ctx} packaging and logo.
Reproduce the EXACT product design, colours, and label from those reference images.
Every product in the image MUST show '{brand}' and '{_product_ctx}' on the label.
Show 2-3 of these products prominently in the RIGHT zone.

═══ TWO DIFFERENT CONCEPTS ═══
Concept 1 — DYNAMIC ENERGY: Model is in full motion (hair flip, jump, spin, or dramatic reach). Background has maximum magical effects. Products displayed dramatically.
Concept 2 — INTIMATE GLOW: Model is closer to camera, intense eye contact, softer but deeply saturated. Background glows behind her. Products at her side, intimately placed.

Output EXACTLY this format (nothing else):
[CONCEPT 1 - DYNAMIC]: <170-200 word detailed image generation prompt>
[CONCEPT 2 - INTIMATE]: <170-200 word detailed image generation prompt>

═══ MANDATORY RULES ═══
- FULL BLEED — subject and background fill the entire frame edge to edge, no flat panels
- LEFT SIDE naturally darker/hazier/more atmospheric than right (scene depth, not a flat colour)
  so overlaid typography reads clearly — achieved through lighting, depth of field, or shadows
- Model and products positioned centre-right or right, facing slightly left into the frame
- Photorealistic DSLR advertising photography quality
- Magical effects: {_magic['effects']}
- Bold saturated colours — award-winning art direction
- NO text anywhere EXCEPT on product packaging labels (which must show '{brand}' clearly)
- Fan truth ({_ft_ctx}) visible in model's expression and scene energy
- Season ({_season_ctx}) woven into atmosphere, lighting temperature, and mood""", temp=0.9)

    # Parse the 2 concept prompts
    import re as _re
    _concept_blocks = _re.findall(r'\[CONCEPT \d+[^\]]*\]:\s*(.*?)(?=\[CONCEPT \d+|\Z)', scene_concepts_raw, _re.DOTALL)
    concept_prompts = [c.strip() for c in _concept_blocks if c.strip()]
    if not concept_prompts:
        concept_prompts = [l.strip() for l in scene_concepts_raw.split('\n') if len(l.strip()) > 80]
    concept_prompts = concept_prompts[:2] or [scene_concepts_raw[:600]]

    log.info("p2_prompt_agent_done", n_concepts=len(concept_prompts))
    await _emit("kv", "step_data", _json2.dumps({
        "image_prompt": concept_prompts[0][:350] if concept_prompts else "",
        "concepts":     [p[:200] for p in concept_prompts],
    }))
    await _emit("kv", "running", f"Brief analysed — generating {len(concept_prompts)} campaign visuals…")

    # Stage 5: Image generation via Google AI
    image_b64  = None
    images_b64: list = []
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
                    "These are existing campaign images for this brand. Analyze them and describe in 5-6 sentences covering: "
                    "1) exact background colours and any gradient/glow effects, "
                    "2) model energy — pose, expression, movement, hair treatment, "
                    "3) magical/special effects — sparkles, light rays, bokeh, particles, steam, energy arcs, "
                    "4) product placement — how products are staged, lit, and scaled, "
                    "5) overall mood and emotional tone. "
                    "Be precise and visual — this description will directly guide a new AI image generation.",
                    *ref_parts,
                ]
                vision_resp = client.models.generate_content(
                    model    = _settings.gemini_model_reasoning,
                    contents = vision_contents,
                )
                style_analysis = vision_resp.text.strip()
                log.info("p2_brand_style_extracted", style=style_analysis[:120])
            except Exception as vision_err:
                log.warning("p2_brand_style_failed", error=str(vision_err),
                            note="skipping style analysis, Imagen 4 will use prompt only")

        # â"€â"€ Step B: Enrich each concept prompt with style + no-text rule ─────────
        # Spell brand name character by character for every brand to prevent AI substitution
        _brand_spelled = " – ".join(brand.upper())
        _REAL_BRAND_WARNINGS = {
            "rnorr":   "NOT 'Knorr', NOT 'Unilever', NOT any real food brand",
            "sunglow": "NOT 'Sunsilk', NOT 'Pantene', NOT any real haircare brand",
            "boozt":   "NOT 'Monster', NOT 'Red Bull', NOT 'Lucozade', NOT any real energy drink brand",
        }
        _real_brand_warn = _REAL_BRAND_WARNINGS.get(brand.lower(), "NOT any real-world brand")
        _no_text_rule = (
            f"CRITICAL BRAND + PRODUCT RULE:\n"
            f"Brand name spelled exactly: {_brand_spelled}  ← copy this spelling letter-for-letter onto every product label.\n"
            f"Selected product: '{_product_ctx}'\n"
            f"Show 2-3 '{brand}' product packages/bottles prominently in the scene. "
            f"Match the packaging SHAPE and COLOURS from the reference product images. "
            f"The label on EVERY product MUST display '{brand}' (spelled {_brand_spelled}) and '{_product_ctx}' in large, clear, readable text.\n"
            f"This is a completely fictional brand — {_real_brand_warn}.\n\n"
            "TYPOGRAPHY RULE: No text anywhere in the image EXCEPT on the product packaging labels themselves. "
            "Zero headlines, zero slogans, zero copy on backgrounds — all added in post-production.\n\n"
        )
        _style_suffix = (
            f"\n\nBRAND VISUAL STYLE (match this aesthetic):\n{style_analysis}"
            if style_analysis else ""
        )
        enriched_concepts = [
            f"{_no_text_rule}{p}{_style_suffix}" for p in concept_prompts
        ]

        # -- Step C: Load reference images (product + logo) for multimodal input --
        SUPPORTED_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        _ref_parts: list = []

        # Logo first — most important brand anchor
        if logo_uri:
            _logo_mime = _mime_for(logo_uri)
            if _logo_mime in SUPPORTED_MIME:
                _logo_data = _load_bytes(logo_uri)
                if _logo_data:
                    _ref_parts.append("BRAND LOGO — reproduce the exact shape, colours and design of this logo on the product packaging:")
                    _ref_parts.append(_gtypes.Part.from_bytes(data=_logo_data, mime_type=_logo_mime))
                    log.info("p2_logo_ref_loaded", uri=logo_uri)

        # Product images — up to 3
        for _uri in (product_uris or [])[:3]:
            _pmime = _mime_for(_uri)
            if _pmime not in SUPPORTED_MIME:
                continue
            _pdata = _load_bytes(_uri)
            if _pdata and len(_pdata) > 1024:
                _ref_parts.append(f"PRODUCT REFERENCE — Reproduce this '{brand}' '{_product_ctx}' product: same packaging shape, same colours, same label design. Label must show '{brand}' on every product. Feature 2-3 of these products prominently:")
                _ref_parts.append(_gtypes.Part.from_bytes(data=_pdata, mime_type=_pmime))

        log.info("p2_ref_parts_loaded", n=len([p for p in _ref_parts if not isinstance(p, str)]))

        # -- Step D: Generate one image per concept in parallel -------------------
        image_model = _get_settings().gemini_model_image
        log.info("p2_generate_image_start", model=image_model, n=len(enriched_concepts))
        await _emit("kv", "running", f"Generating {len(enriched_concepts)} campaign visuals with brand references…")

        async def _gen_one_image(prompt: str, delay: float = 0.0) -> bytes | None:
            if delay:
                await asyncio.sleep(delay)
            loop = asyncio.get_event_loop()
            # Build multimodal contents: reference images first, then prompt
            contents: list = []
            if _ref_parts:
                contents.extend(_ref_parts)
            contents.append(prompt)
            for attempt in range(4):
                try:
                    resp = await loop.run_in_executor(None, lambda: client.models.generate_content(
                        model    = image_model,
                        contents = contents,
                        config   = _gtypes.GenerateContentConfig(
                            response_modalities = ["IMAGE", "TEXT"],
                            image_config        = _gtypes.ImageConfig(aspect_ratio="16:9"),
                        ),
                    ))
                    for part in resp.candidates[0].content.parts:
                        if hasattr(part, "inline_data") and part.inline_data is not None:
                            return part.inline_data.data
                    return None
                except Exception as _e:
                    if "429" in str(_e) and attempt < 3:
                        wait = 8 * (2 ** attempt)
                        log.warning("p2_image_rate_limit", attempt=attempt + 1, wait_s=wait)
                        await asyncio.sleep(wait)
                    else:
                        log.warning("p2_gen_one_image_failed", error=str(_e))
                        return None
            return None

        # Stagger starts by 5s each to avoid simultaneous 429s
        _img_results = await asyncio.gather(*[
            _gen_one_image(p, delay=i * 2) for i, p in enumerate(enriched_concepts)
        ])
        generated_bytes_list = [r for r in _img_results if r is not None]
        if not generated_bytes_list:
            raise ValueError("Gemini Pro Image returned no images")

        # Apply brand overlay (logo + headline + brand name + product) to every variation
        _headline_overlay = copy_headline or _extract_headline(big_idea)
        primary_bytes = generated_bytes_list[0]  # raw, for channel crops
        images_b64 = []
        for _img_bytes in generated_bytes_list:
            _overlaid = _apply_brand_overlay(
                _img_bytes, brand, _headline_overlay, product_uris, product_name
            )
            images_b64.append(base64.b64encode(_overlaid).decode("utf-8"))
        image_b64 = images_b64[0] if images_b64 else None
        log.info("p2_generate_image_done", n_generated=len(images_b64))

        # Channel adaptations — only for channels selected in the wizard
        primary_bytes = generated_bytes_list[0]
        selected_ch = {c.lower().strip() for c in (channels or [])}
        if selected_ch:
            active_keys: set = set()
            for ch in selected_ch:
                active_keys.update(_CHANNEL_KEY_MAP.get(ch, [ch]))
        else:
            active_keys = {key for *_, key in _CHANNEL_FORMATS}

        channel_adaptations: dict = {}
        for rw, rh, label, key in _CHANNEL_FORMATS:
            if key not in active_keys:
                continue
            adapted = _create_channel_adaptation(primary_bytes, rw, rh, label, brand)
            if adapted:
                channel_adaptations[key] = {"label": label, "image_b64": adapted,
                                            "ratio": f"{rw}:{rh}"}
        log.info("p2_channel_adaptations_done", count=len(channel_adaptations))

    except Exception as e:
        image_error = str(e)
        log.warning("p2_generate_image_failed", error=image_error)
        await _emit("kv", "error", f"Image generation failed: {image_error[:80]}")

    # ── Upload KV images + channel adaptations to GCS (outside image try block) ─
    _gcs_uris: list = []
    if images_b64 and not image_error:
        try:
            from google.cloud import storage as _gcs_client
            _gcs = _gcs_client.Client()
            _bucket_obj = _gcs.bucket(_settings.gcs_bucket)

            def _upload(data: bytes, path: str, mime: str = "image/jpeg") -> str:
                blob = _bucket_obj.blob(path)
                blob.upload_from_string(data, content_type=mime)
                return f"gs://{_settings.gcs_bucket}/{path}"

            # KV images (with overlay) — upload each independently
            for idx, _overlaid_bytes in enumerate(images_b64):
                try:
                    _raw = base64.b64decode(_overlaid_bytes)
                    _uri = _upload(_raw, f"outputs/{campaign_id}/kv_image_{idx + 1}.jpg")
                    _gcs_uris.append(_uri)
                    log.info("p2_kv_uploaded", idx=idx + 1, uri=_uri)
                except Exception as _kv_err:
                    log.warning("p2_kv_upload_failed", idx=idx + 1, error=str(_kv_err))

            # Channel adaptations — upload each independently
            for key, val in channel_adaptations.items():
                if val.get("image_b64"):
                    try:
                        _raw = base64.b64decode(val["image_b64"])
                        _uri = _upload(_raw, f"outputs/{campaign_id}/channels/{key}.jpg")
                        channel_adaptations[key]["gcs_uri"] = _uri
                    except Exception as _ch_err:
                        log.warning("p2_channel_upload_failed", key=key, error=str(_ch_err))

            log.info("p2_gcs_upload_done", n_images=len(_gcs_uris),
                     n_channels=sum(1 for v in channel_adaptations.values() if v.get("gcs_uri")))
        except Exception as _gcs_err:
            log.warning("p2_gcs_upload_failed", error=str(_gcs_err))

        await _emit("kv", "step_data", _json2.dumps({"image_b64": image_b64, "images_b64": images_b64,
                                                      "gcs_uris": _gcs_uris}))
        await _asyncio.sleep(0.5)
        await _emit("kv", "done", f"{len(images_b64)} key visual variations ready")

    # ── Stage 6: Campaign Reel via Veo ────────────────────────────────────────
    video_b64 = ""
    video_uri = ""
    if os.getenv("REEL_ENABLED", "true").lower() not in ("false", "0", "no"):
        try:
            await _emit("reel", "running", "Generating 6-second campaign reel with Veo…")
            _settings_r = _get_settings()
            video_b64, video_uri = await generate_campaign_reel(
                brand           = brand,
                big_idea        = big_idea,
                fan_truth       = fan_truth,
                season          = season,
                product_name    = product_name,
                audience        = audience,
                gcs_bucket      = _settings_r.gcs_bucket,
                gcp_project     = _settings_r.gcp_project,
                gcp_region      = _settings_r.gcp_region,
                campaign_id     = campaign_id,
                copy_headline   = copy_headline,
                reasoning_model = _settings_r.gemini_model_reasoning,
            )
            if video_b64:
                await _emit("reel", "milestone", _json2.dumps({"video_b64": video_b64}))
                await _emit("reel", "done", "Campaign reel ready ✓")
            else:
                await _emit("reel", "error", "Reel generation failed or timed out")
        except Exception as e:
            log.warning("p2_reel_failed", error=str(e))
            await _emit("reel", "error", f"Reel error: {str(e)[:80]}")

    return {
        "campaign_id":          campaign_id,
        "culture_brief":        culture,
        "brand_summary":        brand_summary,
        "big_idea":             big_idea,
        "image_prompt":         concept_prompts[0] if concept_prompts else "",
        "image_b64":            image_b64,
        "images_b64":           images_b64,
        "image_error":          image_error,
        "gcs_uris":             _gcs_uris,
        "channel_adaptations":  channel_adaptations,
        "video_b64":            video_b64,
        "video_uri":            video_uri,
    }


