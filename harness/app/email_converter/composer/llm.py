from __future__ import annotations

import json
import re

from typing import Any

import structlog

from ..instructions import (
    SYSTEM_PROMPT,
)

logger = structlog.get_logger()


def compose_with_llm(
    slots: dict[str, Any],
    brand_name: str = "",
    brand_context: dict | None = None,
    campaign_context: list | None = None,
    model: str = "",
    project: str = "",
    location: str = "",
) -> dict[str, Any]:

    from app.config import (
        get_settings,
    )

    settings = get_settings()

    project = (
        project
        or settings.gcp_project
        or ""
    )

    location = (
        location
        or settings.gcp_region
        or "global"
    )

    model = (
        model
        or settings.gemini_model_reasoning
        or "gemini-2.0-flash"
    )

    brand_context = (
        brand_context
        or {}
    )

    campaign_context = (
        campaign_context
        or []
    )

    # =====================================
    # Build SOURCE context
    # =====================================

    raw_lines = []

    for key in (
        "subject",
        "headline",
        "subline",
    ):

        if slots.get(key):

            raw_lines.append(
                f"[Explicit {key}] "
                f"{slots[key]}"
            )

    for item in slots.get(
        "body",
        [],
    ):

        text = str(
            item
        ).strip()

        if text:

            raw_lines.append(
                f"[Source body] {text}"
            )

    # =====================================
    # Tables
    # =====================================

    for table in slots.get(
        "tables",
        [],
    )[:3]:

        headers = " | ".join(
            map(
                str,
                table.get(
                    "headers",
                    [],
                ),
            )
        )

        for row in table.get(
            "rows",
            [],
        )[:4]:

            row_text = " | ".join(
                map(str, row)
            )

            raw_lines.append(
                f"[Source table] "
                f"{headers}: "
                f"{row_text}"
            )

    # =====================================
    # Image semantic context
    # =====================================

    image_context = (
        slots.get(
            "_image_context",
            [],
        )
    )

    image_context_text = "\n".join(

        (
            "[Image context] "
            f"title={item.get('semantic_title', '')}; "
            f"tagline={item.get('semantic_tagline', '')}; "
            f"description={item.get('description', '')}; "
            "contains_prominent_text="
            f"{item.get('contains_prominent_text', False)}"
        )

        for item
        in image_context[:3]
    )

    # =====================================
    # Brand RAG
    # =====================================

    tone = brand_context.get(
        "tone_of_voice",
        "professional and clear",
    )

    do_say = ", ".join(
        brand_context.get(
            "do_say",
            [],
        )
    ) or "none specified"

    dont_say = ", ".join(
        brand_context.get(
            "dont_say",
            [],
        )
    ) or "none specified"

    # =====================================
    # Campaign history
    # =====================================

    campaign_reference = "\n".join(

        f"- {item.get('subject_line', '')}"

        for item
        in campaign_context[:3]

    ) or "(none)"

    # =====================================
    # Final Gemini prompt
    # =====================================

    prompt = f"""
{SYSTEM_PROMPT}

Brand:
{brand_name}

Tone:
{tone}

Preferred phrases:
{do_say}

Avoid phrases:
{dont_say}

Top campaign references:
{campaign_reference}

=====================================
RAW SOURCE MATERIAL
=====================================

{chr(10).join(raw_lines) or "(no text)"}

=====================================
IMAGE SEMANTIC CONTEXT
=====================================

{image_context_text or "(none)"}

Write ONE cohesive customer-facing email.

Never expose:

- filenames
- governance
- brand guideline instructions
- approval instructions
- implementation notes
- internal headings

Return JSON only.
"""

    # =====================================
    # No project → safe fallback
    # =====================================

    if not project:

        logger.warning(
            "llm_compose_skipped",
            reason="no GCP project",
        )

        return (
            _rule_based_fallback(
                slots,
                brand_name,
            )
        )

    # =====================================
    # Gemini
    # =====================================

    try:

        from google import genai

        client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

        response = (
            client.models.generate_content(
                model=model,
                contents=prompt,
            )
        )

        raw_text = (
            response.text
            or ""
        ).strip()

        # Remove accidental markdown fences

        raw_text = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            raw_text,
            flags=re.MULTILINE,
        ).strip()

        result = json.loads(
            raw_text
        )

        # =================================
        # Build body
        # =================================

        body_items = []

        intro = str(
            result.get(
                "intro",
                "",
            )
        ).strip()

        body = str(
            result.get(
                "body",
                "",
            )
        ).strip()

        if intro:

            body_items.append(
                intro
            )

        if body:

            body_items.append(
                body
            )

        # =================================
        # IMPORTANT
        #
        # Create a NEW safe object.
        #
        # DO NOT:
        #
        # updated = dict(slots)
        #
        # because that would carry raw
        # source fields into rendering.
        # =================================

        updated = {

            "subject":
                str(
                    result.get(
                        "subject_line",
                        "",
                    )
                ).strip(),

            "preheader":
                str(
                    result.get(
                        "preheader",
                        "",
                    )
                ).strip(),

            "partner_name":
                str(
                    result.get(
                        "partner_name",
                        "",
                    )
                ).strip(),

            "headline":
                str(
                    result.get(
                        "headline",
                        "",
                    )
                ).strip(),

            "subline":
                str(
                    result.get(
                        "subline",
                        "",
                    )
                ).strip(),

            "intro":
                intro,

            "body":
                body_items,

            "highlights": [

                str(item).strip()

                for item
                in result.get(
                    "highlights",
                    [],
                )

                if str(item).strip()

            ][:3],

            "cta":
                str(
                    result.get(
                        "cta",
                        "",
                    )
                ).strip(),

            "legal_copy":
                str(
                    result.get(
                        "legal_copy",
                        "",
                    )
                ).strip(),

            "hero_contains_text":
                bool(
                    result.get(
                        "hero_contains_text",
                        False,
                    )
                ),

            # Safe visual assets
            "images":
                list(
                    slots.get(
                        "images",
                        [],
                    )
                ),

            "tables": [],
        }

        logger.info(
            "llm_compose_ok",
            brand=brand_name,
            subject=updated[
                "subject"
            ],
        )

        return updated

    except Exception as exc:

        logger.warning(
            "llm_compose_failed",
            error=str(exc),
        )

        return (
            _rule_based_fallback(
                slots,
                brand_name,
            )
        )


