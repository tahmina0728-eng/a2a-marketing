from __future__ import annotations

import structlog

from app.config import get_settings
from app.brand_assets import get_asset_loader
from app.agents._utils import _generate, _genai_client
from app.brands import barclays as _barclays

logger   = structlog.get_logger()
settings = get_settings()


def run_kv(brand: str, prompt: str, product_name: str = "", market: str = "", audience: str = "", copy_headline: str = "", campaign_type: str = "") -> dict:
    """
    Standalone Morphis: one text call for a headline + visual scene, one image
    call for the actual key visual, then the same Pillow brand-overlay
    post-processing (_apply_brand_overlay) the full pipeline uses so the
    headline actually renders on the image instead of falling back to just
    the brand name.

    Skips the full pipeline's reference-banner vision analysis step (an extra
    Gemini call for marginal quality gain) and any upstream big-idea/copy
    context — same standalone tradeoff already accepted for the other agents.
    """
    # Derive audience descriptor for scene persona
    _al = (audience or "").lower()
    if "famil" in _al:
        _who = "a family (parents in their 30s-40s with one or two children aged 8-14)"
    elif "sme" in _al or "entrepreneur" in _al:
        _who = "two entrepreneurs aged 25-45, driven and ambitious"
    elif "business prof" in _al or "professional" in _al:
        _who = "two business professionals aged 30-50, confident and polished"
    elif "digital native" in _al or ("16" in _al and "24" in _al):
        _who = "two digital natives aged 16-24, creative and expressive, phones in hand"
    elif "young adult" in _al or ("18" in _al and "35" in _al):
        _who = "two young adults aged 18-35, stylish and vibrant"
    elif "women" in _al or "woman" in _al:
        _who = "two women aged 18-35, stylish and modern"
    elif "men" in _al or "man" in _al:
        _who = "two men aged 25-45, active and confident"
    else:
        _who = "two or three people of diverse ages"

    _is_wimbledon = brand.lower() == "barclays" and "wimbledon" in campaign_type.lower()
    _is_haleon_brand = brand.lower() == "haleon"

    if _is_wimbledon:
        # Headline only — scene direction comes from concepts.json, not the LLM.
        _morphis_sys = (
            "You are Morphis, the key visual designer for an AI marketing campaign system. "
            "You specialise in sports partnership advertising. Your images feel aspirational, "
            "human, and emotionally resonant — real people in meaningful sporting moments."
        )
        _morphis_instr = (
            "The campaign is Barclays × Wimbledon — Official Banking Partner of The Championships. "
            "The creative platform is progress through sport and human connection. "
            'Respond ONLY with JSON, no markdown fences: '
            '{"headline": "short aspirational campaign headline, 4-8 words — about progress, belief, or shared achievement. No financial product claims."}'
        )
    elif product_name and _is_haleon_brand:
        # Haleon health products — scene must show the specific product, not a smartphone
        _morphis_sys = (
            "You are Morphis, the key visual designer for an AI marketing campaign system. "
            "You specialise in healthcare and FMCG advertising. Your images feel warm, human, "
            "and credible — real people in relatable everyday health moments."
        )
        _morphis_instr = (
            f'The Haleon product being advertised is: "{product_name}". '
            f'The target audience is: {_who}. '
            'Respond ONLY with JSON, no markdown fences: '
            '{"headline": "short empathetic campaign headline, 4-8 words", '
            f'"scene": "2-3 sentences: show {_who} in a warm everyday moment where '
            f'they are holding or have just used the {product_name} product pack/box/tube — '
            'the product packaging is clearly visible and in focus in their hand or on a surface nearby. '
            'People occupy the RIGHT TWO-THIRDS of the frame. The LEFT THIRD is clean, bright, '
            'uncluttered (white wall, soft bokeh, or open daylight). '
            'Warm natural daylight, no clinical settings, no text or logos."}'
        )
    elif product_name:
        _morphis_sys = (
            "You are Morphis, the key visual designer for an AI marketing campaign system. "
            "You specialise in product offer advertising — your images must feel exciting, "
            "energetic, and celebratory. The campaign is about a special deal or plan, "
            "so the mood should convey joy, freedom, achievement, and the thrill of a great offer."
        )
        _morphis_instr = (
            f'The product being promoted is: "{product_name}". '
            f'The target audience is: {_who}. '
            'Respond ONLY with JSON, no markdown fences: '
            '{"headline": "bold 4-7 word offer headline — exciting, benefit-driven, action-oriented", '
            f'"scene": "2-3 sentences: show {_who} actively using a smartphone together — '
            'holding it, smiling at the screen, or sharing the display. They occupy the RIGHT HALF '
            'of the frame. The upper-left area is naturally light, airy, and uncluttered — '
            'bright sky, soft background, or blurred environment. Clean, aspirational, joyful. '
            'Do not mention any text, words, logos, or price figures."}'
        )
    else:
        _morphis_sys = (
            "You are Morphis, the key visual designer for an AI marketing campaign system. "
            "You write a short campaign headline and describe a visual scene for an image generator."
        )
        _morphis_instr = (
            f'The target audience is: {_who}. '
            'Respond ONLY with JSON, no markdown fences: '
            '{"headline": "short punchy campaign headline, 4-8 words", '
            f'"scene": "2-3 sentences: show {_who} in a vibrant, aspirational setting. '
            'Setting, mood, lighting — no text, words, or logos in the image."}'
        )

    data = _generate(_morphis_sys, brand, prompt, _morphis_instr)

    # Use copy agent's headline if provided; otherwise use LLM-generated one
    headline = copy_headline.strip() if copy_headline and copy_headline.strip() else (data.get("headline", "") or prompt)

    if _is_wimbledon:
        # Scene comes from concepts.json, not the LLM.
        # select_concepts() keyword-matches the prompt + headline against themes
        # (partnership / progress / belief / community / tradition) and returns
        # the structured creative_direction from the matching concept.
        c1_dir, _ = _barclays.select_concepts(
            big_idea_seed=prompt,
            copy_headline=headline,
            fan_truth="",
        )
        scene = c1_dir
        logger.info("kv_wimbledon_concept_selected", brand=brand, concept=scene[:80])
    else:
        scene = data.get("scene", "") or prompt

    image_b64 = ""
    try:
        from google.genai import types as gtypes
        from app.creative_pipeline import _part_for_uri

        loader = get_asset_loader()
        brand_spelled = " - ".join(brand.upper())
        if brand == "UBS Bank":
            no_text_rule = (
                "TYPOGRAPHY RULE: Absolutely NO text, logos, numbers, or words anywhere in the "
                "image. All copy is added in post-production.\n\n"
            )
        else:
            no_text_rule = (
                f"CRITICAL BRAND RULE: Brand name spelled exactly: {brand_spelled} — this is a "
                f"completely fictional brand, not a real-world product.\n"
                "TYPOGRAPHY RULE: No text anywhere in the image except brand packaging labels "
                "if products are shown. All headline copy is added in post-production.\n\n"
            )
        _product_rule = (
            f"PRODUCT RULE: The product being advertised is {product_name}. "
            f"The {product_name} packaging (its actual box, tube, or bottle with its real colours "
            f"and label) must be clearly visible and prominent in the scene — "
            f"held in someone's hand, on a surface, or on a shelf. "
            f"Do NOT show any other product, generic bottle, or unrelated packaging.\n\n"
        ) if product_name and _is_haleon_brand else ""
        image_prompt = (
            f"{no_text_rule}{_product_rule}{scene}\n\n"
            "Aspect ratio 16:9, photorealistic, premium advertising photography."
        )

        contents: list = []
        logos = loader.list_logos(brand)
        # Prefer a logo that contains the brand name and isn't a pure-white variant.
        # Sunrise logo is skipped entirely — its distinctive S-circle causes Gemini to
        # reproduce the logo in the generated image; we composite it in post-production.
        _bslug = brand.split()[0].lower()
        _ref_logo = (
            next((p for p in logos if _bslug in p.lower() and "_dark" in p.lower()), None) or
            next((p for p in logos if _bslug in p.lower() and "_white" not in p.lower()), None) or
            next((p for p in logos if _bslug in p.lower()), None) or
            (logos[0] if logos else None)
        )
        if _ref_logo and brand.lower() not in ("sunrise",) and (part := _part_for_uri(_ref_logo)):
            contents.append(f"BRAND IDENTITY REFERENCE for {brand} — colour palette and style "
                             f"only, do not render this logo in the image.")
            contents.append(part)
        products = loader.list_products(brand)
        # Haleon: sort the matched sub-brand product to the front so Gemini
        # gets the right packaging reference (not whatever comes first alphabetically).
        if brand.lower() == "haleon" and product_name and products:
            from pathlib import Path as _PPkv
            _pk = product_name.lower().replace("-", "").replace(" ", "")
            _pm = next(
                (p for p in products
                 if _pk in _PPkv(p).stem.lower().replace("-", "").replace(" ", "")),
                None,
            )
            if _pm:
                products = [_pm] + [p for p in products if p != _pm]
        # For brands with no Products folder (e.g. Sunrise), use a campaign asset
        # from the Assets folder as a visual style reference so Gemini can match
        # the brand's actual photography style, palette, and mood.
        # Sunrise is excluded: its campaign banner assets show the S-circle logo, and
        # Gemini reproduces it in the generated image — causing a duplicate when we
        # composite the programmatic logo in post-production via _apply_brand_overlay.
        _style_refs = [] if products or brand.lower() in ("sunrise",) else [
            a for a in loader.list_assets(brand)
            if not a.lower().endswith((".mp4", ".svg"))
        ][:1]

        if products and (part := _part_for_uri(products[0])):
            contents.append(f"PRODUCT REFERENCE for {brand} — match shape and colours if products "
                             f"are shown in the scene.")
            contents.append(part)
        elif _style_refs:
            try:
                from app.creative_pipeline import _load_bytes as _clb
                from google.genai import types as _gt2
                from PIL import Image as _PILr
                from io import BytesIO as _BIOr
                _raw = _clb(_style_refs[0])
                if _raw:
                    _ri = _PILr.open(_BIOr(_raw)).convert("RGB")
                    if max(_ri.size) > 1024:
                        _sc = 1024 / max(_ri.size)
                        _ri = _ri.resize(
                            (int(_ri.width * _sc), int(_ri.height * _sc)), _PILr.LANCZOS
                        )
                    _rb = _BIOr()
                    _ri.save(_rb, format="JPEG", quality=85)
                    contents.append(
                        f"BRAND CAMPAIGN STYLE REFERENCE for {brand} — match this exact visual style: "
                        f"photography approach, colour palette, mood, lighting, and composition. "
                        f"Generate the new image in the same aesthetic as this reference campaign."
                    )
                    contents.append(_gt2.Part.from_bytes(data=_rb.getvalue(), mime_type="image/jpeg"))
            except Exception as _sre:
                logger.warning("kv_style_ref_failed", brand=brand, error=str(_sre))

        # Sunrise-specific composition rule — differs by mode
        if brand.lower() in ("sunrise",):
            # Applied to both modes: Sunrise campaign banners contain the S-circle; we
            # skip those as references, but Gemini still knows the brand from guidelines.
            # Explicitly forbid reproducing any circular brand marks or logo elements.
            _no_logo_rule = (
                "CRITICAL RULE: Do NOT render any S-circle icons, Sunrise logos, sun icons, "
                "circular brand marks, semicircle symbols, or any recognisable brand symbols "
                "anywhere in the image. All brand elements are composited in post-production.\n"
            )
            if product_name:
                # Offer mode: full-bleed, person with phone/device on right, light upper-left
                image_prompt = (
                    _no_logo_rule +
                    "SUBJECT: A confident, happy person actively using a smartphone or mobile device — "
                    "holding it to their ear, smiling at the screen, or gesturing with it naturally. "
                    "The device must be clearly and prominently visible. Professional, aspirational. "
                    "Swiss lifestyle or business context.\n"
                    "COMPOSITION: Full-bleed portrait or landscape frame. Person positioned on the "
                    "RIGHT HALF of the frame, facing slightly left or toward camera. "
                    "The UPPER-LEFT area of the frame must be naturally light, airy, and uncluttered "
                    "(bright sky, soft blurred background, or open space) — this area will receive "
                    "the headline and price overlay in post-production. "
                    "LIGHTING: Bright, clean, natural daylight or soft studio light. Avoid dark or "
                    "heavily shadowed backgrounds in the upper-left quadrant. "
                    "Do NOT render any text, numbers, logos, or brand symbols in the image.\n\n"
                ) + image_prompt
            else:
                # Lifestyle mode: full-bleed, left third clear for white text overlay
                image_prompt = (
                    _no_logo_rule +
                    "COMPOSITION RULE: The subject, action, and visual interest must be "
                    "concentrated in the CENTRE to RIGHT two-thirds of the frame. "
                    "The LEFT THIRD of the image should be relatively uncluttered and "
                    "slightly darker in tone — this area will receive large white text overlay. "
                    "Swiss landscape, Swiss urban, or Swiss lifestyle context. "
                    "Premium Swiss telecommunications advertising photography style.\n\n"
                ) + image_prompt

        # Barclays Wimbledon composition override
        if _is_wimbledon:
            image_prompt = (
                "SUBJECT: A young tennis player and an experienced coach or mentor — "
                "sharing a meaningful, human moment of connection and progress. "
                "Neither person wears business attire. Tennis clothing, natural sporting context.\n"
                "SETTING: Outdoors on or near a grass tennis court at Wimbledon — "
                "lush green grass, white court lines, English summer sky. "
                "No indoor courts, no office buildings, no corporate environments.\n"
                "LIGHTING: English summer — golden hour warmth, soft morning mist, or bright overcast. "
                "Natural, warm, aspirational.\n"
                "COMPOSITION: Subjects occupy the RIGHT TWO-THIRDS of the frame. "
                "The LEFT THIRD is open — grass, sky, or soft bokeh — for white text overlay in post-production.\n"
                "MOOD: Aspiration, progress, human connection, shared achievement.\n"
                "FORBIDDEN: Business suits, office buildings, bank branches, financial products, "
                "app screens, logos, text, or brand marks anywhere in the image.\n\n"
            ) + image_prompt

        # Haleon-specific composition rule
        if brand.lower() == "haleon":
            _haleon_subject = (
                "SUBJECT: A real person in a relatable everyday health moment — "
                "using, holding, or just having used the product. Warm, human, credible. "
                "No lab coats, no clinical settings, no dramatic illness portrayal. "
                "The product pack/tube/bottle must be clearly visible and in focus.\n"
                "COMPOSITION: The subject and product must occupy the RIGHT TWO-THIRDS of the frame. "
                "The LEFT THIRD must be clean, bright, and uncluttered — white wall, soft bokeh, "
                "or open daylight — this area receives the headline overlay in post-production.\n"
                "PALETTE: White-dominant background with natural Haleon green accents (plants, packaging, "
                "fabric details). Warm, natural daylight or soft studio light. No dark or moody backgrounds.\n"
                "CRITICAL: No text, logos, brand marks, or pricing anywhere in the image. "
                "No overly clinical or pharmaceutical imagery.\n\n"
            )
            image_prompt = _haleon_subject + image_prompt

        contents.append(image_prompt)

        import time as _time
        _resp = None
        for _attempt in range(3):
            try:
                _resp = _genai_client().models.generate_content(
                    model    = settings.gemini_model_image,
                    contents = contents,
                    config   = gtypes.GenerateContentConfig(
                        response_modalities = ["IMAGE", "TEXT"],
                        image_config        = gtypes.ImageConfig(aspect_ratio="16:9"),
                    ),
                )
                break
            except Exception as _img_exc:
                _emsg = str(_img_exc)
                if "429" in _emsg or "RESOURCE_EXHAUSTED" in _emsg:
                    _delay = 2 ** (_attempt + 2)  # 4s, 8s, 16s
                    logger.warning("kv_image_rate_limited", brand=brand, attempt=_attempt + 1, retry_in=_delay)
                    if _attempt < 2:
                        _time.sleep(_delay)
                        continue
                raise
        resp = _resp

        raw_bytes = None
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None) is not None:
                raw_bytes = part.inline_data.data
                break

        if raw_bytes:
            import base64
            if _is_wimbledon:
                # Use the Barclays-specific overlay directly so is_wimbledon=True is
                # guaranteed. _apply_brand_overlay detects Wimbledon from the logo URI
                # or headline text — both can miss when the headline is copy-only
                # ("Greatness is never a solo sport."). Calling apply_overlay() directly
                # bypasses that fragile heuristic.
                from pathlib import Path as _PB
                _bfont_dir = _PB(__file__).resolve().parent.parent / "bucket" / "brands" / "Barclays"
                _bfp = _barclays.resolve_font_path(_bfont_dir)
                _logo_uri = _ref_logo or (logos[0] if logos else "")
                logger.info("kv_overlay", brand=brand, wimbledon=True, logo_uri=str(_logo_uri)[:60])
                overlaid = _barclays.apply_overlay(
                    raw_bytes,
                    headline,
                    logo_uri    = _logo_uri or "",
                    is_wimbledon= True,
                    font_path   = _bfp,
                    copy_subline= "",
                    copy_cta    = "",
                )
            else:
                from app.runner import _apply_brand_overlay
                logger.info("kv_overlay", brand=brand, product_name=product_name, market=market,
                            offer_mode=bool(product_name))
                overlaid = _apply_brand_overlay(raw_bytes, brand, headline, products[:1], product_name, market)
            image_b64 = base64.b64encode(overlaid).decode("utf-8")
    except Exception as e:
        logger.warning("standalone_kv_failed", brand=brand, error=str(e))

    return {"agent": "kv", "brand": brand, "headline": headline, "image_b64": image_b64}
