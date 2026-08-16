"""
email_converter_runner.py — Standalone runner for the Email Converter agent.

Follows the same pattern as briefing.py, email_templates.py, etc.:
  - Takes (brand, prompt) as input
  - Calls _generate() for LLM composition
  - Calls our pipeline modules (parsers → normaliser → builder → validator)
  - Returns a structured dict with agent="email_converter"

Called by agent_standalone.py when agent_key == "email_converter".

Note: this runner does NOT use ADK sessions or ToolContext — it is a
direct Python call path for the /agent-standalone endpoint.
The full ADK agent (email_converter_agent) is used by the pipeline DAG.
"""
from __future__ import annotations

import json
import structlog

from app.agents._utils import _generate, _brand_guidelines

logger = structlog.get_logger()


def run_email_converter(brand: str, prompt: str) -> dict:
    """
    Standalone Email Converter agent.

    Generates a complete on-brand HTML email from a text prompt, without
    requiring file uploads. Uses Gemini to compose the copy, then renders
    it using the email_converter builder pipeline.

    Returns a dict with:
      agent, brand, subject, headline, template, html,
      validation_summary, templates (list of 3 layout variants)
    """
    logger.info("email_converter_standalone_start", brand=brand)

    # ── Step 1: Generate email copy via Gemini ────────────────────────────
    copy_data = _generate(
        persona=(
            "You are Mailer, the Email Converter Agent for CampaignOS. "
            "You transform campaign briefs into polished, on-brand email copy."
        ),
        brand=brand,
        prompt=prompt,
        output_instructions=(
            "Respond ONLY with valid JSON (no markdown fences):\n"
            '{"subject": "compelling subject line ≤55 chars", '
            '"preheader": "inbox preview text ≤120 chars", '
            '"headline": "punchy benefit-led headline ≤10 words", '
            '"subline": "one supporting sentence ≤25 words", '
            '"body": ["bullet 1 ≤90 chars", "bullet 2", "bullet 3", "bullet 4", "bullet 5"], '
            '"cta": "call-to-action ≤4 words", '
            '"template": "hero" or "text_first" or "product"}'
        ),
    )

    subject  = copy_data.get("subject",   f"{brand} — Campaign Update")
    preheader= copy_data.get("preheader", "")
    headline = copy_data.get("headline",  brand)
    subline  = copy_data.get("subline",   "")
    body     = copy_data.get("body",      [])
    cta      = copy_data.get("cta",       "Learn More")
    template = copy_data.get("template",  "hero")

    if isinstance(body, str):
        body = [body]
    if template not in ("hero", "text_first", "product"):
        template = "hero"

    # ── Step 2: Build structured slots ────────────────────────────────────
    slots = {
        "subject":   subject,
        "preheader": preheader,
        "headline":  headline,
        "subline":   subline,
        "body":      body,
        "cta":       cta,
        "_template": template,
        "images":    [],
        "tables":    [],
    }

    # ── Step 3: Load brand colour from guidelines (heuristic) ─────────────
    brand_color = _detect_brand_color(brand)

    # ── Step 4: Build all three template variants ─────────────────────────
    from app.email_converter.builder.templates import hero, text_first, product

    templates = []
    for tmpl_id, tmpl_name, renderer in [
        ("hero",       "Hero",       hero.render),
        ("text_first", "Text-first", text_first.render),
        ("product",    "Product",    product.render),
    ]:
        try:
            html = renderer(
                {**slots, "_template": tmpl_id},
                brand_name  = brand,
                brand_color = brand_color,
                multi_file  = False,
            )
        except Exception as exc:
            logger.warning("email_converter_render_failed", template=tmpl_id, error=str(exc))
            html = f"<!-- render error: {exc} -->"
        templates.append({
            "id":     tmpl_id,
            "name":   tmpl_name,
            "layout": _TEMPLATE_LABELS[tmpl_id],
            "html":   html,
        })

    # Primary HTML is the Gemini-chosen template
    primary_html = next((t["html"] for t in templates if t["id"] == template), templates[0]["html"])

    # ── Step 5: Validate ──────────────────────────────────────────────────
    validation_summary = "Not validated"
    validation_passed  = True
    try:
        from app.email_converter.validator import validate as _validate
        report = _validate(primary_html, slots=slots, brand_name=brand)
        validation_summary = report.summary()
        validation_passed  = report.passed
    except Exception as exc:
        logger.warning("email_converter_validate_failed", error=str(exc))

    logger.info(
        "email_converter_standalone_done",
        brand    = brand,
        template = template,
        valid    = validation_passed,
    )

    return {
        "agent":              "email_converter",
        "brand":              brand,
        "subject":            subject,
        "preheader":          preheader,
        "headline":           headline,
        "subline":            subline,
        "cta":                cta,
        "template":           template,
        "html":               primary_html,
        "templates":          templates,       # all 3 variants for the frontend picker
        "validation_summary": validation_summary,
        "validation_passed":  validation_passed,
        "copy":               copy_data,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

_TEMPLATE_LABELS = {
    "hero":       "Hero — full-width image, bold CTA",
    "text_first": "Text-first — clean, copy-led layout",
    "product":    "Product — feature showcase with CTA",
}

def _detect_brand_color(brand: str) -> str:
    """
    Read the primary brand colour from brand.json in the GCS bucket / local bucket.
    Falls back to CampaignOS blue if brand.json is missing or has no colours.
    """
    try:
        from app.brand_assets import get_asset_loader
        profile = get_asset_loader().load_brand_profile(brand)
        if profile:
            colors = profile.get("visual_identity", {}).get("primary_colors", [])
            if colors:
                return colors[0]
    except Exception:
        pass
    return "#0055A4"
