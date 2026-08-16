"""
LLM Composer — classifies raw extracted document content and writes
customer-facing email marketing copy using the same google.genai client
that all other CampaignOS agents use.

Critical design:
  Uploaded documents are SOURCE MATERIAL, not email copy.
  The LLM classifies content before writing anything:

  PDF/TXT → brand rules / guidelines  → guide tone/style, NEVER shown to customer
  PDF/TXT → campaign facts             → become customer-facing copy
  PDF/TXT → governance / internal      → excluded entirely
  JPG/PNG → visual asset               → hero image (never used as text)

Falls back to rule-based trimming when LLM is unavailable, so the email
is at least coherent even without a GCP project configured.
"""
from __future__ import annotations
import json
import re
from typing import Any

import structlog

logger = structlog.get_logger()


_SYSTEM_PROMPT = """\
You are an expert email marketing copywriter for a brand marketing platform.
You receive RAW EXTRACTED TEXT from uploaded documents — these may be brand
guidelines, campaign briefs, product sheets, press releases, or internal
reference material.

══════════════════════════════════════════════════════════════
STEP 1 — CLASSIFY THE CONTENT
══════════════════════════════════════════════════════════════

Mentally separate the extracted text into these categories:

  BRAND_RULES     — tone of voice, design rules, governance, co-brand
                    lock-up rules. Use to control writing style only.
                    NEVER reproduce as customer copy.

  CAMPAIGN_FACTS  — what the campaign is actually about: partnership
                    details, product names, event names, dates, benefits,
                    key messages. These become your copy source.

  CUSTOMER_COPY   — already-written marketing sentences aimed at customers.
                    Include if short and polished.

  LEGAL           — disclaimers, T&Cs. Goes to footer only.

  INTERNAL        — filenames, document headings, implementation notes,
                    governance text, "KEY POINTS" sections, co-brand rules.
                    EXCLUDE COMPLETELY.

══════════════════════════════════════════════════════════════
STEP 2 — WRITE FRESH MARKETING EMAIL COPY
══════════════════════════════════════════════════════════════

Using ONLY campaign_facts and customer_copy, write:

  subject_line  : ≤55 characters. Compelling, no ALL CAPS, no clickbait.
  preheader     : ≤120 characters. Expands on the subject.
  headline      : ≤10 words. Punchy, benefit-led. A REAL campaign message —
                  NOT a filename, NOT a document section heading.
  subline       : One sentence, ≤25 words, value-proposition focused.
  body_bullets  : 3–5 items, each ≤90 chars, starting with an active verb.
                  Must be customer-facing marketing messages — NOT guidelines,
                  NOT governance, NOT filenames, NOT internal instructions.
  cta           : ≤4 words (e.g. "Discover More", "Shop Now", "Book a Demo").

══════════════════════════════════════════════════════════════
ABSOLUTE EXCLUSIONS — NEVER include in output
══════════════════════════════════════════════════════════════

  ✗  "KEY POINTS", "Governance", "Co-brand", "Lock-up rules"
  ✗  Filenames: "Campaign3", "brand_guidelines", "brief", etc.
  ✗  Markdown headings, document section titles, bullet markers
  ✗  Internal instructions or implementation guidance

══════════════════════════════════════════════════════════════
OUTPUT
══════════════════════════════════════════════════════════════

Return ONLY valid JSON — no markdown fences, no commentary:
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
    brand_name:       str   = "",
    brand_context:    dict  = None,
    campaign_context: list  = None,
    model:            str   = "",
    project:          str   = "",
    location:         str   = "",   # defaults to settings.gcp_region (GOOGLE_CLOUD_LOCATION)
) -> dict[str, Any]:
    """
    Classify raw extracted content and write polished customer-facing copy.

    Uses google.genai.Client (same client as all other CampaignOS agents).
    Falls back to rule-based trimming if LLM is unavailable.
    """
    from app.config import get_settings
    s = get_settings()

    project  = project  or s.gcp_project              or ""
    location = location or s.gcp_region                or "global"
    model    = model    or s.gemini_model_reasoning    or "gemini-2.0-flash"

    brand_context    = brand_context    or {}
    campaign_context = campaign_context or []

    # Build the full raw content dump — ALL extracted text so LLM can classify
    all_text: list[str] = []
    if slots.get("headline"):
        all_text.append(f"[Heading] {slots['headline']}")
    if slots.get("subline"):
        all_text.append(f"[Subheading] {slots['subline']}")
    for item in slots.get("body", []):
        if item.strip():
            all_text.append(f"[Body] {item.strip()}")
    for tbl in slots.get("tables", [])[:3]:
        hdrs = " | ".join(tbl.get("headers", []))
        for row in tbl.get("rows", [])[:4]:
            all_text.append(f"[Table] {hdrs}: {' | '.join(str(c) for c in row)}")

    raw_content = "\n".join(all_text) or "(no text content extracted from uploaded files)"

    tone     = brand_context.get("tone_of_voice", "professional and clear")
    do_say   = ", ".join(brand_context.get("do_say",   [])) or "none specified"
    dont_say = ", ".join(brand_context.get("dont_say", [])) or "none specified"

    top_campaigns = "\n".join(
        f'  • "{c.get("subject_line","")}" '
        f'(open {c.get("open_rate",0):.0%}, click {c.get("click_rate",0):.0%})'
        for c in campaign_context[:3]
    ) or "  (no campaign history available)"

    full_prompt = f"""{_SYSTEM_PROMPT}

