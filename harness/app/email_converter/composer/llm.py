"""
LLM Composer — uses Gemini to turn raw extracted document content into
polished, customer-facing email marketing copy.

Critical design:
  Uploaded documents are SOURCE MATERIAL, not email copy.
  The LLM must classify and filter content before writing anything.

  PDF/TXT → brand rules, internal guidelines → guide tone/style ONLY
  PDF/TXT → campaign facts                   → become customer-facing copy
  PDF/TXT → governance, lock-up rules        → excluded entirely
  JPG/PNG → visual asset                     → hero image (no text from filename)

Falls back silently to the original slots on any API or parsing error.
"""
from __future__ import annotations
import json
from typing import Any


_SYSTEM_PROMPT = """\
You are an expert email marketing copywriter. You receive RAW EXTRACTED TEXT
from uploaded documents — these may be brand guidelines, campaign briefs,
product sheets, press releases, or internal reference material.

══════════════════════════════════════════════════════════════
STEP 1 — CLASSIFY THE CONTENT
══════════════════════════════════════════════════════════════

Mentally separate the extracted text into these categories:

  BRAND_RULES     — tone of voice, design rules, governance, lock-up rules.
                    Use these to control your writing style. Never quote them
                    as customer-facing copy.

  CAMPAIGN_FACTS  — what the campaign is actually about: partnership details,
                    product names, event names, dates, benefits, key messages.
                    These become the source material for your copy.

  CUSTOMER_COPY   — already-written marketing sentences genuinely aimed at
                    a customer. Include only if they are short and polished.

  LEGAL           — disclaimers, T&Cs, regulatory text.
                    Include in the footer field only.

  INTERNAL        — filenames, document headings, implementation notes,
                    governance text, "KEY POINTS" sections, co-brand rules.
                    EXCLUDE COMPLETELY. Never include in any output field.

══════════════════════════════════════════════════════════════
STEP 2 — WRITE FRESH MARKETING COPY
══════════════════════════════════════════════════════════════

Using ONLY campaign_facts and customer_copy, write the following fields:

  subject_line  : ≤55 characters. Compelling, no clickbait, no ALL CAPS.
  preheader     : ≤120 characters. Expands on the subject.
  headline      : ≤10 words. Punchy, benefit-led. Must be a REAL campaign
                  message — NOT a filename, NOT a document heading.
  subline       : One sentence, ≤25 words, value-proposition focused.
  body_bullets  : 3–5 items. Each ≤90 chars, starting with an active verb.
                  Must be CUSTOMER-FACING marketing messages.
  cta           : ≤4 words (e.g. "Discover More", "Shop Now", "Book a Demo").

══════════════════════════════════════════════════════════════
ABSOLUTE EXCLUSIONS — NEVER include in output
══════════════════════════════════════════════════════════════

  ✗  Any text about "KEY POINTS", "Governance", "Co-brand", "Lock-up rules"
  ✗  Any filenames (e.g. "Campaign3", "brand_guidelines", "brief")
  ✗  Any markdown headings or document structure (##, **, ---)
  ✗  Any internal instructions or implementation guidance
  ✗  Any text that reads as internal documentation

══════════════════════════════════════════════════════════════
OUTPUT FORMAT
══════════════════════════════════════════════════════════════

Return ONLY a valid JSON object — no markdown fences, no commentary:
{
  "subject_line":  "...",
  "preheader":     "...",
  "headline":      "...",
  "subline":       "...",
  "body_bullets":  ["...", "...", "..."],
  "cta":           "..."
}
"""


