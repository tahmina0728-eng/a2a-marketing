"""
ADK tool functions for the Email Converter Agent.

These are plain Python functions — ADK reads the type hints and docstrings
to build the tool schema automatically. The ToolContext parameter (last arg)
gives access to ADK session state, used here to re-attach uploaded images
that were stored before the agent was invoked (images are too large to pass
through the LLM context directly).

Tool list:
  build_email_html    — renders composed slots into a full HTML email
  validate_email_html — checks brand compliance, HTML compatibility, and
                        regulatory requirements (CAN-SPAM / GDPR / CASL)
"""
from __future__ import annotations

import json
import structlog

from google.adk.tools import ToolContext

from app.email_converter.builder  import build_html
from app.email_converter.validator import validate

logger = structlog.get_logger()


def build_email_html(
    slots_json:   str,
    brand_name:   str,
    brand_color:  str,
    template:     str,
    tool_context: ToolContext,
) -> str:
    """
    Render structured email copy (slots) into a complete, email-client-safe
    HTML string using the chosen layout template.

    Args:
        slots_json  : JSON string with keys: subject, preheader, headline,
                      subline, body (list[str]), cta, _template
        brand_name  : brand display name for header/footer
        brand_color : primary brand hex colour (e.g. "#0055A4")
        template    : layout — "hero" | "text_first" | "product"

    Returns:
        Complete HTML email string, or an error string prefixed with "ERROR:".
    """
    try:
        slots = json.loads(slots_json)
    except json.JSONDecodeError as exc:
        return f"ERROR: slots_json is not valid JSON — {exc}"

    # Normalise keys the LLM might use interchangeably
    if "body_bullets" in slots and "body" not in slots:
        slots["body"] = slots.pop("body_bullets")
    if isinstance(slots.get("body"), str):
        slots["body"] = [slots["body"]]

    slots["_template"] = template or slots.get("_template", "hero")

    # Re-attach images from session state (stored before agent was invoked)
    images = tool_context.state.get("email_images", [])
    slots["images"] = images

    # Re-attach multi-file sections if present
    sections = tool_context.state.get("email_sections", [])
    if sections:
        slots["_sections"] = sections

    multi_file = bool(sections)

    try:
        html = build_html(
            slots,
            brand_name  = brand_name,
            brand_color = brand_color,
            multi_file  = multi_file,
        )
    except Exception as exc:
        logger.error("build_email_html_failed", error=str(exc))
        return f"ERROR: HTML build failed — {exc}"

    # Save HTML to session state so downstream pipeline stages can read it
    tool_context.state["email_html"]     = html
    tool_context.state["email_slots"]    = slots
    tool_context.state["email_template"] = template

    logger.info("build_email_html_ok", template=template, brand=brand_name)
    return html


def validate_email_html(
    html:         str,
    brand_name:   str,
    tool_context: ToolContext,
) -> str:
    """
    Validate the generated HTML email for brand compliance, email-client
    compatibility (Gmail, Outlook), and regulatory requirements
    (CAN-SPAM, GDPR, CASL).

    Args:
        html       : full HTML email string from build_email_html
        brand_name : brand name (used for compliance sender-identification check)

    Returns:
        JSON string with keys: passed (bool), summary (str), size_kb (float),
        errors (list), warnings (list).
    """
    if html.startswith("ERROR:"):
        return json.dumps({
            "passed":  False,
            "summary": "Skipped — HTML build failed",
            "size_kb": 0.0,
            "errors":  [{"code": "build_error", "message": html}],
            "warnings": [],
        })

    try:
        slots = tool_context.state.get("email_slots", {})
        report = validate(html, slots=slots, brand_name=brand_name)
    except Exception as exc:
        logger.error("validate_email_html_failed", error=str(exc))
        return json.dumps({
            "passed":  False,
            "summary": f"Validation error — {exc}",
            "size_kb": 0.0,
            "errors":  [{"code": "validator_error", "message": str(exc)}],
            "warnings": [],
        })

    result = {
        "passed":   report.passed,
        "summary":  report.summary(),
        "size_kb":  report.size_kb,
        "errors": [
            {"code": e.code, "message": e.message}
            for e in report.all_errors
        ],
        "warnings": [
            {"code": w.code, "message": w.message}
            for w in report.all_warnings
        ],
    }

    # Persist validation report to session state
    tool_context.state["email_validation"] = result

    logger.info(
        "validate_email_html_ok",
        passed  = report.passed,
        errors  = len(report.all_errors),
        warnings= len(report.all_warnings),
        size_kb = report.size_kb,
    )
    return json.dumps(result)
