"""Parser: .pdf (PyMuPDF / fitz)"""
from __future__ import annotations
import base64
import re


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def parse_pdf(content: bytes) -> dict:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=content, filetype="pdf")
    blocks: list[dict] = []
    images: list[dict] = []

    for page in doc:
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            btype = block.get("type")
            if btype == 0:  # text block
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    line_text = _clean(" ".join(s.get("text", "") for s in spans))
                    if not line_text:
                        continue
                    max_size = max((s.get("size", 0) for s in spans), default=0)
                    if max_size >= 18:
                        blocks.append({"type": "heading", "level": 1, "text": line_text})
                    elif max_size >= 14:
                        blocks.append({"type": "heading", "level": 2, "text": line_text})
                    else:
                        blocks.append({"type": "paragraph", "text": line_text})
            elif btype == 1:  # image block
                try:
                    xref = block.get("xref", 0)
                    if xref:
                        img_data = doc.extract_image(xref)
                        raw  = img_data.get("image", b"")
                        mime = f"image/{img_data.get('ext', 'jpeg')}"
                    else:
                        raw  = block.get("image", b"")
                        mime = "image/jpeg"
                    if raw:
                        images.append({"b64": base64.b64encode(raw).decode(), "mime": mime})
                except Exception:
                    pass

    doc.close()
    return {"blocks": blocks, "images": images[:6]}
