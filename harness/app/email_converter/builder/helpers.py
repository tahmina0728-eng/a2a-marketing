from __future__ import annotations

import html


def escape(
    value,
) -> str:

    return html.escape(
        str(value or ""),
        quote=True,
    )


def _hex_to_rgb(
    value: str,
):

    value = value.lstrip("#")

    if len(value) != 6:

        return (
            0,
            85,
            164,
        )

    return tuple(

        int(
            value[i:i + 2],
            16,
        )

        for i in (
            0,
            2,
            4,
        )
    )


def darken(
    value: str,
    factor: float = 0.8,
) -> str:

    r, g, b = (
        _hex_to_rgb(value)
    )

    return "#{:02X}{:02X}{:02X}".format(

        max(
            0,
            min(
                255,
                int(r * factor),
            ),
        ),

        max(
            0,
            min(
                255,
                int(g * factor),
            ),
        ),

        max(
            0,
            min(
                255,
                int(b * factor),
            ),
        ),
    )


def text_on(
    value: str,
) -> str:

    r, g, b = (
        _hex_to_rgb(value)
    )

    luminance = (
        0.299 * r
        + 0.587 * g
        + 0.114 * b
    )

    return (
        "#000000"
        if luminance > 180
        else "#FFFFFF"
    )