"""
EmailConverterAgent — synchronous Python class used by the REST endpoint.

This is NOT the ADK agent (see agent.py for that).
This class is called directly by main.py /convert-email and handles:
  parsers → normaliser → brand RAG → builder → validator

The ADK agent (email_converter_agent in agent.py) is used by the
pipeline DAG and operates via ADK session state / ToolContext.
"""
from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger()


class EmailConverterAgent:
    """
    Convert uploaded documents into a polished HTML email.

    Usage:
        agent  = EmailConverterAgent()
        result = agent.run(
            files       = [(pdf_bytes, "brief.pdf"), (img_bytes, "hero.jpg")],
            brand_name  = "Haleon",
            brand_color = "",        # auto-read from brand.json if empty
        )
        html = result["html"]
    """

    def __init__(
        self,
        gcp_project: str = "",
        use_vision:  bool = False,
        use_rag:     bool = True,
        use_llm:     bool = False,
    ):
        self.gcp_project = gcp_project
        self.use_vision  = use_vision
        self.use_rag     = use_rag
        self.use_llm     = use_llm

    def run(
        self,
        files:       list[tuple[bytes, str]],
        brand_name:  str = "",
        brand_color: str = "",
    ) -> dict[str, Any]:
        """
        Parse files, normalise content, build HTML email, validate.

        Args:
            files       : list of (raw_bytes, filename) tuples
            brand_name  : display brand name (used in header/footer)
            brand_color : primary hex colour; auto-read from brand.json if blank

        Returns:
            {
              html         : str   — complete HTML email,
              slots        : dict  — subject/headline/body/cta etc.,
              image_count  : int,
              file_count   : int,
              filename     : str   — primary filename,
              validation_summary : str,
              validation_passed  : bool,
            }
        """
        if not files:
            raise ValueError("At least one file is required.")

        from app.email_converter.parsers._registry import parse_file, SUPPORTED_EXTENSIONS
        from app.email_converter.normaliser.slots   import map_slots, merge_slots_list
        from app.email_converter.rag.brand_rag       import BrandRAG
        from app.email_converter.rag.template_library import TemplateLibrary
        from app.email_converter.builder             import build_html
        from app.email_converter.validator           import validate

        # ── 1. Parse every file ───────────────────────────────────────────
        slots_list: list[dict] = []
        filenames:  list[str]  = []
        image_count = 0

        for raw, filename in files:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in SUPPORTED_EXTENSIONS:
                logger.warning("email_converter_unsupported_ext", filename=filename, ext=ext)
                continue
            try:
                parsed = parse_file(
                    raw, filename,
                    use_vision   = self.use_vision,
                    gcp_project  = self.gcp_project,
                )
                slots = map_slots(parsed)
                slots_list.append(slots)
                filenames.append(filename)
                image_count += len(parsed.get("images", []))
            except Exception as exc:
                logger.warning("email_converter_parse_failed", filename=filename, error=str(exc))

        if not slots_list:
            raise ValueError("Could not extract content from any of the uploaded files.")

        # ── 2. Merge multi-file slots ─────────────────────────────────────
        merged = merge_slots_list(slots_list, filenames)

        # ── 3. Brand RAG — resolve colour + guidelines ────────────────────
        brand_ctx: dict = {}
        if self.use_rag and brand_name:
            try:
                brand_ctx = BrandRAG().search(brand_name)
            except Exception as exc:
                logger.warning("email_converter_brand_rag_failed", brand=brand_name, error=str(exc))

        # Resolve brand colour: explicit arg → brand.json → fallback blue
        if not brand_color:
            colors = brand_ctx.get("brand_colors", [])
            brand_color = colors[0] if colors else "#0055A4"

        # ── 4. Select template ────────────────────────────────────────────
        template = TemplateLibrary().select(merged)
        merged["_template"] = template

        # ── 5. Build HTML ─────────────────────────────────────────────────
        multi_file = len(slots_list) > 1
        html = build_html(
            merged,
            brand_name  = brand_name,
            brand_color = brand_color,
            multi_file  = multi_file,
        )

        # ── 6. Validate ───────────────────────────────────────────────────
        validation_summary = "Not validated"
        validation_passed  = True
        try:
            report = validate(
                html,
                slots      = merged,
                brand_name = brand_name,
                brand_guidelines = brand_ctx or None,
            )
            validation_summary = report.summary()
            validation_passed  = report.passed
        except Exception as exc:
            logger.warning("email_converter_validate_failed", error=str(exc))

        logger.info(
            "email_converter_run_ok",
            brand      = brand_name,
            template   = template,
            files      = len(slots_list),
            images     = image_count,
            valid      = validation_passed,
        )

        return {
            "html":               html,
            "slots":              merged,
            "image_count":        image_count,
            "file_count":         len(slots_list),
            "filename":           filenames[0] if filenames else "",
            "template":           template,
            "brand_color":        brand_color,
            "validation_summary": validation_summary,
            "validation_passed":  validation_passed,
        }
