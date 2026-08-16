"""
Shared HTML email rendering primitives used by all template renderers.

All functions return inline <tr>…</tr> strings ready to drop into a
containing <table role="presentation"> wrapper.
"""
from __future__ import annotations
from .helpers import escape, darken, text_on


# ── Content blocks ─────────────────────────────────────────────────────────────

def eyebrow(label: str, brand_color: str) -> str:
    return (
        f'<tr><td style="padding:28px 40px 10px;" class="pad">'
        f'<p style="margin:0;font-size:11px;font-weight:800;letter-spacing:.11em;'
        f'text-transform:uppercase;color:{brand_color};'
        f'font-family:Helvetica,Arial,sans-serif;">{escape(label)}</p>'
        f'</td></tr>'
    )


def para_block(text: str, lead: bool = False) -> str:
    sz  = "17px" if lead else "15.5px"
    fw  = "500"  if lead else "400"
    col = "#333333" if lead else "#454545"
    return (
        f'<tr><td style="padding:0 40px 16px;" class="pad">'
        f'<p style="margin:0;font-size:{sz};line-height:1.8;color:{col};font-weight:{fw};'
        f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">"
        f'{escape(text)}</p></td></tr>'
    )


def subhead_block(text: str, brand_color: str) -> str:
    return (
        f'<tr><td style="padding:20px 40px 6px;" class="pad">'
        f'<p style="margin:0;font-size:13px;font-weight:800;letter-spacing:.05em;'
        f'text-transform:uppercase;color:{brand_color};'
        f"font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">"
        f'{escape(text)}</p></td></tr>'
    )


def bullet_list(items: list[str], brand_color: str) -> str:
    rows = ""
    for item in items:
        rows += (
            f'<tr>'
            f'<td width="28" valign="top" style="padding-bottom:13px;padding-top:2px;">'
            f'<table cellpadding="0" cellspacing="0"><tr>'
            f'<td style="width:8px;height:8px;background:{brand_color};'
            f'border-radius:50%;font-size:0;line-height:0;">&nbsp;</td>'
            f'</tr></table></td>'
            f'<td style="padding-bottom:13px;font-size:15px;line-height:1.7;'
            f"color:#333333;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;\">"
            f'{escape(item)}</td></tr>'
        )
    return (
        f'<tr><td style="padding:4px 40px 4px;" class="pad">'
        f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
        f'</td></tr>'
    )


def table_block(tbl: dict, brand_color: str) -> str:
    headers   = tbl.get("headers", [])
    rows      = tbl.get("rows", [])
    on_brand  = text_on(brand_color)
    if not headers and not rows:
        return ""
    th_cells = "".join(
        f'<th style="background:{brand_color};color:{on_brand};padding:11px 14px;'
        f'text-align:left;font-size:12px;font-weight:700;white-space:nowrap;'
        f'font-family:Helvetica,Arial,sans-serif;">{escape(str(h))}</th>'
        for h in headers
    )
    tbody_rows = ""
    for i, row in enumerate(rows[:50]):
        bg  = "#f7f8fc" if i % 2 == 0 else "#ffffff"
        tds = "".join(
            f'<td style="padding:10px 14px;font-size:13px;color:#444444;'
            f'border-bottom:1px solid #eeeeee;'
            f'font-family:Helvetica,Arial,sans-serif;">{escape(str(c))}</td>'
            for c in row
        )
        tbody_rows += f'<tr style="background:{bg};">{tds}</tr>'
    note = (
        f'<p style="margin:6px 0 0;font-size:11px;color:#999;'
        f'font-family:Helvetica,Arial,sans-serif;">Showing 50 of {len(rows)} rows.</p>'
        if len(rows) > 50 else ""
    )
    return (
        f'<tr><td style="padding:12px 40px 4px;" class="pad">'
        f'<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;">'
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;border:1px solid #e8e8e8;min-width:300px;">'
        f'<thead><tr>{th_cells}</tr></thead><tbody>{tbody_rows}</tbody></table>'
        f'</div>{note}</td></tr>'
    )


def section_divider(label: str, brand_color: str) -> str:
    return (
        f'<tr><td style="padding:28px 40px 0;" class="pad">'
        f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="border-top:1px solid #e8e8e8;font-size:0;">&nbsp;</td>'
        f'</tr></table></td></tr>'
        f'<tr><td style="padding:16px 40px 4px;" class="pad">'
        f'<table cellpadding="0" cellspacing="0"><tr>'
        f'<td style="background:{brand_color};width:3px;border-radius:3px;">&nbsp;</td>'
        f'<td style="padding-left:12px;font-size:12px;font-weight:800;'
        f'letter-spacing:.08em;text-transform:uppercase;color:#777777;'
        f'font-family:Helvetica,Arial,sans-serif;">{escape(label)}</td>'
        f'</tr></table></td></tr>'
    )


