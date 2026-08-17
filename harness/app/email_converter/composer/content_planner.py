from __future__ import annotations

from typing import Any


class ContentPlanner:

    """
    Operates only on already composed
    customer-facing email content.

    It never promotes arbitrary source
    document headings into email headlines.
    """

    def plan(
        self,
        slots: dict[str, Any],
    ) -> dict[str, Any]:

        slots = dict(slots)

        # --------------------------------
        # Normalise body
        # --------------------------------

        body = slots.get(
            "body",
            [],
        )

        if isinstance(
            body,
            str,
        ):

            body = (
                [body]
                if body.strip()
                else []
            )

        slots["body"] = [

            str(item).strip()

            for item in body

            if str(item).strip()
        ]

        # --------------------------------
        # Normalise highlights
        # --------------------------------

        highlights = slots.get(
            "highlights",
            [],
        )

        if isinstance(
            highlights,
            str,
        ):

            highlights = (
                [highlights]
                if highlights.strip()
                else []
            )

        slots["highlights"] = [

            str(item).strip()

            for item in highlights

            if str(item).strip()

        ][:3]

        # --------------------------------
        # Subject fallback
        # --------------------------------

        if (
            not slots.get("subject")
            and slots.get("headline")
        ):

            slots["subject"] = (
                slots["headline"][:55]
            )

        # --------------------------------
        # Preheader fallback
        # --------------------------------

        if not slots.get(
            "preheader"
        ):

            slots["preheader"] = (

                slots.get("subline")

                or slots.get("intro")

                or (
                    slots["body"][0][:120]
                    if slots["body"]
                    else ""
                )
            )

        return slots