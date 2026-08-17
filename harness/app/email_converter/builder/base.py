from __future__ import annotations

from .helpers import (
    escape,
    darken,
    text_on,
)


def eyebrow(
    label: str,
    brand_color: str,
) -> str:

    return f"""
<tr>
<td
    class="pad"
    style="
        padding:28px 40px 10px;
    "
>
    <p
        style="
            margin:0;
            font-size:11px;
            font-weight:800;
            letter-spacing:.11em;
            text-transform:uppercase;
            color:{brand_color};
            font-family:Arial,sans-serif;
        "
    >
        {escape(label)}
    </p>
</td>
</tr>
"""


def para_block(
    text: str,
    lead: bool = False,
) -> str:

    size = (
        "17px"
        if lead
        else "15.5px"
    )

    weight = (
        "500"
        if lead
        else "400"
    )

    return f"""
<tr>
<td
    class="pad"
    style="
        padding:0 40px 16px;
    "
>
    <p
        style="
            margin:0;
            font-size:{size};
            line-height:1.7;
            color:#333;
            font-weight:{weight};
            font-family:Arial,sans-serif;
        "
    >
        {escape(text)}
    </p>
</td>
</tr>
"""


def bullet_list(
    items: list[str],
    brand_color: str,
) -> str:

    rows = ""

    for item in items:

        rows += f"""
<tr>

<td
    width="24"
    valign="top"
    style="
        padding:2px 0 12px;
    "
>
    <span
        style="
            color:{brand_color};
            font-size:18px;
        "
    >
        •
    </span>
</td>

<td
    style="
        padding:0 0 12px;
        font:15px/1.6 Arial,sans-serif;
        color:#333;
    "
>
    {escape(item)}
</td>

</tr>
"""

    return f"""
<tr>

<td
    class="pad"
    style="
        padding:4px 40px 10px;
    "
>

<table
    width="100%"
    role="presentation"
>

{rows}

</table>

</td>

</tr>
"""


def body_headline(
    text: str,
) -> str:

    return f"""
<tr>

<td
    class="pad"
    style="
        padding:8px 40px 18px;
    "
>

<h1
    style="
        margin:0;
        font-size:28px;
        line-height:1.25;
        color:#111;
        font-family:Arial,sans-serif;
    "
>
    {escape(text)}
</h1>

</td>

</tr>
"""


def dual_brand_header(
    brand_name: str,
    partner_name: str,
    brand_color: str,
) -> str:

    on_brand = (
        text_on(
            brand_color
        )
    )

    partner_cell = ""

    if partner_name:

        partner_cell = f"""
<td
    align="right"
    style="
        font:700 13px Arial,sans-serif;
        color:{on_brand};
    "
>
    {escape(partner_name.upper())}
</td>
"""

    else:

        partner_cell = (
            "<td></td>"
        )

    return f"""
<tr>

<td
    class="pad"
    style="
        background:{brand_color};
        padding:18px 40px;
    "
>

<table
    width="100%"
    role="presentation"
>

<tr>

<td
    style="
        font:800 14px Arial,sans-serif;
        color:{on_brand};
        letter-spacing:.08em;
    "
>
    {escape((brand_name or "BRAND").upper())}
</td>

{partner_cell}

</tr>

</table>

</td>

</tr>
"""


def hero_text_band(
    headline: str,
    subline: str,
    brand_color: str,
) -> str:

    on_brand = (
        text_on(
            brand_color
        )
    )

    dark = darken(
        brand_color,
        0.78,
    )

    return f"""
<tr>

<td
    class="pad"
    style="
        background:{dark};
        padding:36px 40px;
        text-align:center;
    "
>

<h2
    style="
        margin:0 0 10px;
        font:800 28px/1.2 Arial,sans-serif;
        color:{on_brand};
    "
>
    {escape(headline)}
</h2>

<p
    style="
        margin:0;
        font:16px/1.5 Arial,sans-serif;
        color:{on_brand};
    "
>
    {escape(subline)}
</p>

</td>

</tr>
"""


def cta_button_wide(
    label: str,
    brand_color: str,
) -> str:

    on_brand = (
        text_on(
            brand_color
        )
    )

    return f"""
<tr>

<td
    align="center"
    class="pad"
    style="
        padding:30px 40px;
    "
>

<a
    href="#"
    style="
        display:inline-block;
        background:{brand_color};
        color:{on_brand};
        text-decoration:none;
        font:800 14px Arial,sans-serif;
        padding:16px 44px;
        border-radius:4px;
    "
>
    {escape(label)}
</a>

</td>

</tr>
"""


def sub_footer_strip(
    text: str,
    brand_color: str,
) -> str:

    dark = darken(
        brand_color,
        0.76,
    )

    on_dark = text_on(
        dark
    )

    return f"""
<tr>

<td
    class="pad"
    style="
        background:{dark};
        padding:20px 40px;
        color:{on_dark};
        font:13px/1.5 Arial,sans-serif;
    "
>
    {escape(text)}
</td>

</tr>
"""


def footer_simple(
    brand_name: str,
) -> str:

    label = escape(
        brand_name or "Campaign"
    )

    return f"""
    <tr>
      <td
        align="center"
        style="
          padding:22px 40px 26px;
          background:#f7f7f7;
          border-top:1px solid #e5e5e5;
          font-family:Arial,Helvetica,sans-serif;
          color:#666666;
        "
      >

        <p
          style="
            margin:0 0 8px;
            font-size:12px;
            line-height:1.5;
          "
        >
          <a
            href="#"
            style="
              color:#666666;
              text-decoration:underline;
            "
          >
            Privacy
          </a>

          &nbsp;&nbsp;|&nbsp;&nbsp;

          <a
            href="#"
            style="
              color:#666666;
              text-decoration:underline;
            "
          >
            Terms
          </a>

          &nbsp;&nbsp;|&nbsp;&nbsp;

          <a
            href="#"
            style="
              color:#666666;
              text-decoration:underline;
            "
          >
            Unsubscribe
          </a>
        </p>

        <p
          style="
            margin:0;
            font-size:12px;
            line-height:1.5;
            color:#777777;
          "
        >
          &copy; 2026 {label}. All rights reserved.
        </p>

      </td>
    </tr>
    """


def html_shell(
    subject: str,
    brand_color: str,
    inner_rows: str,
    preheader: str = "",
) -> str:

    preheader_html = ""

    if preheader:

        preheader_html = f"""
<div
    style="
        display:none;
        max-height:0;
        overflow:hidden;
        mso-hide:all;
    "
>
    {escape(preheader)}
</div>
"""

    return f"""<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1.0"
>

<title>
    {escape(subject)}
</title>

<style>

body {{
    margin:0;
    padding:0;
    background:#ebebeb;
    -webkit-text-size-adjust:100%;
}}

table {{
    border-collapse:collapse;
}}

img {{
    border:0;
    display:block;
}}

@media(max-width:640px) {{

    .wrap {{
        width:100%!important;
    }}

    .pad {{
        padding-left:24px!important;
        padding-right:24px!important;
    }}
}}

</style>

</head>

<body>

{preheader_html}

<table
    width="100%"
    role="presentation"
    style="
        background:#ebebeb;
    "
>

<tr>

<td
    align="center"
    style="
        padding:28px 16px 48px;
    "
>

<table
    class="wrap"
    width="600"
    role="presentation"
    style="
        width:600px;
        max-width:600px;
        background:#fff;
    "
>

{inner_rows}

</table>

</td>

</tr>

</table>

</body>

</html>
"""