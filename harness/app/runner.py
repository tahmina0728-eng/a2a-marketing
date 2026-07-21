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


def _apply_ubs_overlay(
    img_data:     bytes,
    headline:     str,
    product_name: str = "",
    font_dir=None,
) -> bytes:
    """
    UBS Bank full-bleed KV — matches official UBS Instagram / brand style.

    Full-bleed photo background with:
      ├── Semi-transparent white wash behind text for readability
      ├── 4px UBS Red (#E60000) vertical accent line at left margin
      ├── Large regular-weight Frutiger headline (sentence case)
      ├── Smaller sub-copy below if product_name supplied
      └── UBS logo (white box) bottom-right corner
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io as _io
        from pathlib import Path as _P

        UBS_RED   = (230,   0,   0)
        UBS_BLACK = ( 15,  15,  15)
        UBS_GRAY  = ( 89,  89,  89)
        UBS_WHITE = (255, 255, 255)

        Image.MAX_IMAGE_PIXELS = None
        photo = Image.open(_io.BytesIO(img_data)).convert("RGBA")
        if max(photo.size) > 1536:
            sc    = 1536 / max(photo.size)
            photo = photo.resize((int(photo.width * sc), int(photo.height * sc)), Image.LANCZOS)
        W, H = photo.size

        canvas = photo.copy()
        margin  = max(32, int(W * 0.05))
        _fd     = _P(font_dir) if font_dir else None

        def _ubs_font(bold: bool, size: int):
            if _fd and _fd.exists():
                for f in sorted(_fd.glob("*.ttf")):
                    n = f.name.lower()
                    if bold and ("bold" in n or "heavy" in n):
                        try: return ImageFont.truetype(str(f), size)
                        except: pass
                    elif not bold and "bold" not in n and "italic" not in n:
                        try: return ImageFont.truetype(str(f), size)
                        except: pass
            try:    return ImageFont.load_default(size=size)
            except: return ImageFont.load_default()

        hl_clean  = (headline or "UBS Bank").strip()
        red_x     = margin
        text_x    = red_x + 14           # 4px line + 10px gap
        max_txt_w = int(W * 0.38) - text_x

        _tmp = Image.new("RGBA", (1, 1))
        _td  = ImageDraw.Draw(_tmp)

        def _wrap(text, max_w, fnt):
            words, lines, cur = text.split(), [], ""
            for w in words:
                test = (cur + " " + w).strip()
                if (_td.textbbox((0, 0), test, font=fnt)[2]) <= max_w:
                    cur = test
                else:
                    if cur: lines.append(cur)
                    cur = w
            if cur: lines.append(cur)
            return lines or [text]

        # Target: headline fills ~42% of image height — regular weight like the reference
        head_sz = max(36, int(H * 0.092))
        while head_sz > 22:
            hfnt  = _ubs_font(bold=False, size=head_sz)
            lines = _wrap(hl_clean, max_txt_w, hfnt)
            if len(lines) * int(head_sz * 1.32) <= int(H * 0.50):
                break
            head_sz = max(22, int(head_sz * 0.88))

        hfnt    = _ubs_font(bold=False, size=head_sz)
        lines   = _wrap(hl_clean, max_txt_w, hfnt)
        line_h  = int(head_sz * 1.32)
        block_h = len(lines) * line_h

        text_y   = int(H * 0.07)
        sub_gap  = int(head_sz * 0.5)
        sub_h    = (int(head_sz * 0.4) + sub_gap) if product_name else 0
        total_h  = block_h + sub_h

        # Horizontal gradient wash: full opacity at left edge, fades to transparent at right
        # so the model's face on the right side of frame remains unobscured
        wash_pad_r = int(W * 0.06)
        wash_pad_b = int(H * 0.04)
        wash_x2 = text_x + max_txt_w + wash_pad_r
        wash_y1 = max(0, text_y - int(H * 0.04))
        wash_y2 = text_y + total_h + wash_pad_b
        wash_h  = wash_y2 - wash_y1
        wash = Image.new("RGBA", (wash_x2, wash_h), (255, 255, 255, 0))
        _wd = ImageDraw.Draw(wash)
        _steps = 32
        for _s in range(_steps):
            _xa = (_s * wash_x2) // _steps
            _xb = ((_s + 1) * wash_x2) // _steps
            _a  = int(190 * (1.0 - _s / _steps) ** 0.6)
            _wd.rectangle([_xa, 0, _xb, wash_h], fill=(255, 255, 255, _a))
        canvas.alpha_composite(wash, (0, wash_y1))

        draw = ImageDraw.Draw(canvas)

        # Red vertical accent line
        line_top = text_y - int(head_sz * 0.08)
        line_bot = text_y + block_h + int(head_sz * 0.08)
        draw.rectangle([red_x, line_top, red_x + 4, line_bot], fill=(*UBS_RED, 255))

        # Headline — regular weight, dark near-black
        y = text_y
        for line in lines:
            draw.text((text_x, y), line, font=hfnt, fill=(*UBS_BLACK, 255))
            y += line_h

        # Sub-copy — product name below headline
        if product_name:
            sub_sz = max(14, int(head_sz * 0.38))
            sfnt   = _ubs_font(bold=False, size=sub_sz)
            draw.text((text_x, y + sub_gap // 2), product_name,
                      font=sfnt, fill=(*UBS_GRAY, 255))

        # UBS logo — bottom-right corner, white box (matches reference)
        try:
            from app.brand_assets import get_asset_loader as _gal
            _logos = _gal().list_logos("UBS Bank")
            _lpath = next(
                (p for p in _logos if "whiteBG" in p or "whitebg" in p.lower()),
                _logos[0] if _logos else None,
            )
            # Fallback: logo copied alongside the Font folder
            if not _lpath and font_dir:
                _local_logo = _P(font_dir).parent / "Logos" / "ubs-bank-logo.png"
                if _local_logo.exists():
                    _lpath = str(_local_logo)
            if _lpath:
                _lb = (_P(_lpath).read_bytes() if not str(_lpath).startswith("gs://")
                       else __import__("app.creative_pipeline", fromlist=["_load_bytes"])._load_bytes(_lpath))
                _logo = Image.open(_io.BytesIO(_lb)).convert("RGBA")
                max_lw = int(W * 0.20)
                max_lh = int(H * 0.09)
                sc  = min(max_lw / max(1, _logo.width), max_lh / max(1, _logo.height), 1.0)
                lw  = max(60, int(_logo.width  * sc))
                lh2 = max(22, int(_logo.height * sc))
                _logo = _logo.resize((lw, lh2), Image.LANCZOS)
                pad = 12
                lx  = W - lw - pad * 2 - int(W * 0.03)
                ly  = H - lh2 - pad * 2 - int(H * 0.04)
                lbg = Image.new("RGBA", (lw + pad * 2, lh2 + pad * 2), (*UBS_WHITE, 255))
                canvas.alpha_composite(lbg,  (lx, ly))
                canvas.alpha_composite(_logo, (lx + pad, ly + pad))
        except Exception: pass

        result = canvas.convert("RGB")
        buf = _io.BytesIO()
        result.save(buf, format="JPEG", quality=93)
        return buf.getvalue()

    except Exception as _e:
        logger.warning("ubs_overlay_failed", error=str(_e))
        return img_data


def _draw_sunrise_logo_img(height_px: int, font_path: str | None) -> "Image":
    """
    Render the Sunrise telecom logo using Pillow primitives:
    circle ring outline + filled lower semicircle (the sunrise icon) + 'Sunrise' wordmark.
    Returns an RGBA image with transparent background — composite directly, no pill needed.
    """
    from PIL import Image as _PI, ImageDraw as _PID, ImageFont as _PIF

    h = max(28, height_px)
    stroke = max(2, h // 14)   # ~7% stroke — matches reference
    icon = _PI.new("RGBA", (h, h), (0, 0, 0, 0))
    d = _PID.Draw(icon)
    bb = [0, 0, h - 1, h - 1]  # full bbox for both so fill is solid at bottom
    d.ellipse(bb, outline=(255, 255, 255, 255), width=stroke)
    d.chord(bb, start=15, end=165, fill=(255, 255, 255, 255))

    fs = max(12, int(h * 0.72))
    try:
        fnt = _PIF.truetype(font_path, fs) if font_path else _PIF.load_default(size=fs)
        if font_path:
            try:
                fnt.set_variation_by_axes([700])  # Bold weight for the wordmark
            except Exception:
                pass
    except Exception:
        fnt = _PIF.load_default(size=fs)

    _tmp = _PI.new("RGBA", (1, 1))
    _tbb = _PID.Draw(_tmp).textbbox((0, 0), "Sunrise", font=fnt)
    tw, th = _tbb[2] - _tbb[0], _tbb[3] - _tbb[1]
    gap = max(6, int(h * 0.18))
    total_w = h + gap + tw
    total_h = max(h, th + 4)

    logo = _PI.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    logo.paste(icon, (0, (total_h - h) // 2), icon)
    _PID.Draw(logo).text(
        (h + gap - _tbb[0], (total_h - th) // 2 - _tbb[1]),
        "Sunrise", font=fnt, fill=(255, 255, 255, 255),
    )
    return logo


def _apply_brand_overlay(
    img_data:     bytes,
    brand:        str,
    headline:     str,
    product_uris: list,
    product_name: str = "",
    market:       str = "",
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
        # UBS Bank uses its own editorial layout — redirect immediately
        if brand == "UBS Bank":
            _ubs_font_dir = _P(__file__).parent.parent / "bucket" / "brands" / "UBS Bank" / "Font"
            return _apply_ubs_overlay(img_data, headline, product_name, str(_ubs_font_dir))

        BRAND_FONT_PREFS = {
            "Sunglow":     ["Alatsi"],
            "Rnorr":       ["Antonio", "Rubik"],
            "Boozt":       ["Rubik"],
            "Glenfiddich": ["Agrandir", "Aston Martin Flare"],
            "sunrise":     ["Figtree"],
            "Sunrise":     ["Figtree"],
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

        def _font(size: int, weight: int | None = None):
            if font_path:
                try:
                    _fnt = ImageFont.truetype(font_path, size)
                    if brand.lower() in ("sunrise",):
                        try:
                            # Default 300 (Light) for taglines/labels; callers pass an
                            # explicit weight for headline text (lifestyle=700, offer=800).
                            _fnt.set_variation_by_axes([weight if weight is not None else 300])
                        except Exception:
                            pass
                    return _fnt
                except Exception: pass
            try: return ImageFont.load_default(size=size)
            except Exception: return ImageFont.load_default()

        # ── Brand accent colour ───────────────────────────────────────────────
        BRAND_ACCENT = {
            "Sunglow":  (255, 199,  44),
            "Rnorr":    (255, 222,   0),
            "Boozt":    (  0, 134, 254),
            "sunrise":  (218,  41,  28),   # Sunrise Red #DA291C (brand spec §3.4)
            "Sunrise":  (218,  41,  28),
            # Glenfiddich intentionally omitted — chartreuse blends with the AMF1 swirl background
        }
        accent_rgb = BRAND_ACCENT.get(brand, (255, 255, 255))

        # ── 1. Split headline into 2 display lines (sentence-aware) ───────────
        # Group raw words into sentence fragments, then collapse into ≤2 lines.
        raw_words = [w.strip() for w in (headline or "").split() if w.strip()]
        if not raw_words:
            raw_words = [brand.upper()]

        sentences: list = []
        current:   list = []
        for w in raw_words:
            current.append(w)
            if w[-1] in ".!?":
                sentences.append(" ".join(current))
                current = []
        if current:
            sentences.append(" ".join(current))
        if not sentences:
            sentences = [brand.upper()]

        # Collapse into at most 2 display lines
        if len(sentences) > 2:
            mid = len(sentences) // 2
            sentences = [" ".join(sentences[:mid]), " ".join(sentences[mid:])]

        # If still a single long sentence, split at the first comma so the
        # headline always reads as two lines (e.g. "Summer flavor, zero kitchen sweat.")
        if len(sentences) == 1 and "," in sentences[0]:
            _parts = sentences[0].split(",", 1)
            sentences = [_parts[0].strip() + ",", _parts[1].strip()]

        # Final fallback: split at the word-count midpoint for headlines with 2+ words
        # that have no punctuation or comma. Without this, a short headline like
        # "GRENZENLOSE FREIHEIT" stays as one shrunken line instead of two bold lines.
        # Sunrise lifestyle always targets 2 headline lines + tagline = 3 visible lines.
        if len(sentences) == 1 and len(raw_words) >= 2:
            _mid = (len(raw_words) + 1) // 2  # round up — first line gets the extra word
            sentences = [
                " ".join(raw_words[:_mid]),
                " ".join(raw_words[_mid:]),
            ]

        # Auto-fit each line: shrink font until it fits within allowed width.
        # Sunrise uses wider text zone (70%) to match their large-headline campaign style.
        # Sunrise lifestyle headlines: Light (300) — large SIZE carries the impact, not weight.
        # Offer mode: font weight is handled separately in section 6 (ExtraBold 800).
        _measure   = Image.new("RGBA", (1, 1))
        _md        = ImageDraw.Draw(_measure)
        max_line_w = int(W * (0.70 if brand.lower() in ("sunrise",) else 0.55))
        base_sz    = max(44, W // 10)
        lines_spec = []
        for line_text in sentences:
            sz = base_sz
            while sz > 18:
                fnt = _font(sz)  # Light (300) for Sunrise via _font() default
                bb  = _md.textbbox((0, 0), line_text.upper(), font=fnt)
                if (bb[2] - bb[0]) <= max_line_w:
                    break
                sz = max(18, int(sz * 0.88))
            lines_spec.append((line_text.upper(), sz, _font(sz)))

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

        # Place text in the lower third — keeps model faces clear in the upper/mid frame
        # Sunrise: text sits vertically centred in the upper portion (matches Campaign1 refs)
        # Other brands: pushed to lower third so product imagery dominates
        if brand.lower() in ("sunrise",):
            text_y_start = max(margin, min(int(H * 0.28), H - block_h - margin * 2))
        else:
            text_y_start = max(margin, min(int(H * 0.58), H - block_h - margin))
        text_x = margin

        # Offer mode = Sunrise + product selected → product-ad layout (section 6)
        # vs. lifestyle mode → full-bleed photo with text overlay (sections 2-3)
        _sunrise_offer = brand.lower() in ("sunrise",) and bool(product_name)

        # ── 2. Left vignette (Sunrise only, lifestyle mode) ────────────────────
        if brand.lower() in ("sunrise",) and not _sunrise_offer:
            _vig_w = int(W * 0.50)
            _vig   = Image.new("RGBA", (_vig_w, H), (0, 0, 0, 0))
            _vd    = ImageDraw.Draw(_vig)
            for _vx in range(_vig_w):
                _va = int(110 * (1.0 - _vx / _vig_w) ** 1.5)
                _vd.line([(_vx, 0), (_vx, H)], fill=(0, 0, 0, _va))
            img.alpha_composite(_vig, (0, 0))

        # ── 3. Billboard text — lifestyle mode only (offer mode builds own layout) ──
        draw = ImageDraw.Draw(img)
        y = text_y_start
        if not _sunrise_offer:
            for i, (word, fnt, lh, tw) in enumerate(line_data):
                for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1),(0,2),(2,0)]:
                    draw.text((text_x+dx, y+dy), word, font=fnt, fill=(0,0,0,80))
                _all_white = brand.lower() in ("sunrise",)
                color = (255, 255, 255, 255) if _all_white else (
                    (*accent_rgb, 255) if i == 0 and len(line_data) > 1 else (255, 255, 255, 255)
                )
                draw.text((text_x, y), word, font=fnt, fill=color)
                y += lh

            # "DREAM BIG. DO BIG." tagline — lifestyle mode only
            if brand.lower() in ("sunrise",):
                _tg     = "DREAM BIG. DO BIG."
                _tg_sz  = max(16, int(lines_spec[0][1] * 0.30))
                _tg_fnt = _font(_tg_sz, 400)  # Regular (400) — slightly heavier than headline Light
                _tg_y   = y + max(6, int(_tg_sz * 0.30))
                for _dx, _dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
                    draw.text((text_x+_dx, _tg_y+_dy), _tg, font=_tg_fnt, fill=(0,0,0,80))
                draw.text((text_x, _tg_y), _tg, font=_tg_fnt, fill=(255, 255, 255, 200))

        # ── 4. Brand logo — top-right ─────────────────────────────────────────
        try:
            from app.brand_assets import get_asset_loader as _gal
            _logos = _gal().list_logos(brand)
            _bslug = brand.split()[0].lower()
            _primary = (
                next((p for p in _logos if _bslug in p.lower() and "_dark"  in p.lower()), None) or
                next((p for p in _logos if _bslug in p.lower()
                      and not any(k in p.lower() for k in ("_white","_green","_red","_blue","_yellow"))), None) or
                next((p for p in _logos if _bslug in p.lower()), None) or
                next((p for p in _logos if p.lower().endswith(".png")
                      and not any(p.lower().rsplit(".",1)[0].endswith(s)
                                  for s in {"green","red","yellow","orange","purple","blue"})), None) or
                (_logos[0] if _logos else None)
            )

            _logo_img = None
            _use_pill = True  # white pill for raster logos; False = composite directly

            if _primary and str(_primary).lower().endswith(".svg"):
                # SVG can't be opened by Pillow — draw programmatically for known brands
                if brand.lower() in ("sunrise",):
                    _logo_img = _draw_sunrise_logo_img(int(H * 0.10), font_path)
                    _use_pill = False  # white wordmark composited directly on image
            elif _primary:
                _logo_bytes = None
                if not _primary.startswith("gs://"):
                    _logo_bytes = _P(_primary).read_bytes()
                else:
                    try:
                        from app.creative_pipeline import _load_bytes as _clb
                        _logo_bytes = _clb(_primary)
                    except Exception: pass
                if _logo_bytes:
                    _logo_img = Image.open(io.BytesIO(_logo_bytes)).convert("RGBA")

            # Sunrise offer mode: logo belongs in the red bottom strip (section 6), not here
            if _logo_img is not None and not _sunrise_offer:
                max_lw = int(W * (0.26 if not _use_pill else 0.14))
                max_lh = int(H * 0.10)
                sc  = min(max_lw / max(1, _logo_img.width), max_lh / max(1, _logo_img.height), 1.0)
                lw  = max(32, int(_logo_img.width  * sc))
                lh2 = max(32, int(_logo_img.height * sc))
                _logo_img = _logo_img.resize((lw, lh2), Image.LANCZOS)
                lx = W - lw - margin
                # Sunrise: logo vertically centred on the right — matches reference images
                # Other brands: top-right corner
                ly = (H - lh2) // 2 if brand.lower() in ("sunrise",) else margin
                if _use_pill:
                    pad     = max(8, int(lw * 0.18))
                    bg_w    = lw + pad * 2
                    bg_h    = lh2 + pad * 2
                    logo_bg = Image.new("RGBA", (bg_w, bg_h), (0, 0, 0, 0))
                    _lgd    = ImageDraw.Draw(logo_bg)
                    _lgd.rounded_rectangle(
                        [0, 0, bg_w - 1, bg_h - 1],
                        radius=max(6, pad // 2),
                        fill=(255, 255, 255, 210),
                    )
                    lx = W - lw - margin - pad
                    img.paste(logo_bg, (lx, ly), logo_bg)
                    img.paste(_logo_img, (lx + pad, ly + pad), _logo_img)
                else:
                    img.alpha_composite(_logo_img, (lx, ly))
        except Exception as _le:
            logger.debug("logo_skipped", brand=brand, error=str(_le))

        # ── 5. Product label stamp — brand + product name in product zone ────────
        # Placed bottom-right where products sit; guarantees brand name is readable
        # even if the AI model rendered wrong/no text on the packaging.
        # Glenfiddich skipped — logo pill top-right already carries brand identity.
        try:
            if brand in ("Glenfiddich", "sunrise", "Sunrise"):
                raise ValueError("stamp_not_needed")  # logo already composited top-right
            _LABEL_COLORS = {
                "Sunglow":     {"bg": (176,   0, 100, 220), "text": (255, 255, 255), "accent": (255, 199,  44)},
                "Rnorr":       {"bg": (  0,  86,  41, 220), "text": (255, 255, 255), "accent": (255, 222,   0)},
                "Boozt":       {"bg": ( 14,  16,  94, 220), "text": (255, 255, 255), "accent": (  0, 186, 254)},
                # White bg so the stamp always pops against the dark teal/green image
                "Glenfiddich": {"bg": (255, 255, 255, 225), "text": (  6,  75,  71), "accent": (  6,  75,  71)},
                "sunrise":     {"bg": (227,   5,  27, 220), "text": (255, 255, 255), "accent": (255, 255, 255)},
                "Sunrise":     {"bg": (227,   5,  27, 220), "text": (255, 255, 255), "accent": (255, 255, 255)},
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

        # ── 6. Sunrise offer: 4 layout types, one per product plan ──────────────
        # A: Business Dark  — photo + white vignette + dark text + circle badge + logo right
        # B: Pink Gradient  — photo + rose overlay  + white text + big price right + logo left
        # C: Warm Gradient  — photo + warm overlay  + white text + big price left  + logo left
        # D: Sunrise Red    — photo + red overlay   + white text + big price right + logo left
        if _sunrise_offer:
            import re as _re

            _SR      = (218, 41, 28)              # Sunrise Red #DA291C
            _strip_h = max(70, int(H * 0.20))

            # ── Currency / plan label ─────────────────────────────────────────────
            _MARKET_CURRENCY: dict = {
                "switzerland": "CHF", "ch": "CHF",
                "germany": "EUR",     "de": "EUR",
                "austria": "EUR",     "at": "EUR",
                "france": "EUR",      "fr": "EUR",
                "netherlands": "EUR", "nl": "EUR",
                "belgium": "EUR",     "be": "EUR",
                "uk": "GBP",         "united kingdom": "GBP", "gb": "GBP",
                "usa": "USD",        "us": "USD", "united states": "USD",
                "canada": "CAD",     "ca": "CAD",
                "australia": "AUD",  "au": "AUD",
            }
            _SYM_MAP: dict = {"£": "GBP", "€": "EUR", "$": "USD", "fr.": "CHF"}
            _inline = _re.search(
                r'(CHF|EUR|GBP|USD|CAD|AUD|£|€|\$|Fr\.?)\s*(\d{1,4}[.,]\d{2})',
                product_name, _re.IGNORECASE,
            )
            _price_str  = ""
            _plan_label = product_name
            if _inline:
                _amount    = _inline.group(2).replace(",", ".")
                _mk_cur    = _MARKET_CURRENCY.get(market.lower().strip(), "") if market.strip() else ""
                _currency  = _mk_cur if _mk_cur else _SYM_MAP.get(_inline.group(1).lower(), _inline.group(1).upper())
                _price_str = f"{_currency} {_amount}"
                _plan_label = _re.sub(
                    r'(CHF|EUR|GBP|USD|CAD|AUD|£|€|\$|Fr\.?)\s*\d{1,4}[.,]\d{2}.*',
                    "", product_name, flags=_re.IGNORECASE,
                ).strip().rstrip("–-/").strip()
            else:
                _pm2 = _re.search(r'(\d{1,4}[.,]\d{2})', product_name)
                if _pm2:
                    _currency   = _MARKET_CURRENCY.get(market.lower().strip(), "CHF")
                    _price_str  = f"{_currency} {_pm2.group(1).replace(',', '.')}"
                    _plan_label = _re.sub(r'\d{1,4}[.,]\d{2}.*', '', product_name).strip().rstrip("–-/").strip()

            # ── Select layout type by plan name ──────────────────────────────────
            _PLAN_TYPES: dict = {
                "mobile unlimited":  "B",   # Pink gradient  — vibrant consumer mobile
                "easy internet":     "C",   # Warm gradient  — friendly home browsing
                "5g home internet":  "D",   # Red gradient   — bold speed/technology
                "business connect":  "A",   # Business dark  — professional, like Offer1
            }
            _otype = _PLAN_TYPES.get(_plan_label.lower().strip(), "B")

            # ── Full-bleed canvas: AI photo as background ─────────────────────────
            canvas = img.convert("RGBA")
            draw_c = ImageDraw.Draw(canvas)
            _md3   = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

            if _otype == "A":
                # White vignette upper-left so dark headline reads on any photo
                _txt_col = (46, 46, 46, 255)    # #2E2E2E
                _lbl_col = (*_SR, 255)
                _vw, _vh = int(W * 0.65), H - _strip_h
                _vg = Image.new("RGBA", (_vw, _vh), (0, 0, 0, 0))
                _vd = ImageDraw.Draw(_vg)
                for _row in range(_vh):
                    _va = int(115 * (1.0 - _row / _vh) ** 0.65)
                    _vd.line([(0, _row), (_vw, _row)], fill=(255, 255, 255, _va))
                canvas.alpha_composite(_vg, (0, 0))
            else:
                # Coloured gradient overlay left-to-right; white text on top
                _txt_col = (255, 255, 255, 255)
                _lbl_col = (255, 255, 255, 210)
                _GRAD: dict = {
                    "B": (215, 95, 135),    # rose/pink  — Mobile Unlimited
                    "C": (155, 135, 112),   # warm beige — Easy Internet
                    "D": (218,  41,  28),   # Sunrise Red — 5G Home Internet
                }
                _gc   = _GRAD.get(_otype, (155, 135, 112))
                _gw, _gh = int(W * 0.72), H
                _gd   = Image.new("RGBA", (_gw, _gh), (0, 0, 0, 0))
                _gdrw = ImageDraw.Draw(_gd)
                for _gx in range(_gw):
                    _ga = int(210 * (1.0 - _gx / _gw) ** 0.55)
                    _gdrw.line([(_gx, 0), (_gx, _gh)], fill=(*_gc, _ga))
                canvas.alpha_composite(_gd, (0, 0))

            # ── Headline (uniform size/weight across all lines) ───────────────────
            _lm         = max(36, int(W * 0.05))
            _head_max_w = int(W * 0.45)
            _head_sz    = max(20, int(H * 0.115))

            def _tracked_w(text, fnt, tracking):
                total = sum(
                    (_md3.textbbox((0, 0), ch, font=fnt)[2]
                     - _md3.textbbox((0, 0), ch, font=fnt)[0]) + tracking
                    for ch in text
                )
                return max(0, total - tracking)

            def _draw_tracked(drw, xy, text, fnt, fill, tracking):
                x, y = xy
                for ch in text:
                    drw.text((x, y), ch, font=fnt, fill=fill)
                    cb = _md3.textbbox((0, 0), ch, font=fnt)
                    x += (cb[2] - cb[0]) + tracking

            # Pass 1: most-constrained size so all lines match
            _sz_uni = _head_sz
            for _lt in sentences:
                _sz3 = _head_sz
                while _sz3 > 13:
                    _f3 = _font(_sz3)
                    try: _f3.set_variation_by_axes([600])
                    except: pass
                    if _tracked_w(_lt.upper(), _f3, max(1, int(_sz3 * 0.02))) <= _head_max_w:
                        break
                    _sz3 = max(13, int(_sz3 * 0.88))
                _sz_uni = min(_sz_uni, _sz3)

            _fnt_uni = _font(_sz_uni)
            try: _fnt_uni.set_variation_by_axes([600])   # SemiBold — matches reference weight
            except: pass

            _hy = max(40, int(H * 0.08))
            for _lt3 in sentences:
                _bb3 = _md3.textbbox((0, 0), _lt3.upper(), font=_fnt_uni)
                _draw_tracked(draw_c, (_lm, _hy), _lt3.upper(), _fnt_uni,
                              _txt_col, max(1, int(_sz_uni * 0.02)))
                _hy += (_bb3[3] - _bb3[1]) + int(_sz_uni * 0.08)

            # ── Plan label ────────────────────────────────────────────────────────
            _hy += int(H * 0.025)
            _lbl_fnt = _font(max(11, int(H * 0.032)))
            try: _lbl_fnt.set_variation_by_axes([600])
            except: pass
            _lbl_bb3 = _md3.textbbox((0, 0), _plan_label.upper(), font=_lbl_fnt)
            draw_c.text((_lm, _hy), _plan_label.upper(), font=_lbl_fnt, fill=_lbl_col)
            _hy += (_lbl_bb3[3] - _lbl_bb3[1]) + int(H * 0.015)  # advance past label

            # ── Price ─────────────────────────────────────────────────────────────
            if _price_str:
                _pp      = _price_str.split(" ", 1)
                _pr_curr = _pp[0] if len(_pp) > 1 else ""
                _pr_amt  = _pp[1] if len(_pp) > 1 else _price_str

                if _otype == "A":
                    # ── Circle badge (Offer1 / Business Dark style) ───────────────
                    _br   = max(38, int(min(W, H) * 0.13))
                    _bx   = _lm
                    _by   = H - _strip_h - _br * 2 - int(H * 0.025)
                    _bdg  = Image.new("RGBA", (_br * 2, _br * 2), (0, 0, 0, 0))
                    _bdrw = ImageDraw.Draw(_bdg)
                    _bdrw.ellipse(
                        [0, 0, _br * 2 - 1, _br * 2 - 1],
                        fill=(255, 255, 255, 255),
                        outline=(185, 185, 185, 255), width=max(1, _br // 22),
                    )
                    canvas.alpha_composite(_bdg, (_bx, _by))
                    _amt_fnt  = _font(max(10, int(_br * 0.50)))
                    try: _amt_fnt.set_variation_by_axes([700])
                    except: pass
                    _cur_fnt  = _font(max(7, int(_br * 0.24)))
                    _amt_bb   = draw_c.textbbox((0, 0), _pr_amt,  font=_amt_fnt)
                    _cur_bb   = draw_c.textbbox((0, 0), _pr_curr, font=_cur_fnt) if _pr_curr else (0, 0, 0, 0)
                    _badge_th = (_amt_bb[3]-_amt_bb[1]) + ((_cur_bb[3]-_cur_bb[1]+3) if _pr_curr else 0)
                    _ty = _by + _br - _badge_th // 2
                    _dk = (46, 46, 46, 255)
                    if _pr_curr:
                        _lx = _bx + _br - (_cur_bb[2]-_cur_bb[0]) // 2 - _cur_bb[0]
                        draw_c.text((_lx, _ty - _cur_bb[1]), _pr_curr, font=_cur_fnt, fill=_dk)
                        _ty += (_cur_bb[3]-_cur_bb[1]) + 3
                    _ax = _bx + _br - (_amt_bb[2]-_amt_bb[0]) // 2 - _amt_bb[0]
                    draw_c.text((_ax, _ty - _amt_bb[1]), _pr_amt, font=_amt_fnt, fill=_dk)

                else:
                    # ── Dark circle price badge (Types B/C/D) ─────────────────────────
                    # Same badge style as Type A but right-aligned, so it clears the logo
                    _br   = max(38, int(min(W, H) * 0.13))
                    _bx   = W - _lm - _br * 2   # right side
                    _by   = H - _strip_h - _br * 2 - int(H * 0.025)
                    _bdg  = Image.new("RGBA", (_br * 2, _br * 2), (0, 0, 0, 0))
                    _bdrw = ImageDraw.Draw(_bdg)
                    _bdrw.ellipse(
                        [0, 0, _br * 2 - 1, _br * 2 - 1],
                        fill=(255, 255, 255, 245),
                    )
                    canvas.alpha_composite(_bdg, (_bx, _by))
                    _amt_fnt  = _font(max(10, int(_br * 0.50)))
                    try: _amt_fnt.set_variation_by_axes([700])
                    except: pass
                    _cur_fnt  = _font(max(7, int(_br * 0.24)))
                    _amt_bb   = _md3.textbbox((0, 0), _pr_amt,  font=_amt_fnt)
                    _cur_bb   = _md3.textbbox((0, 0), _pr_curr, font=_cur_fnt) if _pr_curr else (0, 0, 0, 0)
                    _badge_th = (_amt_bb[3]-_amt_bb[1]) + ((_cur_bb[3]-_cur_bb[1]+3) if _pr_curr else 0)
                    _ty = _by + _br - _badge_th // 2
                    _dk = (46, 46, 46, 255)
                    if _pr_curr:
                        _lx = _bx + _br - (_cur_bb[2]-_cur_bb[0]) // 2 - _cur_bb[0]
                        draw_c.text((_lx, _ty - _cur_bb[1]), _pr_curr, font=_cur_fnt, fill=_dk)
                        _ty += (_cur_bb[3]-_cur_bb[1]) + 3
                    _ax = _bx + _br - (_amt_bb[2]-_amt_bb[0]) // 2 - _amt_bb[0]
                    draw_c.text((_ax, _ty - _amt_bb[1]), _pr_amt, font=_amt_fnt, fill=_dk)

            # ── Red footer strip ──────────────────────────────────────────────────
            draw_c.rectangle([0, H - _strip_h, W, H], fill=(*_SR, 255))

            # ── Sunrise logo ─────────────────────────────────────────────────────────
            # Reference layout: circle ~90% of footer height; filled S-arc (bottom ~37%)
            # sits inside the red strip; outline-only top 63% peeks above footer border.
            # "Sunrise" text to the RIGHT of circle; "BUSINESS" below it (Type A only).
            _logo_mg = max(40, int(W * 0.08))
            _ic_d2   = max(36, int(_strip_h * 0.90))
            _ic_cx   = (_logo_mg + _ic_d2 // 2) if _otype != "A" else (W - _logo_mg - _ic_d2 // 2)

            _ic_img2 = Image.new("RGBA", (_ic_d2, _ic_d2), (0, 0, 0, 0))
            _ic_drw2 = ImageDraw.Draw(_ic_img2)
            _ic_stk2 = max(2, _ic_d2 // 14)
            _ic_bb2  = [0, 0, _ic_d2-1, _ic_d2-1]
            _ic_drw2.ellipse(_ic_bb2, outline=(255, 255, 255, 255), width=_ic_stk2)
            _ic_drw2.chord(_ic_bb2, start=15, end=165, fill=(255, 255, 255, 255))
            _ic_x2 = _ic_cx - _ic_d2 // 2
            # chord (start=15,end=165) is at 63% from circle top — place it at footer top edge
            # so the filled S-arc sits entirely inside the red strip
            _ic_y2 = H - _strip_h - int(_ic_d2 * 0.63)
            canvas.alpha_composite(_ic_img2, (max(0, _ic_x2), max(0, _ic_y2)))

            # "Sunrise" wordmark — centred BELOW the circle inside the red strip
            _wm_sz   = max(11, int(_strip_h * 0.38))
            _wm_fnt2 = _font(_wm_sz)
            try: _wm_fnt2.set_variation_by_axes([700])
            except: pass
            _wm_bb2     = _md3.textbbox((0, 0), "Sunrise", font=_wm_fnt2)
            _wm_w2      = _wm_bb2[2] - _wm_bb2[0]
            _wm_h2      = _wm_bb2[3] - _wm_bb2[1]
            _circle_bot = _ic_y2 + _ic_d2                          # bottom of circle (inside footer)
            _wm_gap     = max(3, int(_ic_d2 * 0.05))               # small gap between circle and text
            _wm_x2      = _ic_cx - _wm_w2 // 2 - _wm_bb2[0]       # horizontally centred on circle
            _wm_y2      = _circle_bot + _wm_gap - _wm_bb2[1]       # just below circle bottom

            if _otype == "A":
                # Type A: "Sunrise" + "BUSINESS" stacked below circle, both centred
                _sub_sz  = max(7, int(_wm_sz * 0.42))
                _sub_fnt = _font(_sub_sz)
                try: _sub_fnt.set_variation_by_axes([400])
                except: pass
                _sub_bb  = _md3.textbbox((0, 0), "BUSINESS", font=_sub_fnt)
                _sub_w   = _sub_bb[2] - _sub_bb[0]
                _sub_gap = max(2, int(_wm_sz * 0.08))
                draw_c.text((_wm_x2, _wm_y2), "Sunrise", font=_wm_fnt2, fill=(255, 255, 255, 255))
                _sub_x = _ic_cx - _sub_w // 2 - _sub_bb[0]
                _sub_y = _circle_bot + _wm_gap + _wm_h2 + _sub_gap - _sub_bb[1]
                draw_c.text((_sub_x, _sub_y), "BUSINESS", font=_sub_fnt, fill=(255, 255, 255, 210))
            else:
                # B/C/D: "Sunrise" to the right of circle, centred in footer strip
                draw_c.text((_wm_x2, _wm_y2), "Sunrise", font=_wm_fnt2, fill=(255, 255, 255, 255))

            img = canvas
            logger.info("sunrise_offer_layout_applied",
                        product=product_name, price=_price_str, layout=_otype)

        result = img.convert("RGB")
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=93)
        logger.info("brand_overlay_applied", brand=brand, lines=len(raw_words), W=W, H=H)
        return buf.getvalue()

    except Exception as e:
        logger.warning("brand_overlay_failed", brand=brand, error=str(e))
        return img_data


# ── Copy text lower-third overlay for Veo reels ──────────────────────────────

def _overlay_copy_text_on_video(
    video_bytes: bytes,
    brand: str,
    headline: str,
    cta: str = "",
    start_sec: float = 3.5,
) -> bytes:
    """
    Burn the copy agent's headline (and optional CTA) as a lower-third onto the
    reel using FFmpeg.

    start_sec controls when the text fades in:
    - Full pipeline default: 3.5s (text rides alongside the closing voiceover)
    - Standalone: 4.5s (text appears AFTER the voiceover finishes, as an end card)

    Falls back gracefully (returns original bytes untouched) if:
    - FFmpeg is not installed (dev machines), or
    - Any encoding error occurs.
    """
    import shutil, subprocess, tempfile, re as _re
    from pathlib import Path as _P

    if not shutil.which("ffmpeg"):
        logger.warning("reel_text_overlay_skipped", reason="ffmpeg not found")
        return video_bytes
    if not headline:
        return video_bytes

    # ── Pick brand font (TTF) ────────────────────────────────────────────────
    _font_dir = _P(__file__).parent.parent / "bucket" / "brands" / brand / "Font"
    _ttf = None
    if _font_dir.is_dir():
        # Prefer regular/non-italic, non-bold first for headline readability
        _ttf = next((str(f) for f in sorted(_font_dir.glob("*.ttf"))
                     if "italic" not in f.name.lower() and "bold" not in f.name.lower()), None)
        if not _ttf:  # any TTF is fine as fallback
            _ttf = next((str(f) for f in sorted(_font_dir.glob("*.ttf"))), None)
    # Final fallback: Liberation Sans installed via fonts-liberation in Docker
    if not _ttf:
        for _sys_font in [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            if _P(_sys_font).exists():
                _ttf = _sys_font
                break

    if not _ttf:
        logger.warning("reel_text_overlay_no_font", brand=brand)
        return video_bytes

    def _esc(text: str) -> str:
        """Escape text for FFmpeg drawtext: colon, single quote, backslash."""
        return (text.replace("\\", "\\\\")
                    .replace("'", "'\\''")
                    .replace(":", "\\:"))

    _hl  = _esc(headline[:80])
    _cta = _esc(cta[:40]) if cta else ""

    try:
        with tempfile.TemporaryDirectory() as _tmp:
            _in  = _P(_tmp) / "input.mp4"
            _out = _P(_tmp) / "output.mp4"
            _in.write_bytes(video_bytes)

            # Copy font to temp dir as "font.ttf" — a relative name with no
            # path separators or Windows drive colon.  FFmpeg is launched with
            # cwd=_tmp so "font.ttf" resolves correctly without any absolute
            # path in the drawtext filter (Windows drive-letter colons such as
            # "C:" are mis-parsed as option separators by FFmpeg's filtergraph
            # parser even inside single-quoted values).
            _font_tmp = _P(_tmp) / "font.ttf"
            _font_tmp.write_bytes(_P(_ttf).read_bytes())

            # Commas inside FFmpeg expressions (enable=, alpha=) must be
            # escaped as \, at the filtergraph level — single-quoting alone
            # is unreliable on Windows FFmpeg builds.
            # Input/output use plain relative filenames so no path issues.
            _t0  = start_sec            # headline fade-in start
            _t1  = round(_t0 + 0.5, 1) # headline fully opaque
            _t2  = round(_t0 + 0.3, 1) # cta fade-in start (offset)
            _t3  = round(_t2 + 0.3, 1) # cta fully opaque
            _headline_filter = (
                f"drawtext=fontfile=font.ttf:text='{_hl}':"
                f"fontsize=40:fontcolor=white:"
                f"x=60:y=H-{140 if _cta else 100}:"
                f"enable=between(t\\,{_t0}\\,6):"
                f"alpha=if(lt(t\\,{_t1})\\,(t-{_t0})/0.5\\,1):"
                f"box=1:boxcolor=black@0.55:boxborderw=18"
            )
            _filters = _headline_filter

            if _cta:
                _cta_filter = (
                    f"drawtext=fontfile=font.ttf:text='{_cta}':"
                    f"fontsize=26:fontcolor=white@0.85:"
                    f"x=60:y=H-85:"
                    f"enable=between(t\\,{_t2}\\,6):"
                    f"alpha=if(lt(t\\,{_t3})\\,(t-{_t2})/0.3\\,1):"
                    f"box=1:boxcolor=black@0.40:boxborderw=12"
                )
                _filters = f"{_headline_filter},{_cta_filter}"

            _result = subprocess.run(
                ["ffmpeg", "-y", "-i", "input.mp4",
                 "-vf", _filters,
                 "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                 "-c:a", "copy",
                 "output.mp4"],
                capture_output=True, timeout=120,
                cwd=_tmp,   # all relative paths resolve against the temp dir
            )
            if _result.returncode != 0 or not _out.exists():
                logger.warning("reel_text_overlay_failed", brand=brand,
                               stderr=_result.stderr.decode(errors="ignore")[-400:])
                return video_bytes
            logger.info("reel_text_overlay_applied", brand=brand, headline=headline[:40])
            return _out.read_bytes()
    except Exception as e:
        logger.warning("reel_text_overlay_error", brand=brand, error=str(e))
        return video_bytes


def _overlay_logo_end_card(
    video_bytes: bytes,
    brand: str,
    start_sec: float = 4.2,
) -> bytes:
    """
    Overlay the brand logo as a frosted bottom-right card for the final
    ~1.8 seconds of the reel (start_sec → 6s), with a 0.4s fade-in.

    Uses FFmpeg's overlay filter with a pre-built RGBA logo card saved to
    the temp dir — no absolute paths so the Windows drive-colon issue that
    affects drawtext doesn't apply here.  Falls back to the original bytes
    on any error (missing ffmpeg, missing logo, etc.).
    """
    import shutil, subprocess, tempfile
    from pathlib import Path as _P

    if not shutil.which("ffmpeg"):
        return video_bytes

    try:
        from io import BytesIO
        from PIL import Image as _PIL, ImageDraw as _Draw
        from app.brand_assets import get_asset_loader
        from app.creative_pipeline import _load_bytes

        loader = get_asset_loader()
        logos  = loader.list_logos(brand)
        if not logos:
            return video_bytes

        # Prefer a logo without a white background (transparent PNG); fall back
        # to whitebg variant only if nothing else exists.
        logo_uri = next(
            (p for p in logos if "whitebg" not in p.lower()),
            logos[0],
        )
        logo_bytes = _load_bytes(logo_uri)
        if not logo_bytes:
            return video_bytes

        # White pill card — standard brand end-card treatment (white background,
        # logo centred, thin border so it's visible on both dark and light video
        # backgrounds). White works for all logos whether the source has a white
        # or transparent background.
        card_w, card_h = 340, 100
        card = _PIL.new("RGB", (card_w, card_h), (255, 255, 255))
        _Draw.Draw(card).rounded_rectangle(
            [0, 0, card_w - 1, card_h - 1],
            radius=20, fill=(255, 255, 255), outline=(220, 220, 228), width=2,
        )
        logo = _PIL.open(BytesIO(logo_bytes)).convert("RGBA")
        # Flatten onto white so any transparent logo areas become white
        white_bg = _PIL.new("RGBA", logo.size, (255, 255, 255, 255))
        white_bg.alpha_composite(logo)
        logo = white_bg.convert("RGB")
        max_lw, max_lh = card_w - 40, card_h - 28
        sc  = min(max_lw / max(1, logo.width), max_lh / max(1, logo.height), 1.0)
        lw  = max(32, int(logo.width * sc))
        lh  = max(32, int(logo.height * sc))
        logo = logo.resize((lw, lh), _PIL.LANCZOS)
        # Paste directly (both RGB now, no alpha needed)
        x0  = (card_w - lw) // 2
        y0  = (card_h - lh) // 2
        card.paste(logo, (x0, y0))

        with tempfile.TemporaryDirectory() as _tmp:
            _in  = _P(_tmp) / "input.mp4"
            _out = _P(_tmp) / "output.mp4"
            _in.write_bytes(video_bytes)

            # Save as RGB PNG — no alpha channel so the overlay is fully opaque.
            # The fade filter fades from black (luminance fade), which looks clean
            # on a dark card and doesn't require alpha compositing in FFmpeg.
            card_path = _P(_tmp) / "logo_card.png"
            card.convert("RGB").save(str(card_path), format="PNG")

            _t0 = start_sec
            _fc = (
                f"[1:v]scale={card_w}:{card_h},"
                f"fade=t=in:st={_t0}:d=0.4[fcard];"
                f"[0:v][fcard]overlay=W-w-24:H-h-24:"
                f"enable=between(t\\,{_t0}\\,6)"
            )

            _result = subprocess.run(
                ["ffmpeg", "-y",
                 "-i", "input.mp4",
                 "-i", "logo_card.png",
                 "-filter_complex", _fc,
                 "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                 "-c:a", "copy",
                 "output.mp4"],
                capture_output=True, timeout=120,
                cwd=_tmp,
            )
            if _result.returncode != 0 or not _out.exists():
                logger.warning("reel_logo_overlay_failed", brand=brand,
                               stderr=_result.stderr.decode(errors="ignore")[-300:])
                return video_bytes
            logger.info("reel_logo_overlay_applied", brand=brand)
            return _out.read_bytes()

    except Exception as e:
        logger.warning("reel_logo_overlay_error", brand=brand, error=str(e))
        return video_bytes


def _overlay_reel(
    video_bytes: bytes,
    brand: str,
    headline: str,
    cta: str = "",
    text_start_sec: float = 3.5,
    logo_start_sec: float = 4.2,
) -> bytes:
    """
    Single FFmpeg pass: text lower-third + brand logo end-card on the reel.

    Combines what was previously two separate passes (_overlay_copy_text_on_video
    + _overlay_logo_end_card) into one filter_complex call so neither operation
    overwrites the other.  Logo card uses dark navy pill with pixel-level recolouring
    (white bg → transparent, black symbol → white, coloured text → kept) so
    brand logos look correct on the dark card regardless of source variant.
    """
    import shutil, subprocess, tempfile, os
    from pathlib import Path as _P

    if not shutil.which("ffmpeg") or not headline:
        return video_bytes

    try:
        from io import BytesIO
        from PIL import Image as _PIL, ImageDraw as _Draw
        from app.brand_assets import get_asset_loader
        from app.creative_pipeline import _load_bytes

        # ── Font ─────────────────────────────────────────────────────────────
        _font_dir = _P(__file__).resolve().parent.parent / "bucket" / "brands" / brand / "Font"
        _ttf = None
        if _font_dir.is_dir():
            _ttf = next((str(f) for f in sorted(_font_dir.glob("*.ttf"))
                         if "italic" not in f.name.lower() and "bold" not in f.name.lower()), None) \
                or next((str(f) for f in sorted(_font_dir.glob("*.ttf"))), None)
        if not _ttf:
            for _wf in [r"C:\Windows\Fonts\arial.ttf",
                        r"C:\Windows\Fonts\calibri.ttf",
                        r"C:\Windows\Fonts\segoeui.ttf"]:
                if os.path.exists(_wf):
                    _ttf = _wf
                    break

        # ── Logo (no background card — overlay raw PNG directly with alpha) ──────
        # The dark pill card was distracting. Brands like Rnorr/Sunglow/Boozt have
        # transparent logos that look cleaner composited straight onto the video.
        # FFmpeg overlay with format=auto handles the alpha channel correctly.
        _logo_bytes_raw = None
        _logo_w = 200   # target width on video; height scales proportionally
        try:
            loader = get_asset_loader()
            logos  = loader.list_logos(brand)
            if logos:
                def _pick_logo(ps):
                    _bslug = brand.split()[0].lower()
                    return (
                        next((p for p in ps if _bslug in p.lower() and "_dark" in p.lower()), None) or
                        next((p for p in ps if _bslug in p.lower()
                              and not any(k in p.lower() for k in ("_white","_green","_red","_blue","_yellow"))), None) or
                        next((p for p in ps if _bslug in p.lower()), None) or
                        next((p for p in ps if p.lower().endswith(".png")
                              and not any(p.lower().rsplit(".",1)[0].endswith(s)
                                          for s in {"green","red","yellow","orange","purple","blue"})), None) or
                        ps[0]
                    )
                _logo_bytes_raw = _load_bytes(_pick_logo(logos))
        except Exception as _le:
            logger.warning("reel_logo_load_failed", brand=brand, error=str(_le))

        def _esc(s: str) -> str:
            return s.replace("\\","\\\\").replace("'","\\'").replace(":","\\:")

        def _wrap(text: str, max_chars: int = 40) -> tuple[str, str]:
            """Split text into two lines at a word boundary near max_chars."""
            text = text.strip()
            if len(text) <= max_chars:
                return text, ""
            idx = text.rfind(" ", 0, max_chars)
            if idx == -1:
                idx = max_chars
            return text[:idx].strip(), text[idx:].strip()

        with tempfile.TemporaryDirectory() as _tmp:
            _in  = _P(_tmp) / "input.mp4"
            _out = _P(_tmp) / "output.mp4"
            _in.write_bytes(video_bytes)

            _font_arg = None
            if _ttf:
                _ft = _P(_tmp) / "font.ttf"
                _ft.write_bytes(_P(_ttf).read_bytes())
                _font_arg = "font.ttf"

            if _logo_bytes_raw:
                _lc = _P(_tmp) / "logo.png"
                _lc.write_bytes(_logo_bytes_raw)

            # Build filters — headline wraps to 2 lines, CTA on third line
            _t0, _t1 = text_start_sec, round(text_start_sec + 0.5, 1)
            _t2, _t3 = round(text_start_sec + 0.3, 1), round(text_start_sec + 0.6, 1)

            _txt_f = None
            if _font_arg:
                _line1, _line2 = _wrap(headline[:80])
                _hl1 = _esc(_line1)
                _has_two_lines = bool(_line2)
                # y positions shift up when we have 2 headline lines
                _y1 = "H-170" if (_has_two_lines and cta) else ("H-145" if _has_two_lines else ("H-120" if cta else "H-90"))
                _y2 = "H-125" if cta else "H-90"
                _yc = "H-80"

                _txt_f = (
                    f"drawtext=fontfile={_font_arg}:text='{_hl1}':"
                    f"fontsize=36:fontcolor=white:x=60:y={_y1}:"
                    f"enable=between(t\\,{_t0}\\,6):"
                    f"alpha=if(lt(t\\,{_t1})\\,(t-{_t0})/0.5\\,1):"
                    f"box=1:boxcolor=black@0.55:boxborderw=16"
                )
                if _has_two_lines:
                    _hl2 = _esc(_line2[:80])
                    _txt_f += (
                        f",drawtext=fontfile={_font_arg}:text='{_hl2}':"
                        f"fontsize=36:fontcolor=white:x=60:y={_y2}:"
                        f"enable=between(t\\,{_t0}\\,6):"
                        f"alpha=if(lt(t\\,{_t1})\\,(t-{_t0})/0.5\\,1):"
                        f"box=1:boxcolor=black@0.55:boxborderw=16"
                    )
                if cta:
                    _ct = _esc(cta[:50])
                    _txt_f += (
                        f",drawtext=fontfile={_font_arg}:text='{_ct}':"
                        f"fontsize=24:fontcolor=white@0.85:x=60:y={_yc}:"
                        f"enable=between(t\\,{_t2}\\,6):"
                        f"alpha=if(lt(t\\,{_t3})\\,(t-{_t2})/0.3\\,1):"
                        f"box=1:boxcolor=black@0.40:boxborderw=12"
                    )

            # format=auto on overlay lets FFmpeg use the PNG alpha channel so
            # the logo composites directly onto the video with no background card
            if _logo_bytes_raw and _txt_f:
                _fc  = (f"[0:v]{_txt_f}[txt];"
                        f"[1:v]scale={_logo_w}:-1[logo];"
                        f"[txt][logo]overlay=W-w-24:24:format=auto:"
                        f"enable=between(t\\,{logo_start_sec}\\,6)[vout]")
                _cmd = ["ffmpeg","-y","-i","input.mp4","-i","logo.png",
                        "-filter_complex",_fc,"-map","[vout]","-map","0:a?",
                        "-c:v","libx264","-preset","fast","-crf","20","-c:a","copy","output.mp4"]
            elif _logo_bytes_raw:
                _fc  = (f"[1:v]scale={_logo_w}:-1[logo];"
                        f"[0:v][logo]overlay=W-w-24:24:format=auto:"
                        f"enable=between(t\\,{logo_start_sec}\\,6)[vout]")
                _cmd = ["ffmpeg","-y","-i","input.mp4","-i","logo.png",
                        "-filter_complex",_fc,"-map","[vout]","-map","0:a?",
                        "-c:v","libx264","-preset","fast","-crf","20","-c:a","copy","output.mp4"]
            elif _txt_f:
                _cmd = ["ffmpeg","-y","-i","input.mp4","-vf",_txt_f,
                        "-c:v","libx264","-preset","fast","-crf","20","-c:a","copy","output.mp4"]
            else:
                return video_bytes

            _r = subprocess.run(_cmd, capture_output=True, timeout=120, cwd=_tmp)
            if _r.returncode == 0 and _out.exists():
                logger.info("reel_overlay_applied", brand=brand)
                return _out.read_bytes()
            logger.warning("reel_overlay_failed", brand=brand,
                           stderr=_r.stderr.decode(errors="ignore")[-400:])
            return video_bytes

    except Exception as e:
        logger.warning("reel_overlay_error", brand=brand, error=str(e))
        return video_bytes


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
    copy_cta: str = "",
    reasoning_model: str = "gemini-3.5-flash",
    language: str = "",
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
                f"An athlete refreshing with a cold can of {p} after a workout, "
                f"condensation droplets rolling down the can in slow motion under cool blue studio light. "
                f"The {p} can gleams in the foreground against a deep navy background. "
                f"Deep midnight navy and electric cobalt blue brand colours, clean reflective light."
            )
        else:  # Original Energy, default
            return (
                f"A confident young professional opening a can of {p} in a modern urban setting, "
                f"cobalt blue light reflecting off the condensation-covered can as they take a refreshing sip. "
                f"The {p} can displayed prominently in foreground under dramatic studio lighting. "
                f"Deep midnight navy and cobalt blue brand colours, energetic and clean atmosphere."
            )

    def _glenfiddich_scene(p: str) -> str:
        return (
            f"A sophisticated man in a dark green blazer stands in a moody bar interior, "
            f"picking up a glass of {p} as amber liquid catches warm candlelight. "
            f"A teal-and-chartreuse Glenfiddich AMF1 bottle gleams prominently in the foreground. "
            f"Slow cinematic dolly push-in, bokeh highlights, deep teal and chartreuse brand palette. "
            f"Premium Scotch whisky advertising quality — elegant, restrained, confident."
        )

    def _sunrise_scene(p: str) -> str:
        _pl = (p or "").lower()
        if any(x in _pl for x in ["business", "enterprise", "b2b", "sme", "office"]):
            return (
                f"A confident Swiss professional in a sleek modern office switches seamlessly between "
                f"a video call on their laptop and a {p}-powered smartphone without missing a beat. "
                f"Floor-to-ceiling windows reveal a crisp Zurich skyline in golden morning light. "
                f"Clean white interior, Sunrise Red accents, Swiss precision, dynamic energy — "
                f"the network disappears so the work can breathe."
            )
        elif any(x in _pl for x in ["home", "internet", "tv", "fiber", "fibre", "broadband", "wifi"]):
            return (
                f"A warm Swiss family evening — a parent video-calling grandparents on a tablet in the kitchen "
                f"while children stream on the TV in the living room, all seamlessly on {p}. "
                f"Cosy modern Swiss apartment, soft amber light, the connection just works. "
                f"Sunrise Red router glowing quietly, clean white and red palette, genuine human warmth."
            )
        else:
            return (
                f"A young Swiss professional strides confidently through Zurich's old town, "
                f"phone in hand — a video call staying crystal-clear as they move through the crowd and under archways. "
                f"Cobblestones and modern glass side by side, Sunrise Red on their jacket, "
                f"warm human connection, Swiss urban energy, the signal never drops."
            )

    _BRAND_SCENE_FN = {
        "Sunglow":     _sunglow_scene,
        "Rnorr":       _rnorr_scene,
        "Boozt":       _boozt_scene,
        "Glenfiddich": _glenfiddich_scene,
        "sunrise":     _sunrise_scene,
        "Sunrise":     _sunrise_scene,
    }
    brand_scene = _BRAND_SCENE_FN[brand](_prod) if brand in _BRAND_SCENE_FN \
        else f"A premium advertising scene featuring {_prod} with dynamic energy and brand colours."

    # ── Season/occasion visual overlay ────────────────────────────────────────
    # Appended to brand_scene so every brand gets the right festive/seasonal
    # ambiance regardless of whether it has a bespoke scene template above.
    def _season_mod(s: str) -> str:
        _s = s.lower()
        if any(k in _s for k in ("christmas", "xmas", "festive", "advent")):
            return (
                "Set within a warm Christmas ambiance: soft golden fairy lights "
                "draped in the background, delicate snowflakes catching the light, "
                "subtle holly and red-ribbon accents — premium and elegant, never kitschy. "
                "The colour palette blends the brand's own hues with deep crimson and gold."
            )
        if any(k in _s for k in ("diwali", "deepavali")):
            return (
                "Diwali setting: glowing diyas in the background, golden rangoli patterns "
                "on the surface, rich jewel-toned fabric — vibrant, celebratory, premium."
            )
        if "valentine" in _s:
            return (
                "Valentine's Day mood: warm soft-focus rose petals, gentle pink and "
                "rose-gold accents, romantic candlelight glow in the background."
            )
        if "easter" in _s:
            return (
                "Easter spring setting: pastel colour palette, soft natural morning light, "
                "delicate blossoms and fresh greenery in the background."
            )
        if "new year" in _s:
            return (
                "New Year celebration: golden confetti trails, champagne bubble bokeh, "
                "midnight countdown energy — joyful, dynamic, aspirational."
            )
        if "spring" in _s:
            return "Spring golden-hour light, fresh blossoms, vibrant greens, renewal energy."
        if "summer" in _s:
            return "Bright summer sunlight, vivid saturated colours, outdoor warmth, sun-kissed atmosphere."
        if "autumn" in _s or "fall" in _s:
            return "Rich autumn palette: warm amber and copper tones, drifting leaves, cosy golden light."
        if "winter" in _s:
            return "Crisp winter atmosphere: cool blue tones, frosted surfaces, warm contrast accent lighting."
        return ""

    # ── Festive scene REPLACEMENT (not append) ────────────────────────────────
    # When a festive/seasonal occasion is active, REPLACE the entire brand scene
    # so the Veo prompt leads with the festive context. Appending (the old approach)
    # meant Veo focused on the base "boiling pot / hair flip / can" scene and treated
    # Christmas/Diwali as an afterthought, producing plain product shots.
    import random as _rnd_r
    def _reel_festive_scene(b: str, s: str, p: str):
        _sl = s.lower()
        _xmas  = any(k in _sl for k in ("christmas","xmas","festive","advent"))
        _diwali = any(k in _sl for k in ("diwali","deepavali"))
        _ny     = "new year" in _sl
        _val    = "valentine" in _sl
        _easter = "easter" in _sl
        _summer = "summer" in _sl
        if not any([_xmas, _diwali, _ny, _val, _easter, _summer]):
            return None
        _scenes = {
            "Rnorr": {
                "xmas": _rnd_r.choice([
                    f"A warm multi-generational family of 4-5 gathered joyfully around a beautifully set Christmas dinner table — the mother proudly serves a steaming festive feast made with {p}. Decorated Christmas tree behind them, golden fairy lights overhead, holly centrepiece, children in Christmas sweaters laughing. {p} pack visible on the counter. Deep forest green and gold, warm amber candlelight, snow outside the window.",
                    f"A parent and two excited children (ages 5 and 8) cooking the Christmas feast together — adding {p} to a bubbling pot while Christmas music plays, steam rising dramatically. Christmas cards on the mantle, fairy lights twinkling in the window, festive aprons. Deep green and red palette, genuine family magic.",
                ]),
                "diwali": f"A South Asian family of 5 gathered around a Diwali feast — the mother serving a rich dish made with {p} to excited children and grandparents in traditional festive attire. Diyas glowing everywhere, marigold garlands, rangoli patterns on the floor. Warm golden diya light, {p} pack on the counter. Vibrant jewel tones and gold.",
                "ny":     f"A couple and friends celebrating New Year's Eve with a glamorous dinner — {p} the hero ingredient in the centrepiece dish. Champagne glasses raised, city lights through the window, countdown energy. {p} pack on the kitchen island, deep green and gold NYE palette.",
                "val":    f"A couple cooking a romantic Valentine's dinner together by candlelight — {p} being stirred lovingly into a bubbling pot, red roses on the counter. Warm rose and deep green palette, intimate and genuinely delicious.",
                "easter": f"A family with young children making a bright Easter Sunday lunch — {p} in a pot on the stove, Easter eggs and spring flowers on the table, pastel colours and natural light. Joyful and warm.",
                "summer": f"A group of friends hosting a sunny outdoor summer garden party — the hero cook serves a sizzling dish made with {p} at a table loaded with fresh summer produce. Golden afternoon light, garden flowers, laughter and vibrant energy.",
            },
            "Sunglow": {
                "xmas": _rnd_r.choice([
                    f"Three diverse women (20-35) getting glamorous together for Christmas night, doing each other's hair in front of a beautifully decorated Christmas tree — {p} bottles on the vanity, golden fairy lights reflecting in their shiny hair, laughing with festive joy. Deep magenta-pink and Christmas gold palette.",
                    f"A mother and teenage daughter styling each other's hair on Christmas morning — gifts around the tree, fairy lights in the window, {p} bottle between them. Warm golden light, slow-motion hair flip catching the festive glow. Magenta-pink and gold.",
                ]),
                "diwali": f"Three South Asian women in jewel-toned traditional outfits getting ready for Diwali together, doing each other's hair amid glowing diyas and marigold garlands — {p} bottles prominent, hair FLYING in slow motion catching warm golden diya light. Rich vibrant festive palette.",
                "ny":     f"Four women getting glamorous for New Year's Eve together — sequined outfits, champagne flutes on the vanity, {p} products centre-stage, golden confetti beginning to fall. Hair FLYING, pure NYE euphoria.",
                "val":    f"A woman styling her hair with {p} for a Valentine's date — roses on the dressing table, soft rose-gold candlelight, slow-motion hair flip with pink bokeh and petals falling around her.",
                "summer": f"Three women at an outdoor summer festival laughing with hair flying in the warm breeze — {p} products on the picnic blanket, sunshine yellow and magenta palette, golden hour hair flip.",
            },
            "Boozt": {
                "xmas": _rnd_r.choice([
                    f"A group of 6 young people (20-30) at a Christmas house party — Boozt cans raised high, laughing, tinsel and coloured fairy lights everywhere, Christmas tree glowing behind them. Electric cobalt and Christmas red palette, cans PROMINENT and glistening.",
                    f"Friends celebrating on a rooftop decorated for Christmas — fairy lights strung across the space, Boozt cans raised in a toast, soft snow drifting past. Midnight navy, electric blue and Christmas gold.",
                ]),
                "diwali": f"Young South Asian people celebrating Diwali outdoors with sparklers — Boozt cans raised in a toast, Diwali fireworks in the sky, vibrant outfits. Electric cobalt and gold, pure energy and celebration.",
                "ny":     _rnd_r.choice([
                    f"A crowd of friends celebrating New Year's Eve countdown — Boozt cans raised as midnight strikes, golden confetti exploding, fireworks through huge windows. Electric cobalt and gold, unstoppable NYE energy.",
                    f"Four friends on a penthouse rooftop at midnight — Boozt cans clinked together as fireworks burst over the city skyline. Deep navy and electric gold, pure euphoria.",
                ]),
                "val":    f"A stylish couple sharing ice-cold Boozt cans on a Valentine's rooftop date — city lights and rose bokeh behind them, condensation rolling down the cans. Cobalt and rose palette.",
                "summer": f"A group of friends at a summer music festival raising Boozt cans to the sky — stage lights, golden hour sunlight, crowd energy. Electric cobalt and sunshine, euphoric summer festival.",
            },
            "Glenfiddich": {
                "xmas": _rnd_r.choice([
                    f"Four sophisticated adults around a candlelit Christmas dinner table — crystal Glenfiddich glasses raised in a toast, {p} bottle centre-stage catching the fireplace glow. Holly centrepiece, tall taper candles. Deep teal and Christmas gold.",
                    f"A {p} bottle with a velvet ribbon on a mantelpiece above a roaring fireplace — Christmas stockings hung, fairy lights reflected in the bottle. Premium aspirational, the ultimate Christmas gift.",
                ]),
                "diwali": f"A sophisticated Diwali celebration — {p} bottle beautifully lit among diyas and marigolds, adults raising crystal glasses in a toast. Rich jewel tones, warm diya light, premium and festive.",
                "ny":     f"Three adults in black tie at a NYE gala — crystal Glenfiddich glasses raised as midnight strikes, {p} bottle prominently lit, confetti beginning to fall. Deep teal and gold, elegant and celebratory.",
                "val":    f"A couple sharing a glass of {p} at an intimate candlelit Valentine's dinner — red roses, {p} bottle catching the candlelight. Deep teal and rose-red palette, sophisticated romance.",
                "summer": f"A sophisticated man in a linen blazer on a sunlit outdoor terrace pouring {p} over ice — golden afternoon light, ocean or countryside vista behind him. Teal and chartreuse, premium summer leisure.",
            },
        }
        # Sunrise — Swiss connectivity brand: warm human moments, mountain/urban Switzerland
        if b in ("sunrise", "Sunrise"):
            if _xmas:
                return _rnd_r.choice([
                    "A Swiss family gathered around the Christmas table video-calling faraway relatives on a tablet — grandparents' faces lit with joy on the screen, fairy lights twinkling, snow visible through the chalet window. The call holds perfectly. Sunrise Red glow on the device, warm golden Christmas light, Swiss mountain warmth.",
                    "A woman in a Zurich Christmas market video-calling a friend abroad — her breath visible in the cold air, stall lights glowing around her, the call crystal-clear on her phone. Sunrise Red scarf, golden market lights, snow beginning to fall, warm human connection across distance.",
                ])
            if _ny:
                return _rnd_r.choice([
                    "Swiss friends on a rooftop in Zurich counting down to midnight — phones raised, video-calling loved ones as fireworks burst over the city. Every call connects. Sunrise Red and white, golden fireworks, Swiss New Year energy and warmth.",
                    "A couple on a snowy Swiss hillside watching midnight fireworks — one video-calling family, the connection perfect on a clear winter night. Sunrise Red on their jacket, golden bursts, mountain silhouette, quiet Swiss magic.",
                ])
            if _val:
                return "A couple on a candlelit Valentine's dinner video-calling their parents to share the news — warm Swiss apartment, soft pink bokeh, the call holding perfectly. Sunrise Red rose on the table, warm intimate light, human connection that matters."
            if _summer:
                return _rnd_r.choice([
                    "A group of young Swiss hikers reaching a mountain summit — phones out, streaming a victory video call, signal perfect at the peak. Blue sky, Alpine panorama, Sunrise Red on their backpacks, pure Swiss summer euphoria.",
                    "Swiss friends at a lakeside summer party — someone streaming music via their phone, another on a video call, all seamlessly connected. Golden lake light, Sunrise Red accents, warm summer energy.",
                ])
            return None

        # UBS Bank — pure lifestyle, zero financial/brand terms (RAI safe)
        if b == "UBS Bank":
            if _xmas:
                return _rnd_r.choice([
                    "A family of 4 walking hand-in-hand through a beautifully decorated Christmas market — stalls glowing with fairy lights, soft snow falling, warm golden light, children laughing with delight. Cinematic slow dolly, aspirational and heartwarming.",
                    "A couple decorating their home for Christmas together — hanging ornaments on the tree, fairy lights twinkling, cosy fireplace glowing. Intimate, warm, aspirational domestic happiness in slow motion.",
                ])
            if _diwali:
                return "A family lighting diyas together on their home doorstep at dusk — three generations in traditional festive attire, golden diya light warming their faces, rangoli at their feet. Cinematic slow-motion, warm and joyful."
            if _ny:
                return _rnd_r.choice([
                    "A family on a rooftop terrace watching fireworks at midnight — parents lifting children to see the colourful bursts over the city skyline, golden confetti falling. Wide cinematic shot, joy and optimism.",
                    "A couple dressed elegantly embracing as midnight fireworks illuminate the sky — confetti falling, city lights below, faces lit with golden light. Cinematic and aspirational.",
                ])
            if _val:
                return "A couple walking through a rose-lit city street on Valentine's evening — boutique windows decorated with hearts and roses, warm pink bokeh, holding hands and smiling. Cinematic and romantic."
            return None

        b_scenes = _scenes.get(b, {})
        key = ("xmas" if _xmas else "diwali" if _diwali else "ny" if _ny else
               "val" if _val else "easter" if _easter else "summer" if _summer else None)
        return b_scenes.get(key) if key else None

    _festive = _reel_festive_scene(brand, season, _prod)
    if _festive:
        brand_scene = _festive          # REPLACE — leads with festive context
    else:
        _mod = _season_mod(season)
        if _mod:
            brand_scene = f"{brand_scene} {_mod}"  # append for non-festive seasons

    _gc = _veo_genai.Client(vertexai=True, project=gcp_project, location=gcp_region)
    _lang_label = language.strip() if language else "English"
    _voiceover_line = (
        f'A warm confident voiceover says in {_lang_label}: "{copy_headline}"' if copy_headline
        else f"A warm confident voiceover narrates the campaign tagline in {_lang_label}."
    )
    _language_rule = (
        f"\nLanguage: {_lang_label} — the voiceover MUST be delivered entirely in {_lang_label}. "
        "The script text in the prompt should be written in that language."
        if _lang_label and _lang_label.lower() != "english"
        else ""
    )
    video_prompt = await asyncio.get_event_loop().run_in_executor(None, lambda: _gc.models.generate_content(
        model=reasoning_model,
        contents=f"""Write a single cinematic video+audio generation prompt (80-100 words) for a 6-second {brand} campaign reel with voiceover.

