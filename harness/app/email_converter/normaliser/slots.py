from __future__ import annotations

from typing import Any


def _detect_slot(
    text: str,
) -> str | None:

    lower = text.lower().strip()

    mapping = {

        "subject": (
            "subject:",
            "email subject:",
            "subject line:",
        ),

        "preheader": (
            "preheader:",
            "preview text:",
            "preview:",
        ),

        "headline": (
            "headline:",
        ),

        "subline": (
            "subline:",
            "subtitle:",
            "tagline:",
        ),

        "cta": (
            "cta:",
            "call to action:",
            "button:",
            "action:",
        ),
    }

    for slot, prefixes in mapping.items():

        if any(
            lower.startswith(prefix)
            for prefix in prefixes
        ):
            return slot

    return None


def _strip_label(
    text: str,
) -> str:

    idx = text.find(":")

    return (
        text[idx + 1:].strip()
        if idx != -1
        else text.strip()
    )


def map_slots(
    parsed: dict,
    filename: str = "",
) -> dict[str, Any]:

    """
    Convert parsed content into SOURCE slots.

    Generic document headings are NOT promoted
    automatically to email headline/subline.
    """

    slots = {

        "subject": "",

        "preheader": "",

        "headline": "",

        "subline": "",

        "body": [],

        "cta": "",

        "tables": [],

        "images": parsed.get(
            "images",
            [],
        ),

        "_source_filename":
            filename,

        "_image_context":
            parsed.get(
                "image_context",
                [],
            ),
    }

    for block in parsed.get(
        "blocks",
        [],
    ):

        btype = block.get(
            "type"
        )

        # ----------------------------------
        # Tables
        # ----------------------------------

        if btype == "table":

            slots["tables"].append({

                "headers":
                    block.get(
                        "headers",
                        [],
                    ),

                "rows":
                    block.get(
                        "rows",
                        [],
                    ),
            })

            continue

        # ----------------------------------
        # Text
        # ----------------------------------

        text = str(
            block.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        explicit_slot = (
            _detect_slot(text)
        )

        if explicit_slot:

            slots[
                explicit_slot
            ] = _strip_label(
                text
            )

        else:

            # Generic document text remains
            # SOURCE MATERIAL.

            slots["body"].append(
                text
            )

    return slots


def merge_slots_list(
    slots_list: list[dict],
    filenames: list[str],
) -> dict[str, Any]:

    """
    Merge multiple files into ONE source context.

    Important:

    3 uploaded files != 3 email sections.

    They are simply three sources from which the
    composer creates one coherent email.
    """

    if not slots_list:

        return map_slots({
            "blocks": [],
            "images": [],
        })

    merged = {

        "subject": "",

        "preheader": "",

        "headline": "",

        "subline": "",

        "cta": "",

        "body": [],

        "tables": [],

        "images": [],

        "_source_files": [],

        "_image_context": [],
    }

    for slots, fname in zip(
        slots_list,
        filenames,
    ):

        # Metadata only.
        # Never rendered by templates.

        merged[
            "_source_files"
        ].append({
            "filename": fname
        })

        merged["body"].extend(
            slots.get(
                "body",
                [],
            )
        )

        merged["tables"].extend(
            slots.get(
                "tables",
                [],
            )
        )

        merged["images"].extend(
            slots.get(
                "images",
                [],
            )
        )

        merged[
            "_image_context"
        ].extend(
            slots.get(
                "_image_context",
                [],
            )
        )

        # Only explicit email fields
        # are carried forward.

        for key in (
            "subject",
            "preheader",
            "headline",
            "subline",
            "cta",
        ):

            if (
                not merged.get(key)
                and slots.get(key)
            ):

                merged[key] = (
                    slots[key]
                )

    merged["images"] = (
        merged["images"][:10]
    )

    return merged