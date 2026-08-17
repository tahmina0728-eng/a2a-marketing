from __future__ import annotations

from google.adk import Agent

from app.config import get_settings
from app.email_converter.instructions import SYSTEM_PROMPT
from ._pipeline import EmailConverterPipeline

settings = get_settings()

email_converter_agent = Agent(
    name        = "email_converter_agent",
    model       = settings.reasoning_model,
    description = (
        "Converts uploaded documents (PDF, DOCX, XLSX, images, etc.) into a "
        "polished, on-brand HTML email. Composes subject, headline, body and "
        "CTA, selects the best layout template, and validates for brand "
        "compliance and CAN-SPAM / GDPR / CASL requirements."
    ),
    instruction = SYSTEM_PROMPT,
    output_key  = "email_result",
    mode        = "single_turn",
)


class EmailConverterAgent:
    def __init__(
        self,
        gcp_project: str = "",
        use_vision: bool = True,
        use_rag: bool = True,
    ):
        self.pipeline = EmailConverterPipeline(
            gcp_project=gcp_project,
            use_vision=use_vision,
            use_rag=use_rag,
        )

    def run(
        self,
        files,
        brand_name: str = "",
        brand_color: str = "",
    ):
        return self.pipeline.run(
            files=files,
            brand_name=brand_name,
            brand_color=brand_color,
        )