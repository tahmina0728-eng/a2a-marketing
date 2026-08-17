from __future__ import annotations

from typing import Any

from ..rag.template_library import (
    TemplateLibrary,
)


class LayoutPlanner:

    def __init__(self):

        self._library = (
            TemplateLibrary()
        )

    def plan(
        self,
        slots: dict[str, Any],
        use_llm: bool = False,
        llm_fn=None,
    ) -> dict[str, Any]:

        slots = dict(slots)

        if slots.get(
            "_template"
        ) in (
            "hero",
            "text_first",
            "product",
        ):

            return slots

        template = (
            self._library.select(
                slots
            )
        )

        if (
            use_llm
            and callable(llm_fn)
        ):

            try:

                candidate = llm_fn(
                    slots,
                    [
                        "hero",
                        "text_first",
                        "product",
                    ],
                )

                if candidate in (
                    "hero",
                    "text_first",
                    "product",
                ):

                    template = (
                        candidate
                    )

            except Exception:
                pass

        slots[
            "_template"
        ] = template

        return slots