Brand: {brand}
Product: {product_name}
Campaign Big Idea: {big_idea}
Fan Truth: {fan_truth}
Season / Occasion: {season}  ← CRITICAL: make the seasonal/festive atmosphere visually central throughout the reel
Audience: {audience}
Campaign Headline (voiceover text): "{copy_headline or big_idea}"{_language_rule}

Base visual direction (FOLLOW THIS CLOSELY): {brand_scene}

Rules:
- Photorealistic, premium FMCG ad quality, dynamic motion, brand colours prominent
- The {season} atmosphere must be unmistakably present in the visuals — lighting, props, colour grading
- AUDIO: upbeat brand-appropriate background music + {_voiceover_line}
- The voiceover should be delivered confidently and warmly over the music
- No text or typography in the image
Output the prompt only.""",
    ))
    final_prompt = video_prompt.text.strip()
    log.info("veo_prompt_ready", prompt=final_prompt[:120])

    # ── Call Veo ──────────────────────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    veo_model = os.getenv("VEO_MODEL", "veo-3.1-generate-001")

    async def _veo_generate(prompt: str, out_uri: str):
        """Call generate_videos; on 429/RESOURCE_EXHAUSTED retry up to 3× with backoff."""
        _waits = [60, 120, 180]
        for _attempt in range(4):
            try:
                return await loop.run_in_executor(None, lambda: _gc.models.generate_videos(
                    model=veo_model,
                    prompt=prompt,
                    config=GenerateVideosConfig(
                        aspect_ratio="16:9",
                        duration_seconds=6,
                        output_gcs_uri=out_uri,
                        number_of_videos=1,
                        generate_audio=True,
                    ),
                ))
            except Exception as _ve:
                if _attempt < 3 and ("429" in str(_ve) or "RESOURCE_EXHAUSTED" in str(_ve)):
                    _w = _waits[_attempt]
                    log.warning("veo_rate_limited_retrying", attempt=_attempt + 1, wait_s=_w, error=str(_ve)[:120])
                    await asyncio.sleep(_w)
                else:
                    raise
        raise RuntimeError("unreachable")  # pragma: no cover

    try:
        operation = await _veo_generate(final_prompt, output_uri)
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
            log.warning("veo_no_videos_returned", prompt_preview=final_prompt[:200])
            # Retry once with a brand-specific safe fallback prompt
            _retry_scenes = {
                "Boozt":       (f"A confident person opens a can of {product_name or 'Boozt'} energy drink in a "
                                f"bright modern setting, condensation droplets in slow motion, cobalt blue lighting. "
                                f"Upbeat music. Voiceover: '{copy_headline or big_idea}'."),
                "Glenfiddich": (f"Close-up of a {product_name or 'Glenfiddich'} whisky bottle on a dark bar surface, "
                                f"amber liquid poured into a crystal glass catching warm light. "
                                f"Teal and chartreuse brand colours. Elegant orchestral music."),
                "Sunglow":     (f"A woman with beautiful natural hair smiles in warm golden light, "
                                f"a {product_name or 'Sunglow'} product bottle beside her. "
                                f"Magenta-pink brand palette. Uplifting music."),
                "Rnorr":       (f"A home cook drops a {product_name or 'Rnorr'} stock cube into a steaming pot, "
                                f"golden broth bubbling with fresh vegetables. "
                                f"Green and yellow brand palette. Warm kitchen atmosphere."),
            }
            fallback_prompt = _retry_scenes.get(
                brand,
                f"A premium advertising video for {brand} {product_name or 'product'}. "
                f"Product prominently featured with brand colours. Upbeat music."
            )
            log.info("veo_retrying_fallback_prompt", prompt=fallback_prompt[:120])
            operation2 = await _veo_generate(fallback_prompt, output_uri.replace(".mp4", "_retry.mp4"))
            deadline2 = time.time() + 480
            while not operation2.done:
                if time.time() > deadline2:
                    log.warning("veo_retry_timeout")
                    return "", ""
                await asyncio.sleep(20)
                operation2 = await loop.run_in_executor(None, lambda: _gc.operations.get(operation2))
            if not operation2.result or not operation2.result.generated_videos:
                log.warning("veo_retry_no_videos_returned")
                return "", ""
            video_gcs = operation2.result.generated_videos[0].video.uri
            log.info("veo_retry_done", uri=video_gcs)
            from google.cloud import storage as _gcs2
            without2 = video_gcs[5:]
            bucket_name2, _, blob_path2 = without2.partition("/")
            video_bytes2 = await loop.run_in_executor(
                None,
                lambda: _gcs2.Client().bucket(bucket_name2).blob(blob_path2).download_as_bytes()
            )
            video_bytes2 = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _overlay_reel(video_bytes2, brand, copy_headline, copy_cta),
            )
            return base64.b64encode(video_bytes2).decode("utf-8"), video_gcs

        video_gcs = operation.result.generated_videos[0].video.uri
        log.info("veo_done", uri=video_gcs)

        # ── Download from GCS ─────────────────────────────────────────────────
        from google.cloud import storage as _gcs
        without = video_gcs[5:]  # strip gs://
        bucket_name, _, blob_path = without.partition("/")
        video_bytes = await loop.run_in_executor(
            None,
            lambda: _gcs.Client().bucket(bucket_name).blob(blob_path).download_as_bytes()
        )

        # ── Text lower-third + logo end-card — single FFmpeg pass ────────────
        video_bytes = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _overlay_reel(video_bytes, brand, copy_headline, copy_cta),
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
    colour_uris: list = None,
    brand_guidelines: str = "",
    big_idea_seed: str = "",
    copy_headline: str = "",
    copy_headlines: list = None,
    copy_cta: str = "",
    product_name: str = "",
    fan_truth: str = "",
    season: str = "",
    market: str = "",
    language: str = "",
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

    # ── Brand-specific concept directions for image generation ───────────────
    _BRAND_CONCEPT_DIRS = {
        "Boozt": (
            "Concept 1 — DYNAMIC ENERGY: Model mid-sprint, jumping, or thrusting the can forward — explosive athletic motion, electric arcs, zero hair focus. Can PROMINENT, glistening with condensation.",
            "Concept 2 — FOCUSED POWER: Model close to camera, intense direct eye contact, can raised to lips or gripped at chest. Urban or gym backdrop, cool controlled power. No flowing hair — face and can are the heroes.",
        ),
        "Sunglow": (
            "Concept 1 — DYNAMIC ENERGY: Model in full motion (hair flip, dramatic spin), hair FLYING and catching golden light. Background has maximum warm magical effects. Products displayed dramatically.",
            "Concept 2 — INTIMATE GLOW: Model closer to camera, intense eye contact, hair softly draped. Background glows warmly. Products at her side, intimately placed.",
        ),
        "Rnorr": (
            "Concept 1 — DYNAMIC ENERGY: Model caught mid-stir or mid-taste, steam rising dramatically, genuine delight. Bold food energy. Products prominent in scene.",
            "Concept 2 — INTIMATE GLOW: Model closer to camera, warm proud smile, holding a steaming bowl or pan. Cosy kitchen atmosphere. Products naturally integrated.",
        ),
    }
    _c1_dir, _c2_dir = _BRAND_CONCEPT_DIRS.get(brand, (
        "Concept 1 — DYNAMIC ENERGY: Model is in full motion (jump, spin, or dramatic reach). Background has maximum magical effects. Products displayed dramatically.",
        "Concept 2 — INTIMATE GLOW: Model is closer to camera, intense eye contact, softer but deeply saturated. Background glows behind them. Products at their side.",
    ))

    # ── Scene variety: season + objective drive people count and scene type ──
    # When a campaign is festive, social, or family-oriented the images should
    # reflect that — not always a lone hero. C1 and C2 are also deliberately
    # structurally different (people-hero vs product/lifestyle-hero).
    def _scene_variety_override(
        _season: str, _objective: str, _brand: str, _product: str
    ) -> tuple[str | None, str | None, str | None]:
        """
        Returns (c1_override, c2_override, model_override) or (None,None,None)
        when no override is warranted. Only c1/c2 that are non-None are applied.
        """
        _sl = _season.lower()
        _ol = (_objective or "").lower()

        # ── Social/group signal from objective text ────────────────────────
        _is_group_obj = any(k in _ol for k in (
            "family", "families", "friends", "together", "community",
            "gathering", "celebration", "group", "crowd", "party",
            "social", "bonding", "sharing", "reunion", "festive",
        ))

        # ── Festive seasons always trigger group/celebration scenes ───────
        _is_christmas  = any(k in _sl for k in ("christmas", "xmas", "festive", "advent"))
        _is_diwali     = any(k in _sl for k in ("diwali", "deepavali"))
        _is_newyear    = "new year" in _sl
        _is_valentines = "valentine" in _sl
        _is_easter     = "easter" in _sl
        _is_festive    = _is_christmas or _is_diwali or _is_newyear or _is_easter

        if not (_is_festive or _is_group_obj or _is_valentines):
            return None, None, None

        # ── Brand-specific festive/group concept directions ────────────────
        if _is_christmas or _is_group_obj:
            _XMAS_DIRS = {
                "Rnorr": (
                    f"Concept 1 — FESTIVE GATHERING: A family of 3-5 people (multi-generational) around a beautifully set Christmas dinner table. The hero parent is serving a steaming dish made with {_product}, faces lit with joy and anticipation. Golden fairy lights, holly centrepiece, festive crockery. Warm amber kitchen light. {_product} pack visible on the table.",
                    f"Concept 2 — MOMENT OF MAGIC: Close-up on two hands (parent and child) adding {_product} to a bubbling pot together. Steam rises dramatically in golden Christmas kitchen light. Soft focus of Christmas decorations behind. The shared cooking moment IS the story — product prominent in frame.",
                    f"family of 3-5 people, warm and multicultural, celebrating Christmas together in the kitchen — the hero parent is the centrepiece, surrounded by children and/or grandparents, all filled with festive joy",
                ),
                "Sunglow": (
                    f"Concept 1 — FESTIVE GLAM SQUAD: Three women (20-35, diverse) getting ready together for a Christmas party, doing each other's hair — laughing, hair FLYING, the whole room glowing with fairy lights and Sunglow magic. {_product} bottles placed prominently on the vanity. Pure euphoria and sisterhood.",
                    f"Concept 2 — CHRISTMAS GLOW PORTRAIT: One woman (25-38) in gorgeous Christmas-night glam, her perfect shining hair draped over a festive red/gold off-shoulder dress, looking directly into camera with magnetic confidence. {_product} bottle gleaming beside her. Warm Christmas bokeh fairy lights behind.",
                    f"three diverse women (20-38) laughing and getting glamorous together in a warm Christmas setting, hair the absolute HERO across all three — sisterhood, joy, festive energy",
                ),
                "Boozt": (
                    f"Concept 1 — FESTIVE CROWD ENERGY: A group of 4-6 young people (20-30, mixed gender) at a Christmas/New Year party — Boozt cans raised high, laughing, confetti falling, electric blue stage lighting and Christmas lights mixing. Pure electric celebration. Cans PROMINENT, glistening in the light.",
                    f"Concept 2 — MIDNIGHT TOAST: Two or three friends at a rooftop party, city lights behind them, countdown energy — Boozt cans clinked together, droplets flying in slow motion under electric blue and golden Christmas bokeh light. Can labels sharp and prominent.",
                    f"group of 4-6 young diverse people (20-30), celebrating together at a festive party — electric energy, Boozt cans raised, joy and momentum, every face alive with celebration",
                ),
                "Glenfiddich": (
                    f"Concept 1 — FESTIVE GATHERING: Three or four sophisticated adults (30-55) in a warmly lit dining room on Christmas evening — crystal whisky glasses raised in a toast, {_product} bottle prominent on the table, amber liquid catching the candlelight. Fireplace glow behind. Elegant, intimate, premium.",
                    f"Concept 2 — THE GIFT: A single beautifully wrapped {_product} bottle sits as the centrepiece of a Christmas gift arrangement — velvet ribbon, sprigs of holly, warm candlelight and fairy lights casting golden reflections off the bottle. Premium, aspirational, the ultimate Christmas gift.",
                    f"a sophisticated group of 3-4 adults in a premium Christmas setting — candlelit, warm, exclusive — raising Glenfiddich glasses in a toast, embodying the pinnacle of festive sophistication",
                ),
            }
            _dirs = _XMAS_DIRS.get(_brand)
            if _dirs:
                return _dirs
            # Generic festive group fallback for other brands (e.g. UBS Bank)
            return (
                f"Concept 1 — FESTIVE CELEBRATION: A group of 3-5 diverse people celebrating the {_season} season together, the {_product} featured prominently in a warm, joyful, richly decorated festive scene. Golden fairy lights, seasonal decorations, genuine happiness — brand colours woven throughout.",
                f"Concept 2 — FESTIVE WARMTH: Two people (couple or friends) sharing a meaningful festive moment with {_product} as the centrepiece. Warm intimate Christmas/festive light, bokeh decorations behind, deep emotional connection — premium and aspirational.",
                f"a warm group of 3-5 diverse people celebrating the {_season} season — inclusive, joyful, multicultural — the brand is at the heart of their moment together",
            )

        if _is_diwali:
            return (
                f"Concept 1 — DIWALI FEAST: A family of 4-6 people (South Asian, multi-generational) gathered around a Diwali spread — diyas glowing everywhere, rangoli on the floor, the mother serving a dish made with {_product} to an excited family. Jewel-toned fabrics, warm golden diya light, genuine joy.",
                f"Concept 2 — DIYA MOMENT: Two women (mother and adult daughter) cooking together in a Diwali kitchen — {_product} being added to a bubbling pot, diyas reflected in the steam, saris or festive salwars, warm amber light. Generational bond, shared recipe, festive spirit.",
                f"South Asian family of 4-6 (multi-generational) celebrating Diwali together — the mother is the hero, surrounded by family in festive traditional attire, warmth and joy filling every face",
            )

        if _is_valentines:
            return (
                f"Concept 1 — ROMANTIC MOMENT: A couple (25-40) sharing a beautiful moment with {_product} — an intimate Valentine's dinner, rose-gold candlelight, soft red and pink floral accents. One partner presenting the product, the other's face lit with joy and love. Premium and romantic.",
                f"Concept 2 — PRODUCT AS LOVE: {_product} presented beautifully as a Valentine's gift — rose petals, soft pink bokeh, warm candlelight catching the packaging. Minimalist product hero shot with maximum romantic atmosphere. Aspirational and desirable.",
                f"a couple in their 25-40s sharing a warm, loving Valentine's moment — natural, genuine affection, the product at the heart of the romantic occasion",
            )

        # Objective-only group signal (no specific season)
        if _is_group_obj:
            return (
                f"Concept 1 — PEOPLE HERO: A group of 3-4 diverse people sharing a genuine moment with {_product} — dynamic, joyful, the brand connecting people. Multiple faces, real emotion, product prominent.",
                f"Concept 2 — BRAND LIFESTYLE: The same group in a wider lifestyle shot — {_product} integrated naturally into a shared social moment (meal, outing, gathering). Warm and authentic, brand colours in the environment.",
                f"a group of 3-4 diverse people (matching market demographics), genuinely sharing a moment with the brand — inclusive, warm, real",
            )

        return None, None, None

    _c1_ov, _c2_ov, _model_ov = _scene_variety_override(
        _season_ctx, big_idea_seed or fan_truth, brand, _product_ctx
    )
    if _c1_ov: _c1_dir = _c1_ov
    if _c2_ov: _c2_dir = _c2_ov
    if _model_ov:
        _magic["model"] = _model_ov

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

    if _matched_persona and not _model_ov:
        # Scene variety override takes priority — only apply persona when no
        # group/festive override was set (persona always describes a single person).
        _brand_settings = _BRAND_SETTING.get(brand, {})
        _resolved_setting = next(
            (_brand_settings[k] for k in _brand_settings if k in _aud_lower),
            _brand_settings.get("default", _matched_persona["setting"])
        )
        _ethnicity_note = _market_demo

        _magic["model"] = (
            f"{_matched_persona['person']}"
            f"{', ' + _age_note if _age_note else ''}. "
            f"{_ethnicity_note + '. ' if _ethnicity_note else ''}"
            f"{_brand_expr}. "
            f"Setting: {_resolved_setting}"
        )
        _magic["energy"]   = f"{_matched_persona['energy']} — {_magic['energy']}"
        _magic["wardrobe"] = f"{_matched_persona['wardrobe']}, colours drawn from brand palette: {_brand_palette_str}"
    elif (not _model_ov) and (_age_note or _market_demo):
        # No matching segment and no group override — apply age + market demo to brand default
        _magic["model"] = (
            _magic["model"]
            + (f" — {_age_note}" if _age_note else "")
            + (f". Market: {_market_demo}" if _market_demo else "")
        )

    scene_concepts_raw = await _llm(f"""You are a world-class FMCG advertising creative director.
