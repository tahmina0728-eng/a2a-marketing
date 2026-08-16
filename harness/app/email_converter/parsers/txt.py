"""Parser: .txt plain text"""
from __future__ import annotations
import re


def parse_txt(content: bytes) -> dict:
    text  = content.decode("utf-8-sig", errors="replace")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    blocks: list[dict] = []

    for i, para in enumerate(paras):
        lines = [l.strip() for l in para.splitlines() if l.strip()]
        if not lines:
            continue
        first = lines[0]
        rest  = " ".join(lines[1:])
        # First non-empty para: treat first line as H1 if short enough
        if i == 0 and len(first) < 120:
            blocks.append({"type": "heading", "level": 1, "text": first})
            if rest:
                blocks.append({"type": "paragraph", "text": rest})
        else:
            blocks.append({"type": "paragraph", "text": " ".join(lines)})

    return {"blocks": blocks, "images": []}
