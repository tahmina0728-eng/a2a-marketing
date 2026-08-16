"""Parser: image files (.jpg, .png, .gif, .webp)

Two modes:
  parse_image(content, filename, mime)
      → basic mode: base64-encodes the image, uses filename as headline.
        Always works, no API needed.

  parse_image_with_vision(content, filename, mime, project, location)
      → enriched mode: calls Gemini Vision to extract visible text,
        describe the image, and detect brand colours.
        Requires google-cloud-aiplatform and a GCP project.
        Falls back to parse_image on any error.
"""
from __future__ import annotations
import base64
import re


_EXT_MIME: dict[str, str] = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png",  "gif": "image/gif",
    "webp": "image/webp",
}


def parse_image(content: bytes, filename: str, mime: str) -> dict:
    """Base mode — embed image as-is, derive headline from filename."""
    b64  = base64.b64encode(content).decode()
    name = re.sub(r"[-_]+", " ", filename.rsplit(".", 1)[0]).strip().title()
    return {
        "blocks": [{"type": "heading", "level": 1, "text": name}],
        "images": [{"b64": b64, "mime": mime}],
        "vision": None,
    }


def parse_image_with_vision(
    content: bytes,
    filename: str,
    mime: str,
    project: str  = "",
    location: str = "us-central1",
) -> dict:
    """
    Enriched mode — sends the image to Gemini Vision (gemini-2.0-flash)
    and extracts:
      - visible_text : text readable in the image (taglines, prices, dates)
      - description  : one-sentence description of what the image shows
      - brand_colours: up to 3 dominant hex colours detected

    The enriched data is stored in slots["vision"] and also injected into
    blocks so the normaliser can use them for subject/headline/body.

    Falls back gracefully to parse_image() on any API or import error.
    """
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, Part, Image as VImage

        if not project:
            raise ValueError("GCP project required for Vision mode.")

        from app.config import get_settings
        _model_id = get_settings().reasoning_model or "gemini-2.0-flash"

        vertexai.init(project=project, location=location)
        gemini = GenerativeModel(_model_id)

        image_part = Part.from_data(data=content, mime_type=mime)
        prompt = (
            "Analyse this image and respond with ONLY a JSON object with these keys:\n"
            '  "visible_text": string — all text readable in the image, or "" if none\n'
            '  "description":  string — one sentence describing the image content\n'
            '  "brand_colours": list of up to 3 dominant hex colour strings (e.g. ["#FF0000"])\n'
            "No markdown fences, no extra keys."
        )

        response = gemini.generate_content([image_part, prompt])
        import json as _json
        vision_data = _json.loads(response.text.strip())

    except Exception:
        return parse_image(content, filename, mime)

    b64  = base64.b64encode(content).decode()
    name = re.sub(r"[-_]+", " ", filename.rsplit(".", 1)[0]).strip().title()

    blocks: list[dict] = []

    description = vision_data.get("description", "").strip()
    visible_text = vision_data.get("visible_text", "").strip()

    # Use visible tagline/text as headline if short enough, else filename
    if visible_text and len(visible_text) < 120:
        blocks.append({"type": "heading", "level": 1, "text": visible_text})
    else:
        blocks.append({"type": "heading", "level": 1, "text": name})

    if description:
        blocks.append({"type": "paragraph", "text": description})

    if visible_text and len(visible_text) >= 120:
        blocks.append({"type": "paragraph", "text": visible_text})

    return {
        "blocks": blocks,
        "images": [{"b64": b64, "mime": mime}],
        "vision": vision_data,
    }
