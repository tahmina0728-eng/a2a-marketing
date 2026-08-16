"""
LLM Composer — uses Gemini to refine raw slots into polished email copy.

What it rewrites:
  headline  → punchy, on-brand, action-oriented
  subline   → one-sentence value proposition
  subject   → inbox-optimised subject line (≤55 chars)
  preheader → inbox preview text (≤120 chars)
  body      → summarised to 3-5 concise bullet points
  cta       → strong imperative verb phrase (≤4 words)

The brand_context dict (from BrandRAG) informs tone of voice.
The campaign_context list (from CampaignRAG) shows what worked before.

Falls back silently to the original slots on any API or parsing error.
"""
from __future__ import annotations
import json
from typing import Any


_SYSTEM_PROMPT = """\
You are an expert email marketing copywriter. You receive structured content
extracted from uploaded documents and rewrite it as polished, on-brand email copy.

Rules:
- Keep the brand's tone of voice exactly as described.
- subject_line must be ≤55 characters, curiosity-driven, no clickbait.
- preheader must be ≤120 characters, expand on subject without repeating it.
- headline must be ≤10 words, punchy, benefit-led.
- subline must be 1 sentence, ≤25 words, value-proposition focused.
- body_bullets: 3-5 bullet strings, each ≤90 chars, starting with an active verb.
- cta: ≤4 words, strong imperative (e.g. "Download the Report", "Book a Demo").
- Return ONLY a valid JSON object with these keys:
  subject_line, preheader, headline, subline, body_bullets, cta
- No markdown, no commentary, no extra keys.
"""


async def compose_with_llm(
    slots: dict[str, Any],
    brand_name: str           = "",
    brand_context: dict       = None,
    campaign_context: list    = None,
    model: str                = "",
    project: str              = "",
    location: str             = "us-central1",
) -> dict[str, Any]:
    """
    Call Gemini to rewrite slots into polished email copy.

    Args:
        slots            : ContentSlots from normaliser (and content planner)
        brand_name       : display brand name
        brand_context    : dict from BrandRAG.search() — tone, do/dont_say, etc.
        campaign_context : list from CampaignRAG.search() — top performing campaigns
        model            : Gemini model ID
        project          : GCP project (required)
        location         : Vertex AI region

    Returns:
        Updated slots dict with rewritten headline, subject, body, etc.
        Original slots returned unchanged on any error.
    """
    if not project:
        return slots

    # Resolve model from settings if not explicitly passed
    if not model:
        from app.config import get_settings
        model = get_settings().reasoning_model or "gemini-2.0-flash"

    brand_context    = brand_context    or {}
    campaign_context = campaign_context or []

    raw_body = "\n".join(f"- {item}" for item in slots.get("body", []))
    top_campaigns = "\n".join(
        f"  • \"{c.get('subject_line','')}\" "
        f"(open {c.get('open_rate',0):.0%}, click {c.get('click_rate',0):.0%})"
        for c in campaign_context[:3]
    )

    user_message = f"""
Brand: {brand_name}
Tone of voice: {brand_context.get("tone_of_voice", "professional and clear")}
Phrases to use: {", ".join(brand_context.get("do_say", [])) or "none specified"}
Phrases to avoid: {", ".join(brand_context.get("dont_say", [])) or "none specified"}

Top-performing past campaigns for this brand:
{top_campaigns or "  (no history available)"}

--- CONTENT TO REWRITE ---
Current headline : {slots.get("headline", "")}
Current subline  : {slots.get("subline", "")}
Body content:
{raw_body or "(no body content)"}
Current CTA      : {slots.get("cta", "")}
""".strip()

    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig

        vertexai.init(project=project, location=location)
        gemini = GenerativeModel(
            model,
            system_instruction=_SYSTEM_PROMPT,
        )
        config = GenerationConfig(
            temperature=0.4,
            max_output_tokens=1024,
            response_mime_type="application/json",
        )
        response = gemini.generate_content(user_message, generation_config=config)
        result   = json.loads(response.text.strip())

        # Merge LLM output back into slots
        updated = dict(slots)
        updated["subject"]   = result.get("subject_line", slots.get("subject", ""))
        updated["preheader"] = result.get("preheader",    slots.get("preheader", ""))
        updated["headline"]  = result.get("headline",     slots.get("headline", ""))
        updated["subline"]   = result.get("subline",      slots.get("subline", ""))
        updated["cta"]       = result.get("cta",          slots.get("cta", ""))
        updated["body"]      = result.get("body_bullets", slots.get("body", []))
        return updated

    except Exception:
        return slots
