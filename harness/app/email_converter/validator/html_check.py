import re


FORBIDDEN = [

    r"governance",

    r"co.?brand lock.?up",

    r"parent guidelines",

    r"brand_guidelines",

    r"approval required",

    r"internal use",

    r"##\s",

    r"\*\*",
]


def validate_html(
    html: str,
):

    issues = []

    if (
        "<html"
        not in html.lower()
    ):

        issues.append((
            "HTML_MISSING_ROOT",
            "Missing <html> root element.",
        ))

    for pattern in FORBIDDEN:

        if re.search(
            pattern,
            html,
            re.IGNORECASE,
        ):

            issues.append((
                "INTERNAL_CONTENT_LEAK",
                (
                    "Forbidden source/internal "
                    f"content matched: {pattern}"
                ),
            ))

    return issues