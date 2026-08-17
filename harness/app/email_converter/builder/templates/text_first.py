from __future__ import annotations

from ..base import (
    dual_brand_header,
    hero_text_band,
    para_block,
    bullet_list,
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

    partner = slots.get(
        "partner_name",
        "",
    )

    rows = dual_brand_header(
        brand_name,
        partner,
        brand_color,
    )

    rows += hero_text_band(

        slots.get(
            "headline",
            "",
        ),

        slots.get(
            "subline",
            "",
        ),

        brand_color,
    )

    for index, item in enumerate(
        slots.get(
            "body",
            [],
        )
    ):

        rows += para_block(
            item,
            lead=(
                index == 0
            ),
        )

    if slots.get(
        "highlights"
    ):

        rows += bullet_list(
            slots["highlights"],
            brand_color,
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