from .hero import (
    render as render_hero,
)

from .text_first import (
    render as render_text_first,
)

from .product import (
    render as render_product,
)


def render(
    slots,
    brand_name="",
    brand_color="#0055A4",
    multi_file=False,
):

    template = slots.get(
        "_template",
        "hero",
    )

    if template == "text_first":

        return render_text_first(
            slots,
            brand_name,
            brand_color,
            multi_file,
        )

    if template == "product":

        return render_product(
            slots,
            brand_name,
            brand_color,
            multi_file,
        )

    return render_hero(
        slots,
        brand_name,
        brand_color,
        multi_file,
    )