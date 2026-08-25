"""
brand_context/models.py — BrandContext: all brand knowledge for one Infosys agent turn.

Loaded once per pipeline run by loader.py and passed into every agent's prompt.
"""
from __future__ import annotations

import json
from pydantic import BaseModel


class BrandContext(BaseModel):
    brand: str = "Infosys"
    version: str = "1.0"
    guidelines_rag: str = ""      # top chunks from BQ vector search
    guidelines_local: str = ""    # local guidelines file (first N chars)
    colours: dict = {}            # parsed infosys-colours.json
    logo_names: list[str] = []
    font_names: list[str] = []
    template_names: list[str] = []
    asset_names: list[str] = []

    @property
    def as_prompt_block(self) -> str:
        """Formatted brand context string for injection into LLM prompts."""
        parts = [f"Brand: {self.brand}"]

        if self.guidelines_rag:
            parts.append(f"\nGuidelines (semantic search — most relevant sections):\n{self.guidelines_rag}")
        elif self.guidelines_local:
            parts.append(f"\nGuidelines (local file):\n{self.guidelines_local[:4000]}")

        if self.colours:
            parts.append(f"\nColour tokens:\n{json.dumps(self.colours, indent=2)}")

        if self.logo_names:
            parts.append(f"\nApproved logos: {', '.join(self.logo_names)}")

        if self.font_names:
            parts.append(f"\nLicensed fonts: {', '.join(self.font_names)}")

        if self.template_names:
            parts.append(f"\nAvailable templates/assets: {', '.join(self.template_names)}")

        return "\n".join(parts)
