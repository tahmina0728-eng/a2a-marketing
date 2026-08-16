"""
Download — prepares the HTML for file download.

The frontend already has a "Download .html" button that uses the html
string from the API response. This module handles the server-side
preparation when a dedicated /download endpoint is needed.
"""
from __future__ import annotations


def prepare(html: str, filename: str = "campaign-email.html") -> tuple[bytes, str]:
    """
    Returns (content_bytes, content_type) ready for a FastAPI FileResponse
    or a StreamingResponse.

    Usage in a FastAPI route:
        content, ctype = prepare(html, "my-campaign.html")
        return Response(content=content, media_type=ctype,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    """
    content_bytes = html.encode("utf-8")
    return content_bytes, "text/html; charset=utf-8"