def _rule_based_fallback(
    slots: dict[str, Any],
    brand_name: str,
) -> dict[str, Any]:

    internal = re.compile(
        r"("
        r"key\s+points?|"
        r"governance|"
        r"lock.?up|"
        r"co.?brand|"
        r"brand\s+guide|"
        r"guideline|"
        r"do\s+not\s+use|"
        r"prohibited|"
        r"mandatory|"
        r"approval|"
        r"required|"
        r"regulatory|"
        r"internal\s+use|"
        r"confidential|"
        r"precedence"
        r")",
        re.IGNORECASE,
    )

    safe_candidates = [

        str(item).strip()

        for item
        in slots.get(
            "body",
            [],
        )

        if (
            8
            < len(
                str(item).strip()
            )
            < 180

            and not internal.search(
                str(item)
            )
        )

    ][:3]

    # Conservative fallback.
    # Do not invent unsupported claims.

    headline = (
        brand_name
        or "Campaign Update"
    )

    body = (
        safe_candidates[:2]
    )

    return {

        "subject":
            headline[:55],

        "preheader":
            (
                body[0][:120]
                if body
                else ""
            ),

        "partner_name":
            "",

        "headline":
            headline,

        "subline":
            "",

        "intro":
            "",

        "body":
            body,

        "highlights":
            [],

        "cta":
            (
                "Learn More"
                if body
                else ""
            ),

        "legal_copy":
            "",

        "hero_contains_text":
            False,

        "images":
            list(
                slots.get(
                    "images",
                    [],
                )
            ),

        "tables":
            [],
    }


async def async_compose_with_llm(
    *args,
    **kwargs,
) -> dict[str, Any]:

    return compose_with_llm(
        *args,
        **kwargs,
    )