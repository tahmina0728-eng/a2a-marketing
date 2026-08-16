"""
EmailConverterAgent — synchronous Python class used by the REST endpoint.

Pipeline stages (in order):
  1. Parse      — extract text/images from each uploaded file
  2. Normalise  — map raw blocks → structured slots (headline/body/cta)
  3. Brand RAG  — load brand colour, tone, do/dont_say from GCS bucket
  4. LLM Compose— classify content, discard internal text, write fresh copy
  5. Template   — pick hero / text_first / product based on content signals
  6. Build HTML — render email-safe HTML from structured slots
  7. Validate   — brand compliance, HTML compatibility, CAN-SPAM/GDPR/CASL

The response includes `pipeline_steps` — a list of dicts describing what
happened at each stage so you can see exactly what the agent did.
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
            brand_color = "",   # auto-read from brand.json if empty
        )
        html  = result["html"]
        steps = result["pipeline_steps"]   # diagnostic: what each stage did
    """

    def __init__(
        self,
        gcp_project: str  = "",
        use_vision:  bool = False,
        use_rag:     bool = True,
    ):
        self.gcp_project = gcp_project
        self.use_vision  = use_vision
        self.use_rag     = use_rag

    def run(
        self,
        files:       list[tuple[bytes, str]],
        brand_name:  str = "",
        brand_color: str = "",
    ) -> dict[str, Any]:

        if not files:
            raise ValueError("At least one file is required.")

        from app.email_converter.parsers._registry  import parse_file, SUPPORTED_EXTENSIONS
        from app.email_converter.normaliser.slots    import map_slots, merge_slots_list
        from app.email_converter.rag.brand_rag        import BrandRAG
        from app.email_converter.rag.template_library import TemplateLibrary
        from app.email_converter.composer.llm         import compose_with_llm
        from app.email_converter.builder              import build_html
        from app.email_converter.validator            import validate
        from app.config import get_settings

        steps: list[dict] = []   # diagnostic log — each stage records what it did

        # ── Stage 1: Parse ────────────────────────────────────────────────
        slots_list: list[dict] = []
        filenames:  list[str]  = []
        image_count  = 0
        parse_errors = []

        for raw, filename in files:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in SUPPORTED_EXTENSIONS:
                parse_errors.append(f"{filename}: unsupported type (.{ext})")
                continue
            try:
                parsed      = parse_file(raw, filename,
                                         use_vision=self.use_vision,
                                         gcp_project=self.gcp_project)
                slot        = map_slots(parsed)
                slots_list.append(slot)
                filenames.append(filename)
                image_count += len(parsed.get("images", []))
            except Exception as exc:
                parse_errors.append(f"{filename}: {exc}")
                logger.warning("email_converter_parse_failed", filename=filename, error=str(exc))

        steps.append({
            "stage":       "1_parse",
            "label":       "Parse files",
            "files_ok":    len(slots_list),
            "files_failed": len(parse_errors),
            "images_found": image_count,
            "errors":      parse_errors,
        })

        if not slots_list:
            raise ValueError(
                "Could not extract content from any uploaded files. "
                + "; ".join(parse_errors)
            )

        # ── Stage 2: Normalise ────────────────────────────────────────────
        merged = merge_slots_list(slots_list, filenames)

        steps.append({
            "stage":        "2_normalise",
            "label":        "Normalise slots",
            "headline":     merged.get("headline", ""),
            "body_items":   len(merged.get("body", [])),
            "tables":       len(merged.get("tables", [])),
            "images":       len(merged.get("images", [])),
        })

        # ── Stage 3: Brand RAG ────────────────────────────────────────────
        brand_ctx: dict = {}
        rag_status = "skipped (no brand name)"

        if self.use_rag and brand_name:
            try:
                brand_ctx  = BrandRAG().search(brand_name)
                rag_status = (
                    f"ok — tone: {brand_ctx.get('tone_of_voice','')[:60] or 'not set'}, "
                    f"colors: {brand_ctx.get('brand_colors', [])}"
                )
            except Exception as exc:
                rag_status = f"failed: {exc}"
                logger.warning("email_converter_brand_rag_failed", brand=brand_name, error=str(exc))

        if not brand_color:
            colors = brand_ctx.get("brand_colors", [])
            brand_color = colors[0] if colors else "#0055A4"

        steps.append({
            "stage":       "3_brand_rag",
            "label":       "Brand RAG",
            "status":      rag_status,
            "brand_color": brand_color,
        })

        # ── Stage 4: LLM Compose ──────────────────────────────────────────
        project = self.gcp_project or get_settings().gcp_project or ""
        llm_status = ""
        body_before = list(merged.get("body", []))

        try:
            merged     = compose_with_llm(
                merged,
                brand_name    = brand_name,
                brand_context = brand_ctx,
                project       = project,
            )
            body_after = merged.get("body", [])

            if project:
                llm_status = (
                    f"ok — subject: '{merged.get('subject','')}', "
                    f"body trimmed {len(body_before)} → {len(body_after)} items"
                )
            else:
                llm_status = (
                    f"rule-based fallback (no GCP project) — "
                    f"body trimmed {len(body_before)} → {len(body_after)} items"
                )
        except Exception as exc:
            llm_status = f"failed: {exc}"
            logger.warning("email_converter_llm_compose_failed", error=str(exc))

        steps.append({
            "stage":    "4_llm_compose",
            "label":    "LLM copy composer",
            "status":   llm_status,
            "headline": merged.get("headline", ""),
            "subject":  merged.get("subject",  ""),
            "cta":      merged.get("cta",      ""),
            "body":     merged.get("body",     []),
        })

        # ── Stage 5: Template selection ───────────────────────────────────
        template = TemplateLibrary().select(merged)
        merged["_template"] = template

        steps.append({
            "stage":    "5_template",
            "label":    "Template selection",
            "template": template,
            "reason":   (
                "product (tables + ≥2 images)"   if template == "product"
                else "hero (images present)"     if template == "hero"
                else "text_first (no images)"
            ),
        })

        # ── Stage 6: Build HTML ───────────────────────────────────────────
        multi_file = len(slots_list) > 1
        html = build_html(
            merged,
            brand_name  = brand_name,
            brand_color = brand_color,
            multi_file  = multi_file,
        )

        steps.append({
            "stage":    "6_build",
            "label":    "Build HTML",
            "size_kb":  round(len(html.encode()) / 1024, 1),
            "template": template,
        })

        # ── Stage 7: Validate ─────────────────────────────────────────────
        validation_summary = "Not validated"
        validation_passed  = True
        validation_errors:  list = []
        validation_warnings: list = []

        try:
            report = validate(
                html,
                slots            = merged,
                brand_name       = brand_name,
                brand_guidelines = brand_ctx or None,
            )
            validation_summary  = report.summary()
            validation_passed   = report.passed
            validation_errors   = [{"code": e.code, "message": e.message} for e in report.all_errors]
            validation_warnings = [{"code": w.code, "message": w.message} for w in report.all_warnings]
        except Exception as exc:
            validation_summary = f"Validation error: {exc}"
            logger.warning("email_converter_validate_failed", error=str(exc))

        steps.append({
            "stage":    "7_validate",
            "label":    "Validate",
            "passed":   validation_passed,
            "summary":  validation_summary,
            "errors":   validation_errors,
            "warnings": validation_warnings,
        })

        logger.info(
            "email_converter_run_ok",
            brand    = brand_name,
            template = template,
            files    = len(slots_list),
            images   = image_count,
            valid    = validation_passed,
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
            "pipeline_steps":     steps,   # ← diagnostic: full stage-by-stage log
        }
