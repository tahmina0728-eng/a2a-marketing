from __future__ import annotations

import base64
import mimetypes


def parse(
    raw: bytes,
    filename: str,
    use_vision: bool = True,
    gcp_project: str = "",
    **kwargs,
) -> dict:

    mime = (
        mimetypes.guess_type(
            filename
        )[0]
        or "image/jpeg"
    )

    image = {

        "filename":
            filename,

        "mime":
            mime,

        "b64":
            base64.b64encode(
                raw
            ).decode("ascii"),
    }

    context = {}

    if (
        use_vision
        and gcp_project
    ):

        context = _analyse_image(
            raw,
            mime,
            filename,
            gcp_project,
        )

    return {

        "blocks":
            [],

        "images":
            [image],

        "image_context":
            (
                [context]
                if context
                else []
            ),
    }


def _analyse_image(
    raw: bytes,
    mime: str,
    filename: str,
    project: str,
) -> dict:

    try:

        import json
        import re

        from google import genai

        from app.config import (
            get_settings,
        )

        settings = (
            get_settings()
        )

        location = (
            settings.gcp_region
            or "global"
        )

        model = (
            settings.gemini_model_reasoning
            or "gemini-2.0-flash"
        )

        client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

        prompt = """
Analyse this marketing image.

Return only JSON:

{
  "semantic_title": "",
  "semantic_tagline": "",
  "description": "",
  "contains_prominent_text": false
}

semantic_title:
The visible campaign/product/event title.

semantic_tagline:
The visible marketing tagline if one exists.

description:
A short semantic description of the visual.

contains_prominent_text:
true when the artwork already contains a major
headline/title/tagline that would make adding another
large headline above it visually repetitive.

Do not infer unsupported campaign claims.
"""

        response = (
            client.models.generate_content(
                model=model,
                contents=[
                    prompt,
                    genai.types.Part.from_bytes(
                        data=raw,
                        mime_type=mime,
                    ),
                ],
            )
        )

        text = (
            response.text
            or ""
        ).strip()

        text = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            text,
            flags=re.MULTILINE,
        ).strip()

        return json.loads(
            text
        )

    except Exception:

        return {}