Brand: {brand_name}
Tone of voice: {tone}
Phrases to use: {do_say}
Phrases to avoid: {dont_say}

Top-performing past campaigns (reference, do not copy):
{top_campaigns}

════════════════════════════════════════
RAW EXTRACTED CONTENT FROM UPLOADED FILES
════════════════════════════════════════
{raw_content}

Classify this content, exclude all internal/governance text, and write
fresh customer-facing email copy. Return only the JSON object.
"""

    if not project:
        logger.warning("llm_compose_skipped", reason="no GCP project — using rule-based fallback")
        return _rule_based_fallback(slots, brand_name)

    try:
        from google import genai
        client   = genai.Client(vertexai=True, project=project, location=location)
        response = client.models.generate_content(model=model, contents=full_prompt)
        raw_text = (response.text or "").strip()

        # Strip markdown fences if model wraps output anyway
        raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
        result   = json.loads(raw_text)

        updated = dict(slots)
        updated["subject"]   = result.get("subject_line", slots.get("subject",   ""))
        updated["preheader"] = result.get("preheader",    slots.get("preheader", ""))
        updated["headline"]  = result.get("headline",     slots.get("headline",  ""))
        updated["subline"]   = result.get("subline",      slots.get("subline",   ""))
        updated["cta"]       = result.get("cta",          slots.get("cta",       ""))
        updated["body"]      = result.get("body_bullets", slots.get("body",      []))

        logger.info("llm_compose_ok", brand=brand_name, subject=updated.get("subject",""))
        return updated

    except Exception as exc:
        logger.warning("llm_compose_failed", brand=brand_name, error=str(exc))
        return _rule_based_fallback(slots, brand_name)


def _rule_based_fallback(slots: dict[str, Any], brand_name: str) -> dict[str, Any]:
    """
    Minimal rule-based cleanup when LLM is unavailable.

    Filters out lines that look like internal/governance content, trims
    the body to 5 items max, and fills in subject/headline from what's there.
    """
    updated = dict(slots)

    # Patterns that identify internal/governance text (never customer-facing)
    _INTERNAL_PATTERNS = re.compile(
        r"(key\s+points?|governance|lock.up|co.brand|brand\s+guide|"
        r"guideline|do\s+not\s+use|prohibited|disclaimer|mandatory|"
        r"approval\s+required|regulatory|internal\s+use|confidential)",
        re.IGNORECASE,
    )

    clean_body = [
        item for item in slots.get("body", [])
        if (
            len(item.strip()) > 8
            and len(item.strip()) < 200        # long paragraphs are usually guidelines
            and not _INTERNAL_PATTERNS.search(item)
        )
    ][:5]   # cap at 5 bullets

    updated["body"] = clean_body

    # Promote headline from first clean body item if missing
    if not updated.get("headline") and clean_body:
        updated["headline"] = clean_body[0]
        updated["body"]     = clean_body[1:]

    if not updated.get("subject") and updated.get("headline"):
        hl = updated["headline"]
        updated["subject"] = hl[:55] if len(hl) <= 55 else hl[:52] + "..."

    if not updated.get("cta"):
        updated["cta"] = "Learn More"

    logger.info("llm_compose_fallback_used", brand=brand_name,
                body_items=len(updated["body"]))
    return updated


async def async_compose_with_llm(*args, **kwargs) -> dict[str, Any]:
    """Async wrapper — compose_with_llm is sync internally."""
    return compose_with_llm(*args, **kwargs)
