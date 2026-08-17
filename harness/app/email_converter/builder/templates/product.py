from __future__ import annotations

from ..helpers import escape

from ..base import (
    dual_brand_header,
    para_block,
    cta_button_wide,
    footer_simple,
    html_shell,
)


def render(
    slots,
    brand_name="",
    brand_color="#0055A4",
    multi_file=False,
):

    rows = dual_brand_header(

        brand_name,

        slots.get(
            "partner_name",
            "",
        ),

        brand_color,
    )

    if slots.get(
        "headline"
    ):

        rows += para_block(
            slots["headline"],
            lead=True,
        )

    images = slots.get(
        "images",
        [],
    )[:2]

    if images:

        cells = ""

        for image in images:

            cells += f"""
<td
    width="50%"
    style="
        padding:8px;
    "
>

<img
    src="data:{image['mime']};base64,{image['b64']}"
    width="270"
    alt="{escape(brand_name)} image"
    style="
        width:100%;
        height:auto;
    "
>

</td>
"""

        rows += f"""
<tr>

<td>

<table
    width="100%"
    role="presentation"
>

<tr>

{cells}

</tr>

</table>

</td>

</tr>
"""

    for item in slots.get(
        "body",
        [],
    ):

        rows += para_block(
            item
        )

    if slots.get(
        "cta"
    ):

        rows += cta_button_wide(
            slots["cta"],
            brand_color,
        )

    rows += footer_simple(
        brand_name
    )

    return html_shell(

        slots.get(
            "subject",
            "",
        ),

        brand_color,

        rows,

        slots.get(
            "preheader",
            "",
        ),
    )