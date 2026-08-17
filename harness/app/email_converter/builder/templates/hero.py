from __future__ import annotations

from typing import Any

from ..helpers import escape

from ..base import (
    dual_brand_header,
    eyebrow,
    body_headline,
    para_block,
    bullet_list,
    cta_button_wide,
    sub_footer_strip,
    footer_simple,
    html_shell,
)


def render(
    slots: dict[str, Any],
    brand_name: str = "",
    brand_color: str = "#0055A4",
    multi_file: bool = False,
) -> str:

    # ============================================================
    # SAFE CUSTOMER-FACING CONTENT ONLY
    # ============================================================

    subject = slots.get("subject", "")
    preheader = slots.get("preheader", "")

    partner = slots.get("partner_name", "")
    headline = slots.get("headline", "")
    subline = slots.get("subline", "")

    body = slots.get("body", [])
    highlights = slots.get("highlights", [])

    cta = slots.get("cta", "")
    legal_copy = slots.get("legal_copy", "")

    images = list(slots.get("images", []))

    hero_contains_text = bool(
        slots.get(
            "hero_contains_text",
            False,
        )
    )

    rows = ""

    # ============================================================
    # 1. SMALL BRAND HEADER
    #
    # Keep this compact.
    # Do not create a large campaign banner here.
    # ============================================================

    rows += dual_brand_header(
        brand_name=brand_name,
        partner_name=partner,
        brand_color=brand_color,
    )

    # ============================================================
    # 2. HERO IMAGE
    #
    # Image comes immediately after the header.
    #
    # This prevents:
    #
    # HEADER
    # LARGE BLUE TEXT PANEL
    # LARGE BLUE IMAGE AREA
    #
    # from visually merging into one oversized header.
    # ============================================================

    if images:

        hero = images.pop(0)

        hero_alt = (
            f"{brand_name} campaign"
            if brand_name
            else "Campaign image"
        )

        rows += f"""
        <tr>
          <td
            style="
              padding:0;
              margin:0;
              line-height:0;
              font-size:0;
              background:#ffffff;
            "
          >
            <img
              src="data:{hero['mime']};base64,{hero['b64']}"
              width="600"
              alt="{escape(hero_alt)}"
              style="
                display:block;
                width:100%;
                max-width:600px;
                height:auto;
                margin:0;
                padding:0;
                border:0;
              "
            />
          </td>
        </tr>
        """

    # ============================================================
    # 3. BODY EYEBROW
    #
    # Example:
    # BARCLAYS × THE CHAMPIONSHIPS, WIMBLEDON
    # ============================================================

    if brand_name or partner:

        if brand_name and partner:
            eyebrow_text = (
                f"{brand_name} × {partner}"
            )

        elif brand_name:
            eyebrow_text = brand_name

        else:
            eyebrow_text = partner

        rows += eyebrow(
            eyebrow_text,
            brand_color,
        )

    # ============================================================
    # 4. EMAIL HEADLINE
    #
    # The generated campaign/email headline now sits BELOW
    # the hero image instead of above it.
    #
    # This avoids competing with text already inside the artwork.
    # ============================================================

    if headline:

        rows += body_headline(
            headline
        )

    # ============================================================
    # 5. SUBLINE
    #
    # Render as lead paragraph rather than another huge heading.
    # ============================================================

    if subline:

        rows += para_block(
            subline,
            lead=True,
        )

    # ============================================================
    # 6. BODY CONTENT
    #
    # Keep hero email concise.
    # Max 2 paragraphs.
    # ============================================================

    clean_body = _clean_body(
        body,
        max_items=2,
    )

    for item in clean_body:

        rows += para_block(
            item,
            lead=False,
        )

    # ============================================================
    # 7. HIGHLIGHTS
    #
    # Up to 3 concise customer-facing bullets.
    # ============================================================

    clean_highlights = (
        _clean_highlights(
            highlights
        )
    )

    if clean_highlights:

        rows += bullet_list(
            clean_highlights,
            brand_color,
        )

    # ============================================================
    # 8. CTA
    # ============================================================

    if cta:

        rows += cta_button_wide(
            cta,
            brand_color,
        )

    # ============================================================
    # 9. ADDITIONAL IMAGES
    #
    # Normally hero template should have only one hero image.
    # But if extra safe campaign assets exist, render them below.
    # ============================================================

    for image in images:

        rows += _additional_image(
            image,
            brand_name,
        )

    # ============================================================
    # 10. SUPPORTING BRAND STRIP
    # ============================================================

    if partner:

        rows += sub_footer_strip(
            f"Supporting {partner}",
            brand_color,
        )

    # ============================================================
    # 11. LEGAL COPY
    # ============================================================

    if legal_copy:

        rows += _legal_block(
            legal_copy
        )

    # ============================================================
    # 12. STANDARD FOOTER
    # ============================================================

    rows += footer_simple(
        brand_name
    )

    # ============================================================
    # COMPLETE EMAIL
    # ============================================================

    return html_shell(
        subject=subject,
        brand_color=brand_color,
        inner_rows=rows,
        preheader=preheader,
    )


# =================================================================
# HELPERS
# =================================================================


def _clean_body(
    items: list[str],
    max_items: int = 2,
) -> list[str]:

    """
    Return only concise customer-facing paragraphs.

    Raw guideline/source material should already have been removed
    by the composer, but this keeps the hero renderer conservative.
    """

    cleaned = []

    for item in items:

        text = str(item).strip()

        if not text:
            continue

        # Ignore tiny fragments
        if len(text) < 15:
            continue

        # Prevent document-length paragraphs
        if len(text) > 500:
            text = (
                text[:497].rstrip()
                + "..."
            )

        cleaned.append(text)

        if len(cleaned) >= max_items:
            break

    return cleaned


def _clean_highlights(
    items: list[str],
) -> list[str]:

    """
    Max 3 short marketing highlights.
    """

    cleaned = []

    for item in items:

        text = str(item).strip()

        if not text:
            continue

        if len(text) > 120:

            text = (
                text[:117].rstrip()
                + "..."
            )

        cleaned.append(text)

        if len(cleaned) >= 3:
            break

    return cleaned


def _additional_image(
    image: dict,
    brand_name: str,
) -> str:

    alt = (
        f"{brand_name} campaign image"
        if brand_name
        else "Campaign image"
    )

    return f"""
    <tr>
      <td
        class="pad"
        style="
          padding:10px 40px 20px;
          line-height:0;
          font-size:0;
        "
      >
        <img
          src="data:{image['mime']};base64,{image['b64']}"
          width="520"
          alt="{escape(alt)}"
          style="
            display:block;
            width:100%;
            max-width:520px;
            height:auto;
            margin:0 auto;
            border:0;
          "
        />
      </td>
    </tr>
    """


def _legal_block(text: str) -> str:
    return f"""
    <tr>
      <td
        class="pad"
        style="
          padding:24px 40px;
          background:#f5f5f5;
          border-bottom:1px solid #e3e3e3;
        "
      >
        <p
          style="
            margin:0;
            color:#5f6368;
            font-family:Arial,Helvetica,sans-serif;
            font-size:12px;
            line-height:1.65;
          "
        >
          {escape(text)}
        </p>
      </td>
    </tr>
    """