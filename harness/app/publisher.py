"""
publisher.py — Campaign distribution to Google Ads, Brand Landing Page, and Email.

For demo purposes:
  - Google Ads : mock submission with realistic preview data
  - Landing Page: generate branded HTML and store in memory (served at /landing/{id})
  - Email       : send HTML email via SMTP (Gmail app password)
"""

import os
import base64
import textwrap
import io
import structlog

logger = structlog.get_logger()

# ── Brand visual config (from official brand guidelines) ──────────────────────
BRAND_CONFIG: dict[str, dict] = {
    # Sunglow: #B00064 Magenta master | #950155 Deep Magenta | #F9F9F9 Off-White | Alatsi font
    "Sunglow": {
        "primary":    "#B00064",   # Sunglow Magenta (master brand colour)
        "secondary":  "#950155",   # Deep Magenta (depth/outline/emphasis)
        "accent":     "#FFC72C",   # Sunshine Yellow (Moisture range accent)
        "accent2":    "#F26E36",   # Glow Orange (Strength range)
        "text":       "#ffffff",
        "body_bg":    "#F9F9F9",   # Off-White (brand neutral base)
        "section_bg": "#fff0f6",   # soft magenta tint
        "font":       "'Alatsi', sans-serif",
        "font_url":   "https://fonts.googleapis.com/css2?family=Alatsi&display=swap",
        "tagline":    "Let it glow.",
        "hero_tag":   "✨ Made for Black Hair",
        "copy":       "Hair care formulated for Black hair from the start — never adapted, never an afterthought. Every texture. Every glow.",
        "features":   ["Made for Black Hair", "Real Glow", "Every Texture", "No Rescue Narratives"],
    },
    # Rnorr: #008641 Green | #FFDE00 Yellow | #FFFFFF White | Antonio (display) + Rubik (body)
    "Rnorr": {
        "primary":    "#008641",   # Rnorr Green (PMS 356 C)
        "secondary":  "#005c2c",   # darker green for overlays
        "accent":     "#FFDE00",   # Rnorr Yellow (PMS 109 C)
        "accent2":    "#ffd000",
        "text":       "#ffffff",
        "body_bg":    "#ffffff",   # White (brand neutral)
        "section_bg": "#f5fff8",
        "font":       "'Antonio', 'Rubik', sans-serif",
        "font_url":   "https://fonts.googleapis.com/css2?family=Antonio:wght@400;700&family=Rubik:ital,wght@0,400;0,600;1,400;1,600&display=swap",
        "tagline":    "Tastes like time.",
        "hero_tag":   "🍲 Real Flavour",
        "copy":       "Rnorr stock cubes and cook-in sauces bring rich, authentic flavour to every dish. Trusted by home cooks for generations.",
        "features":   ["No Artificial Colours", "Real Herb Extracts", "Trusted Since 1838", "100% Natural Stock"],
    },
    # Glenfiddich × AMF1: #0E6B6B Deep Teal (bottle) | #B8D400 Chartreuse (AMF1 stripe) | Aston Martin Flare
    "Glenfiddich": {
        "primary":    "#0A6B65",   # Deep Teal — the actual AMF1 bottle colour
        "secondary":  "#064d49",   # Darker teal for overlays and depth
        "accent":     "#B8D400",   # Chartreuse lime — the AMF1 collaboration stripe
        "accent2":    "#D4F000",   # Brighter chartreuse for highlights
        "text":       "#ffffff",
        "body_bg":    "#ffffff",
        "section_bg": "#f0faf9",   # very light teal tint
        "font":       "'Cormorant Garamond', 'Georgia', serif",
        "font_url":   "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&display=swap",
        "tagline":    "After the noise, your quiet victory.",
        "hero_tag":   "🏎 Limited Edition · AMF1 × Glenfiddich",
        "copy":       "Glenfiddich 16 Year Old — a Limited Edition created with the Aston Martin Aramco Formula One™ Team. Two icons. One extraordinary Scotch.",
        "features":   ["Aged 16 Years", "Single Malt Scotch Whisky", "AMF1 Limited Edition", "Product of Scotland"],
    },
    # Boozt: #0E105E Midnight | #0086FE Boozt Blue | #00BFFE Sky | #FFFFFF White | Rubik italic
    "Boozt": {
        "primary":    "#0E105E",   # Midnight (master brand colour)
        "secondary":  "#080a45",   # deeper midnight for overlays
        "accent":     "#0086FE",   # Boozt Blue (Energy Stroke / CTA)
        "accent2":    "#00BFFE",   # Sky (lighter stroke / gradient)
        "text":       "#ffffff",
        "body_bg":    "#ffffff",
        "section_bg": "#f4f5ff",   # soft midnight tint
        "font":       "'Rubik', sans-serif",
        "font_url":   "https://fonts.googleapis.com/css2?family=Rubik:ital,wght@0,400;0,700;0,900;1,700;1,900&display=swap",
        "tagline":    "Get a Boozt.",
        "hero_tag":   "⚡ Pure Energy",
        "copy":       "Boozt Energy Drink delivers instant focus, sustained energy and electrolyte hydration — engineered for people who don't stop.",
        "features":   ["Zero Sugar", "Natural Caffeine", "Electrolyte Blend", "B-Vitamin Complex"],
    },
    # UBS Bank: #E60000 UBS Red | #000000 Black | #F4F3EF Stone | Arial/Frutiger
    "UBS Bank": {
        "primary":    "#E60000",   # UBS Red — accent colour (keys, CTA, keyline)
        "secondary":  "#000000",   # Black — headlines and structure
        "accent":     "#F4F3EF",   # Stone — calm editorial background
        "accent2":    "#595959",   # Secondary text / captions
        "text":       "#ffffff",
        "body_bg":    "#F4F3EF",   # Stone (default advisory layout background)
        "section_bg": "#ffffff",   # White for clean data/product sections
        "font":       "Arial, Helvetica, sans-serif",
        "font_url":   "",
        "tagline":    "Helping you discover a clearer financial future.",
        "hero_tag":   "🏦 Private Banking & Wealth Management",
        "copy":       "UBS delivers integrated wealth and investment solutions to high-net-worth individuals, families, and institutions — combining Swiss precision with global reach to make your financial future feel clear and within reach.",
        "features":   ["Wealth Management", "Private Banking", "Asset Management", "Global Reach"],
    },
    # Sunrise: #DA291C Red (accent/CTA only) | #FFFFFF White (body) | #1A1A1A Charcoal | Source Sans / system-ui
    "Sunrise": {
        "primary":    "#DA291C",   # Sunrise Red — CTA, badges, highlights only
        "secondary":  "#b81f14",   # Deeper red for hover states
        "accent":     "#DA291C",   # Same red — consistent accent system
        "accent2":    "#f5f5f5",   # Light grey for alternating section backgrounds
        "text":       "#ffffff",
        "body_bg":    "#ffffff",   # White — dominant brand background
        "section_bg": "#f5f5f5",   # Near-white for card/section alternation
        "font":       "'Source Sans Pro', system-ui, -apple-system, sans-serif",
        "font_url":   "",
        "tagline":    "Sunrise. Simply the best.",
        "hero_tag":   "🌅 Business Connect",
        "copy":       "Switzerland's leading communications provider — combining high-speed internet, mobile, and TV in one seamless package for your business.",
        "features":   ["Business Mobile", "High-Speed Internet", "Cloud Solutions", "24/7 Support"],
    },
}
DEFAULT_BRAND = {"primary": "#0055A4", "secondary": "#003d7a", "accent": "#f59e0b",
                 "accent2": "#fbbf24", "text": "#ffffff", "body_bg": "#f8f9fa",
                 "section_bg": "#f0f4ff",
                 "font": "Inter, sans-serif", "font_url": "",
                 "tagline": "", "hero_tag": "✨ Campaign", "copy": "", "features": []}


# ── Google Ads (mock) ──────────────────────────────────────────────────────────

def publish_google_ads(campaign_id: str, brand: str,
                       short_headline: str, medium_headline: str,
                       cta: str, body: str) -> dict:
    """Simulate Google Ads Responsive Search Ad submission."""
    import random, string
    ad_id = "GA-" + "".join(random.choices(string.digits, k=10))
    grp_id = "GAG-" + "".join(random.choices(string.digits, k=9))
    logger.info("google_ads_mock_submit", ad_id=ad_id, brand=brand)
    return {
        "platform":        "Google Ads",
        "status":          "submitted",
        "ad_id":           ad_id,
        "ad_group_id":     grp_id,
        "type":            "Responsive Search Ad",
        "headline_1":      short_headline[:30] if short_headline else brand,
        "headline_2":      medium_headline[:30] if medium_headline else "Shop Now",
        "description":     body[:90] if body else cta,
        "cta":             cta or "Learn More",
        "est_impressions": f"{random.randint(40,120):,}K / week",
        "est_cpc":         f"£{random.uniform(0.35, 1.40):.2f}",
        "quality_score":   random.randint(7, 10),
        "campaign_id":     campaign_id,
    }


# ── Brand Landing Page ─────────────────────────────────────────────────────────

def _make_bg_src(b64_or_url: str, mime: str = "image/jpeg") -> str:
    """Return a CSS-ready src from raw base64, a GCS URI, or an HTTPS URL."""
    if not b64_or_url:
        return ""
    if b64_or_url.startswith("gs://"):
        return b64_or_url.replace("gs://", "https://storage.googleapis.com/", 1)
    if b64_or_url.startswith(("https://", "http://", "data:")):
        return b64_or_url
    return f"data:{mime};base64,{b64_or_url}"


def _gcs_to_b64(uri: str, mime: str = "image/jpeg", max_kb: int = 800) -> str:
    """
    Load a brand asset, resize to max 600 px, return as base64 data URI.
    Handles very large source images (brand banner JPEGs can be 100-300 MP).
    """
    try:
        from app.creative_pipeline import _load_bytes
        data = _load_bytes(uri)
        if not data:
            return ""
        try:
            from PIL import Image
            # Brand source files can be enormous (13K×13K px).
            # Disable the decompression-bomb limit — we immediately thumbnail down.
            Image.MAX_IMAGE_PIXELS = None
            img = Image.open(io.BytesIO(data))
            # Composite RGBA/P onto white before converting to RGB so transparent
            # areas become white rather than black (Pillow default for RGB conversion).
            if img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                alpha = img.convert("RGBA").split()[3]
                bg.paste(img.convert("RGBA"), mask=alpha)
                img = bg
            else:
                img = img.convert("RGB")
            img.thumbnail((600, 600), Image.LANCZOS)   # resize in-place to ≤600px
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=72)
            data = buf.getvalue()
            mime = "image/jpeg"
        except Exception as _pe:
            logger.debug("gcs_to_b64_pil_failed", uri=uri, error=str(_pe))
            if len(data) > max_kb * 1024:
                return ""  # skip oversized raw file if Pillow can't resize it
        b64 = base64.b64encode(data).decode()
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.debug("gcs_to_b64_failed", uri=uri, error=str(e))
        return ""


def generate_brand_website(brand: str, hero_message: str = "", tagline: str = "",
                            body_copy: str = "", cta: str = "",
                            campaign_image_b64: str = "", hero_image_b64: str = "",
                            campaign_id: str = "", video_b64: str = "") -> str:
    """Route to the correct brand website generator."""
    if brand.lower() == "rnorr":
        return generate_rnorr_website(campaign_image_b64, campaign_id, hero_message, body_copy, cta, hero_image_b64, video_b64)
    if brand.lower() == "boozt":
        return generate_boozt_website(campaign_image_b64, campaign_id, hero_message, body_copy, cta, hero_image_b64, video_b64)
    if brand.lower() == "glenfiddich":
        return generate_glenfiddich_website(campaign_image_b64, campaign_id, hero_message, body_copy, cta, hero_image_b64, video_b64)
    if brand.lower() == "sunrise":
        return generate_sunrise_website(campaign_image_b64, campaign_id, hero_message, body_copy, cta, hero_image_b64, video_b64)
    return _generate_sunglow_website(brand, hero_message, tagline, body_copy, cta,
                                     campaign_image_b64, campaign_id, hero_image_b64, video_b64)


