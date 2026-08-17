from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


class EmailConverterPipeline:

    def __init__(
        self,
        gcp_project: str = "",
        use_vision: bool = True,
        use_rag: bool = True,
    ):
        self.gcp_project = gcp_project
        self.use_vision = use_vision
        self.use_rag = use_rag

    def run(
        self,
        files: list[tuple[bytes, str]],
        brand_name: str = "",
        brand_color: str = "",
    ) -> dict[str, Any]:

        if not files:
            raise ValueError(
                "At least one file is required."
            )

        from .parsers._registry import (
            parse_file,
            SUPPORTED_EXTENSIONS,
        )

        from .normaliser.slots import (
            map_slots,
            merge_slots_list,
        )

        from .rag.brand_rag import BrandRAG
        from .rag.campaign_rag import CampaignRAG

        from .composer.llm import compose_with_llm
        from .composer.content_planner import ContentPlanner
        from .composer.layout_planner import LayoutPlanner

        from .builder import build_html
        from .validator import validate

        steps = []

        slots_list = []
        filenames = []
        parse_errors = []

        # ==============================================
        # STAGE 1
        # Parse uploaded files
        # ==============================================

        for raw, filename in files:

            ext = (
                filename.rsplit(".", 1)[-1].lower()
                if "." in filename
                else ""
            )

            if ext not in SUPPORTED_EXTENSIONS:

                parse_errors.append(
                    f"{filename}: unsupported type .{ext}"
                )

                continue

            try:

                parsed = parse_file(
                    raw,
                    filename,
                    use_vision=self.use_vision,
                    gcp_project=self.gcp_project,
                )

                slots = map_slots(
                    parsed,
                    filename=filename,
                )

                slots_list.append(slots)
                filenames.append(filename)

            except Exception as exc:

                logger.warning(
                    "email_parse_failed",
                    filename=filename,
                    error=str(exc),
                )

                parse_errors.append(
                    f"{filename}: {exc}"
                )

        if not slots_list:

            raise ValueError(
                "Could not extract content "
                "from uploaded files."
            )

        steps.append({
            "stage": "parse",
            "files_ok": len(slots_list),
            "files_failed": len(parse_errors),
            "errors": parse_errors,
        })

        # ==============================================
        # STAGE 2
        # Merge SOURCE material
        # ==============================================

        source_context = merge_slots_list(
            slots_list,
            filenames,
        )

        steps.append({
            "stage": "normalise",
            "body_items": len(
                source_context.get("body", [])
            ),
            "images": len(
                source_context.get("images", [])
            ),
        })

        # ==============================================
        # STAGE 3
        # Brand RAG
        # ==============================================

        brand_ctx = {}

        if self.use_rag and brand_name:

            try:

                brand_ctx = BrandRAG().search(
                    brand_name
                )

            except Exception as exc:

                logger.warning(
                    "brand_rag_failed",
                    error=str(exc),
                )

        # ==============================================
        # Campaign RAG
        # ==============================================

        campaign_ctx = []

        if self.use_rag:

            try:

                campaign_ctx = CampaignRAG().search(
                    brand_name=brand_name,
                    source_context=source_context,
                )

            except Exception as exc:

                logger.warning(
                    "campaign_rag_failed",
                    error=str(exc),
                )

        # ==============================================
        # Brand colour
        # ==============================================

        if not brand_color:

            colors = brand_ctx.get(
                "brand_colors",
                [],
            )

            brand_color = (
                colors[0]
                if colors
                else "#0055A4"
            )

        # ==============================================
        # STAGE 4
        # LLM composition
        #
        # Source material goes IN.
        # Clean email content comes OUT.
        # ==============================================

        email_content = compose_with_llm(
            source_context,
            brand_name=brand_name,
            brand_context=brand_ctx,
            campaign_context=campaign_ctx,
            project=self.gcp_project,
        )

        # ==============================================
        # HARD SECURITY / CONTENT BOUNDARY
        #
        # Only these fields can reach HTML renderer.
        # ==============================================

        allowed = {
            "subject",
            "preheader",
            "partner_name",
            "headline",
            "subline",
            "intro",
            "body",
            "highlights",
            "cta",
            "legal_copy",
            "hero_contains_text",
            "images",
            "tables",
        }

        email_content = {
            key: value
            for key, value
            in email_content.items()
            if key in allowed
        }

        # Preserve images if composer did not
        # explicitly return them.

        if not email_content.get("images"):

            email_content["images"] = list(
                source_context.get(
                    "images",
                    [],
                )
            )

        steps.append({
            "stage": "compose",
            "headline": email_content.get(
                "headline",
                "",
            ),
            "body_items": len(
                email_content.get(
                    "body",
                    [],
                )
            ),
        })

        # ==============================================
        # STAGE 5
        # Content planning
        # ==============================================

        email_content = (
            ContentPlanner().plan(
                email_content
            )
        )

        # ==============================================
        # STAGE 6
        # Layout planning
        # ==============================================

        email_content = (
            LayoutPlanner().plan(
                email_content
            )
        )

        template = email_content[
            "_template"
        ]

        # ==============================================
        # STAGE 7
        # HTML rendering
        #
        # IMPORTANT:
        # multiple input files DO NOT create
        # multiple email sections.
        # ==============================================

        html = build_html(
            email_content,
            brand_name=brand_name,
            brand_color=brand_color,
            multi_file=False,
        )

        # ==============================================
        # STAGE 8
        # Validation
        # ==============================================

        report = validate(
            html,
            slots=email_content,
            brand_name=brand_name,
            brand_guidelines=(
                brand_ctx or None
            ),
        )

        steps.append({
            "stage": "validate",
            "passed": report.passed,
            "summary": report.summary(),
        })

        # ==============================================
        # Final result
        # ==============================================

        return {

            "html": html,

            "slots": email_content,

            "template": template,

            "brand_color": brand_color,

            "file_count": len(
                slots_list
            ),

            "validation_passed":
                report.passed,

            "validation_summary":
                report.summary(),

            "pipeline_steps":
                steps,
        }