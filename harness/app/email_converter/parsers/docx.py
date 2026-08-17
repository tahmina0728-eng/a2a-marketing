def parse(
    raw: bytes,
    filename: str,
    **kwargs,
) -> dict:

    import io

    try:

        from docx import Document

    except ImportError as exc:

        raise RuntimeError(
            "Install python-docx"
        ) from exc

    document = Document(
        io.BytesIO(raw)
    )

    blocks = []

    for paragraph in (
        document.paragraphs
    ):

        text = (
            paragraph.text.strip()
        )

        if not text:
            continue

        style = (
            (
                paragraph.style.name
                or ""
            ).lower()
            if paragraph.style
            else ""
        )

        if style.startswith(
            "heading"
        ):

            try:

                level = int(
                    style.split()[-1]
                )

            except Exception:

                level = 1

            blocks.append({

                "type":
                    "heading",

                "level":
                    level,

                "text":
                    text,
            })

        else:

            blocks.append({

                "type":
                    "paragraph",

                "text":
                    text,
            })

    return {

        "blocks":
            blocks,

        "images":
            [],

        "image_context":
            [],
    }