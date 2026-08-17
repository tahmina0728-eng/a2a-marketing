def preview_payload(
    html: str,
    subject: str = "",
) -> dict:

    return {
        "subject": subject,
        "html": html,
    }