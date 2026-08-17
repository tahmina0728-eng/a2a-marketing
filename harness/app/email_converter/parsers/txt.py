def parse(
    raw: bytes,
    filename: str,
    **kwargs,
) -> dict:

    text = raw.decode(
        "utf-8",
        errors="replace",
    )

    blocks = []

    for line in text.splitlines():

        value = line.strip()

        if not value:
            continue

        if value.startswith("#"):

            level = (
                len(value)
                - len(
                    value.lstrip("#")
                )
            )

            blocks.append({

                "type":
                    "heading",

                "level":
                    level,

                "text":
                    value
                    .lstrip("#")
                    .strip(),
            })

        else:

            blocks.append({

                "type":
                    "paragraph",

                "text":
                    value,
            })

    return {

        "blocks":
            blocks,

        "images":
            [],

        "image_context":
            [],
    }