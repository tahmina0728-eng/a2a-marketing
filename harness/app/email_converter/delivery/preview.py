"""
Preview — packages the HTML for browser preview.

The frontend receives the raw HTML string and renders it in an iframe.
This module provides the data URI helper used by the download path
and any server-side preview generation needed.
"""
from __future__ import annotations
import base64


def to_data_uri(html: str) -> str:
    """Return a data: URI that can be set as an iframe src."""
    encoded = base64.b64encode(html.encode("utf-8")).decode()
    return f"data:text/html;base64,{encoded}"


def preview_payload(html: str, filename: str = "email-preview.html") -> dict:
    """
    Return a dict ready to include in the API response.
    The frontend EmailConverter renders slots["html"] directly in an iframe,
    so this is mainly used when a separate preview endpoint is needed.
    """
    return {
        "html":      html,
        "data_uri":  to_data_uri(html),
        "filename":  filename,
    }
