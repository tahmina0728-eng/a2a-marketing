"""
brand_context/loader.py — loads Infosys brand context from local files + BQ vector search.

Call load_infosys_brand(query) once at the start of each agent turn.
When search_mode=bigquery, guidelines_rag is populated from BQ VECTOR_SEARCH.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.brand_context.models import BrandContext

# Resolve to harness/app/brands/infosys/
_INFOSYS_DIR = Path(__file__).parent.parent / "brands" / "infosys"


def load_infosys_brand(query: str = "", top_k: int = 5) -> BrandContext:
    ctx = BrandContext()

    # Colour tokens
    colour_file = _INFOSYS_DIR / "colours" / "infosys-colours.json"
    if colour_file.exists():
        try:
            ctx.colours = json.loads(colour_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Local guidelines text (first 3 000 chars as safety net)
    for gfile in ["brand_guidelines.md", "Guideline.md"]:
        g = _INFOSYS_DIR / "guidelines" / gfile
        if g.exists():
            ctx.guidelines_local = g.read_text(encoding="utf-8")[:3000]
            break

    # Logo, font and asset names for the prompt
    ctx.logo_names = [
        f.name for f in (_INFOSYS_DIR / "logos").iterdir()
        if f.suffix.lower() in (".png", ".svg", ".jpg", ".jpeg")
    ] if (_INFOSYS_DIR / "logos").exists() else []

    ctx.font_names = [
        f.name for f in (_INFOSYS_DIR / "fonts").iterdir()
        if f.suffix.lower() in (".otf", ".ttf")
    ] if (_INFOSYS_DIR / "fonts").exists() else []

    ctx.asset_names = [
        f.name for f in (_INFOSYS_DIR / "assets").iterdir()
        if f.is_file()
    ] if (_INFOSYS_DIR / "assets").exists() else []

    # BQ vector search for guideline RAG (preferred when search_mode=bigquery)
    if query:
        try:
            from app.config import get_settings
            settings = get_settings()
            if settings.search_mode == "bigquery":
                from app.bq_vector_client import search_brand_guidelines
                rag = search_brand_guidelines("Infosys", query, top_k=top_k)
                if rag:
                    ctx.guidelines_rag = rag
        except Exception:
            pass

    return ctx