Study these reference ad styles: Sunsilk (dynamic hair, sparkles, vibrant energy), Pantene (cinematic hair movement, golden glow), Knorr (warm kitchen magic, steam, real moments), L'Oréal (empowered model, bold colour, premium feel).

Generate 2 DISTINCT advertising key visual prompts for this campaign.
CRITICAL: The two concepts MUST be structurally different — different number of people, different scene types, different emotional angles. NEVER produce two near-identical single-person shots.
If Concept 1 is a group/crowd/family scene → Concept 2 must be an intimate 1-2 person or product-hero shot, and vice versa.

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
Hair/Focus: {_magic.get('hair', _magic.get('product', 'natural and minimal'))}
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
{_c1_dir}
{_c2_dir}

Output EXACTLY this format (nothing else):
[CONCEPT 1 - DYNAMIC]: <170-200 word detailed image generation prompt>
[CONCEPT 2 - INTIMATE]: <170-200 word detailed image generation prompt>

═══ MANDATORY RULES ═══
- FULL BLEED — subject and background fill the entire frame edge to edge, no flat panels
- Model and products positioned centre-right or right, facing slightly left into the frame
- Photorealistic DSLR advertising photography quality
- Magical effects: {_magic['effects']}
- Bold saturated colours — award-winning art direction
- NO text anywhere in the image — headline is injected separately after generation
- Fan truth ({_ft_ctx}) visible in model's expression and scene energy
- Season ({_season_ctx}) woven into atmosphere, lighting temperature, and mood
- Natural balanced lighting across the full frame — no artificial dark zone on the left""", temp=0.9)

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
            if data and len(data) > 1024:
                ref_parts.append(_gtypes.Part.from_bytes(data=data, mime_type=mime))

        # Load colour swatch images — gives Gemini the exact brand palette
        colour_parts = []
        for uri in (colour_uris or [])[:2]:
            mime = _mime_for(uri)
            if mime not in SUPPORTED_MIME:
                continue
            data = _load_bytes(uri)
            if data and len(data) > 512:
                colour_parts.append(_gtypes.Part.from_bytes(data=data, mime_type=mime))

        style_analysis = ""
        if ref_parts or colour_parts:
            n_total = len(ref_parts) + len(colour_parts)
            log.info("p2_analyze_brand_assets", n_banners=len(ref_parts), n_colours=len(colour_parts))
            await _emit("kv", "running", f"Analysing {n_total} brand assets (banners + colour palette)...")
            try:
                vision_contents = []
                if ref_parts:
                    vision_contents.append("These are existing campaign images for this brand. Study them carefully.")
                    vision_contents.extend(ref_parts)
                if colour_parts:
                    vision_contents.append("These are the official brand colour palette swatches.")
                    vision_contents.extend(colour_parts)
                vision_contents.append(
                    f"You are analysing {brand} brand visual assets. "
                    "Describe in 7-8 sentences: "
                    "1) exact background colours, gradients, and glow effects from the campaign ads "
                    "   — name the specific colours with hex codes from the palette swatch if visible, "
                    "2) model energy — pose, expression, movement, and hair treatment specific to this brand, "
                    "3) magical/special effects — sparkles, light rays, bokeh, particles, steam, or energy arcs "
                    "   that are signature to this brand, "
                    "4) product placement — how the product is staged, lit, and scaled relative to the model, "
                    "5) typography style — any text treatment visible in the ads (font weight, size, positioning), "
                    "6) overall mood, emotional tone, and brand personality, "
                    "7) COMPOSITION — look across all the reference images together and describe the typical "
                    "   framing and camera angle (close-up portrait vs wide establishing shot vs aerial/overhead), "
                    "   the usual number of people in frame (solo subject vs small group vs crowd), and whether "
                    "   scenes read as intimate/personal or expansive/environmental. If the references show "
                    "   variety (not always one person, not always a close-up), call that out explicitly so the "
                    "   generated image doesn't default to a single static portrait. "
                    "Be precise with colour values and visual specifics — this will directly instruct AI image generation."
                )
                vision_resp = client.models.generate_content(
                    model    = _settings.gemini_model_reasoning,
                    contents = vision_contents,
                )
                style_analysis = vision_resp.text.strip()
                log.info("p2_brand_style_extracted", style=style_analysis[:150])
            except Exception as vision_err:
                log.warning("p2_brand_style_failed", error=str(vision_err),
                            note="skipping style analysis, proceeding with prompt only")

        # â"€â"€ Step B: Enrich each concept prompt with style + no-text rule ─────────
        # Spell brand name character by character for every brand to prevent AI substitution
        _brand_spelled = " – ".join(brand.upper())
        _REAL_BRAND_WARNINGS = {
            "rnorr":   "NOT 'Knorr', NOT 'Unilever', NOT any real food brand",
            "sunglow": "NOT 'Sunsilk', NOT 'Pantene', NOT any real haircare brand",
            "boozt":   "NOT 'Monster', NOT 'Red Bull', NOT 'Lucozade', NOT any real energy drink brand",
        }
        _real_brand_warn = _REAL_BRAND_WARNINGS.get(brand.lower(), "NOT any real-world brand")
        if brand in ("UBS Bank",) or brand.lower() == "sunrise":
            # Service/telecom brands — no physical product packaging to show.
            # Strictly no text in the image; all prices, headlines, logos added in post-production.
            _no_text_rule = (
                "TYPOGRAPHY RULE: Absolutely NO text, logos, numbers, currency symbols, "
                "or words anywhere in the image — including prices, CHF amounts, plan names, "
                "or any other copy. Zero headlines, zero slogans. All copy is added in "
                "post-production.\n\n"
            )
        else:
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
        # UBS composition: cinematic wide scenes matching their actual ad reference images —
        # aerial/overhead perspectives, groups in environments, action metaphors, NOT portraits.
        _composition_rule = (
            "\n\nCOMPOSITION RULE (UBS Bank visual style): "
            "Create a CINEMATIC, wide-angle scene — NOT a portrait or close-up of one person. "
            "Use an unexpected perspective: aerial/overhead view, low angle, wide establishing shot, or dramatic crop. "
            "The subject(s) should be SMALL within a large environment — a landscape, arena, rooftop, coastline, city skyline, or stadium. "
            "Groups of 2-4 people are welcome — athletes, professionals, families. "
            "People can be in motion (running, skating, swimming, climbing) or contemplative (sitting on a cliff, overlooking a view). "
            "Dramatic lighting: deep shadows with strong highlights, golden hour warmth, or bold architectural contrast. "
            "The LEFT THIRD of the frame must stay relatively open — sky, horizon, or soft negative space — to allow headline text overlay in post-production."
        ) if brand == "UBS Bank" else ""
        enriched_concepts = [
            f"{_no_text_rule}{p}{_style_suffix}{_composition_rule}" for p in concept_prompts
        ]

        # -- Step C: Load reference images (logo + colour palette + products) ------
        SUPPORTED_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        _ref_parts: list = []

        # Colour swatch — 1 only to reduce quota cost per request
        for _c_uri in (colour_uris or [])[:1]:
            _c_mime = _mime_for(_c_uri)
            if _c_mime in SUPPORTED_MIME:
                _c_data = _load_bytes(_c_uri)
                if _c_data and len(_c_data) > 512:
                    _ref_parts.append(
                        f"BRAND COLOUR PALETTE — use ONLY these exact colours for {brand} backgrounds, "
                        f"effects, and product packaging. Do not substitute or approximate."
                    )
                    _ref_parts.append(_gtypes.Part.from_bytes(data=_c_data, mime_type=_c_mime))

        # Logo — colour/identity reference only; Pillow composites it in post-production
        if logo_uri:
            _logo_mime = _mime_for(logo_uri)
            if _logo_mime in SUPPORTED_MIME:
                _logo_data = _load_bytes(logo_uri)
                if _logo_data:
                    _ref_parts.append(
                        f"BRAND IDENTITY REFERENCE — this is the {brand} logo. "
                        f"DO NOT render or place this logo anywhere in the image — "
                        f"it will be composited programmatically after generation. "
                        f"Use it ONLY as a reference for the brand's color palette and graphic style."
                    )
                    _ref_parts.append(_gtypes.Part.from_bytes(data=_logo_data, mime_type=_logo_mime))
                    log.info("p2_logo_ref_loaded", uri=logo_uri)

        # Product images — 1 only to reduce quota cost per request
        for _uri in (product_uris or [])[:1]:
            _pmime = _mime_for(_uri)
            if _pmime not in SUPPORTED_MIME:
                continue
            _pdata = _load_bytes(_uri)
            if _pdata and len(_pdata) > 1024:
                _ref_parts.append(
                    f"PRODUCT REFERENCE — this is the actual '{brand}' '{_product_ctx}' packaging. "
                    f"Reproduce the exact shape, label design, and brand colours. "
                    f"Feature 2-3 of these products prominently in the right zone of the scene:"
                )
                _ref_parts.append(_gtypes.Part.from_bytes(data=_pdata, mime_type=_pmime))

        log.info("p2_ref_parts_loaded",
                 n_images=len([p for p in _ref_parts if not isinstance(p, str)]),
                 n_colours=len(colour_uris or []))

        # -- Step D: Generate one image per concept in parallel -------------------
        image_model = _get_settings().gemini_model_image
        log.info("p2_generate_image_start", model=image_model, n=len(enriched_concepts))
        await _emit("kv", "running", f"Generating {len(enriched_concepts)} campaign visuals with brand references…")

        _fallback_image_model = os.getenv("FALLBACK_IMAGE_MODEL", "gemini-2.0-flash-exp")
        _image_models = (
            [image_model, _fallback_image_model]
            if _fallback_image_model and _fallback_image_model != image_model
            else [image_model]
        )

        async def _gen_one_image(prompt: str) -> bytes | None:
            loop = asyncio.get_event_loop()
            contents: list = []
            if _ref_parts:
                contents.extend(_ref_parts)
            contents.append(prompt)
            _img_waits = [60, 90, 120]  # Vertex AI quota windows are ~60s

            for _mi, _cur_model in enumerate(_image_models):
                _max_attempts = 4 if _mi == 0 else 2  # fewer retries on fallback
                for attempt in range(_max_attempts):
                    try:
                        resp = await loop.run_in_executor(None, lambda m=_cur_model: client.models.generate_content(
                            model    = m,
                            contents = contents,
                            config   = _gtypes.GenerateContentConfig(
                                response_modalities = ["IMAGE", "TEXT"],
                                image_config        = _gtypes.ImageConfig(aspect_ratio="16:9"),
                            ),
                        ))
                        for part in resp.candidates[0].content.parts:
                            if hasattr(part, "inline_data") and part.inline_data is not None:
                                if _mi > 0:
                                    log.info("p2_image_fallback_succeeded", model=_cur_model)
                                return part.inline_data.data
                        return None
                    except Exception as _e:
                        is_429 = "429" in str(_e) or "RESOURCE_EXHAUSTED" in str(_e)
                        if is_429 and attempt < _max_attempts - 1:
                            wait = _img_waits[min(attempt, len(_img_waits) - 1)]
                            log.warning("p2_image_rate_limit", model=_cur_model, attempt=attempt + 1, wait_s=wait)
                            await asyncio.sleep(wait)
                        elif is_429 and _mi < len(_image_models) - 1:
                            log.warning("p2_image_quota_switching", from_model=_cur_model, to_model=_image_models[_mi + 1])
                            break  # move to next model
                        else:
                            log.warning("p2_gen_one_image_failed", model=_cur_model, error=str(_e))
                            return None
            return None

        # Sequential — one concept at a time so they never compete for the same quota window
        _img_results = []
        for _i, _p in enumerate(enriched_concepts):
            log.info("p2_generate_concept", concept=_i + 1, total=len(enriched_concepts))
            _img_results.append(await _gen_one_image(_p))
        generated_bytes_list = [r for r in _img_results if r is not None]
        if not generated_bytes_list:
            raise ValueError("Gemini Pro Image returned no images")

        # Apply Pillow overlay: headline text + brand label stamp (logo handled separately).
        # Concept 1 gets the short billboard headline; concept 2 gets the medium headline
        # so the two KVs carry distinct copy angles (not just different backgrounds).
        _fallback        = _extract_headline(big_idea)
        _hl1 = (copy_headlines[0] if copy_headlines and len(copy_headlines) > 0 else None) or copy_headline or _fallback
        _hl2 = (copy_headlines[1] if copy_headlines and len(copy_headlines) > 1 else None) or copy_headline or _fallback
        _headline_short  = _hl1
        log.info("kv_headlines", hl1=_hl1, hl2=_hl2)
        _concept_lines   = [_hl1, _hl2]

        primary_bytes = generated_bytes_list[0]  # raw, for channel crops
        images_b64 = []
        for i, _img_bytes in enumerate(generated_bytes_list):
            _hl = _concept_lines[i] if i < len(_concept_lines) else _headline_short
            _overlaid = _apply_brand_overlay(
                _img_bytes, brand, _hl, product_uris, product_name, market
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
                copy_cta        = copy_cta,
                reasoning_model = _settings_r.gemini_model_reasoning,
                language        = language or "",
            )
            if video_b64:
                # Send GCS URI immediately so frontend can stream directly from GCS.
                # Also send video_b64 for in-browser playback without extra fetch.
                # video_b64 of a 6s video can be 20+ MB — send URI first as fast signal.
                await _emit("reel", "milestone", _json2.dumps({
                    "video_uri": video_uri,
                    "video_b64": video_b64,
                }))
                await _emit("reel", "done", "Campaign reel ready ✓")
            else:
                log.warning("reel_no_video_returned", campaign_id=campaign_id)
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


async def run_performance_forecast(
    machine_brief: dict,
    strategy: dict,
    copy: dict,
    channels: list,
    campaign_id: str,
) -> dict:
    """Generate pre-launch performance forecast using Vertex AI (Nexus agent)."""
    import google.genai as _g
    from app.config import get_settings as _gs

    _ss  = _gs()
    _gc  = _g.Client(vertexai=True, project=_ss.gcp_project, location=_ss.gcp_region)

    ft       = machine_brief.get("fan_truth", {})
    ft_score = ft.get("overall", 70) if isinstance(ft, dict) else 70
    brand    = machine_brief.get("brand", "")
    market   = machine_brief.get("market", "")
    season   = machine_brief.get("season", "")

    # Derive confidence based on Fan Truth score
    if ft_score >= 80:
        conf = "HIGH"
        conf_note = f"Fan Truth {ft_score}/100 — strong authentic connection drives +15% organic uplift"
    elif ft_score >= 60:
        conf = "MEDIUM"
        conf_note = f"Fan Truth {ft_score}/100 — solid but could benefit from deeper cultural specificity"
    else:
        conf = "LOW"
        conf_note = f"Fan Truth {ft_score}/100 — confidence reduced 20%; recommend brief refinement"

    channels_str = ", ".join(channels) if channels else "Instagram, TikTok, Google Ads"

    prompt = f"""You are Nexus, a pre-launch campaign performance forecaster for {brand}.

