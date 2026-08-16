"""Parser: .docx / .doc (python-docx)"""
from __future__ import annotations
import base64
import io
import re


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def parse_docx(content: bytes) -> dict:
    from docx import Document

    doc = Document(io.BytesIO(content))
    blocks: list[dict] = []
    images: list[dict] = []

    for para in doc.paragraphs:
        text = _clean(para.text)
        if not text:
            continue
        style = (para.style.name or "").lower()
        level = 0
        if "heading 1" in style or "title" in style:
            level = 1
        elif "heading 2" in style:
            level = 2
        elif "heading 3" in style:
            level = 3
        blocks.append({"type": "heading" if level else "paragraph", "level": level, "text": text})

    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            try:
                blob = rel.target_part.blob
                mime = rel.target_part.content_type or "image/png"
                images.append({"b64": base64.b64encode(blob).decode(), "mime": mime})
            except Exception:
                pass

    return {"blocks": blocks, "images": images[:6]}
