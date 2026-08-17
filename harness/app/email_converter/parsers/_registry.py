from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = {
    "txt",
    "pdf",
    "docx",
    "pptx",
    "xlsx",
    "jpg",
    "jpeg",
    "png",
    "webp",
}


def parse_file(
    raw: bytes,
    filename: str,
    use_vision: bool = True,
    gcp_project: str = "",
) -> dict:

    ext = (
        Path(filename)
        .suffix
        .lower()
        .lstrip(".")
    )

    if ext == "txt":

        from .txt import parse

    elif ext == "pdf":

        from .pdf import parse

    elif ext == "docx":

        from .docx import parse

    elif ext == "pptx":

        from .pptx import parse

    elif ext == "xlsx":

        from .xlsx import parse

    elif ext in {
        "jpg",
        "jpeg",
        "png",
        "webp",
    }:

        from .image import parse

    else:

        raise ValueError(
            f"Unsupported extension: {ext}"
        )

    return parse(
        raw,
        filename,
        use_vision=use_vision,
        gcp_project=gcp_project,
    )