Use these inputs to generate a realistic pre-launch performance forecast:

CAMPAIGN SUMMARY:
- Brand: {brand}
- Market: {market}
- Season: {season}
- Channels: {channels_str}
- Fan Truth Score: {ft_score}/100 ({conf_note})
- Big Idea: {strategy.get("big_idea", "")}
- Hero Message: {strategy.get("hero_message", "")}
- Budget: {machine_brief.get("budget", "£50,000")}

BENCHMARKS (typical for {market} beauty/FMCG campaigns):
- Instagram: CTR 1.8-2.5%, Reach 2-5M per £10k spend, Engagement 4-6%, ROAS 2.5-3.5x
- TikTok: CTR 2.5-4%, Reach 3-8M per £10k spend, Engagement 6-9%, ROAS 2.0-3.0x
- Google Ads: CTR 3-6%, Reach 1-3M per £10k spend, ROAS 4-6x
- Email: CTR 18-24%, Reach depends on list size, ROAS 3-5x
- OOH: Impressions 500k-2M, low direct ROAS but high brand uplift

Apply these Fan Truth adjustments:
- Fan Truth >= 80: +15% organic reach, boost confidence to HIGH
- Fan Truth 60-79: standard benchmarks, MEDIUM confidence
- Fan Truth < 60: -20% on reach forecasts, LOW confidence

