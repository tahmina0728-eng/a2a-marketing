"""Parser registry — maps file extension → parse function."""
from __future__ import annotations

from .docx  import parse_docx
from .pdf   import parse_pdf
from .xlsx  import parse_xlsx, parse_csv
from .txt   import parse_txt
from .pptx  import parse_pptx
from .image import parse_image

IMAGE_EXTS: frozenset[str] = frozenset({"jpg", "jpeg", "png", "gif", "webp"})

EXT_MIME: dict[str, str] = {
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
    "gif":  "image/gif",
    "webp": "image/webp",
}

_PARSERS: dict[str, object] = {
    "docx": parse_docx,
    "doc":  parse_docx,   # python-docx can open many .doc files; fails on true binary
    "pdf":  parse_pdf,
    "xlsx": parse_xlsx,
    "xls":  parse_xlsx,
    "csv":  parse_csv,
    "txt":  parse_txt,
    "pptx": parse_pptx,
}

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(_PARSERS) | IMAGE_EXTS


def parse_file(
    content: bytes,
    filename: str,
    use_vision: bool  = False,
    gcp_project: str  = "",
    gcp_location: str = "us-central1",
) -> dict:
    """
    Dispatch to the right parser based on file extension.

    Args:
        content      : raw file bytes
        filename     : original filename (used for extension + fallback headline)
        use_vision   : if True and file is an image, call Gemini Vision
        gcp_project  : GCP project ID (required when use_vision=True)
        gcp_location : Vertex AI region (default: us-central1)

    Returns:
        { blocks: list[dict], images: list[dict], vision?: dict|None }

    Raises:
        ValueError for unsupported extensions.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in IMAGE_EXTS:
        mime = EXT_MIME.get(ext, "image/jpeg")
        if use_vision:
            from .image import parse_image_with_vision
            return parse_image_with_vision(content, filename, mime, gcp_project, gcp_location)
        return parse_image(content, filename, mime)

    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(
            f"Unsupported file type: .{ext}  "
            f"(supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))})"
        )
    return parser(content)  # type: ignore[call-arg]