def inline_image(img: dict, width: int = 520) -> str:
    return (
        f'<tr><td style="padding:16px 40px 0;" class="pad">'
        f'<img src="data:{img["mime"]};base64,{img["b64"]}" alt="" width="{width}"'
        f' style="display:block;width:100%;max-width:{width}px;height:auto;'
        f'border-radius:6px;border:1px solid #eeeeee;" /></td></tr>'
    )


def cta_button(label: str, brand_color: str) -> str:
    on_brand = text_on(brand_color)
    return f"""
        <tr>
          <td align="center" style="padding:36px 40px 12px;">
            <!--[if mso]>
            <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
              href="#" style="height:52px;v-text-anchor:middle;width:240px;"
              arcsize="10%" stroke="f" fillcolor="{brand_color}">
            <w:anchorlock/><center><![endif]-->
            <a href="#"
               style="display:inline-block;background:{brand_color};color:{on_brand};
                      font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                      font-size:16px;font-weight:800;text-decoration:none;
                      padding:16px 50px;border-radius:8px;letter-spacing:.03em;">
              {escape(label)}&nbsp;&rarr;
            </a>
            <!--[if mso]></center></v:roundrect><![endif]-->
          </td>
        </tr>
        <tr><td style="height:16px;font-size:0;">&nbsp;</td></tr>"""


def brand_header(brand_name: str, brand_color: str) -> str:
    on_brand = text_on(brand_color)
    dark_col = darken(brand_color, 0.82)
    label    = escape(brand_name) if brand_name else "CampaignOS"
    return f"""
        <tr>
          <td style="background:{brand_color};">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:18px 40px;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <p style="margin:0;font-size:17px;font-weight:900;
                           letter-spacing:.09em;text-transform:uppercase;color:{on_brand};
                           font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
                          {label}
                        </p>
                      </td>
                      <td align="right">
                        <p style="margin:0;font-size:10px;color:{on_brand};opacity:.65;
                           font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                           letter-spacing:.07em;text-transform:uppercase;">
                          Campaign&nbsp;Update
                        </p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="height:3px;background:{dark_col};font-size:0;">&nbsp;</td>
              </tr>
            </table>
          </td>
        </tr>"""


def footer(brand_name: str) -> str:
    label = escape(brand_name) if brand_name else "CampaignOS"
    return f"""
        <tr>
          <td style="border-top:1px solid #e8e8e8;padding:28px 40px 36px;">
            <p style="margin:0 0 10px;font-size:12px;color:#aaaaaa;text-align:center;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;line-height:1.7;">
              You are receiving this because you subscribed to {label} updates.
            </p>
            <p style="margin:0 0 12px;font-size:12px;color:#aaaaaa;text-align:center;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
              <a href="#" style="color:#aaaaaa;text-decoration:underline;">Unsubscribe</a>
              &nbsp;&middot;&nbsp;
              <a href="#" style="color:#aaaaaa;text-decoration:underline;">Privacy&nbsp;Policy</a>
              &nbsp;&middot;&nbsp;
              <a href="#" style="color:#aaaaaa;text-decoration:underline;">View&nbsp;in&nbsp;browser</a>
            </p>
            <p style="margin:0;font-size:11px;color:#cccccc;text-align:center;
               font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
              &copy; 2026 {label}. Powered by CampaignOS.
            </p>
          </td>
        </tr>"""


def html_shell(
    subject: str,
    brand_color: str,
    inner_rows: str,
    preheader: str = "",
) -> str:
    """Wrap inner table rows in a complete, email-client-safe HTML document."""
    ph = (
        f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;'
        f'font-size:1px;color:#f5f5f5;line-height:1px;">'
        f'{escape(preheader)}&nbsp;' + '&#847;&nbsp;' * 80 + '</div>'
        if preheader else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>{escape(subject)}</title>
  <!--[if mso]>
  <noscript><xml><o:OfficeDocumentSettings>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings></xml></noscript>
  <![endif]-->
  <style>
    body{{margin:0;padding:0;background:#ebebeb;-webkit-text-size-adjust:100%;}}
    img{{border:0;outline:none;text-decoration:none;display:block;}}
    table{{border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;}}
    a{{color:{brand_color};}}
    @media only screen and (max-width:640px){{
      .wrap{{width:100%!important;max-width:100%!important;}}
      .pad{{padding-left:24px!important;padding-right:24px!important;}}
      h1{{font-size:26px!important;line-height:1.25!important;}}
      .col2{{display:block!important;width:100%!important;max-width:100%!important;margin-bottom:12px!important;}}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#ebebeb;">
{ph}
<table width="100%" cellpadding="0" cellspacing="0"
  style="background:#ebebeb;min-width:280px;" role="presentation">
  <tr>
    <td align="center" style="padding:28px 16px 48px;">
      <table class="wrap" width="600" cellpadding="0" cellspacing="0"
        style="background:#ffffff;border-radius:10px;overflow:hidden;
               box-shadow:0 4px 32px rgba(0,0,0,.14);" role="presentation">
        {inner_rows}
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""
