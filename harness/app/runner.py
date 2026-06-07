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

    raw = await _vertex_generate(_gc2, os.getenv("CREATIVE_MODEL", "gemini-2.5-flash"), prompt, temperature=0.7)
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
    Composite a clean branded top-bar onto the Imagen output.

    Layout:
    ┌──────────────────────────────────────────────────────┐  top of image
    │ [LOGO]   Headline from copy agent                    │  solid brand bar
    │          ─── accent divider ───                      │
    │          BRAND  ·  Product Name                      │
    ├──────────────────────────────────────────────────────┤  clean hard edge
    │  3 px accent-colour rule                             │
    ├──────────────────────────────────────────────────────┤
    │                                                      │
    │          [clean Imagen photographic scene]           │
    │                                                      │
    └──────────────────────────────────────────────────────┘

    No gradient bleeding into the photo.
    Logo from bucket/brands/{brand}/Logos/ — primary PNG (no colour variant).
    Font from bucket/brands/{brand}/Font/ — display TTF (non-italic).
    Colors hardcoded from official brand guidelines.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        from pathlib import Path as _P

        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        W, H = img.size

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
            hits = [f for f in sorted(font_dir.glob("*.ttf"))
                    if "italic" not in f.name.lower()]
            font_path = str(hits[0]) if hits else None

        # ── Official brand colors ──────────────────────────────────────────────
        BRAND_COLORS = {
            "Sunglow": {"bar": "#B00064", "accent": "#FFC72C", "text": "#FFFFFF"},
            "Rnorr":   {"bar": "#008641", "accent": "#FFDE00", "text": "#FFFFFF"},
            "Boozt":   {"bar": "#0E105E", "accent": "#0086FE", "text": "#FFFFFF"},
        }
        col        = BRAND_COLORS.get(brand, {"bar": "#1a1a2e", "accent": "#0055A4", "text": "#FFFFFF"})

        def hex_rgba(h: str, a: int = 255) -> tuple:
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (a,)

        bar_rgb    = hex_rgba(col["bar"])[:3]
        accent_rgb = hex_rgba(col["accent"])[:3]
        text_rgba  = hex_rgba(col["text"])

        # ── Font helpers ──────────────────────────────────────────────────────
        hl_size      = max(30, W // 18)    # headline — dominant
        brand_sz     = max(16, W // 32)    # brand · product line
        rule_sz      = max(2, W // 320)    # accent rule thickness

        def _font(size: int):
            if font_path:
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    pass
            try:
                return ImageFont.load_default(size=size)
            except Exception:
                return ImageFont.load_default()

        f_hl    = _font(hl_size)
        f_brand = _font(brand_sz)

        # ── Measure text to size the bar correctly ────────────────────────────
        # temp draw for measurements
        _tmp = Image.new("RGBA", (W, 4))
        _d   = ImageDraw.Draw(_tmp)

        def _tw(text: str, font) -> int:
            bb = _d.textbbox((0, 0), text, font=font)
            return bb[2] - bb[0]

        def _th(text: str, font) -> int:
            bb = _d.textbbox((0, 0), text, font=font)
            return max(1, bb[3] - bb[1])

        # Wrap headline to max 80% of text-area width (leaves room for logo)
        logo_zone = int(W * 0.20)   # logo occupies left 20%
        text_x    = logo_zone + int(W * 0.02)
        max_tw    = W - text_x - int(W * 0.02)

        words = (headline or "").split()
        lines_hl, cur = [], []
        for w in words:
            test = " ".join(cur + [w])
            if _tw(test, f_hl) > max_tw and cur:
                lines_hl.append(" ".join(cur)); cur = [w]
            else:
                cur.append(w)
        if cur:
            lines_hl.append(" ".join(cur))

        # Brand + product label: "SUNGLOW  ·  Define & Glow Serum"
        product_label = ""
        if product_name:
            pname = product_name.strip()
            # Prefix brand if not already there
            if not pname.lower().startswith(brand.lower()):
                pname = f"{brand} {pname}"
            product_label = pname

        brand_line = brand.upper()
        if product_label:
            brand_line = f"{brand.upper()}  ·  {product_label}"

        gap      = max(6, int(H * 0.008))
        pad_v    = max(12, int(H * 0.015))   # vertical padding inside bar
        hl_line_h = _th(lines_hl[0] if lines_hl else "A", f_hl) + 4
        total_hl_h = len(lines_hl) * hl_line_h
        sep_h    = rule_sz + gap * 2
        brand_h  = _th(brand_line, f_brand)
        bar_h    = pad_v + total_hl_h + sep_h + brand_h + pad_v
        bar_h    = max(80, bar_h)

        # ── Draw solid bar — NO gradient bleeding ─────────────────────────────
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)
        draw.rectangle([(0, 0), (W, bar_h)], fill=(*bar_rgb, 238))

        # Thin accent rule at the bottom of the bar (3 px)
        draw.rectangle([(0, bar_h), (W, bar_h + rule_sz * 2)],
                        fill=(*accent_rgb, 255))

        # ── Headline text ──────────────────────────────────────────────────────
        y = pad_v
        for line in lines_hl:
            tw = _tw(line, f_hl)
            x  = text_x
            # Drop shadow
            draw.text((x + 1, y + 1), line, font=f_hl, fill=(0, 0, 0, 110))
            draw.text((x, y),         line, font=f_hl, fill=text_rgba)
            y += hl_line_h

        # ── Thin accent separator ─────────────────────────────────────────────
        y += gap
        draw.rectangle([(text_x, y), (text_x + int(max_tw * 0.55), y + rule_sz)],
                        fill=(*accent_rgb, 255))
        y += rule_sz + gap

        # ── Brand · Product line ───────────────────────────────────────────────
        # Brand name in accent color, product in white
        brand_part = brand.upper()
        if product_label:
            mid  = f"  ·  {product_label}"
            bx   = text_x
            # Brand name (accent)
            draw.text((bx + 1, y + 1), brand_part, font=f_brand, fill=(0, 0, 0, 90))
            draw.text((bx, y),         brand_part, font=f_brand, fill=(*accent_rgb, 255))
            bx2 = bx + _tw(brand_part, f_brand)
            # Separator · product (white, dimmed)
            draw.text((bx2 + 1, y + 1), mid, font=f_brand, fill=(0, 0, 0, 90))
            draw.text((bx2, y),         mid, font=f_brand, fill=(*text_rgba[:3], 210))
        else:
            draw.text((text_x + 1, y + 1), brand_part, font=f_brand, fill=(0, 0, 0, 90))
            draw.text((text_x, y),         brand_part, font=f_brand, fill=(*accent_rgb, 255))

        # ── Brand logo — top-left corner, vertically centred in bar ───────────
        try:
            from app.brand_assets import get_asset_loader as _gal
            _logos   = _gal().list_logos(brand)
            _sfx     = {"green", "red", "yellow", "orange", "purple", "blue"}
            _primary = next(
                (p for p in _logos
                 if p.lower().endswith(".png")
                 and not any(p.lower().rsplit(".", 1)[0].endswith(s) for s in _sfx)),
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
                    except Exception:
                        pass
                if _logo_bytes:
                    _logo = Image.open(io.BytesIO(_logo_bytes)).convert("RGBA")
                    max_lw = int(logo_zone * 0.85)
                    max_lh = int(bar_h * 0.70)
                    sc     = min(max_lw / max(1, _logo.width),
                                 max_lh / max(1, _logo.height), 1.0)
                    _logo  = _logo.resize(
                        (max(24, int(_logo.width * sc)), max(24, int(_logo.height * sc))),
                        Image.LANCZOS,
                    )
                    # Centre logo in the left zone
                    lx = (logo_zone - _logo.width) // 2
                    ly = (bar_h - _logo.height) // 2
                    overlay.paste(_logo, (lx, ly), _logo)
        except Exception as _le:
            logger.debug("logo_skipped", brand=brand, error=str(_le))

        # ── Composite ──────────────────────────────────────────────────────────
        result = Image.alpha_composite(img, overlay).convert("RGB")
        buf    = io.BytesIO()
        result.save(buf, format="JPEG", quality=93)
        logger.info("brand_overlay_applied", brand=brand,
                    headline=(headline or "")[:50], product=product_name,
                    bar_h=bar_h, W=W, H=H)
        return buf.getvalue()

    except Exception as e:
        logger.warning("brand_overlay_failed", brand=brand, error=str(e))
        return img_data



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
    # No hex codes — Imagen renders them literally as signs/labels in the scene
    _BRAND_PALETTE = {
        "Sunglow": "hot magenta pink, sunshine yellow, off-white",
        "Rnorr":   "forest green, bright yellow, white",
        "Boozt":   "deep midnight navy, electric blue, sky blue, white",
    }
    _brand_palette_str = _BRAND_PALETTE.get(brand, "brand primary colour, accent colour, white")

    image_prompt = await _llm(f"""You are a senior creative director writing Imagen 4 prompts for premium advertising campaigns.

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

        # -- Step C: Generate 3 key visual variations with Imagen 4 -------------------
        image_model = _get_settings().gemini_model_image
        log.info("p2_generate_image_start", model=image_model, n=3)
        await _emit("kv", "running", "Generating 3 key visual variations...")

        response = client.models.generate_images(
            model  = image_model,
            prompt = enriched_prompt,
            config = {"number_of_images": 3, "aspect_ratio": "1:1"},
        )
        if not response.generated_images:
            raise ValueError("Imagen 4 returned no images")

        # Apply brand overlay (logo + headline + brand name + product) to every variation
        _headline_overlay = copy_headline or _extract_headline(big_idea)
        primary_bytes = response.generated_images[0].image.image_bytes  # raw, for channel crops
        images_b64 = []
        for _gi in response.generated_images:
            _overlaid = _apply_brand_overlay(
                _gi.image.image_bytes, brand, _headline_overlay, product_uris, product_name
            )
            images_b64.append(base64.b64encode(_overlaid).decode("utf-8"))
        image_b64 = images_b64[0] if images_b64 else None
        log.info("p2_generate_image_done", n_generated=len(images_b64))

        # Channel adaptations — only for channels selected in the wizard
        primary_bytes = response.generated_images[0].image.image_bytes
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

        await _emit("kv", "step_data", _json2.dumps({"image_b64": image_b64, "images_b64": images_b64}))
        await _asyncio.sleep(5)
        await _emit("kv", "done", f"{len(images_b64)} key visual variations ready")
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
        "images_b64":           images_b64,
        "image_error":          image_error,
        "channel_adaptations":  channel_adaptations,
    }