Produce a JSON object (no markdown, no explanation):
{{
  "campaign_id": "{campaign_id}",
  "headline_prediction": "<one bold sentence predicting campaign performance>",
  "overall_confidence": "{conf}",
  "predicted_total_reach": "<e.g. 8.2M – 11.4M across all channels>",
  "predicted_blended_roas": "<e.g. 3.2x>",
  "fan_truth_impact": "<2 sentences on how the Fan Truth score affects performance>",
  "benchmark_comparison": "<1-2 sentences comparing to typical {market} {season} campaigns>",
  "channel_forecasts": [
    {{
      "channel": "<channel name>",
      "predicted_reach": "<e.g. 4.2M – 5.8M>",
      "predicted_ctr": "<e.g. 2.3%>",
      "predicted_roas": "<e.g. 3.1x>",
      "predicted_engagement": "<e.g. 5.8%>",
      "confidence": "HIGH|MEDIUM|LOW",
      "budget_pct": <0.0–1.0 float>,
      "risk_flag": "<optional short risk>",
      "opportunity": "<optional short opportunity>"
    }}
  ],
  "top_risk": "<single biggest risk to performance>",
  "top_opportunity": "<single biggest upside opportunity>",
  "first_48h_watchlist": ["<metric to watch 1>", "<metric to watch 2>", "<metric to watch 3>"],
  "recommended_budget_split": {{"<channel>": <0.0–1.0 float>}}
}}

Only include channels from this list: {channels_str}
Budget split percentages must sum to 1.0."""

    raw = await _vertex_generate(_gc, os.getenv("CREATIVE_MODEL", "gemini-3.5-flash"), prompt)
    return _parse_agent_response(raw)

