from __future__ import annotations

import structlog

from app.agents._utils import _generate

logger = structlog.get_logger()


def run_email_templates(brand: str, prompt: str, provided_image_b64: str = "") -> dict:
    """
    Standalone Email Templates agent.
    Generates 3 distinct HTML email layout variations for a campaign:
      1. Hero  — full-width image hero + headline + CTA
      2. Text-first  — bold headline, body copy, minimal design
      3. Product  — product showcase with features + promotional CTA

    Returns a list of templates ready to preview, edit and send via Mailchimp.
    """
    import base64 as _b64
    from app.brand_assets import get_asset_loader as _gal_e
    from app.creative_pipeline import _load_bytes as _lb_e

    # ── Step 1: Generate email copy via AI ───────────────────────────────────
    copy_data = _generate(
        "You are Ideon, the copy agent. Write email marketing copy for a campaign.",
        brand, prompt,
        'Respond ONLY with valid JSON: '
        '{"subject": "compelling email subject line", '
        '"preheader": "short inbox preview text (max 90 chars)", '
        '"headline": "bold email headline (max 8 words)", '
        '"subheadline": "supporting line (max 12 words)", '
        '"body": "1-2 sentences of persuasive body copy", '
        '"cta": "2-3 word call-to-action button", '
        '"footer_note": "short legal or offer note", '
        '"feature_1": "short product feature or benefit", '
        '"feature_2": "short product feature or benefit", '
        '"feature_3": "short product feature or benefit"}',
    )

    subject      = copy_data.get("subject",      f"{brand} — New Campaign")
    preheader    = copy_data.get("preheader",     "")
    headline     = copy_data.get("headline",      brand)
    subheadline  = copy_data.get("subheadline",   "")
    body         = copy_data.get("body",          "")
    cta          = copy_data.get("cta",           "Shop Now")
    footer_note  = copy_data.get("footer_note",   "")
    feat1        = copy_data.get("feature_1",     "")
    feat2        = copy_data.get("feature_2",     "")
    feat3        = copy_data.get("feature_3",     "")

    # ── Step 2: Load brand assets ─────────────────────────────────────────────
    loader  = _gal_e()
    _bslug  = brand.split()[0].lower()
    logo_b64 = ""
    # Use provided KV image if available; otherwise use a placeholder token
    # that the frontend replaces with result.image_b64 (avoids large POST body)
    hero_b64 = (f"data:image/jpeg;base64,{provided_image_b64}"
                if provided_image_b64 else "__KV_IMAGE__")

    try:
        logos = loader.list_logos(brand)
        if logos:
            _lu = (next((p for p in logos if "whitebg" in p.lower()), None)
                   or next((p for p in logos if _bslug in p.lower()), None)
                   or logos[0])
            lb = _lb_e(_lu)
            if lb:
                logo_b64 = f"data:image/png;base64,{_b64.b64encode(lb).decode()}"
    except Exception:
        pass

    prod_b64 = ""
    try:
        assets = loader.list_assets(brand) or loader.list_products(brand)
        # hero_b64 stays as "__KV_IMAGE__" — the frontend replaces it with
        # the Morphis-generated image. Never overwrite with a GCS asset here.
        if len(assets or []) > 1:
            pb = _lb_e(assets[1])
            if pb:
                prod_b64 = f"data:image/jpeg;base64,{_b64.b64encode(pb).decode()}"
    except Exception:
        pass

    # ── Step 3: Brand colours ─────────────────────────────────────────────────
    BRAND_PALETTE = {
        "Rnorr":       {"primary": "#006b35", "accent": "#ffd700", "bg": "#f5f5f0"},
        "Sunglow":     {"primary": "#c0007c", "accent": "#ffc82c", "bg": "#fff8f0"},
        "Boozt":       {"primary": "#0d1b4a", "accent": "#0086fe", "bg": "#f0f4ff"},
        "Glenfiddich": {"primary": "#0a6b65", "accent": "#b8d400", "bg": "#f0faf8"},
        "UBS Bank":    {"primary": "#e30613", "accent": "#1a1a1a", "bg": "#f9f9f9"},
    }
    pal  = BRAND_PALETTE.get(brand, {"primary": "#7c3aed", "accent": "#6366f1", "bg": "#f8f8ff"})
    col  = pal["primary"]
    acc  = pal["accent"]
    bg   = pal["bg"]

    logo_html = (f'<img src="{logo_b64}" alt="{brand}" '
                 f'style="height:44px;max-width:180px;object-fit:contain;">'
                 if logo_b64 else
                 f'<span style="font-size:22px;font-weight:900;color:{col};">{brand}</span>')

    # Always use __KV_IMAGE__ placeholder — frontend replaces with Morphis image.
    # The img tag uses __KV_IMAGE__ as src; if injection fails the alt text shows.
    hero_img = (f'<img src="{hero_b64}" alt="{brand}" '
                f'style="width:100%;display:block;border-radius:8px 8px 0 0;">')

    prod_img  = (f'<img src="{prod_b64}" alt="{brand}" '
                 f'style="width:100%;max-height:220px;object-fit:cover;border-radius:8px;">'
                 if prod_b64 else "")

    # ── Helper: shared email wrapper ──────────────────────────────────────────
    def _wrap(body_html: str, layout_name: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;overflow:hidden;background:{bg};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

  <!-- Header -->
  <div style="background:{col};padding:18px 32px;display:flex;align-items:center;justify-content:space-between;">
    {logo_html}
  </div>

  {body_html}

  <!-- Footer -->
  <div style="background:#f8f8f8;padding:24px 32px;border-top:1px solid #ececec;text-align:center;">
    {'<p style="margin:0 0 8px;font-size:12px;color:#888;">'+footer_note+'</p>' if footer_note else ''}
    <p style="margin:0;font-size:11px;color:#aaa;">
      © 2026 {brand}. You received this because you subscribed to our list.
      <a href="*|UNSUB|*" style="color:#7c3aed;text-decoration:none;">Unsubscribe</a>
    </p>
    <p style="margin:6px 0 0;font-size:10px;color:#ccc;">Sent via CampaignOS</p>
  </div>

</div>
</body></html>"""

    # ──────────────────────────────────────────────────────────────────────────
    # LAYOUT 1 — Hero: full-width image + headline + CTA
    # ──────────────────────────────────────────────────────────────────────────
    layout_hero = _wrap(f"""
  {hero_img}
  <div style="padding:40px 40px 32px;text-align:center;">
    <h1 style="margin:0 0 12px;font-size:30px;font-weight:900;color:{col};line-height:1.2;">{headline}</h1>
    <p style="margin:0 0 8px;font-size:16px;color:#555;font-style:italic;">{subheadline}</p>
    <p style="margin:0 0 32px;font-size:15px;color:#666;line-height:1.7;max-width:460px;margin-left:auto;margin-right:auto;">{body}</p>
    <a href="#" style="display:inline-block;padding:15px 40px;background:{col};color:white;
       border-radius:99px;font-size:15px;font-weight:800;text-decoration:none;
       letter-spacing:0.03em;box-shadow:0 4px 16px rgba(0,0,0,0.2);">{cta} →</a>
  </div>
""", "Hero")

    # ──────────────────────────────────────────────────────────────────────────
    # LAYOUT 2 — Text-first: headline + body + accent bar + CTA
    # ──────────────────────────────────────────────────────────────────────────
    layout_text = _wrap(f"""
  <div style="padding:48px 40px 16px;">
    <div style="width:48px;height:4px;background:{acc};border-radius:2px;margin-bottom:20px;"></div>
    <h1 style="margin:0 0 14px;font-size:28px;font-weight:900;color:#0f172a;line-height:1.25;">{headline}</h1>
    <p style="margin:0 0 20px;font-size:16px;color:{col};font-weight:600;">{subheadline}</p>
    <p style="margin:0 0 32px;font-size:15px;color:#475569;line-height:1.75;">{body}</p>
  </div>
  <img src="{hero_b64}" alt="{brand}" style="width:100%;max-height:280px;object-fit:cover;display:block;">
  <div style="padding:32px 40px 40px;text-align:center;">
    <a href="#" style="display:inline-block;padding:14px 36px;background:{col};color:white;
       border-radius:8px;font-size:15px;font-weight:700;text-decoration:none;">{cta}</a>
    <p style="margin:14px 0 0;font-size:12px;color:#999;">No commitment. Cancel anytime.</p>
  </div>
""", "Text-first")

    # ──────────────────────────────────────────────────────────────────────────
    # LAYOUT 3 — Product: 3 features + product image + CTA
    # ──────────────────────────────────────────────────────────────────────────
    features_html = "".join([
        f'<div style="flex:1;min-width:140px;padding:16px;background:{bg};border-radius:10px;text-align:center;">'
        f'<div style="font-size:22px;margin-bottom:8px;">{"✦" if i==0 else "★" if i==1 else "◆"}</div>'
        f'<p style="margin:0;font-size:13px;color:#374151;font-weight:600;line-height:1.5;">{f}</p></div>'
        for i, f in enumerate([feat1, feat2, feat3]) if f
    ])

    layout_product = _wrap(f"""
  <div style="padding:40px 40px 24px;text-align:center;">
    <h1 style="margin:0 0 10px;font-size:26px;font-weight:900;color:{col};">{headline}</h1>
    <p style="margin:0 0 28px;font-size:15px;color:#555;line-height:1.6;">{body}</p>
  </div>
  <div style="padding:0 32px;">
    <img src="{hero_b64}" alt="{brand}" style="width:100%;border-radius:8px;display:block;">
  </div>
  <div style="display:flex;gap:12px;flex-wrap:wrap;padding:24px 32px;">
    {features_html}
  </div>
  <div style="padding:8px 40px 40px;text-align:center;">
    <a href="#" style="display:inline-block;padding:14px 40px;background:linear-gradient(135deg,{col},{acc});
       color:white;border-radius:99px;font-size:15px;font-weight:800;text-decoration:none;
       box-shadow:0 4px 20px rgba(0,0,0,0.2);">{cta} →</a>
  </div>
""", "Product")

    templates = [
        {"id": "hero",    "name": "Hero",         "layout": "Hero — full image, bold CTA",       "html": layout_hero},
        {"id": "text",    "name": "Text-first",   "layout": "Text-first — clean, copy-led",      "html": layout_text},
        {"id": "product", "name": "Product",      "layout": "Product — features showcase, CTA",  "html": layout_product},
    ]

    logger.info("email_templates_generated", brand=brand, count=len(templates))

    return {
        "agent":      "email_templates",
        "brand":      brand,
        "subject":    subject,
        "preheader":  preheader,
        "templates":  templates,
        "copy":       copy_data,
        "headline":   headline,
        "body":       body,
    }
