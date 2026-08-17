from __future__ import annotations

from typing import Any


def safe_get(
    data: dict[str, Any],
    key: str,
    default=None,
):
    value = data.get(key, default)

    return default if value is None else value