def generate_sunrise_website(campaign_image_b64: str = "", campaign_id: str = "",
                              hero_message: str = "", body_copy: str = "", cta: str = "",
                              hero_image_b64: str = "", video_b64: str = "") -> str:
    """Sunrise brand landing page — white body, #DA291C red accents, modern Swiss telecom aesthetic."""
    from app.brand_assets import get_asset_loader
    cfg    = BRAND_CONFIG["Sunrise"]
    loader = get_asset_loader()
    logos    = loader.list_logos("Sunrise")
    products = loader.list_products("Sunrise")
    assets   = loader.list_assets("Sunrise")

    _gcs_hero   = next((_gcs_to_b64(a, "image/jpeg", 1200) for a in assets[:3] if a), "")
    hero_bg_src = _make_bg_src(hero_image_b64) or _make_bg_src(campaign_image_b64) or _gcs_hero
    camp_src    = _make_bg_src(campaign_image_b64) or _gcs_hero

    logo_html = '<img src="/brand-logo/Sunrise" alt="Sunrise" style="height:36px;object-fit:contain;">'
    if not logos:
        logo_html = '<span style="font-size:22px;font-weight:900;color:#DA291C;letter-spacing:-0.03em;">sunrise</span>'

    # Product carousel — load from GCS; fall back to telecom device list
    _prod_srcs = [_gcs_to_b64(p, "image/jpeg", 400) for p in products[:8]]
    _carousel_products = [
        ("Apple",    "iPhone 16 Pro"),
        ("Samsung",  "Galaxy S25 Ultra"),
        ("Google",   "Pixel 9 Pro"),
        ("Apple",    "iPhone 16"),
        ("Samsung",  "Galaxy A55"),
        ("Sunrise",  "5G Router"),
        ("Apple",    "iPad Pro"),
        ("Samsung",  "Galaxy Tab S9"),
    ]
    carousel_items_html = ""
    for i, (dev_brand, dev_model) in enumerate(_carousel_products):
        src = _prod_srcs[i] if i < len(_prod_srcs) else ""
        img_html = (f'<img src="{src}" alt="{dev_brand} {dev_model}" '
                    f'style="height:130px;width:100%;object-fit:contain;display:block;margin-bottom:16px;">'
                    if src else
                    '<div style="height:130px;display:flex;align-items:center;justify-content:center;'
                    'font-size:52px;margin-bottom:16px;">📱</div>')
        carousel_items_html += f"""
          <div class="cs-item">
            {img_html}
            <div style="font-size:12px;font-weight:900;letter-spacing:0.08em;text-transform:uppercase;color:#1a1a1a;line-height:1.2;">{dev_brand}</div>
            <div style="font-size:11px;color:#555;margin-top:3px;">{dev_model}</div>
          </div>"""

    # Feature cards — based on actual sunrise.ch product categories
    features = [
        ("Business Mobile",    "Flexible SIM-only plans and device bundles for teams of any size.",         "📱"),
        ("High-Speed Internet", "Fibre and cable broadband with symmetric speeds up to 10 Gbps.",           "⚡"),
        ("Cloud & Security",   "Microsoft 365, backup, and managed security — all on one invoice.",          "☁️"),
        ("TV & Streaming",     "Premium TV packages with live sport, news, and on-demand content.",          "📺"),
    ]
    feat_cards = ""
    for icon, name, desc in [(f[2], f[0], f[1]) for f in features]:
        feat_cards += f"""
        <div class="feat-card">
          <div class="feat-icon">{icon}</div>
          <div class="feat-name">{name}</div>
          <div class="feat-desc">{desc}</div>
          <a href="#" class="feat-link">Learn more →</a>
        </div>"""

    # Plan comparison cards
    plans = [
        ("Mobile Unlimited",  "CHF 39.90/mth", ["Unlimited Mobile Data", "Unlimited CH Calls & SMS", "5G included"], False),
        ("Easy Internet",     "CHF 39.90/mth", ["Home Internet · Up to 1 Gbps", "Free installation", "No lock-in period"], False),
        ("5G Home Internet",  "CHF 29.90/mth", ["Up to 10 Gbps Download", "No router rental fee", "Cancel anytime"], False),
        ("Business Connect",  "CHF 49.90/mth", ["Unlimited Data + 5G", "Unlimited CH + EU Calls", "Up to 5 SIMs · 24/7 support"], True),
    ]
    plan_cards = ""
    for pname, price, perks, featured in plans:
        border  = "border:2px solid #DA291C;" if featured else "border:2px solid #e5e7eb;"
        # Badge sits inside the card (padding-top accounts for it) — not absolutely above, avoids overflow into sibling sections
        badge   = '<div style="display:inline-block;background:#DA291C;color:white;font-size:11px;font-weight:700;letter-spacing:0.1em;padding:4px 16px;border-radius:99px;white-space:nowrap;margin-bottom:16px;">MOST POPULAR</div>' if featured else '<div style="height:29px;margin-bottom:16px;"></div>'
        btn_bg  = "background:#DA291C;color:white;" if featured else "background:white;color:#DA291C;border:2px solid #DA291C;"
        perks_html = "".join(f'<li style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f0f0f0;font-size:14px;color:#444;"><span style="color:#DA291C;font-size:16px;">✓</span>{p}</li>' for p in perks)
        plan_cards += f"""
        <div style="background:white;border-radius:20px;padding:24px 28px 28px;{border}box-shadow:0 4px 20px rgba(0,0,0,0.07);transition:transform 0.2s,box-shadow 0.2s;"
             onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 16px 40px rgba(218,41,28,0.15)'"
             onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 20px rgba(0,0,0,0.07)'">
          {badge}
          <div style="font-size:13px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#DA291C;margin-bottom:8px;">{pname}</div>
          <div style="font-size:32px;font-weight:800;color:#1a1a1a;margin-bottom:4px;">{price}</div>
          <div style="font-size:12px;color:#888;margin-bottom:24px;">excl. VAT · cancel anytime</div>
          <ul style="list-style:none;margin-bottom:28px;">{perks_html}</ul>
          <a href="#" style="display:block;text-align:center;padding:14px;border-radius:12px;font-weight:700;font-size:14px;text-decoration:none;{btn_bg}transition:opacity 0.2s;" onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'">{cta or 'Get unlimited now'}</a>
        </div>"""

    hero_style = ""  # no longer used — hero now uses <img> tag, not CSS background

    reel_section = f"""
<section style="background:#1a1a1a;padding:72px 0;text-align:center;">
  <div style="max-width:1140px;margin:0 auto;padding:0 40px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#DA291C;margin-bottom:12px;">Campaign Reel</div>
    <h2 style="font-size:32px;font-weight:800;color:white;margin-bottom:32px;text-wrap:balance;">{hero_message}</h2>
    <div style="border-radius:20px;overflow:hidden;box-shadow:0 24px 64px rgba(0,0,0,0.5);">
      <video controls autoplay loop muted playsinline style="width:100%;display:block;"
             src="data:video/mp4;base64,{video_b64}"></video>
    </div>
    <a href="#plans" style="display:inline-block;margin-top:32px;background:#DA291C;color:white;padding:16px 44px;border-radius:99px;font-weight:700;font-size:15px;text-decoration:none;">{cta or 'View plans'}</a>
  </div>
</section>""" if video_b64 else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Sunrise Business — {hero_message or 'Simply the best.'}</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;background:#fff;color:#1a1a1a;line-height:1.5}}
    a{{text-decoration:none;color:inherit}}

    /* Top announcement bar */
    .top-bar{{background:#DA291C;color:white;text-align:center;padding:10px 20px;font-size:13px;font-weight:600;letter-spacing:0.02em}}

    /* Navigation */
    nav{{position:sticky;top:0;z-index:100;background:white;border-bottom:1px solid #e5e7eb;height:64px;display:flex;align-items:center;padding:0 40px;box-shadow:0 1px 8px rgba(0,0,0,0.06)}}
    .nav-inner{{max-width:1140px;width:100%;margin:0 auto;display:flex;align-items:center;justify-content:space-between}}
    .nav-links{{display:flex;gap:24px}}
    .nav-links a{{font-size:14px;font-weight:500;color:#444;padding:4px 0;border-bottom:2px solid transparent;transition:color 0.15s,border-color 0.15s}}
    .nav-links a:hover{{color:#DA291C;border-color:#DA291C}}
    .nav-cta{{background:#DA291C;color:white;padding:10px 24px;border-radius:8px;font-weight:700;font-size:13px;transition:background 0.15s}}
    .nav-cta:hover{{background:#b81f14}}

    /* Hero */
    .hero{{position:relative;overflow:hidden;display:block;}}
    .hero img.hero-img{{width:100%;height:auto;display:block;}}
    .hero-overlay{{position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,0.35) 0%,rgba(0,0,0,0.15) 50%,rgba(0,0,0,0.02) 100%)}}
    .hero-content{{position:relative;z-index:1;max-width:1140px;margin:0 auto;padding:52px 40px;width:100%}}
    .hero-tag{{display:inline-block;background:#DA291C;color:white;font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;padding:6px 16px;border-radius:99px;margin-bottom:20px}}
    .hero-title{{font-size:clamp(32px,5vw,56px);font-weight:800;color:white;line-height:1.1;max-width:580px;text-wrap:balance;margin-bottom:16px}}
    .hero-sub{{font-size:18px;color:rgba(255,255,255,0.85);max-width:480px;margin-bottom:36px;line-height:1.6}}
    .hero-btns{{display:flex;gap:16px;flex-wrap:wrap}}
    .btn-primary{{background:#DA291C;color:white;padding:16px 36px;border-radius:10px;font-weight:700;font-size:15px;transition:background 0.15s,transform 0.15s}}
    .btn-primary:hover{{background:#b81f14;transform:translateY(-1px)}}
    .btn-secondary{{background:rgba(255,255,255,0.15);color:white;padding:16px 36px;border-radius:10px;font-weight:600;font-size:15px;border:1.5px solid rgba(255,255,255,0.5);backdrop-filter:blur(6px);transition:background 0.15s}}
    .btn-secondary:hover{{background:rgba(255,255,255,0.25)}}

    /* Trust bar */
    .trust-bar{{background:#f9f9f9;border-bottom:1px solid #e5e7eb;padding:20px 40px}}
    .trust-inner{{max-width:1140px;margin:0 auto;display:flex;justify-content:space-around;align-items:center;gap:20px;flex-wrap:wrap}}
    .trust-item{{display:flex;align-items:center;gap:10px;font-size:13px;font-weight:600;color:#444}}
    .trust-icon{{font-size:20px}}

    /* Section layout */
    .section{{padding:80px 40px}}
    .section-inner{{max-width:1140px;margin:0 auto}}
    .section-label{{font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#DA291C;margin-bottom:12px}}
    .section-title{{font-size:clamp(24px,3.5vw,38px);font-weight:800;color:#1a1a1a;margin-bottom:12px;text-wrap:balance}}
    .section-sub{{font-size:16px;color:#666;max-width:580px;line-height:1.7}}

    /* Feature cards */
    .feat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px;margin-top:48px}}
    .feat-card{{background:#f9f9f9;border-radius:16px;padding:32px 28px;border:1.5px solid transparent;transition:border-color 0.2s,box-shadow 0.2s,transform 0.2s}}
    .feat-card:hover{{border-color:#DA291C;box-shadow:0 8px 28px rgba(218,41,28,0.12);transform:translateY(-3px)}}
    .feat-icon{{font-size:32px;margin-bottom:16px}}
    .feat-name{{font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:8px}}
    .feat-desc{{font-size:14px;color:#666;line-height:1.6;margin-bottom:16px}}
    .feat-link{{font-size:13px;font-weight:700;color:#DA291C}}

    /* Plans grid */
    .plans-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px;margin-top:48px;align-items:start}}

    /* Product carousel */
    .cs-wrap{{position:relative;background:linear-gradient(120deg,#DA291C 0%,#e85d00 60%,#f5a000 100%);border-radius:24px;padding:40px 56px;overflow:hidden;margin:0 40px}}
    .cs-badge-dark{{position:absolute;top:24px;right:120px;width:110px;height:110px;border-radius:50%;background:#1a1a1a;color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-size:13px;font-weight:700;line-height:1.3;z-index:2}}
    .cs-badge-light{{position:absolute;top:52px;right:28px;width:88px;height:88px;border-radius:50%;background:white;color:#1a1a1a;display:flex;align-items:center;justify-content:center;text-align:center;font-size:11px;font-weight:700;line-height:1.3;z-index:2}}
    .cs-badge-light span{{font-size:26px;font-weight:900;display:block;line-height:1}}
    .cs-track-outer{{overflow:hidden}}
    .cs-track{{display:flex;gap:24px;transition:transform 0.4s cubic-bezier(.4,0,.2,1)}}
    .cs-item{{flex:0 0 calc(25% - 18px);background:white;border-radius:16px;padding:24px 16px 16px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.12)}}
    .cs-arrow{{position:absolute;top:50%;transform:translateY(-50%);width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,0.9);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;z-index:3;box-shadow:0 2px 8px rgba(0,0,0,0.18);transition:background 0.15s}}
    .cs-arrow:hover{{background:white}}
    .cs-arrow-prev{{left:12px}}
    .cs-arrow-next{{right:12px}}

    /* Campaign image card — no crop, full image always visible */
    .campaign-image{{width:100%;height:auto;display:block;border-radius:20px;box-shadow:0 8px 40px rgba(0,0,0,0.12)}}

    /* CTA band */
    .cta-band{{background:#DA291C;padding:72px 40px;text-align:center}}
    .cta-band h2{{font-size:clamp(24px,3.5vw,38px);font-weight:800;color:white;margin-bottom:12px;text-wrap:balance}}
    .cta-band p{{font-size:16px;color:rgba(255,255,255,0.85);margin-bottom:32px}}
    .cta-band a{{display:inline-block;background:white;color:#DA291C;padding:16px 44px;border-radius:10px;font-weight:800;font-size:15px;transition:transform 0.15s}}
    .cta-band a:hover{{transform:translateY(-2px)}}

    /* Footer */
    footer{{background:#1a1a1a;color:#aaa;padding:56px 40px 32px}}
    .foot-inner{{max-width:1140px;margin:0 auto}}
    .foot-top{{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:40px;margin-bottom:48px}}
    .foot-brand{{color:white;font-size:24px;font-weight:900;letter-spacing:-0.03em;margin-bottom:12px}}
    .foot-brand span{{color:#DA291C}}
    .foot-tagline{{font-size:13px;color:#aaa;line-height:1.6;max-width:260px}}
    .foot-col h4{{font-size:12px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:white;margin-bottom:16px}}
    .foot-col a{{display:block;font-size:13px;color:#888;margin-bottom:10px;transition:color 0.15s}}
    .foot-col a:hover{{color:white}}
    .foot-bottom{{border-top:1px solid #333;padding-top:24px;display:flex;justify-content:space-between;align-items:center;font-size:12px;flex-wrap:wrap;gap:12px}}
  </style>
</head>
<body>

  <div class="top-bar">New: Business Connect M — Unlimited data + 5G from CHF 49.–/mo &nbsp;·&nbsp; <strong>Limited offer</strong></div>

  <nav>
    <div class="nav-inner">
      <div style="display:flex;align-items:center;gap:32px">
        {logo_html}
        <div class="nav-links">
          <a href="#">Mobile</a>
          <a href="#">Internet</a>
          <a href="#plans">Business</a>
          <a href="#">TV</a>
          <a href="#">Support</a>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:16px">
        <a href="#" style="font-size:13px;font-weight:600;color:#444">My Sunrise</a>
        <a href="#plans" class="nav-cta">{cta or 'View plans'}</a>
      </div>
    </div>
  </nav>

  <!-- Hero — full natural-height image so baked-in headline is never cropped -->
  <div class="hero">
    {f'<img class="hero-img" src="{hero_bg_src}" alt="Campaign hero">' if hero_bg_src else '<div style="height:420px;background:linear-gradient(135deg,#1a1a1a,#333);"></div>'}
    <div class="hero-overlay"></div>
  </div>

  <!-- Trust bar -->
  <div class="trust-bar">
    <div class="trust-inner">
      <div class="trust-item"><span class="trust-icon">🏅</span>Switzerland's #1 Network 2025</div>
      <div class="trust-item"><span class="trust-icon">⚡</span>5G in 99% of Switzerland</div>
      <div class="trust-item"><span class="trust-icon">🔒</span>ISO 27001 Certified Security</div>
      <div class="trust-item"><span class="trust-icon">📞</span>24/7 Dedicated Business Support</div>
    </div>
  </div>

  <!-- Product carousel -->
  <section style="padding:64px 0;background:#fff;">
    <div class="cs-wrap">
      <!-- Promo badges -->
      <div class="cs-badge-dark">Premium devices.<br>Best prices.</div>
      <div class="cs-badge-light"><span>3</span>months<br>free</div>

      <!-- Arrow prev -->
      <button class="cs-arrow cs-arrow-prev" onclick="csPrev()" aria-label="Previous">&#8249;</button>

      <!-- Track -->
      <div class="cs-track-outer">
        <div class="cs-track" id="csTrack">
          {carousel_items_html}
        </div>
      </div>

      <!-- Arrow next -->
      <button class="cs-arrow cs-arrow-next" onclick="csNext()" aria-label="Next">&#8250;</button>
    </div>
  </section>
  <script>
    (function(){{
      var track = document.getElementById('csTrack');
      var items = track ? track.children.length : 0;
      var visible = 4, idx = 0;
      function move(){{
        var pct = idx * (100 / visible);
        track.style.transform = 'translateX(-' + pct + '%)';
      }}
      window.csNext = function(){{ if(idx < items - visible){{ idx++; move(); }} }};
      window.csPrev = function(){{ if(idx > 0){{ idx--; move(); }} }};
    }})();
  </script>

  <!-- Features -->
  <section class="section" id="features" style="background:#fff">
    <div class="section-inner">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <span style="display:inline-block;background:#DA291C;color:white;font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;padding:5px 14px;border-radius:99px;">Business Connect</span>
        <span class="section-label" style="margin-bottom:0;">Why Sunrise Business</span>
      </div>
      <h2 class="section-title">Everything your business needs, in one place.</h2>
      <p class="section-sub">From mobile and internet to cloud and security — simplified billing, one dedicated contact.</p>
      <div class="feat-grid">
        {feat_cards}
      </div>
    </div>
  </section>

  <!-- Campaign image — full width -->
  {f'''<section style="padding:0 40px 0;background:#f5f5f5;">
    <div style="max-width:1140px;margin:0 auto;">
      <img src="{camp_src}" alt="Campaign visual"
           style="width:100%;height:auto;display:block;border-radius:20px;
                  box-shadow:0 8px 40px rgba(0,0,0,0.14);">
    </div>
  </section>''' if camp_src else ""}

  <!-- Plans — all 4 in one row -->
  <section class="section" id="plans" style="background:#f5f5f5">
    <div class="section-inner">
      <div class="section-label">Pricing</div>
      <h2 class="section-title">Simple plans. No surprises.</h2>
      <p class="section-sub" style="margin-bottom:32px;">All plans include a dedicated account manager, 24/7 support, and free onboarding.</p>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">
        {plan_cards}
      </div>
    </div>
  </section>

  {reel_section}

  <!-- CTA band -->
  <div class="cta-band">
    <h2>Ready to connect your business?</h2>
    <p>Talk to a Sunrise Business advisor today — no commitment required.</p>
    <a href="#">Request a free consultation</a>
  </div>

  <!-- Footer -->
  <footer>
    <div class="foot-inner">
      <div class="foot-top">
        <div>
          <div class="foot-brand">sun<span>rise</span></div>
          <p class="foot-tagline">Sunrise is Switzerland's leading communications provider for businesses and private customers.</p>
        </div>
        <div class="foot-col">
          <h4>Business</h4>
          <a href="#">Mobile Plans</a>
          <a href="#">Internet</a>
          <a href="#">Cloud Solutions</a>
          <a href="#">Business TV</a>
        </div>
        <div class="foot-col">
          <h4>Support</h4>
          <a href="#">Help Centre</a>
          <a href="#">Contact Us</a>
          <a href="#">Coverage Map</a>
          <a href="#">My Sunrise</a>
        </div>
        <div class="foot-col">
          <h4>Company</h4>
          <a href="#">About Sunrise</a>
          <a href="#">Newsroom</a>
          <a href="#">Careers</a>
          <a href="#">Sustainability</a>
        </div>
      </div>
      <div class="foot-bottom">
        <span>© 2025 Sunrise Communications AG. All rights reserved.</span>
        <div style="display:flex;gap:20px">
          <a href="#" style="color:#888">Privacy</a>
          <a href="#" style="color:#888">Legal</a>
          <a href="#" style="color:#888">Cookies</a>
        </div>
      </div>
    </div>
  </footer>

</body>
</html>"""


def generate_glenfiddich_website(campaign_image_b64: str = "", campaign_id: str = "",
                                  hero_message: str = "", body_copy: str = "", cta: str = "",
                                  hero_image_b64: str = "", video_b64: str = "") -> str:
    """Glenfiddich × AMF1 Limited Edition brand website."""
    from app.brand_assets import get_asset_loader
    cfg     = BRAND_CONFIG["Glenfiddich"]
    loader  = get_asset_loader()
    logos   = loader.list_logos("Glenfiddich")
    products = loader.list_products("Glenfiddich")
    assets  = loader.list_assets("Glenfiddich")

    prod_srcs    = [_gcs_to_b64(p, "image/jpeg", 800) for p in products[:3]]
    # Try multiple assets for hero background — pick first that loads successfully
    _gcs_hero    = next((s for s in [_gcs_to_b64(a, "image/jpeg", 800) for a in assets[:3]] if s), "")
    camp_src     = _make_bg_src(campaign_image_b64) or _gcs_hero
    # Priority: website 16:9 adaptation → KV campaign image → GCS brand asset
    # _make_bg_src handles raw base64, gs:// URIs, and https:// URLs uniformly
    hero_bg_src  = _make_bg_src(hero_image_b64) or _make_bg_src(campaign_image_b64) or _gcs_hero

    # Use the harness /brand-logo/ endpoint — avoids PNG→JPEG transparency loss
    logo_html = '<img src="/brand-logo/Glenfiddich" alt="Glenfiddich × AMF1" style="height:40px;object-fit:contain;">'
    if not logos:
        logo_html = '<span style="font-size:22px;font-weight:900;color:#B8D400;letter-spacing:-0.02em;">Glenfiddich × AMF1</span>'

    _products = [
        ("16 Year Old",  "AMF1 Limited Edition",          "Single Malt Scotch Whisky · The collaboration bottle"),
        ("12 Year Old",  "Our Signature Expression",       "Single Malt Scotch Whisky · Aged 12 Years"),
        ("18 Year Old",  "Small Batch Reserve",            "Single Malt Scotch Whisky · Aged 18 Years"),
    ]
    prod_cards = ""
    for i, src in enumerate(prod_srcs):
        if not src:
            continue
        name, sub, desc = _products[i] if i < len(_products) else (f"Expression {i+1}", "", "Single Malt Scotch Whisky")
        prod_cards += f"""
    <div style="background:white;border-radius:20px;overflow:hidden;
                box-shadow:0 4px 20px rgba(10,107,101,0.10);
                transition:transform 0.2s,box-shadow 0.2s;"
         onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 12px 32px rgba(10,107,101,0.18)'"
         onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 20px rgba(10,107,101,0.10)'">
      <div style="aspect-ratio:1;background:#f0faf9;display:flex;align-items:center;justify-content:center;overflow:hidden;">
        <img src="{src}" alt="{name}" style="width:100%;height:100%;object-fit:cover;">
      </div>
      <div style="padding:20px 22px 24px;">
        <div style="font-size:10px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#B8D400;margin-bottom:6px;">{sub}</div>
        <div style="font-size:17px;font-weight:700;color:#0A6B65;margin-bottom:4px;">Glenfiddich {name}</div>
        <div style="font-size:12px;color:#64748b;margin-bottom:16px;line-height:1.5;">{desc}</div>
        <a href="#" style="display:block;padding:11px;border-radius:10px;background:#0A6B65;
                            color:white;font-weight:700;font-size:13px;text-align:center;text-decoration:none;">
          {cta or "Secure your bottle."}
        </a>
      </div>
    </div>"""

    reel_section = f"""
<section style="background:#064d49;padding:56px 48px;text-align:center;">
  <div style="font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#B8D400;margin-bottom:12px;">Campaign Reel</div>
  <h2 style="font-family:'Cormorant Garamond',Georgia,serif;font-size:28px;font-weight:700;color:white;margin-bottom:24px;">{hero_message}</h2>
  <div style="max-width:800px;margin:0 auto;border-radius:16px;overflow:hidden;box-shadow:0 24px 64px rgba(0,0,0,0.4);">
    <video controls autoplay loop muted playsinline style="width:100%;display:block;"
           src="data:video/mp4;base64,{video_b64}"></video>
  </div>
</section>""" if video_b64 else ""

    bg_style = (f'background-image:url("{hero_bg_src}");background-size:cover;background-position:center;'
                if hero_bg_src else f"background:linear-gradient(135deg,#0A6B65,#064d49);")

    return f"""<!DOCTYPE html><html lang="en"><head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Glenfiddich × AMF1 — {hero_message[:55]}</title>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Cormorant Garamond','Georgia',serif;background:#fff;color:#1a2332}}
    a{{text-decoration:none;color:inherit}}
  </style>
</head><body>

<!-- Top bar -->
<div style="background:#0A6B65;color:#B8D400;text-align:center;padding:9px;
            font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;
            font-family:'Cormorant Garamond',Georgia,serif;">
  🏎 AMF1 × Glenfiddich · 16 Year Old Limited Edition · Available Now
</div>

<!-- Nav -->
<nav style="background:white;border-bottom:1px solid #e2e8f0;padding:0 48px;height:70px;
            display:flex;align-items:center;justify-content:space-between;
            position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(10,107,101,0.08);">
  <div>{logo_html}</div>
  <div style="display:flex;gap:28px;">
    <a href="#" style="font-size:14px;font-weight:600;color:#374151;">Our Whiskies</a>
    <a href="#campaign" style="font-size:14px;font-weight:600;color:#374151;">Campaign</a>
    <a href="#cta" style="font-size:14px;font-weight:600;color:#374151;">The Collection</a>
  </div>
  <a href="#cta" style="background:#0A6B65;color:white;padding:10px 24px;border-radius:99px;
                         font-weight:700;font-size:13px;">{cta or "Secure your bottle."}</a>
</nav>

<!-- Hero -->
<section style="position:relative;min-height:600px;display:flex;align-items:center;overflow:hidden;">
  <div style="position:absolute;inset:0;{bg_style}filter:brightness(0.5);"></div>
  <div style="position:absolute;inset:0;background:linear-gradient(90deg,#0A6B65ee 0%,#0A6B6566 55%,transparent 100%);"></div>
  <div style="position:relative;z-index:2;padding:80px 80px;max-width:640px;">
    <div style="display:inline-block;background:#B8D400;color:#0A6B65;font-size:11px;font-weight:800;
                letter-spacing:0.14em;text-transform:uppercase;padding:5px 14px;border-radius:99px;margin-bottom:20px;">
      🏎 Limited Edition · AMF1 × Glenfiddich
    </div>
    <h1 style="font-size:clamp(36px,4.5vw,58px);font-weight:700;color:white;line-height:1.1;
               letter-spacing:-0.01em;margin-bottom:18px;">{hero_message or cfg["tagline"]}</h1>
    <p style="font-size:18px;color:rgba(255,255,255,0.82);line-height:1.65;margin-bottom:36px;max-width:480px;">
      {body_copy or cfg["copy"]}
    </p>
    <div style="display:flex;gap:14px;flex-wrap:wrap;">
      <a href="#cta" style="background:#B8D400;color:#0A6B65;padding:15px 36px;border-radius:99px;
                             font-weight:800;font-size:15px;">{cta or "Secure your bottle."}</a>
      <a href="#campaign" style="border:2px solid white;color:white;padding:13px 32px;border-radius:99px;
                                  font-weight:700;font-size:15px;">Discover the Story</a>
    </div>
  </div>
</section>

<!-- Features bar -->
<div style="background:#0A6B65;padding:22px 48px;display:flex;gap:32px;justify-content:center;flex-wrap:wrap;">
  {''.join(f'<div style="display:flex;align-items:center;gap:10px;color:white;"><div style="width:20px;height:20px;background:#B8D400;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:900;color:#0A6B65;flex-shrink:0;">✓</div><span style="font-size:13px;font-weight:600;">{f}</span></div>' for f in cfg["features"])}
</div>

<!-- Products -->
{"" if not prod_cards else f'''
<section style="padding:72px 48px;">
  <div style="text-align:center;margin-bottom:48px;">
    <div style="font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;
                color:#0A6B65;margin-bottom:10px;">The Collection</div>
    <h2 style="font-size:32px;font-weight:700;color:#0A6B65;">Expressions Worth Waiting For</h2>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
              gap:24px;max-width:900px;margin:0 auto;">{prod_cards}</div>
</section>'''}

<!-- Campaign section -->
{"" if not camp_src else f'''
<section style="background:#f0faf9;padding:72px 80px;display:flex;align-items:center;gap:56px;flex-wrap:wrap;" id="campaign">
  <div style="flex:1;min-width:280px;max-width:480px;border-radius:24px;overflow:hidden;
              box-shadow:0 16px 48px rgba(10,107,101,0.18);">
    <img src="{camp_src}" alt="Campaign Visual" style="width:100%;height:auto;display:block;">
  </div>
  <div style="flex:1;min-width:280px;">
    <div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;
                color:#0A6B65;margin-bottom:12px;">AI Campaign · {campaign_id[:16]}</div>
    <h2 style="font-size:clamp(24px,3vw,36px);font-weight:700;color:#0A6B65;margin-bottom:16px;line-height:1.15;">
      {hero_message}
    </h2>
    <p style="font-size:15px;color:#475569;line-height:1.75;margin-bottom:28px;">{body_copy or cfg["copy"]}</p>
    <a href="#cta" style="background:#0A6B65;color:white;padding:14px 32px;border-radius:99px;
                           font-weight:700;font-size:14px;">{cta or "Secure your bottle."}</a>
  </div>
</section>'''}

{reel_section}

<!-- CTA -->
<section style="background:linear-gradient(135deg,#0A6B65,#064d49);padding:80px 48px;text-align:center;" id="cta">
  <div style="font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;
              color:#B8D400;margin-bottom:16px;">Limited Edition</div>
  <h2 style="font-size:clamp(28px,3.5vw,44px);font-weight:700;color:white;margin-bottom:20px;">
    After the noise, your quiet victory.
  </h2>
  <p style="font-size:17px;color:rgba(255,255,255,0.75);margin-bottom:36px;max-width:520px;margin-left:auto;margin-right:auto;">
    Glenfiddich 16 Year Old × Aston Martin F1. Two icons. One extraordinary Scotch.
  </p>
  <a href="#" style="background:#B8D400;color:#0A6B65;padding:18px 52px;border-radius:99px;
                     font-weight:800;font-size:17px;display:inline-block;">
    {cta or "Secure your bottle."}
  </a>
</section>

<!-- Footer -->
<footer style="background:#031e1c;color:#64748b;padding:36px 48px;
               display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;">
  <div style="font-size:16px;font-weight:700;color:#B8D400;">Glenfiddich × AMF1</div>
  <div style="display:flex;gap:20px;">
    <a href="#" style="color:#64748b;font-size:12px;">Our Whiskies</a>
    <a href="#" style="color:#64748b;font-size:12px;">The Story</a>
    <a href="#" style="color:#64748b;font-size:12px;">Responsible Drinking</a>
  </div>
  <div style="font-size:11px;color:#475569;width:100%;text-align:center;margin-top:8px;">
    © 2026 Glenfiddich × Aston Martin Aramco Formula One™ Team · AI campaign by CampaignOS · {campaign_id}
    · Please drink responsibly. Available to over 18s only.
  </div>
</footer>

</body></html>"""


def _generate_sunglow_website(brand: str, hero_message: str, tagline: str,
                               body_copy: str, cta: str,
                               campaign_image_b64: str, campaign_id: str,
                               hero_image_b64: str = "", video_b64: str = "") -> str:
    """
    Generate a full Sunsilk-inspired brand website HTML page.
    Loads logo, product images, and assets directly from GCS bucket.
    """
    from app.brand_assets import get_asset_loader
    cfg        = BRAND_CONFIG.get(brand, DEFAULT_BRAND)
    loader     = get_asset_loader()
    hero_tag   = cfg.get("hero_tag", "✨ Campaign")
    brand_copy = cfg.get("copy", body_copy or "")
    features   = cfg.get("features", [])

    # Load GCS assets as base64
    logos     = loader.list_logos(brand)
    products  = loader.list_products(brand)
    assets    = loader.list_assets(brand)

    logo_src     = _gcs_to_b64(logos[0],    "image/png", max_kb=200) if logos    else ""
    prod_srcs    = [_gcs_to_b64(p, "image/jpeg", max_kb=800) for p in products[:3]]
    hero_asset_src = _gcs_to_b64(assets[0], "image/jpeg", max_kb=800) if assets else ""
    campaign_src   = (f"data:image/jpeg;base64,{campaign_image_b64}"
                     if campaign_image_b64 else hero_asset_src)
    # Website banner (16:9 channel adaptation) takes priority as hero background
    hero_src_final = (f"data:image/jpeg;base64,{hero_image_b64}"
                      if hero_image_b64 else hero_asset_src)

    logo_html = (f'<img src="{logo_src}" alt="{brand}" style="height:44px;object-fit:contain;">'
                if logo_src else
                f'<span style="font-size:26px;font-weight:900;color:{cfg["accent"]};letter-spacing:-0.02em;">{brand}</span>')

    product_cards_html = ""
    for i, src in enumerate(prod_srcs):
        if src:
            product_cards_html += f"""
            <div class="prod-card">
              <div class="prod-img-wrap"><img src="{src}" alt="{brand} Product {i+1}"></div>
              <div class="prod-name">{brand} {['Moisture Shampoo','Repair Conditioner','Styling Cream'][i] if i < 3 else 'Product'}</div>
              <div class="prod-desc">Advanced formula for healthy hair</div>
              <a href="#" class="prod-btn">{cta or 'Shop Now'}</a>
            </div>"""

    feature_html = "".join([
        f'<div class="feat"><div class="feat-icon">✓</div><div class="feat-text">{f}</div></div>'
        for f in features[:4]
    ])

    bg_section = f'background-image: url("{hero_src_final}"); background-size: cover; background-position: center;' if hero_src_final else f"background: linear-gradient(135deg, {cfg['primary']}, {cfg['secondary']});"

    reel_section = f"""
<section class="section" id="reel" style="background:{cfg['primary']};padding:0 48px 64px">
  <div class="section-title" style="color:white;padding-top:56px;margin-bottom:24px">Campaign Reel</div>
  <video controls autoplay loop muted playsinline style="width:100%;display:block;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,0.3);" src="data:video/mp4;base64,{video_b64}"></video>
</section>""" if video_b64 else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{brand} — {hero_message[:55]}</title>
  <link href="{cfg.get('font_url','https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap')}" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:{cfg["font"]};background:{cfg["body_bg"]};color:#1a2332;}}
    a{{text-decoration:none}}

    /* ── Top bar ── */
    .topbar{{background:{cfg["primary"]};color:{cfg["accent"]};text-align:center;padding:8px;font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase}}

    /* ── Nav ── */
    nav{{background:white;border-bottom:1px solid #e2e8f0;padding:0 48px;display:flex;align-items:center;justify-content:space-between;height:70px;position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(0,0,0,0.06)}}
    .nav-links{{display:flex;gap:32px}}
    .nav-links a{{font-size:13px;font-weight:600;color:#374151;transition:color 0.2s}}
    .nav-links a:hover{{color:{cfg["primary"]}}}
    .nav-shop{{background:{cfg["primary"]};color:white;padding:10px 24px;border-radius:99px;font-weight:700;font-size:13px;transition:opacity 0.2s}}
    .nav-shop:hover{{opacity:0.85}}

    /* ── Hero ── */
    .hero{{position:relative;min-height:580px;display:flex;align-items:flex-end;overflow:hidden}}
    .hero-bg{{position:absolute;inset:0;{bg_section.replace("background-position: center","background-position: center 30%")}filter:brightness(0.9)}}
    .hero-overlay{{position:absolute;inset:0;background:linear-gradient(90deg,{cfg["primary"]}22 0%,transparent 70%)}}
    .hero-content{{position:relative;z-index:2;padding:48px 80px 56px;max-width:640px}}
    .hero-eyebrow{{display:inline-block;background:{cfg["accent"]};color:{cfg["primary"]};font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;padding:5px 14px;border-radius:99px;margin-bottom:20px}}
    .hero-headline{{font-size:clamp(36px,4.5vw,56px);font-weight:900;color:white;line-height:1.08;letter-spacing:-0.03em;margin-bottom:18px}}
    .hero-sub{{font-size:18px;color:rgba(255,255,255,0.82);line-height:1.65;margin-bottom:36px;max-width:480px}}
    .hero-btns{{display:flex;gap:14px;flex-wrap:wrap}}
    .btn-primary{{background:{cfg["accent"]};color:{cfg["primary"]};padding:15px 36px;border-radius:99px;font-weight:800;font-size:15px;transition:transform 0.2s,box-shadow 0.2s}}
    .btn-primary:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,0.25)}}
    .btn-outline{{border:2px solid white;color:white;padding:13px 32px;border-radius:99px;font-weight:700;font-size:15px}}

    /* ── Features bar ── */
    .features{{background:{cfg["primary"]};padding:24px 48px;display:flex;gap:32px;justify-content:center;flex-wrap:wrap}}
    .feat{{display:flex;align-items:center;gap:10px;color:white}}
    .feat-icon{{width:22px;height:22px;background:{cfg["accent"]};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;color:{cfg["primary"]};flex-shrink:0}}
    .feat-text{{font-size:13px;font-weight:600}}

    /* ── Products ── */
    .section{{padding:72px 48px;}}
    .section-title{{font-size:32px;font-weight:800;text-align:center;color:{cfg["primary"]};margin-bottom:8px}}
    .section-sub{{text-align:center;color:#64748b;font-size:16px;margin-bottom:44px}}
    .prod-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px;max-width:900px;margin:0 auto}}
    .prod-card{{background:white;border-radius:20px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);transition:transform 0.2s,box-shadow 0.2s}}
    .prod-card:hover{{transform:translateY(-4px);box-shadow:0 12px 32px rgba(0,0,0,0.15)}}
    .prod-img-wrap{{aspect-ratio:1;background:{cfg["section_bg"]};display:flex;align-items:center;justify-content:center;overflow:hidden}}
    .prod-img-wrap img{{width:100%;height:100%;object-fit:cover}}
    .prod-name{{font-size:15px;font-weight:700;color:#1a2332;padding:16px 18px 4px}}
    .prod-desc{{font-size:12px;color:#94a3b8;padding:0 18px 16px;line-height:1.5}}
    .prod-btn{{display:block;margin:0 18px 18px;padding:10px;border-radius:10px;background:{cfg["primary"]};color:white;font-weight:700;font-size:13px;text-align:center}}

    /* ── Campaign section ── */
    .campaign{{background:{cfg["section_bg"]};padding:72px 48px;display:flex;align-items:center;gap:56px;flex-wrap:wrap}}
    .campaign-img{{flex:1;min-width:280px;max-width:480px;border-radius:24px;overflow:hidden;box-shadow:0 16px 48px rgba(0,0,0,0.15)}}
    .campaign-img img{{width:100%;height:auto;display:block}}
    .campaign-text{{flex:1;min-width:280px}}
    .campaign-label{{font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:{cfg["primary"]};margin-bottom:12px}}
    .campaign-headline{{font-size:clamp(24px,3vw,36px);font-weight:900;color:#0f172a;margin-bottom:16px;line-height:1.15}}
    .campaign-body{{font-size:15px;color:#475569;line-height:1.75;margin-bottom:28px}}

    /* ── CTA band ── */
    .cta-band{{background:linear-gradient(135deg,{cfg["primary"]},{cfg["secondary"]});padding:80px 48px;text-align:center}}
    .cta-band h2{{font-size:clamp(28px,3.5vw,44px);font-weight:900;color:white;margin-bottom:20px;letter-spacing:-0.02em}}
    .cta-band p{{font-size:17px;color:rgba(255,255,255,0.75);margin-bottom:36px}}
    .cta-big{{background:{cfg["accent"]};color:{cfg["primary"]};padding:18px 52px;border-radius:99px;font-weight:800;font-size:17px;display:inline-block;transition:transform 0.2s}}
    .cta-big:hover{{transform:translateY(-2px)}}

    /* ── Footer ── */
    footer{{background:#0f172a;color:#64748b;padding:36px 48px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px}}
    .footer-brand{{font-size:18px;font-weight:900;color:{cfg["accent"]}}}
    .footer-links{{display:flex;gap:20px}}
    .footer-links a{{color:#64748b;font-size:12px}}
    .footer-copy{{font-size:11px;color:#475569;width:100%;text-align:center;margin-top:16px}}
  </style>
</head>
<body>

<div class="topbar">Free delivery on orders over £30 · New Campaign: {hero_message[:40]}</div>

<nav>
  <div>{logo_html}</div>
  <div class="nav-links">
    <a href="#">Products</a>
    <a href="#campaign">Campaign</a>
    <a href="#cta">Shop</a>
  </div>
  <a href="#cta" class="nav-shop">{cta or 'Shop Now'}</a>
</nav>

<!-- Hero -->
<section class="hero">
  <div class="hero-bg"></div>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-eyebrow">{hero_tag}</div>
    <p class="hero-sub">{brand_copy or tagline or cfg.get("tagline","")}</p>
    <div class="hero-btns">
      <a href="#cta" class="btn-primary">{cta or 'Shop Now'}</a>
      <a href="#campaign" class="btn-outline">Learn More</a>
    </div>
  </div>
</section>

<!-- Features bar -->
{f'<div class="features">{feature_html}</div>' if feature_html else ""}

<!-- Products -->
{f'''<section class="section">
  <div class="section-title">Our Products</div>
  <div class="section-sub">Crafted for every hair type, every day</div>
  <div class="prod-grid">{product_cards_html}</div>
</section>''' if product_cards_html else ""}

<!-- Campaign section -->
<section class="campaign" id="campaign">
  {f'<div class="campaign-img"><img src="{campaign_src}" alt="Campaign Visual"></div>' if campaign_src else ""}
  <div class="campaign-text">
    <div class="campaign-label">AI Campaign · {campaign_id[:16]}</div>
    <h2 class="campaign-headline">{hero_message}</h2>
    <p class="campaign-body">{body_copy or brand_copy}</p>
    <a href="#cta" class="btn-primary">{cta or 'Discover More'}</a>
  </div>
</section>

{reel_section}

<!-- CTA -->
<section class="cta-band" id="cta">
  <h2>Experience {brand} Today</h2>
  <p>Join thousands who've discovered the difference</p>
  <a href="#" class="cta-big">{cta or 'Shop the Collection'}</a>
</section>

<footer>
  <div class="footer-brand">{brand}</div>
  <div class="footer-links">
    <a href="#">About</a>
    <a href="#">Products</a>
    <a href="#">Contact</a>
  </div>
  <div class="footer-copy">© 2026 {brand} · AI campaign by CampaignOS · {campaign_id}</div>
</footer>

</body>
</html>"""


def generate_rnorr_website(campaign_image_b64: str = "", campaign_id: str = "",
                            hero_message: str = "", body_copy: str = "", cta: str = "",
                            hero_image_b64: str = "", video_b64: str = "") -> str:
    """Knorr-inspired brand website for Rnorr."""
    from app.brand_assets import get_asset_loader
    loader   = get_asset_loader()
    logos    = loader.list_logos("Rnorr")
    products = loader.list_products("Rnorr")
    assets   = loader.list_assets("Rnorr")

    logo_src  = _gcs_to_b64(logos[0],   "image/png",  200) if logos    else ""
    prod_srcs = [_gcs_to_b64(p, "image/jpeg", 800) for p in products[:6]]
    hero_bg_src = _gcs_to_b64(assets[0], "image/jpeg", 800) if assets else ""
    camp_src    = f"data:image/jpeg;base64,{campaign_image_b64}" if campaign_image_b64 else hero_bg_src
    # Website banner (16:9 channel adaptation) takes priority as hero background
    hero_bg_src = f"data:image/jpeg;base64,{hero_image_b64}" if hero_image_b64 else hero_bg_src

    logo_html = (f'<img src="{logo_src}" alt="Rnorr" style="height:40px;object-fit:contain;">'
                if logo_src else '<span style="font-size:26px;font-weight:900;color:#FFDE00;letter-spacing:-0.02em;">Rnorr</span>')

    # Recipe cards — use product/asset images; rich brand-colour gradients as fallback
    _recipe_img_srcs = [_gcs_to_b64(p, "image/jpeg", 600) for p in (products + assets)[:3]]
    recipes = [
        {"name": "Give It More with Rnorr: Elevate Your Everyday Meals",
         "sub": "Discover how a single cube transforms a simple pot into something extraordinary.",
         "tag": "Recipes", "tag_color": "#FFDE00", "tag_text": "#008641",
         "fallback": "linear-gradient(145deg,#005c2c 0%,#008641 50%,#00a352 100%)"},
        {"name": "Quick & Flavourful Weeknight Dinners",
         "sub": "30-minute meals the whole family will ask for again. Real flavour, real fast.",
         "tag": "Inspiration", "tag_color": "#FFDE00", "tag_text": "#008641",
         "fallback": "linear-gradient(145deg,#003d20 0%,#006633 50%,#008641 100%)"},
        {"name": "Tips & Tricks from Our Kitchen",
         "sub": "Chef-tested techniques to get the most out of every Rnorr product.",
         "tag": "Tips", "tag_color": "#008641", "tag_text": "#FFDE00",
         "fallback": "linear-gradient(145deg,#1a3a1a 0%,#2d6a2d 50%,#008641 100%)"},
    ]
    recipe_cards = ""
    for i, r in enumerate(recipes):
        img_src = _recipe_img_srcs[i] if i < len(_recipe_img_srcs) else ""
        if img_src:
            photo_layer = f'<div style="position:absolute;inset:0;background-image:url(\'{img_src}\');background-size:cover;background-position:center;transition:transform 0.5s ease;" onmouseover="this.style.transform=\'scale(1.06)\'" onmouseout="this.style.transform=\'scale(1)\'"></div>'
        else:
            photo_layer = f'<div style="position:absolute;inset:0;background:{r["fallback"]};"></div>'
        recipe_cards += f"""
    <div style="cursor:pointer;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.13);transition:box-shadow 0.3s,transform 0.3s;" onmouseover="this.style.boxShadow=\'0 12px 40px rgba(0,0,0,0.22)\';this.style.transform=\'translateY(-4px)\'" onmouseout="this.style.boxShadow=\'0 4px 24px rgba(0,0,0,0.13)\';this.style.transform=\'translateY(0)\'">
      <div style="position:relative;height:220px;overflow:hidden;">
        {photo_layer}
        <div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(0,30,10,0.85) 0%,rgba(0,0,0,0.25) 55%,transparent 100%);"></div>
        <div style="position:absolute;top:16px;left:16px;background:{r['tag_color']};color:{r['tag_text']};font-size:10px;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;padding:5px 14px;border-radius:99px;">{r['tag']}</div>
      </div>
      <div style="background:white;padding:20px 22px 24px;">
        <div style="font-family:Antonio,sans-serif;font-size:17px;font-weight:900;color:#1a2332;line-height:1.25;margin-bottom:8px;">{r['name']}</div>
        <div style="font-size:13px;color:#64748b;line-height:1.55;margin-bottom:16px;">{r['sub']}</div>
        <a href="#" style="display:inline-flex;align-items:center;gap:6px;color:#008641;font-size:13px;font-weight:700;text-decoration:none;">Read more <span style="font-size:16px;">→</span></a>
      </div>
    </div>"""

    prod_cards = "".join([f"""
    <div class="prod-card">
      <div class="prod-img">{f'<img src="{src}" alt="Rnorr Product">' if src else '🧂'}</div>
      <div class="prod-info">
        <div class="prod-name">Rnorr {['Chicken Cubes','Beef Cubes','Veg Cubes','Cook-In Sauce','Gravy Mix','Herb Stock'][i] if i < 6 else 'Product'}</div>
        <div class="prod-size">Pack of 8 | 80g</div>
        <a href="#" class="prod-cta">Add to Basket</a>
      </div>
    </div>""" for i, src in enumerate(prod_srcs)])

    # Pre-compute reel section (can't use nested f-string inside f-string)
    reel_section = f"""
<section style="background:#0d2e1a;padding:56px 48px;text-align:center;">
  <div style="font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#FFDE00;margin-bottom:12px;">Campaign Reel</div>
  <h2 style="font-family:Antonio,sans-serif;font-size:28px;font-weight:900;color:white;margin-bottom:24px;">{hero_message}</h2>
  <div style="max-width:800px;margin:0 auto;border-radius:16px;overflow:hidden;box-shadow:0 24px 64px rgba(0,0,0,0.5);">
    <video controls autoplay loop muted playsinline style="width:100%;display:block;" src="data:video/mp4;base64,{video_b64}"></video>
  </div>
  <a href="#cta" style="display:inline-block;margin-top:24px;background:#FFDE00;color:#008641;padding:14px 40px;border-radius:99px;font-weight:800;font-size:15px;text-decoration:none;">{cta or 'Shop Now'}</a>
</section>""" if video_b64 else ""

    return f"""<!DOCTYPE html><html lang="en"><head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Rnorr -- Tastes like time.</title>
  <link href="https://fonts.googleapis.com/css2?family=Antonio:wght@400;700&family=Rubik:ital,wght@0,400;0,600;1,400;1,600&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Antonio','Rubik',sans-serif;background:#fff;color:#1a2332}}
    a{{text-decoration:none;color:inherit}}

    /* Utility bar */
    .util-bar{{background:#008641;color:#FFDE00;text-align:center;padding:9px;font-size:12px;font-weight:700;letter-spacing:0.1em}}

    /* Nav — Knorr-style white sticky */
    nav{{position:sticky;top:0;z-index:100;background:white;border-bottom:2px solid #008641;padding:0 48px;height:68px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,0.08)}}
    .nav-logo{{display:flex;align-items:center;gap:12px}}
    .nav-links{{display:flex;gap:28px}}
    .nav-links a{{font-size:14px;font-weight:600;color:#333;padding:4px 0;border-bottom:2px solid transparent;transition:all 0.2s}}
    .nav-links a:hover{{color:#008641;border-color:#FFDE00}}
    .nav-right{{display:flex;gap:12px;align-items:center}}
    .nav-search{{padding:8px 16px;border:2px solid #e2e8f0;border-radius:99px;font-size:13px;outline:none;width:160px}}
    .nav-btn{{background:#008641;color:white;padding:9px 20px;border-radius:99px;font-weight:700;font-size:13px;transition:opacity 0.2s}}
    .nav-btn:hover{{opacity:0.85}}

    /* Hero — full-bleed with image */
    .hero{{position:relative;height:520px;display:flex;align-items:center;overflow:hidden;background:#005c2c}}
    .hero-bg{{position:absolute;inset:0;background-size:cover;background-position:center;{f'background-image:url("{hero_bg_src}");' if hero_bg_src else "background:linear-gradient(135deg,#008641,#005c2c);"}filter:brightness(0.55)}}
    .hero-overlay{{position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,107,63,0.9) 0%,rgba(0,107,63,0.5) 50%,transparent 100%)}}
    .hero-content{{position:relative;z-index:2;padding:0 80px;max-width:600px}}
    .hero-badge{{display:inline-block;background:#FFDE00;color:#008641;font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;padding:5px 14px;border-radius:99px;margin-bottom:18px}}
    .hero-title{{font-size:clamp(34px,4vw,52px);font-weight:900;color:white;line-height:1.1;margin-bottom:16px;letter-spacing:-0.02em}}
    .hero-sub{{font-size:17px;color:rgba(255,255,255,0.82);line-height:1.65;margin-bottom:32px}}
    .hero-btns{{display:flex;gap:14px}}
    .btn-yellow{{background:#FFDE00;color:#008641;padding:14px 32px;border-radius:99px;font-weight:800;font-size:15px;transition:transform 0.2s}}
    .btn-yellow:hover{{transform:translateY(-2px)}}
    .btn-white-outline{{border:2px solid white;color:white;padding:12px 28px;border-radius:99px;font-weight:600;font-size:14px}}

    /* Features strip */
    .features{{background:#008641;padding:20px 48px;display:flex;justify-content:center;gap:48px;flex-wrap:wrap}}
    .feat{{display:flex;align-items:center;gap:10px;color:white;font-size:13px;font-weight:600}}
    .feat-dot{{width:8px;height:8px;background:#FFDE00;border-radius:50%}}

    /* Products — Knorr card style */
    .section{{padding:64px 48px;background:#fff}}
    .section.alt{{background:#f9fff4}}
    .section-head{{text-align:center;margin-bottom:40px}}
    .section-label{{font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#008641;margin-bottom:8px}}
    .section-title{{font-size:30px;font-weight:900;color:#005c2c}}
    .prod-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:20px;max-width:1100px;margin:0 auto}}
    .prod-card{{background:white;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);transition:transform 0.2s,box-shadow 0.2s;border:1px solid #e8f5e9}}
    .prod-card:hover{{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,0.14)}}
    .prod-img{{aspect-ratio:1;background:#f0fdf4;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:48px}}
    .prod-img img{{width:100%;height:100%;object-fit:cover}}
    .prod-info{{padding:14px}}
    .prod-name{{font-size:14px;font-weight:700;color:#1a2332;margin-bottom:4px}}
    .prod-size{{font-size:11px;color:#94a3b8;margin-bottom:12px}}
    .prod-cta{{display:block;background:#008641;color:white;padding:8px;border-radius:8px;font-weight:700;font-size:12px;text-align:center}}

    /* Recipe section */
    .recipe-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:24px;max-width:1000px;margin:0 auto}}
    .recipe-card{{background:white;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08)}}
    .recipe-img{{height:180px}}
    .recipe-body{{padding:18px}}
    .recipe-name{{font-size:16px;font-weight:700;margin-bottom:6px}}
    .recipe-meta{{font-size:12px;color:#64748b;margin-bottom:14px}}
    .recipe-btn{{display:inline-block;background:#FFDE00;color:#008641;padding:8px 20px;border-radius:99px;font-weight:700;font-size:13px}}

    /* Campaign strip */
    .campaign{{background:#005c2c;padding:64px 80px;display:flex;align-items:center;gap:56px;flex-wrap:wrap}}
    .camp-img{{flex:1;min-width:260px;max-width:440px;border-radius:20px;overflow:hidden;box-shadow:0 16px 48px rgba(0,0,0,0.3)}}
    .camp-img img{{width:100%;height:auto;display:block}}
    .camp-text{{flex:1;min-width:260px;color:white}}
    .camp-label{{font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#FFDE00;margin-bottom:12px}}
    .camp-title{{font-size:clamp(24px,3vw,36px);font-weight:900;margin-bottom:16px;line-height:1.15}}
    .camp-body{{font-size:15px;color:rgba(255,255,255,0.8);line-height:1.7;margin-bottom:28px}}

    /* CTA */
    .cta-band{{background:#FFDE00;padding:72px 48px;text-align:center}}
    .cta-band h2{{font-size:36px;font-weight:900;color:#008641;margin-bottom:12px}}
    .cta-band p{{color:#005c2c;margin-bottom:28px;font-size:16px}}
    .cta-green{{background:#008641;color:white;padding:16px 48px;border-radius:99px;font-weight:800;font-size:16px;display:inline-block}}

    /* Footer */
    footer{{background:#0d2e1a;color:#94a3b8;padding:40px 48px}}
    .footer-top{{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:24px;margin-bottom:28px}}
    .footer-brand{{font-size:22px;font-weight:900;color:#FFDE00;margin-bottom:8px}}
    .footer-desc{{font-size:12px;max-width:260px;line-height:1.6}}
    .footer-cols{{display:flex;gap:48px;flex-wrap:wrap}}
    .footer-col h4{{font-size:12px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:white;margin-bottom:12px}}
    .footer-col a{{display:block;font-size:12px;color:#94a3b8;margin-bottom:7px}}
    .footer-bottom{{border-top:1px solid #1e4d2d;padding-top:20px;font-size:11px;text-align:center}}
  </style>
</head>
<body>

<div class="util-bar">🌿 Real Ingredients. Real Flavour. Real Simple. · Free delivery over £30</div>

<nav>
  <div class="nav-logo">{logo_html}</div>
  <div class="nav-links">
    <a href="#">Products</a>
    <a href="#">Recipes</a>
    <a href="#">About Rnorr</a>
    <a href="#">Sustainability</a>
  </div>
  <div class="nav-right">
    <input class="nav-search" placeholder="Search recipes & products…">
    <a href="#cta" class="nav-btn">Shop Now</a>
  </div>
</nav>

<section class="hero">
  <div class="hero-bg"></div>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-badge">🍲 New Campaign</div>
    <h1 class="hero-title">{hero_message or "Real Flavour. Made Simple."}</h1>
    <p class="hero-sub">{body_copy or "Rnorr stock cubes and cook-in sauces bring rich, authentic flavour to every dish. Trusted by home cooks for generations."}</p>
    <div class="hero-btns">
      <a href="#products" class="btn-yellow">{cta or "Shop Products"}</a>
      <a href="#recipes" class="btn-white-outline">Find Recipes</a>
    </div>
  </div>
</section>

<div class="features">
  <div class="feat"><div class="feat-dot"></div>No Artificial Colours</div>
  <div class="feat"><div class="feat-dot"></div>Real Herb Extracts</div>
  <div class="feat"><div class="feat-dot"></div>Trusted Since 1838</div>
  <div class="feat"><div class="feat-dot"></div>100% Natural Stock</div>
</div>

<section class="section" id="products">
  <div class="section-head">
    <div class="section-label">Our Range</div>
    <div class="section-title">Quality Products for Every Kitchen</div>
  </div>
  <div class="prod-grid">{prod_cards or '<div style="text-align:center;color:#94a3b8;width:100%;padding:40px">Products loading from GCS…</div>'}</div>
</section>

<section class="section alt" id="recipes" style="padding:72px 48px;">
  <div style="max-width:1100px;margin:0 auto;">
    <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:40px;">
      <div>
        <div class="section-label" style="margin-bottom:10px;">Explore &amp; Discover</div>
        <h2 style="font-family:Antonio,sans-serif;font-size:clamp(26px,3vw,38px);font-weight:900;color:#005c2c;line-height:1.1;margin:0;">Today, I&apos;m looking for</h2>
      </div>
      <a href="#" style="white-space:nowrap;color:#008641;font-size:14px;font-weight:700;text-decoration:none;border-bottom:2px solid #FFDE00;padding-bottom:2px;">See all articles →</a>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px;">{recipe_cards}</div>
  </div>
</section>

{'<section class="campaign"><div class="camp-img"><img src="' + camp_src + '" alt="Campaign"></div><div class="camp-text"><div class="camp-label">AI Campaign · ' + campaign_id[:16] + '</div><h2 class="camp-title">' + (hero_message or "Home cooking is how you say I care") + '</h2><p class="camp-body">' + (body_copy or "Every great meal starts with great stock.") + '</p><a href="#cta" class="btn-yellow">' + (cta or "Shop Now") + '</a></div></section>' if camp_src else ""}

{reel_section}

<section class="cta-band" id="cta">
  <h2>Flavour that Brings Families Together</h2>
  <p>Stock up on Rnorr — real ingredients, real taste, real simple.</p>
  <a href="#" class="cta-green">Shop the Full Range</a>
</section>

<footer>
  <div class="footer-top">
    <div>
      <div class="footer-brand">Rnorr</div>
      <div class="footer-desc">Real flavour, made simple. Rnorr has been helping home cooks create delicious meals since 1838.</div>
    </div>
    <div class="footer-cols">
      <div class="footer-col">
        <h4>Products</h4>
        <a href="#">Stock Cubes</a><a href="#">Cook-In Sauces</a><a href="#">Gravy</a><a href="#">Bouillon</a>
      </div>
      <div class="footer-col">
        <h4>Explore</h4>
        <a href="#">Recipes</a><a href="#">Our Story</a><a href="#">Sustainability</a>
      </div>
      <div class="footer-col">
        <h4>Help</h4>
        <a href="#">Contact Us</a><a href="#">FAQs</a><a href="#">Delivery</a>
      </div>
    </div>
  </div>
  <div class="footer-bottom">© 2026 Rnorr · AI campaign by CampaignOS · {campaign_id}</div>
</footer>
</body></html>"""


def generate_boozt_website(campaign_image_b64: str = "", campaign_id: str = "",
                            hero_message: str = "", body_copy: str = "", cta: str = "",
                            hero_image_b64: str = "", video_b64: str = "") -> str:
    """Boozt energy drink brand website."""
    from app.brand_assets import get_asset_loader
    loader   = get_asset_loader()
    logos    = loader.list_logos("Boozt")
    products = loader.list_products("Boozt")
    assets   = loader.list_assets("Boozt")

    logo_src     = _gcs_to_b64(logos[0],   "image/png",  200) if logos    else ""
    prod_srcs    = [_gcs_to_b64(p, "image/jpeg", 800) for p in products[:6]]
    hero_bg_src  = _gcs_to_b64(assets[0], "image/jpeg", 800) if assets   else ""
    camp_src     = f"data:image/jpeg;base64,{campaign_image_b64}" if campaign_image_b64 else hero_bg_src
    # Website banner (16:9 channel adaptation) takes priority as hero background
    hero_bg_src  = f"data:image/jpeg;base64,{hero_image_b64}" if hero_image_b64 else hero_bg_src

    logo_html = (f'<img src="{logo_src}" alt="Boozt" style="height:38px;object-fit:contain;">'
                if logo_src else '<span style="font-size:26px;font-weight:900;color:white;letter-spacing:-0.02em;">BOOZT</span>')

    categories = ["Energy","Zero Sugar","Sport Hydration","Tropical","Arctic Mint","Classic"]
    cat_pills  = "".join([f'<a href="#" class="cat-pill">{c}</a>' for c in categories])

    prod_cards = "".join([f"""
    <div class="prod-card">
      <div class="prod-badge">NEW</div>
      <div class="prod-img">{f'<img src="{src}" alt="Boozt">' if src else '⚡'}</div>
      <div class="prod-info">
        <div class="prod-name">Boozt {['Original Energy','Zero Sugar','Sport Hydration','Tropical Blast','Arctic Mint','Classic'][i] if i<6 else 'Energy Drink'}</div>
        <div class="prod-rating">★★★★★ <span style="color:#64748b;font-size:11px">(2,{140+i*37})</span></div>
        <div class="prod-price">£{[1.99,1.99,2.49,1.99,1.99,1.79][i] if i<6 else 1.99}</div>
        <a href="#" class="prod-cta">Add to Basket</a>
      </div>
    </div>""" for i, src in enumerate(prod_srcs)])

    offers = [
        ("💊", "Loyalty Points", "Earn points on every purchase"),
        ("🚚", "Free Delivery", "On orders over £25"),
        ("↩", "Easy Returns", "Free returns within 30 days"),
        ("🎁", "Gift Wrapping", "Available at checkout"),
    ]
    offer_cards = "".join([f'<div class="offer-card"><div class="offer-icon">{o[0]}</div><div class="offer-name">{o[1]}</div><div class="offer-desc">{o[2]}</div></div>' for o in offers])

    reel_section = f"""
<section class="section" id="reel" style="background:#0E105E;padding:0 48px 64px">
  <div class="section-head" style="padding-top:56px"><div class="section-title" style="color:white">Campaign Reel</div></div>
  <video controls autoplay loop muted playsinline style="width:100%;display:block;border-radius:16px;box-shadow:0 12px 40px rgba(0,134,254,0.3);" src="data:video/mp4;base64,{video_b64}"></video>
</section>""" if video_b64 else ""

    return f"""<!DOCTYPE html><html lang="en"><head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Boozt — Energy Drinks</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Rubik',sans-serif;background:#fff;color:#1a1a2e}}
    a{{text-decoration:none;color:inherit}}

    /* Top promo bar */
    .promo-bar{{background:#0E105E;color:#0086FE;text-align:center;padding:9px;font-size:12px;font-weight:700;letter-spacing:0.08em}}
    .promo-bar span{{color:white}}

    /* Nav — Boots style */
    .nav-top{{background:#0E105E;padding:12px 48px;display:flex;align-items:center;justify-content:space-between}}
    .nav-top-right{{display:flex;gap:20px;align-items:center;color:white;font-size:13px}}
    .nav-top-link{{color:rgba(255,255,255,0.8);font-size:12px}}
    nav{{background:white;border-bottom:3px solid #0086FE;padding:0 48px;height:64px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,0.08);position:sticky;top:0;z-index:100}}
    .nav-logo{{display:flex;align-items:center;gap:8px}}
    .nav-search-wrap{{flex:1;max-width:480px;margin:0 32px}}
    .nav-search{{width:100%;padding:10px 18px;border:2px solid #e2e8f0;border-radius:99px;font-size:14px;outline:none}}
    .nav-search:focus{{border-color:#0086FE}}
    .nav-actions{{display:flex;gap:16px;align-items:center}}
    .nav-action{{font-size:12px;font-weight:600;color:#0E105E;display:flex;flex-direction:column;align-items:center;gap:2px}}
    .nav-basket{{background:#0086FE;color:white;padding:10px 20px;border-radius:99px;font-weight:700;font-size:13px}}

    /* Category nav */
    .cat-nav{{background:white;border-bottom:1px solid #e2e8f0;padding:12px 48px;display:flex;gap:8px;flex-wrap:wrap;overflow-x:auto}}
    .cat-pill{{padding:7px 16px;border-radius:99px;font-size:13px;font-weight:600;border:1.5px solid #e2e8f0;color:#374151;white-space:nowrap;transition:all 0.2s}}
    .cat-pill:hover{{border-color:#0086FE;color:#0086FE;background:#fff1f2}}

    /* Hero — Boots-style promo banner */
    .hero{{position:relative;height:500px;display:flex;align-items:center;overflow:hidden;background:#0E105E}}
    .hero-bg{{position:absolute;inset:0;background-size:cover;background-position:center top;{f'background-image:url("{hero_bg_src}");' if hero_bg_src else "background:linear-gradient(135deg,#0E105E,#2d2d4e);"}filter:brightness(0.45)}}
    .hero-overlay{{position:absolute;inset:0;background:linear-gradient(90deg,rgba(26,26,46,0.92) 0%,rgba(26,26,46,0.55) 55%,transparent 100%)}}
    .hero-content{{position:relative;z-index:2;padding:0 80px;max-width:580px}}
    .hero-tag{{display:inline-block;background:#0086FE;color:white;font-size:11px;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;padding:5px 14px;border-radius:99px;margin-bottom:16px}}
    .hero-title{{font-size:clamp(32px,4.2vw,52px);font-weight:900;color:white;line-height:1.1;margin-bottom:14px;letter-spacing:-0.025em}}
    .hero-sub{{font-size:16px;color:rgba(255,255,255,0.8);line-height:1.65;margin-bottom:28px}}
    .hero-btns{{display:flex;gap:12px;flex-wrap:wrap}}
    .btn-red{{background:#0086FE;color:white;padding:14px 32px;border-radius:99px;font-weight:800;font-size:14px;transition:transform 0.2s,box-shadow 0.2s}}
    .btn-red:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(255,68,68,0.4)}}
    .btn-wh{{border:2px solid white;color:white;padding:12px 28px;border-radius:99px;font-weight:600;font-size:14px}}

    /* Offers row */
    .offers{{background:white;padding:24px 48px;display:grid;grid-template-columns:repeat(4,1fr);gap:16px;border-bottom:1px solid #e2e8f0}}
    .offer-card{{display:flex;align-items:center;gap:12px;padding:12px;border-radius:12px;background:#f8f8fc}}
    .offer-icon{{font-size:24px}}
    .offer-name{{font-size:13px;font-weight:700;color:#0E105E}}
    .offer-desc{{font-size:11px;color:#64748b;margin-top:2px}}

    /* Products — Boots card style */
    .section{{padding:56px 48px}}
    .section.grey{{background:white}}
    .section-head{{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:28px}}
    .section-title{{font-size:24px;font-weight:800;color:#0E105E}}
    .section-more{{font-size:13px;font-weight:700;color:#0086FE}}
    .prod-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px}}
    .prod-card{{background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);transition:transform 0.2s,box-shadow 0.2s;position:relative;border:1px solid #f0f0f8}}
    .prod-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.12)}}
    .prod-badge{{position:absolute;top:10px;left:10px;background:#0086FE;color:white;font-size:10px;font-weight:800;padding:3px 8px;border-radius:4px;z-index:1}}
    .prod-img{{aspect-ratio:1;background:#f4f4f8;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:48px}}
    .prod-img img{{width:100%;height:100%;object-fit:cover}}
    .prod-info{{padding:12px}}
    .prod-name{{font-size:13px;font-weight:600;color:#0E105E;margin-bottom:4px;line-height:1.3}}
    .prod-rating{{font-size:11px;color:#f59e0b;margin-bottom:6px}}
    .prod-price{{font-size:16px;font-weight:800;color:#0E105E;margin-bottom:10px}}
    .prod-cta{{display:block;background:#0E105E;color:white;padding:8px;border-radius:8px;font-weight:700;font-size:12px;text-align:center;transition:background 0.2s}}
    .prod-cta:hover{{background:#0086FE}}

    /* Campaign strip */
    .campaign{{background:#f4f4f8;padding:56px 80px;display:flex;align-items:center;gap:48px;flex-wrap:wrap}}
    .camp-img{{flex:1;min-width:260px;max-width:420px;border-radius:20px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.15)}}
    .camp-img img{{width:100%;display:block}}
    .camp-text{{flex:1;min-width:260px}}
    .camp-label{{font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#0086FE;margin-bottom:10px}}
    .camp-title{{font-size:clamp(22px,3vw,34px);font-weight:900;margin-bottom:14px;line-height:1.2}}
    .camp-body{{font-size:15px;color:#64748b;line-height:1.7;margin-bottom:24px}}

    /* Loyalty */
    .loyalty{{background:#0E105E;padding:56px 48px;text-align:center;color:white}}
    .loyalty h2{{font-size:32px;font-weight:900;margin-bottom:12px}}
    .loyalty p{{color:rgba(255,255,255,0.75);margin-bottom:28px;font-size:16px}}
    .loyalty-btn{{background:#0086FE;color:white;padding:15px 44px;border-radius:99px;font-weight:800;font-size:15px;display:inline-block}}

    /* Footer */
    footer{{background:#0d0d1a;color:#64748b;padding:40px 48px}}
    .footer-grid{{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:32px;margin-bottom:32px}}
    .footer-brand{{font-size:22px;font-weight:900;color:white;margin-bottom:8px}}
    .footer-desc{{font-size:12px;line-height:1.6;max-width:240px}}
    .footer-col h4{{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:0.1em;color:white;margin-bottom:12px}}
    .footer-col a{{display:block;font-size:12px;color:#64748b;margin-bottom:7px}}
    .footer-bottom{{border-top:1px solid #0E105E;padding-top:20px;font-size:11px;text-align:center}}
  </style>
</head>
<body>

<div class="promo-bar">⚡ NEW LAUNCH: {hero_message[:45] if hero_message else 'Boozt Original Energy — New Formula'} · <span>Free delivery over £25</span></div>

<div class="nav-top">
  <div style="color:rgba(255,255,255,0.6);font-size:12px">Pure Energy. Zero Limits.</div>
  <div class="nav-top-right">
    <a href="#" class="nav-top-link">My Account</a>
    <a href="#" class="nav-top-link">Track Order</a>
    <a href="#" class="nav-top-link">Help</a>
  </div>
</div>

<nav>
  <div class="nav-logo">{logo_html}</div>
  <div class="nav-search-wrap">
    <input class="nav-search" placeholder="Search energy drinks, hydration, zero sugar…">
  </div>
  <div class="nav-actions">
    <div class="nav-action">👤<span>Account</span></div>
    <div class="nav-action">❤️<span>Saved</span></div>
    <a href="#cta" class="nav-basket">🛒 Basket</a>
  </div>
</nav>

<div class="cat-nav">{cat_pills}</div>

<section class="hero">
  <div class="hero-bg"></div>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-tag">⚡ Pure Energy. Zero Limits.</div>
    <h1 class="hero-title">{hero_message or "Energy That Moves With You"}</h1>
    <p class="hero-sub">{body_copy or "Boozt Energy Drink delivers instant focus, sustained energy and electrolyte hydration — engineered for people who don't stop."}</p>
    <div class="hero-btns">
      <a href="#products" class="btn-red">{cta or "Shop Now"}</a>
      <a href="#campaign" class="btn-wh">Learn More</a>
    </div>
  </div>
</section>

<div class="offers">{offer_cards}</div>

<section class="section grey" id="products">
  <div class="section-head">
    <div class="section-title">New In — Boozt Range</div>
    <a href="#" class="section-more">View all →</a>
  </div>
  <div class="prod-grid">{prod_cards or '<div style="text-align:center;color:#94a3b8;padding:40px;width:100%">Products loading…</div>'}</div>
</section>

{'<section class="campaign" id="campaign"><div class="camp-img"><img src="' + camp_src + '" alt="Campaign"></div><div class="camp-text"><div class="camp-label">AI Campaign · ' + campaign_id[:16] + '</div><h2 class="camp-title">' + (hero_message or "Energy That Commands Attention") + '</h2><p class="camp-body">' + (body_copy or "Natural caffeine, B-vitamins and electrolytes — every can engineered to unlock your peak performance.") + '</p><a href="#cta" class="btn-red">' + (cta or "Shop Now") + '</a></div></section>' if camp_src else ""}

{reel_section}

<section class="loyalty" id="cta">
  <h2>Join the Boozt Community</h2>
  <p>Earn points, get exclusive offers, and be the first to discover new launches.</p>
  <a href="#" class="loyalty-btn">Shop Boozt Now</a>
</section>

<footer>
  <div class="footer-grid">
    <div>
      <div class="footer-brand">BOOZT</div>
      <div class="footer-desc">Natural caffeine, B-vitamins and electrolytes — engineered for people who don't stop.</div>
    </div>
    <div class="footer-col"><h4>Products</h4><a href="#">Original Energy</a><a href="#">Zero Sugar</a><a href="#">Sport Hydration</a><a href="#">Tropical Blast</a></div>
    <div class="footer-col"><h4>Help</h4><a href="#">Delivery</a><a href="#">Returns</a><a href="#">FAQs</a><a href="#">Contact</a></div>
    <div class="footer-col"><h4>Company</h4><a href="#">About</a><a href="#">Careers</a><a href="#">Press</a><a href="#">Sustainability</a></div>
  </div>
  <div class="footer-bottom">© 2026 Boozt Energy Drinks · AI campaign by CampaignOS · {campaign_id}</div>
</footer>
</body></html>"""


def generate_landing_html(brand: str, hero_message: str, tagline: str,
                           body_copy: str, cta: str, image_b64: str,
                           campaign_id: str) -> str:
    """Generate a full branded HTML landing page."""
    cfg = BRAND_CONFIG.get(brand, DEFAULT_BRAND)
    brand_tagline = tagline or cfg["tagline"]
    img_tag = (
        f'<img src="data:image/jpeg;base64,{image_b64}" '
        'alt="Campaign Visual" class="hero-img">'
        if image_b64 else ""
    )
    body_html = "<br>".join(textwrap.wrap(body_copy, 80)) if body_copy else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{brand} — {hero_message[:60]}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=Poppins:wght@400;600;700;900&family=Rubik:wght@400;600;700;900&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: {cfg["font"]};
      background: #f8f9fa;
      color: #1a2332;
    }}

    /* ── Nav ── */
    nav {{
      background: {cfg["primary"]};
      padding: 16px 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .nav-brand {{
      font-size: 24px;
      font-weight: 900;
      color: {cfg["accent"]};
      letter-spacing: -0.03em;
    }}
    .nav-cta {{
      background: {cfg["accent"]};
      color: {cfg["primary"]};
      border: none;
      padding: 10px 28px;
      border-radius: 99px;
      font-weight: 800;
      font-size: 14px;
      cursor: pointer;
      text-decoration: none;
    }}

    /* ── Hero ── */
    .hero {{
      background: linear-gradient(135deg, {cfg["primary"]}f0, {cfg["primary"]}cc);
      min-height: 520px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 64px;
      padding: 64px 48px;
      position: relative;
      overflow: hidden;
    }}
    .hero::before {{
      content: "";
      position: absolute;
      top: -80px; right: -80px;
      width: 400px; height: 400px;
      border-radius: 50%;
      background: rgba(255,255,255,0.06);
    }}
    .hero-text {{
      max-width: 520px;
      z-index: 1;
    }}
    .hero-eyebrow {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: {cfg["accent"]};
      margin-bottom: 16px;
    }}
    .hero-headline {{
      font-size: clamp(32px, 4vw, 52px);
      font-weight: 900;
      color: {cfg["text"]};
      line-height: 1.1;
      letter-spacing: -0.03em;
      margin-bottom: 20px;
    }}
    .hero-sub {{
      font-size: 18px;
      color: rgba(255,255,255,0.75);
      line-height: 1.6;
      margin-bottom: 36px;
    }}
    .hero-btn {{
      display: inline-block;
      background: {cfg["accent"]};
      color: {cfg["primary"]};
      padding: 16px 40px;
      border-radius: 99px;
      font-weight: 800;
      font-size: 16px;
      text-decoration: none;
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .hero-btn:hover {{
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }}
    .hero-img {{
      width: 340px;
      height: 340px;
      object-fit: cover;
      border-radius: 24px;
      box-shadow: 0 24px 64px rgba(0,0,0,0.35);
      z-index: 1;
      flex-shrink: 0;
    }}

    /* ── Copy section ── */
    .copy-section {{
      max-width: 760px;
      margin: 72px auto;
      padding: 0 24px;
      text-align: center;
    }}
    .copy-section h2 {{
      font-size: 28px;
      font-weight: 800;
      margin-bottom: 20px;
      color: {cfg["primary"]};
    }}
    .copy-section p {{
      font-size: 17px;
      line-height: 1.75;
      color: #475569;
    }}

    /* ── CTA band ── */
    .cta-band {{
      background: {cfg["primary"]};
      padding: 56px 48px;
      text-align: center;
    }}
    .cta-band h3 {{
      font-size: 32px;
      font-weight: 900;
      color: {cfg["text"]};
      margin-bottom: 24px;
    }}
    .cta-band a {{
      display: inline-block;
      background: {cfg["accent"]};
      color: {cfg["primary"]};
      padding: 16px 48px;
      border-radius: 99px;
      font-weight: 800;
      font-size: 18px;
      text-decoration: none;
    }}

    /* ── Footer ── */
    footer {{
      background: #0f172a;
      color: #64748b;
      text-align: center;
      padding: 28px;
      font-size: 12px;
    }}
    footer span {{ color: {cfg["accent"]}; }}
  </style>
</head>
<body>

  <nav>
    <div class="nav-brand">{brand}</div>
    <a href="#cta" class="nav-cta">{cta or "Shop Now"}</a>
  </nav>

  <section class="hero">
    <div class="hero-text">
      <div class="hero-eyebrow">{brand_tagline}</div>
      <h1 class="hero-headline">{hero_message}</h1>
      {f'<p class="hero-sub">{brand_tagline}</p>' if brand_tagline else ""}
      <a href="#cta" class="hero-btn">{cta or "Discover More"}</a>
    </div>
    {img_tag}
  </section>

  {f'''<section class="copy-section">
    <h2>Why {brand}?</h2>
    <p>{body_html}</p>
  </section>''' if body_html else ""}

  <section class="cta-band" id="cta">
    <h3>Ready to experience {brand}?</h3>
    <a href="#">{cta or "Get Started"}</a>
  </section>

  <footer>
    <p>© 2026 <span>{brand}</span> · AI-generated campaign by <span>CampaignOS</span> · {campaign_id}</p>
  </footer>

</body>
</html>"""


# ── Email ──────────────────────────────────────────────────────────────────────

def _get_logo_b64(brand: str) -> str:
    """
    Load the primary brand logo PNG and return a base64-encoded data URI string.
    Tries local bucket first (dev), then GCS (production) via asset loader.
    Returns empty string if logo not found — email falls back to text wordmark.
    """
    try:
        from pathlib import Path as _P
        # Local bucket path (dev mode)
        logo_dir = _P(__file__).parent.parent / "bucket" / "brands" / brand / "Logos"
        if logo_dir.is_dir():
            _sfx = {"green", "red", "yellow", "orange", "purple", "blue"}
            candidates = sorted(logo_dir.glob("*.png"))
            logo_file  = next(
                (f for f in candidates
                 if not any(f.stem.lower().endswith(s) for s in _sfx)),
                candidates[0] if candidates else None,
            )
            if logo_file:
                return base64.b64encode(logo_file.read_bytes()).decode("utf-8")
        # GCS fallback
        from app.brand_assets import get_asset_loader as _gal
        logos = _gal().list_logos(brand)
        _sfx  = {"green", "red", "yellow", "orange", "purple", "blue"}
        primary = next(
            (p for p in logos
             if p.lower().endswith(".png")
             and not any(p.lower().rsplit(".", 1)[0].endswith(s) for s in _sfx)),
            logos[0] if logos else None,
        )
        if primary and primary.startswith("gs://"):
            from google.cloud import storage as _gcs
            without = primary[5:]
            bucket_name, _, blob_path = without.partition("/")
            data = _gcs.Client().bucket(bucket_name).blob(blob_path).download_as_bytes()
            return base64.b64encode(data).decode("utf-8")
    except Exception as _e:
        logger.debug("logo_b64_failed", brand=brand, error=str(_e))
    return ""


def _build_email_html(
    brand:          str,
    hero_message:   str,
    short_headline: str,
    body_copy:      str,
    cta:            str,
    landing_url:    str,
    image_url:      str = "",   # HTTPS URL for KV image (Gmail-compatible)
    logo_url:       str = "",   # HTTPS URL for brand logo (Gmail-compatible)
    image_b64:      str = "",   # fallback base64 (Apple Mail / Outlook)
    product_name:   str = "",
    email_subject:  str = "",
) -> str:
    """
    Build a premium brand-specific HTML email.

    Layout:
      1. Pre-header (hidden preview text for inbox)
      2. Brand header bar  — brand primary colour, brand name in accent
      3. Hero image        — full-width KV from campaign (base64 inline)
      4. Headline section  — hero_message large, short_headline as subline
      5. Body copy         — paragraph from campaign copy agent
      6. Feature pills     — 3–4 brand attribute chips
      7. CTA button        — accent-colour pill with landing URL
      8. Product spotlight — product name + tagline if provided
      9. Footer            — tagline, social icons (emoji), unsubscribe link

    All styles are inline for maximum email client compatibility.
    Google Fonts loaded via @import for clients that support it (fallback: system fonts).
    """
    cfg        = BRAND_CONFIG.get(brand, DEFAULT_BRAND)
    primary    = cfg["primary"]
    secondary  = cfg.get("secondary", primary)
    accent     = cfg["accent"]
    accent2    = cfg.get("accent2", accent)
    body_bg    = cfg.get("body_bg", "#f9f9f9")
    section_bg = cfg.get("section_bg", "#f4f4f4")
    font_stack = cfg.get("font", "Inter, Arial, sans-serif")
    font_url   = cfg.get("font_url", "")
    tagline    = cfg.get("tagline", "")
    hero_tag   = cfg.get("hero_tag", "")
    brand_copy = body_copy or cfg.get("copy", "")
    features   = cfg.get("features", [])
    cta_label  = cta or "Discover More"

    # Email channel headline — prefer email_subject from copy agent, fall back to hero_message
    email_headline  = email_subject or hero_message
    # Eyebrow above headline — use tagline or short_headline as a teaser line
    email_eyebrow   = tagline.upper() if tagline else (short_headline[:60] if short_headline else brand.upper())

    # ── Logo: prefer HTTPS URL (Gmail-compatible), fallback to base64 ────────
    logo_b64   = ""
    _logo_src  = logo_url  # HTTPS URL passed from main.py
    if not _logo_src:
        logo_b64  = _get_logo_b64(brand)  # base64 fallback (Apple Mail)
        _logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""

    logo_block = (
        f'<img src="{_logo_src}" alt="{brand}" '
        f'style="height:44px;max-width:160px;display:block;border:0;" />'
        if _logo_src
        else f'<span style="font-family:{font_stack};font-size:26px;font-weight:900;'
             f'color:white;letter-spacing:-0.02em;">{brand.upper()}</span>'
    )

    # ── KV Image: prefer HTTPS URL, fallback to base64 ────────────────────────
    _img_src = image_url  # HTTPS URL passed from main.py
    if not _img_src and image_b64:
        _img_src = f"data:image/jpeg;base64,{image_b64}"

    img_block = ""
    if _img_src:
        img_block = f"""
        <!-- Hero KV image — hosted URL works in Gmail -->
        <tr>
          <td style="padding:0;line-height:0;font-size:0;">
            <img src="{_img_src}"
                 width="600" alt="{email_headline}"
                 style="display:block;width:100%;max-width:600px;height:auto;border:0;" />
          </td>
        </tr>"""
    else:
        # Gradient banner fallback when no image
        img_block = f"""
        <!-- Gradient banner — no image available -->
        <tr>
          <td style="background:linear-gradient(135deg,{primary} 0%,{secondary} 50%,{accent}88 100%);
                      padding:48px 40px;text-align:center;">
            <div style="font-family:{font_stack};font-size:32px;font-weight:900;
                         color:white;letter-spacing:-0.02em;line-height:1.2;">
              {email_headline}
            </div>
          </td>
        </tr>"""

    feature_pills = ""
    if features:
        pills = "".join(
            f'<span style="display:inline-block;background:{section_bg};'
            f'border:1.5px solid {accent};color:{primary};'
            f'font-size:12px;font-weight:700;padding:6px 14px;border-radius:99px;'
            f'margin:4px 4px 4px 0;letter-spacing:0.03em;">'
            f'{f}</span>'
            for f in features[:4]
        )
        feature_pills = f"""
        <!-- Feature pills -->
        <tr>
          <td style="padding:12px 40px 28px;background:white;">
            {pills}
          </td>
        </tr>"""

    product_block = ""
    if product_name:
        product_block = f"""
        <!-- Product spotlight -->
        <tr>
          <td style="padding:0 40px 32px;background:white;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td style="border-left:4px solid {accent};padding:12px 16px;
                            background:{section_bg};border-radius:0 8px 8px 0;">
                  <div style="font-size:10px;font-weight:700;color:{primary};
                               letter-spacing:0.12em;text-transform:uppercase;
                               margin-bottom:4px;">Featured Product</div>
                  <div style="font-size:17px;font-weight:800;color:{primary};
                               font-family:{font_stack};">{product_name}</div>
                  {f'<div style="font-size:13px;color:#64748b;margin-top:4px;">{tagline}</div>' if tagline else ""}
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    font_import = f'<style>@import url("{font_url}");</style>' if font_url else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{brand} — {email_headline}</title>
  {font_import}
</head>
<body style="margin:0;padding:0;background:{body_bg};font-family:{font_stack};">

  <!-- Pre-header (inbox preview line — hidden in body) -->
  <div style="display:none;max-height:0;overflow:hidden;color:{body_bg};">
    {email_headline} &zwnj;&nbsp;&zwnj;&nbsp;{short_headline[:60] if short_headline else ""}&zwnj;&nbsp;
  </div>

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background:{body_bg};padding:32px 16px;">
    <tr>
      <td align="center">

        <!-- Email card — 600 px wide -->
        <table width="600" cellpadding="0" cellspacing="0" role="presentation"
               style="max-width:600px;width:100%;border-radius:16px;
                      overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,0.12);">

          <!-- ① HEADER BAR — brand logo + campaign badge -->
          <tr>
            <td style="background:linear-gradient(135deg,{primary} 0%,{secondary} 100%);
                        padding:22px 32px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="vertical-align:middle;">
                    {logo_block}
                    {f'<div style="font-size:11px;font-weight:700;color:{accent};letter-spacing:0.1em;text-transform:uppercase;margin-top:6px;">{hero_tag}</div>' if hero_tag else ""}
                  </td>
                  <td align="right" style="vertical-align:middle;">
                    <span style="display:inline-block;background:rgba(255,255,255,0.15);
                                  border:1.5px solid rgba(255,255,255,0.35);
                                  color:white;font-size:10px;font-weight:700;
                                  padding:6px 14px;border-radius:99px;letter-spacing:0.08em;
                                  text-transform:uppercase;">
                      New Campaign
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          {img_block}

          <!-- ② HEADLINE from copy agent email channel -->
          <tr>
            <td style="padding:36px 40px 24px;background:white;">
              <!-- Eyebrow — email subject line as teaser -->
              <div style="font-size:11px;font-weight:700;color:{accent};
                           letter-spacing:0.14em;text-transform:uppercase;
                           margin-bottom:12px;">
                {email_eyebrow}
              </div>
              <!-- Main headline — email_subject from copy agent -->
              <h1 style="font-family:{font_stack};font-size:30px;font-weight:900;
                          color:{primary};line-height:1.25;margin:0 0 14px;
                          letter-spacing:-0.02em;">
                {email_headline}
              </h1>
              <!-- Subline -->
              <p style="font-size:17px;color:#475569;line-height:1.7;
                         margin:0 0 28px;font-weight:400;">
                {short_headline}
              </p>
              <!-- Body copy -->
              {f'<p style="font-size:15px;color:#64748b;line-height:1.8;margin:0 0 32px;">{brand_copy}</p>' if brand_copy else ""}
              <!-- CTA button -->
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="border-radius:99px;background:linear-gradient(135deg,{primary},{secondary});">
                    <a href="{landing_url}"
                       style="display:inline-block;padding:16px 40px;
                               font-family:{font_stack};font-size:15px;font-weight:800;
                               color:white;text-decoration:none;letter-spacing:0.02em;
                               border-radius:99px;">
                      {cta_label} &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          {feature_pills}

          {product_block}

          <!-- ③ ACCENT DIVIDER STRIP -->
          <tr>
            <td style="background:linear-gradient(90deg,{primary},{accent},{accent2},{primary});
                        height:4px;line-height:4px;font-size:0;">&nbsp;</td>
          </tr>

          <!-- ④ SECONDARY CONTENT — brand promise -->
          <tr>
            <td style="background:{section_bg};padding:32px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <!-- Left: brand quote / promise -->
                  <td style="width:56%;vertical-align:top;padding-right:24px;">
                    <div style="font-size:10px;font-weight:700;color:{primary};
                                 letter-spacing:0.1em;text-transform:uppercase;
                                 margin-bottom:10px;">Our Promise</div>
                    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0;
                               font-style:italic;">
                      &ldquo;{cfg.get('copy','')[:120]}{"…" if len(cfg.get("copy",""))>120 else ""}&rdquo;
                    </p>
                  </td>
                  <!-- Right: stats / social proof -->
                  <td style="width:44%;vertical-align:top;border-left:2px solid {accent};
                              padding-left:24px;">
                    <div style="font-size:10px;font-weight:700;color:{primary};
                                 letter-spacing:0.1em;text-transform:uppercase;
                                 margin-bottom:10px;">Campaign Channels</div>
                    <div style="font-size:13px;color:#475569;line-height:1.9;">
                      📸 Instagram &amp; Stories<br/>
                      🔍 Google Ads<br/>
                      🌐 Website Banner<br/>
                      📘 Meta Ads
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ⑤ FOOTER -->
          <tr>
            <td style="background:{primary};padding:28px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <!-- Footer logo -->
                    <div style="margin-bottom:10px;">
                      {logo_block.replace('height:44px', 'height:32px') if logo_b64
                       else f'<span style="font-size:18px;font-weight:900;color:white;">{brand.upper()}</span>'}
                    </div>
                    {f'<div style="font-size:12px;color:{accent};font-weight:700;margin-bottom:12px;">{tagline}</div>' if tagline else ""}
                    <div style="font-size:20px;margin-bottom:12px;letter-spacing:0.1em;">
                      📸 &nbsp; 🎵 &nbsp; ▶️ &nbsp; 🌐
                    </div>
                    <div style="font-size:11px;color:rgba(255,255,255,0.5);line-height:1.8;">
                      You received this because you subscribed to {brand} campaign updates.<br/>
                      <a href="#" style="color:{accent};text-decoration:underline;">Unsubscribe</a>
                      &nbsp;·&nbsp;
                      <a href="{landing_url}" style="color:{accent};text-decoration:none;">View in browser</a>
                      &nbsp;·&nbsp;
                      <span>AI-generated by CampaignOS &bull; Infosys Aster</span>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
        <!-- /Email card -->

      </td>
    </tr>
  </table>

</body>
</html>"""


def publish_instagram(
    image_url: str,
    caption: str = "",
    brand: str = "",
) -> dict:
    """
    Publish a single image post to Instagram Business account via Graph API.

    Requires in .env / Cloud Run env vars:
      INSTAGRAM_ACCESS_TOKEN          — Page Access Token with instagram_content_publish
      INSTAGRAM_BUSINESS_ACCOUNT_ID   — Instagram Business Account ID (numeric)

    image_url may be a public HTTPS URL or a GCS URI (gs://...) — GCS URIs are
    automatically converted to storage.googleapis.com public URLs.
    """
    import requests

    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    ig_user_id   = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    if not access_token or not ig_user_id:
        logger.warning("instagram_skipped",
                       reason="INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID not set")
        return {
            "status": "skipped",
            "reason": (
                "Instagram credentials not configured. "
                "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID in .env."
            ),
        }

    if not image_url:
        return {"status": "skipped", "reason": "No image URL provided for Instagram post"}

    # Convert GCS URI → public HTTPS URL
    if image_url.startswith("gs://"):
        image_url = "https://storage.googleapis.com/" + image_url[5:]

    api_base = "https://graph.facebook.com/v19.0"

    # ── Step 1: Create media container ────────────────────────────────────────
    try:
        resp = requests.post(
            f"{api_base}/{ig_user_id}/media",
            data={
                "image_url":    image_url,
                "caption":      caption or "",
                "access_token": access_token,
            },
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            err = data["error"]
            logger.error("instagram_container_failed", error=err)
            return {"status": "error", "step": "create_container",
                    "error": err.get("message", str(err))}

        creation_id = data.get("id")
        if not creation_id:
            return {"status": "error", "step": "create_container",
                    "error": "No creation_id in API response"}

        logger.info("instagram_container_created", creation_id=creation_id, brand=brand)

    except Exception as e:
        logger.error("instagram_container_exception", error=str(e))
        return {"status": "error", "step": "create_container", "error": str(e)}

    # ── Step 2: Poll until FINISHED (max 2 min, 5-sec intervals) ──────────────
    # Instagram needs time to fetch and cache the image before it can be published.
    for _poll in range(24):
        time.sleep(5)
        try:
            _st = requests.get(
                f"{api_base}/{creation_id}",
                params={"fields": "status_code", "access_token": access_token},
                timeout=15,
            ).json()
            _sc = _st.get("status_code", "")
            logger.debug("instagram_image_poll", poll=_poll + 1, status=_sc)
            if _sc == "FINISHED":
                break
            if _sc == "ERROR":
                return {"status": "error", "step": "processing",
                        "error": f"Instagram rejected the image: {_st}"}
        except Exception as _pe:
            logger.warning("instagram_image_poll_error", error=str(_pe))
    else:
        logger.warning("instagram_image_poll_timeout", creation_id=creation_id)
        # Proceed anyway — sometimes status API is slow but publish still works

    # ── Step 3: Publish container ──────────────────────────────────────────────
    try:
        resp = requests.post(
            f"{api_base}/{ig_user_id}/media_publish",
            data={
                "creation_id":  creation_id,
                "access_token": access_token,
            },
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            err = data["error"]
            logger.error("instagram_publish_failed", error=err)
            return {"status": "error", "step": "publish",
                    "error": err.get("message", str(err))}

        post_id = data.get("id", "")
        logger.info("instagram_published", post_id=post_id, brand=brand)
        return {
            "status":    "published",
            "platform":  "Instagram",
            "post_id":   post_id,
            "image_url": image_url,
            "caption":   caption[:100] + "…" if len(caption) > 100 else caption,
            "ig_user":   ig_user_id,
        }

    except Exception as e:
        logger.error("instagram_publish_exception", error=str(e))
        return {"status": "error", "step": "publish", "error": str(e)}


def publish_instagram_reel(
    video_url: str,
    caption: str = "",
    brand: str = "",
) -> dict:
    """
    Publish a video as an Instagram Reel via Graph API.

    Flow: create container → poll status_code until FINISHED → publish.
    Video must be a publicly accessible HTTPS URL (MP4, H.264, max 15 min).
    GCS URIs (gs://...) are auto-converted to storage.googleapis.com URLs.

    Requires same env vars as publish_instagram():
      INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID
    """
    import requests
    import time

    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    ig_user_id   = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    if not access_token or not ig_user_id:
        logger.warning("instagram_reel_skipped", reason="credentials not set")
        return {
            "status": "skipped",
            "reason": "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID in .env.",
        }

    if not video_url:
        return {"status": "skipped", "reason": "No video URL provided for Instagram Reel"}

    if video_url.startswith("gs://"):
        video_url = "https://storage.googleapis.com/" + video_url[5:]

    api_base = "https://graph.facebook.com/v19.0"

    # ── Step 1: Create Reel container ─────────────────────────────────────────
    try:
        resp = requests.post(
            f"{api_base}/{ig_user_id}/media",
            data={
                "media_type":    "REELS",
                "video_url":     video_url,
                "caption":       caption or "",
                "share_to_feed": "true",
                "access_token":  access_token,
            },
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            err = data["error"]
            logger.error("instagram_reel_container_failed", error=err)
            return {"status": "error", "step": "create_container",
                    "error": err.get("message", str(err))}

        creation_id = data.get("id")
        if not creation_id:
            return {"status": "error", "step": "create_container",
                    "error": "No creation_id in response"}

        logger.info("instagram_reel_container_created", creation_id=creation_id, brand=brand)

    except Exception as e:
        logger.error("instagram_reel_container_exception", error=str(e))
        return {"status": "error", "step": "create_container", "error": str(e)}

    # ── Step 2: Poll until FINISHED (max 5 min, 5-sec intervals) ──────────────
    for poll in range(60):
        time.sleep(5)
        try:
            st = requests.get(
                f"{api_base}/{creation_id}",
                params={"fields": "status_code", "access_token": access_token},
                timeout=15,
            ).json()
            status_code = st.get("status_code", "")
            logger.debug("instagram_reel_poll", poll=poll + 1, status=status_code)

            if status_code == "FINISHED":
                break
            if status_code == "ERROR":
                return {"status": "error", "step": "processing",
                        "error": f"Instagram rejected the reel: {st}"}
        except Exception as _pe:
            logger.warning("instagram_reel_poll_error", error=str(_pe))
    else:
        return {"status": "error", "step": "processing",
                "error": "Reel processing timed out after 5 minutes"}

    # ── Step 3: Publish ────────────────────────────────────────────────────────
    try:
        resp = requests.post(
            f"{api_base}/{ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": access_token},
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            err = data["error"]
            logger.error("instagram_reel_publish_failed", error=err)
            return {"status": "error", "step": "publish",
                    "error": err.get("message", str(err))}

        post_id = data.get("id", "")
        logger.info("instagram_reel_published", post_id=post_id, brand=brand)
        return {
            "status":    "published",
            "platform":  "Instagram Reels",
            "post_id":   post_id,
            "video_url": video_url,
            "caption":   caption[:100] + "…" if len(caption) > 100 else caption,
            "ig_user":   ig_user_id,
        }

    except Exception as e:
        logger.error("instagram_reel_publish_exception", error=str(e))
        return {"status": "error", "step": "publish", "error": str(e)}


def send_campaign_email(
    to_email:       str,
    brand:          str,
    hero_message:   str,
    short_headline: str,
    cta:            str,
    landing_url:    str,
    image_url:      str = "",   # HTTPS URL — preferred (Gmail-compatible)
    logo_url:       str = "",   # HTTPS URL — preferred (Gmail-compatible)
    image_b64:      str = "",   # fallback base64 (Apple Mail, Outlook)
    email_subject:  str = "",
    body_copy:      str = "",
    product_name:   str = "",
) -> dict:
    """
    Send a premium branded HTML campaign email via SMTP.

    SMTP configuration (set in .env or Cloud Run env vars):
      EMAIL_SMTP_HOST     — SMTP server hostname  (default: smtp.gmail.com)
      EMAIL_SMTP_PORT     — SMTP port             (default: 587 / STARTTLS)
      EMAIL_FROM          — Sender address        e.g. campaigns@yourbrand.com
      EMAIL_APP_PASSWORD  — SMTP password / app password
      EMAIL_FROM_NAME     — Display name          (default: brand name)

    Gmail setup:
      1. Enable 2-Step Verification on your Google account
      2. Go to myaccount.google.com → Security → App Passwords
      3. Create an app password for "Mail"
      4. Use that 16-char password as EMAIL_APP_PASSWORD

    SendGrid / Mailgun:
      Set EMAIL_SMTP_HOST=smtp.sendgrid.net, EMAIL_SMTP_PORT=587
      EMAIL_FROM=apikey, EMAIL_APP_PASSWORD=<your-sendgrid-api-key>
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text      import MIMEText

    smtp_host  = os.getenv("EMAIL_SMTP_HOST",    "smtp.gmail.com")
    smtp_port  = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    smtp_user  = os.getenv("EMAIL_FROM",          "")
    smtp_pass  = os.getenv("EMAIL_APP_PASSWORD",  "")
    from_name  = os.getenv("EMAIL_FROM_NAME",     brand)

    if not smtp_user or not smtp_pass:
        logger.warning("email_skipped",
                       reason="EMAIL_FROM or EMAIL_APP_PASSWORD not set in environment")
        return {
            "status": "skipped",
            "reason": (
                "SMTP credentials not configured. "
                "Set EMAIL_FROM and EMAIL_APP_PASSWORD in .env "
                "(or Cloud Run env vars) to enable email sending."
            ),
        }

    html_body = _build_email_html(
        brand          = brand,
        hero_message   = hero_message,
        short_headline = short_headline,
        email_subject  = email_subject,
        body_copy      = body_copy,
        cta            = cta,
        image_url      = image_url,
        logo_url       = logo_url,
        image_b64      = image_b64,   # fallback
        landing_url    = landing_url,
        product_name   = product_name,
    )

    # Subject line: email_subject from copy agent if available, else hero_message
    subject = f"{email_subject or hero_message or short_headline} — {brand}"

    msg               = MIMEMultipart("alternative")
    msg["Subject"]    = subject
    msg["From"]       = f"{from_name} <{smtp_user}>"
    msg["To"]         = to_email
    msg["X-Mailer"]   = "CampaignOS / Infosys Aster"
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        logger.info("email_sent", to=to_email, brand=brand, subject=subject)
        return {"status": "sent", "to": to_email, "subject": subject}
    except smtplib.SMTPAuthenticationError:
        logger.error("email_auth_failed", user=smtp_user)
        return {"status": "error",
                "error": "SMTP authentication failed — check EMAIL_APP_PASSWORD"}
    except Exception as e:
        logger.error("email_failed", error=str(e))
        return {"status": "error", "error": str(e)}
