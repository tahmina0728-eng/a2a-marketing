def validate_compliance(
    html: str,
    slots: dict,
):

    issues = []

    if (
        "unsubscribe"
        not in html.lower()
    ):

        issues.append((
            "UNSUBSCRIBE_MISSING",
            (
                "Email footer should include "
                "an unsubscribe link."
            ),
        ))

    if not slots.get(
        "preheader"
    ):

        issues.append((
            "PREHEADER_MISSING",
            (
                "Email preheader is empty."
            ),
        ))

    return issues