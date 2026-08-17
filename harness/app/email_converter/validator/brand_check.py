def validate_brand(
    html: str,
    brand_name: str,
    brand_guidelines=None,
):

    issues = []

    if (
        brand_name
        and brand_name.lower()
        not in html.lower()
    ):

        issues.append((
            "BRAND_NAME_MISSING",
            (
                "Brand name is not visible "
                "in rendered email."
            ),
        ))

    return issues