def compose_with_llm(
    slots:            dict[str, Any],
    brand_name:       str        = "",
    brand_context:    dict       = None,
    campaign_context: list       = None,
    model:            str        = "",
    project:          str        = "",
    location:         str        = "us-central1",
) -> dict[str, Any]:
    """
    Call Gemini to classify raw extracted content and write polished email copy.

    The LLM receives ALL extracted text (body, headlines, sublines) so it can
    identify and exclude internal/governance content, then write fresh copy
    from campaign facts only.

    Args:
        slots            : ContentSlots from normaliser (raw extracted text)
        brand_name       : display brand name
        brand_context    : dict from BrandRAG — tone, do/dont_say, guidelines_text
        campaign_context : list from CampaignRAG — top performing past campaigns
        model            : Gemini model ID (defaults to settings.reasoning_model)
        project          : GCP project (defaults to settings.gcp_project)
        location         : Vertex AI region

    Returns:
        Updated slots dict with rewritten customer-facing copy.
        Original slots returned unchanged on any error.
    """
    # Resolve model and project from settings if not passed
    if not model or not project:
        from app.config import get_settings
        s = get_settings()
        if not model:
            model = s.reasoning_model or "gemini-2.0-flash"
        if not project:
            project = s.gcp_project or ""

    if not project:
        return slots   # no GCP project available — skip LLM

    brand_context    = brand_context    or {}
    campaign_context = campaign_context or []

    # ── Build the full raw content dump for the LLM to classify ──────────────
    # Include everything so the LLM can distinguish campaign facts from
    # internal/governance text and exclude what shouldn't appear.
    all_text_parts: list[str] = []

    if slots.get("headline"):
        all_text_parts.append(f"[Extracted heading] {slots['headline']}")
    if slots.get("subline"):
        all_text_parts.append(f"[Extracted subheading] {slots['subline']}")
    for item in slots.get("body", []):
        all_text_parts.append(f"[Extracted body] {item}")
    for tbl in slots.get("tables", []):
        headers = " | ".join(tbl.get("headers", []))
        for row in tbl.get("rows", [])[:5]:   # cap table rows sent to LLM
            all_text_parts.append(f"[Table row] {headers}: {' | '.join(str(c) for c in row)}")

    raw_content = "\n".join(all_text_parts) or "(no text content extracted)"

    # ── Brand tone context ────────────────────────────────────────────────────
    tone = brand_context.get("tone_of_voice", "professional and clear")
    do_say = ", ".join(brand_context.get("do_say", [])) or "none specified"
    dont_say = ", ".join(brand_context.get("dont_say", [])) or "none specified"

    # ── Top past campaigns as reference ──────────────────────────────────────
    top_campaigns = "\n".join(
        f'  • "{c.get("subject_line", "")}" '
        f'(open {c.get("open_rate", 0):.0%}, click {c.get("click_rate", 0):.0%})'
        for c in campaign_context[:3]
    ) or "  (no campaign history available)"

    user_message = f"""
Brand: {brand_name}
Tone of voice: {tone}
Phrases to use: {do_say}
Phrases to avoid: {dont_say}

Top-performing past campaigns (for reference, not reproduction):
{top_campaigns}

════════════════════════════════════════
RAW EXTRACTED CONTENT FROM UPLOADED FILES
════════════════════════════════════════
{raw_content}

Remember: classify this content first. Only use campaign_facts and
customer_copy to write the output. Exclude all internal/governance content.
""".strip()

    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig

        vertexai.init(project=project, location=location)
        gemini = GenerativeModel(model, system_instruction=_SYSTEM_PROMPT)
        config  = GenerationConfig(
            temperature=0.4,
            max_output_tokens=1024,
            response_mime_type="application/json",
        )
        response = gemini.generate_content(user_message, generation_config=config)
        result   = json.loads(response.text.strip())

        # Merge LLM output back into slots
        updated = dict(slots)
        updated["subject"]   = result.get("subject_line", slots.get("subject",   ""))
        updated["preheader"] = result.get("preheader",    slots.get("preheader", ""))
        updated["headline"]  = result.get("headline",     slots.get("headline",  ""))
        updated["subline"]   = result.get("subline",      slots.get("subline",   ""))
        updated["cta"]       = result.get("cta",          slots.get("cta",       ""))
        updated["body"]      = result.get("body_bullets", slots.get("body",      []))
        return updated

    except Exception:
        return slots


async def async_compose_with_llm(*args, **kwargs) -> dict[str, Any]:
    """Async wrapper for callers that need it — the inner call is sync."""
    return compose_with_llm(*args, **kwargs)
