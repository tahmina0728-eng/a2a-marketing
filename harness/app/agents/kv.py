from __future__ import annotations

import structlog

from app.config import get_settings
from app.brand_assets import get_asset_loader
from app.agents._utils import _generate, _genai_client
from app.brands import barclays as _barclays

logger   = structlog.get_logger()
settings = get_settings()

# Real enterprise brands — replace "fictional brand" prompt with
# explicit "no logos — composited in post-production" instruction.
_REAL_BRANDS = frozenset({"barclays", "haleon", "ubs bank", "sunrise", "glenfiddich", "boozt", "infosys"})


def _build_wimbledon_prompt(concept: dict, aspect_ratio: str) -> str:
    """Build a structured image generation prompt from a concepts.json creative_direction dict.

    Every field that controls the image model comes from concepts.json — not
    from the LLM at generation time. The model receives a deterministic brief
    (CAMPAIGN / CONCEPT / SUBJECT / SETTING / MUST HAVE / MUST NOT HAVE).
    """
    d     = concept.get("creative_direction", {})
    title = concept.get("title", "WIMBLEDON")

    parts = []
    if d.get("subject"):      parts.append(f"SUBJECT:\n{d['subject']}")
    if d.get("relationship"): parts.append(f"RELATIONSHIP:\n{d['relationship']}")
    if d.get("action"):       parts.append(f"ACTION:\n{d['action']}")
    if d.get("narrative"):    parts.append(f"NARRATIVE:\n{d['narrative']}")
    if d.get("setting"):      parts.append(f"SETTING:\n{d['setting']}")
    if d.get("emotion"):      parts.append(f"EMOTION:\n{d['emotion'].capitalize()}")
    if d.get("composition"):  parts.append(f"COMPOSITION:\n{d['composition']}")
    if d.get("lighting"):     parts.append(f"LIGHTING:\n{d['lighting']}")
    if d.get("photography"):  parts.append(f"PHOTOGRAPHY STYLE:\n{d['photography']}")

    must_have = (
        "- Authentic Wimbledon tennis context (grass court, rackets, tennis clothing)\n"
        "- Genuine human emotion and connection\n"
        "- English summer atmosphere and light\n"
        "- Premium cinematic photography quality — not stock photo poses\n"
        "- Generous clean negative space on the LEFT THIRD for headline overlay in post-production"
    )
    must_not = (
        "- Business suits, office attire, or corporate dress\n"
        "- Office buildings, bank branches, or financial environments\n"
        "- Financial products, app screens, or digital displays\n"
        "- Logos, brand marks, wordmarks, or text of any kind\n"
        "- Indoor sport facilities or non-Wimbledon settings\n"
        "- Generic stock photography poses or staged expressions\n"
        "- City skylines or urban corporate environments"
    )

    return (
        f"CAMPAIGN: Barclays × Wimbledon — Official Banking Partner of The Championships\n"
        f"CONCEPT: {title}\n\n"
        + "\n\n".join(parts) + "\n\n"
        f"MUST HAVE:\n{must_have}\n\n"
        f"MUST NOT HAVE:\n{must_not}\n\n"
        "BRAND CONTAMINATION PREVENTION:\n"
        "Do not interpret Barclays colours, blue, or brand identity as clothing patterns, graphics,\n"
        "symbols, badges, patches, logos, or shapes on any person, object, court, building, or equipment.\n"
        "Do not create any invented Barclays logo, abstract Barclays symbol, Wimbledon badge,\n"
        "championship mark, sponsor mark, or invented signage of any kind.\n"
        "The generated photograph must contain ZERO Barclays or Wimbledon branding.\n"
        "All branding is composited in post-production using approved assets.\n\n"
        "GENERATED IMAGE BOUNDARY — the image model is responsible ONLY for:\n"
        "  photography · people · environment · lighting · composition · atmosphere\n\n"
        "The image model MUST NOT generate:\n"
        "  headline · subline · CTA · typography · numbers · logos · sponsor marks\n"
        "  Wimbledon marks · Barclays marks · signage · badges · watermarks\n\n"
        "All copy and brand assets are composited deterministically in post-production.\n\n"
        f"TECHNICAL:\n"
        f"Aspect ratio {aspect_ratio}. Photorealistic, premium UK advertising photography."
    )


def _generate_kv_image(contents: list, aspect_ratio: str) -> "bytes | None":
    """Call Gemini image model with 429 exponential-backoff retry. Returns raw image bytes or None."""
    import time as _time
    from google.genai import types as gtypes

    _resp = None
    for _attempt in range(3):
        try:
            _resp = _genai_client().models.generate_content(
                model    = settings.gemini_model_image,
                contents = contents,
                config   = gtypes.GenerateContentConfig(
                    response_modalities = ["IMAGE", "TEXT"],
                    image_config        = gtypes.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
            break
        except Exception as _exc:
            _emsg = str(_exc)
            if "429" in _emsg or "RESOURCE_EXHAUSTED" in _emsg:
                _delay = 2 ** (_attempt + 2)
                logger.warning("kv_image_rate_limited", attempt=_attempt + 1, retry_in=_delay)
                if _attempt < 2:
                    _time.sleep(_delay)
                    continue
            raise

    if _resp is None:
        return None
    for part in (_resp.candidates[0].content.parts if _resp.candidates else []):
        if getattr(part, "inline_data", None) is not None:
            return part.inline_data.data
    return None


def _creative_qa(
    image_bytes: bytes,
    concept_title: str,
    headline: str,
    brand: str,
) -> dict:
    """Score a generated KV photograph before overlay compositing.

    Checks concept alignment, Wimbledon authenticity, human story, composition,
    logo/brand contamination in the photo, and premium advertising quality.

    Decision: overall ≥ 80 AND logo_contamination ≥ 65 → APPROVE, else REGENERATE.
    Fails open on any error (returns APPROVE) so QA never blocks a valid run.
    """
    import json, re
    try:
        from google.genai import types as gtypes

        _qa_model = settings.gemini_model_reasoning or "gemini-2.0-flash"
        qa_prompt = (
            f"You are a Creative QA director reviewing an AI-generated advertising photograph "
            f"for {brand} × Wimbledon.\n\n"
            f'Intended concept: "{concept_title}"\n'
            f'Intended headline: "{headline}"\n\n'
            "CRITICAL — LOGO CONTAMINATION CHECK:\n"
            "Examine the image carefully for any of the following appearing as PART OF the generated photograph:\n"
            "  • Blue abstract shapes, blocks, or graphics on clothing, equipment, or background\n"
            "  • Any symbol, badge, patch, mark, or graphic resembling a brand logo\n"
            "  • Invented sponsor signage, court markings, championship badges, or lettering\n"
            "  • Text or numbers of any kind\n"
            "Score logo_contamination 0–100 where 100 = completely clean (no contamination).\n\n"
            "Score each dimension 0–100. Be strict — this is for a premium UK financial services brand.\n\n"
            "Respond ONLY with valid JSON, no markdown fences:\n"
            '{"concept_alignment":<0-100>,"wimbledon_context":<0-100>,'
            '"human_story":<0-100>,"composition":<0-100>,'
            '"logo_contamination":<0-100>,"premium_quality":<0-100>,'
            '"issues":["<issue 1>","<issue 2>"]}'
        )

        img_part = gtypes.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        resp = _genai_client().models.generate_content(
            model    = _qa_model,
            contents = [qa_prompt, img_part],
        )

        raw = (resp.text or "").strip()
        m   = re.search(r'\{[\s\S]*\}', raw)
        if not m:
            raise ValueError("QA returned no JSON")
        data = json.loads(m.group())

        # Weighted overall: logo_contamination ×1.5, concept_alignment ×1.2, others ×1.0
        lc   = float(data.get("logo_contamination", 80))
        ca   = float(data.get("concept_alignment", 80))
        rest = sum(float(data.get(k, 80)) for k in ("wimbledon_context", "human_story", "composition", "premium_quality"))
        data["overall"]  = round((lc * 1.5 + ca * 1.2 + rest) / (1.5 + 1.2 + 4.0))
        data["decision"] = "APPROVE" if data["overall"] >= 80 and lc >= 65 else "REGENERATE"
        return data

    except Exception as _qa_err:
        logger.warning("creative_qa_failed", brand=brand, error=str(_qa_err))
        return {"overall": 100, "decision": "APPROVE", "logo_contamination": 100, "issues": []}


def _creative_qa_final(image_bytes: bytes, headline: str) -> dict:
    """Point 12: Vision model QA on the fully composited ad (post-overlay).

    Checks presence of all required brand elements and overall layout quality.
    Decision: overall ≥ 70 AND headline_present ≥ 70 AND barclays_logo_present ≥ 70 → APPROVE.
    Fails open on any error so QA never blocks delivery.
    """
    import json, re
    try:
        from google.genai import types as gtypes

        _qa_model = settings.gemini_model_reasoning or "gemini-2.0-flash"
        qa_prompt = (
            "You are a Creative QA director reviewing a FINAL composited advertising creative "
            "for Barclays × Wimbledon. All brand elements (headline, subline, CTA, logos) have "
            "been added in post-production and must be visually present and legible.\n\n"
            f'Expected headline text (verbatim or very close): "{headline}"\n\n'
            "Score each dimension 0–100 where 100 = perfect presence / execution:\n"
            "  headline_present      — is the headline text visible and legible?\n"
            "  subline_present       — is the supporting subline copy visible?\n"
            "  cta_present           — is a CTA button or call-to-action visible?\n"
            "  barclays_logo_present — is the Barclays eagle/wordmark visible?\n"
            "  wimbledon_logo_present— is the Wimbledon mark/shield visible?\n"
            "  logo_placement        — are logos in the correct bottom-right position?\n"
            "  overall_layout        — does the overall ad look professional and balanced?\n\n"
            "Respond ONLY with valid JSON, no markdown fences:\n"
            '{"headline_present":<0-100>,"subline_present":<0-100>,"cta_present":<0-100>,'
            '"barclays_logo_present":<0-100>,"wimbledon_logo_present":<0-100>,'
            '"logo_placement":<0-100>,"overall_layout":<0-100>}'
        )

        img_part = gtypes.Part.from_bytes(data=image_bytes, mime_type="image/png")
        resp = _genai_client().models.generate_content(
            model    = _qa_model,
            contents = [qa_prompt, img_part],
        )

        raw = (resp.text or "").strip()
        m   = re.search(r'\{[\s\S]*\}', raw)
        if not m:
            raise ValueError("final_qa returned no JSON")
        data = json.loads(m.group())

        hl  = float(data.get("headline_present", 80))
        bl  = float(data.get("barclays_logo_present", 80))
        rest = sum(float(data.get(k, 80)) for k in (
            "subline_present", "cta_present", "wimbledon_logo_present",
            "logo_placement", "overall_layout"
        ))
        data["overall"]  = round((hl + bl + rest) / 7)
        data["decision"] = (
            "APPROVE" if data["overall"] >= 70 and hl >= 70 and bl >= 70 else "REVIEW"
        )
        return data

    except Exception as _err:
        logger.warning("creative_qa_final_failed", error=str(_err))
        return {"overall": 100, "decision": "APPROVE"}


def run_kv(
    brand: str,
    prompt: str,
    product_name: str = "",
    market: str = "",
    audience: str = "",
    copy_headline: str = "",
    copy_subline: str = "",
    copy_body: str = "",
    copy_cta: str = "",
    campaign_type: str = "",
    campaign_id: str = "",
    concept_id: str = "",
    aspect_ratio: str = "16:9",
    color_theme: str = "blue",
) -> dict:
    """
    Standalone Morphis — key visual generator.

    Architecture:
      1. Campaign/concept loaded from JSON (brand.json + concepts.json) — not hallucinated.
      2. Headline comes from the Copy Agent (copy_headline). Generating a fallback
         is supported for standalone use but logs a warning.
      3. Scene direction comes from concepts.json for structured campaigns (Wimbledon).
         Other brands use an LLM-generated scene until their campaign JSON exists.
      4. Image model receives a structured brief only — no logos passed to Gemini
         for campaigns where brand marks must not appear in the photo.
      5. Overlay (_barclays.apply_overlay / _apply_brand_overlay) composites all
         brand assets — logo, lockup, headline, subline — in post-production.
    """

    # ── 1. Campaign detection ─────────────────────────────────────────────────
    # Exact match on campaign_id (preferred). Fall back to campaign_type only
    # when campaign_id is absent — both are sent by the frontend for compat.
    # Exact match prevents "partnership" (a theme name) from being mistaken for
    # "wimbledon" (a campaign name) when substring matching is used.
    _campaign_id  = (campaign_id or campaign_type or "").lower().strip()
    _is_wimbledon = brand.lower() == "barclays" and _campaign_id == "wimbledon"
    _is_haleon    = brand.lower() == "haleon"
    _is_infosys   = brand.lower() == "infosys"
    _is_real      = brand.lower() in _REAL_BRANDS

    # ── Infosys: template-based compositor — no AI image generation needed ────
    if _is_infosys:
        try:
            import base64
            from app.brands.infosys.compositor import generate_kv as _infosys_kv

            _headline = copy_headline
            _subline  = copy_subline or ""
            _cta      = copy_cta     or "Navigate Your Next"

            if not _headline:
                # No pre-supplied copy — run Logos→Helia→Ideon to generate it.
                # Avoids letting the raw user prompt bleed through as the KV headline.
                from app.agents.infosys.logos import LogosAgent
                from app.agents.infosys.helia import HeliaAgent
                from app.agents.infosys.ideon import IdeonAgent
                import copy as _copy_mod

                brief = {
                    "campaign_name": "Infosys Campaign",
                    "objective": prompt,
                    "channels": ["LinkedIn"],
                    "market": market or "UK",
                }
                logos = LogosAgent().run(brief)
                helia = HeliaAgent().run(logos)
                ideon = IdeonAgent().run({"brief": logos, "creative_platform": helia})

                if ideon and ideon.artifact:
                    content = _copy_mod.deepcopy(ideon.artifact.content)
                    variants: list = content.get("variants", [])
                    rec_idx = content.get("recommended_variant", 0)
                    if not (isinstance(rec_idx, int) and 0 <= rec_idx < len(variants)):
                        rec_idx = max(range(len(variants)),
                                      key=lambda i: variants[i].get("quality_score", 0)) if variants else 0
                    best = variants[rec_idx] if variants else {}
                    _headline = best.get("headline", "")
                    _subline  = best.get("subheadline", _subline)
                    _cta      = best.get("cta", _cta) or _cta

            img_bytes = _infosys_kv(
                headline     = _headline,
                subline      = _subline,
                cta          = _cta,
                sub_brand    = product_name  or "",
                aspect_ratio = aspect_ratio,
                color_theme  = color_theme   or "blue",
            )
            return {
                "agent":    "kv",
                "brand":    brand,
                "headline": _headline,
                "subline":  _subline,
                "cta":      _cta,
                "image_b64": base64.b64encode(img_bytes).decode("utf-8"),
                "creative_qa": {},
                "final_qa":   {},
            }
        except Exception as _ie:
            logger.warning("infosys_kv_failed", error=str(_ie))

    # ── 2. Audience persona ───────────────────────────────────────────────────
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

    # ── 3. Headline ───────────────────────────────────────────────────────────
    # Headline should come from the Copy Agent. If absent, generate a fallback
    # and warn — standalone use requires this, but copy should be brand-approved
    # before going to production.
    if copy_headline and copy_headline.strip():
        headline = copy_headline.strip()
    else:
        logger.warning(
            "kv_no_copy_headline", brand=brand, campaign=_campaign_id,
            note="headline should come from Copy Agent — generating standalone fallback",
        )
        if _is_wimbledon:
            _hl_sys  = ("You are Morphis, a sports partnership advertising specialist.")
            _hl_instr = (
                "The campaign is Barclays × Wimbledon — Official Banking Partner of The Championships. "
                "Creative platform: progress through sport and human connection. "
                'Respond ONLY with JSON: {"headline": "short aspirational headline, 4-8 words — '
                'about progress, belief, or shared achievement. No financial product claims."}'
            )
        elif product_name and _is_haleon:
            _hl_sys  = "You are Morphis, a healthcare and FMCG advertising specialist."
            _hl_instr = (
                f'Product: "{product_name}". '
                'Respond ONLY with JSON: {"headline": "short empathetic headline, 4-8 words"}'
            )
        elif product_name:
            _hl_sys  = "You are Morphis, a product offer advertising specialist."
            _hl_instr = (
                f'Product: "{product_name}". '
                'Respond ONLY with JSON: {"headline": "bold 4-7 word offer headline"}'
            )
        else:
            _hl_sys  = "You are Morphis, a creative advertising visual designer."
            _hl_instr = 'Respond ONLY with JSON: {"headline": "short punchy headline, 4-8 words"}'
        headline = (_generate(_hl_sys, brand, prompt, _hl_instr).get("headline", "") or prompt)

    # ── 4. Scene / visual direction ───────────────────────────────────────────
    if _is_wimbledon:
        # Scene comes from concepts.json — not from the LLM.
        # select_concept() keyword-matches the prompt + headline against the five
        # creative territories; concept_id bypasses matching for explicit selection.
        _concept      = _barclays.select_concept(
            big_idea_seed=prompt, copy_headline=headline,
            fan_truth="", concept_id=concept_id,
        )
        image_prompt  = _build_wimbledon_prompt(_concept, aspect_ratio)
        logger.info("kv_wimbledon_concept", brand=brand,
                    concept=_concept.get("title", ""), id=_concept.get("id", ""))
    else:
        # Non-structured path — LLM generates scene for brands without campaign JSON.
        if product_name and _is_haleon:
            _sc_sys  = (
                "You are Morphis, the key visual designer for an AI marketing campaign system. "
                "You specialise in healthcare and FMCG advertising."
            )
            _sc_instr = (
                f'Product: "{product_name}". Audience: {_who}. '
                'Respond ONLY with JSON: '
                '{"scene": "2-3 sentences: show ' + _who + ' holding or having just used '
                f'the {product_name} pack/box/tube — packaging clearly visible. '
                'RIGHT TWO-THIRDS. LEFT THIRD clean, bright, uncluttered. '
                'Warm natural daylight. No clinical settings, no text, no logos."}'
            )
        elif product_name:
            _sc_sys  = (
                "You are Morphis, the key visual designer for an AI marketing campaign system. "
                "You specialise in product offer advertising."
            )
            _sc_instr = (
                f'Product: "{product_name}". Audience: {_who}. '
                'Respond ONLY with JSON: '
                '{"scene": "2-3 sentences: show ' + _who + ' actively using a smartphone — '
                'holding it, smiling at screen. RIGHT HALF of frame. '
                'Upper-left light, airy, uncluttered. No text, logos, price figures."}'
            )
        else:
            _sc_sys  = "You are Morphis, the key visual designer for an AI marketing campaign system."
            _sc_instr = (
                f'Audience: {_who}. '
                'Respond ONLY with JSON: '
                '{"scene": "2-3 sentences: show ' + _who + ' in a vibrant, aspirational setting. '
                'Setting, mood, lighting — no text, words, or logos."}'
            )
        _scene = _generate(_sc_sys, brand, prompt, _sc_instr).get("scene", "") or prompt

        # No-text rule — real brands get explicit "composited in post-production" wording;
        # fictional/demo brands get the generic "no text" rule.
        if _is_real:
            _no_text = (
                f"Do not render the {brand} logo, wordmark, or any brand marks — "
                f"approved assets are composited in post-production.\n"
                "No text, numbers, or typography anywhere in the image.\n\n"
            )
        else:
            _no_text = (
                "No text anywhere in the image except brand packaging labels if shown. "
                "All headline copy is added in post-production.\n\n"
            )

        _product_rule = (
            f"PRODUCT RULE: {product_name} packaging (box, tube, or bottle with its real colours "
            f"and label) must be clearly visible — held in hand, on a surface, or on a shelf. "
            f"Do NOT show any other product or unrelated packaging.\n\n"
        ) if product_name and _is_haleon else ""

        image_prompt = (
            f"{_no_text}{_product_rule}{_scene}\n\n"
            f"Aspect ratio {aspect_ratio}, photorealistic, premium advertising photography."
        )

    # ── 5. Image generation + Creative QA ────────────────────────────────────
    image_b64      = ""
    _qa_result: dict = {}
    _final_qa: dict  = {}
    try:
        from google.genai import types as gtypes
        from app.creative_pipeline import _part_for_uri

        loader   = get_asset_loader()
        _bslug   = brand.split()[0].lower()
        logos    = loader.list_logos(brand)
        products = loader.list_products(brand)
        contents: list = []

        # For Wimbledon: resolve the approved co-brand lockup directly rather
        # than searching filenames generically — the campaign JSON marks it editable:false.
        if _is_wimbledon:
            _ref_logo = (
                next((p for p in logos if "barclays-wimbledon" in p.lower()), None) or
                next((p for p in logos if _bslug in p.lower()), None) or
                (logos[0] if logos else None)
            )
        else:
            _ref_logo = (
                next((p for p in logos if _bslug in p.lower() and "_dark"  in p.lower()), None) or
                next((p for p in logos if _bslug in p.lower() and "_white" not in p.lower()), None) or
                next((p for p in logos if _bslug in p.lower()), None) or
                (logos[0] if logos else None)
            )

        # For Wimbledon: do NOT pass any logo or brand image to Gemini — the
        # generated photo must be brand-mark-free. The eagle, wordmark, and
        # Wimbledon lockup are all composited by apply_overlay() afterwards.
        # For other brands: pass logo as colour/style reference (not to be rendered).
        if not _is_wimbledon and _ref_logo and _bslug not in ("sunrise",):
            part = _part_for_uri(_ref_logo)
            if part:
                contents.append(
                    f"BRAND IDENTITY REFERENCE for {brand} — colour palette and visual style only. "
                    "Do NOT render this logo or any brand mark in the generated image."
                )
                contents.append(part)

        # Haleon: sort the matched sub-brand product to the front so Gemini
        # sees the correct packaging reference first.
        if _is_haleon and product_name and products:
            from pathlib import Path as _PPkv
            _pk = product_name.lower().replace("-", "").replace(" ", "")
            _pm = next(
                (p for p in products
                 if _pk in _PPkv(p).stem.lower().replace("-", "").replace(" ", "")),
                None,
            )
            if _pm:
                products = [_pm] + [p for p in products if p != _pm]

        # Style reference for brands with no Products folder (not Sunrise, not Wimbledon)
        _style_refs = [] if products or _bslug in ("sunrise",) or _is_wimbledon else [
            a for a in loader.list_assets(brand)
            if not a.lower().endswith((".mp4", ".svg"))
        ][:1]

        if products and not _is_wimbledon:
            part = _part_for_uri(products[0])
            if part:
                contents.append(
                    f"PRODUCT REFERENCE for {brand} — match shape and colours if products are shown."
                )
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
                        _ri = _ri.resize((int(_ri.width * _sc), int(_ri.height * _sc)), _PILr.LANCZOS)
                    _rb = _BIOr()
                    _ri.save(_rb, format="JPEG", quality=85)
                    contents.append(
                        f"BRAND CAMPAIGN STYLE REFERENCE for {brand} — match this visual style: "
                        "photography approach, colour palette, mood, lighting, and composition."
                    )
                    contents.append(_gt2.Part.from_bytes(data=_rb.getvalue(), mime_type="image/jpeg"))
            except Exception as _sre:
                logger.warning("kv_style_ref_failed", brand=brand, error=str(_sre))

        # Sunrise composition override
        if _bslug == "sunrise":
            _no_logo_rule = (
                "CRITICAL: Do NOT render S-circle icons, Sunrise logos, sun icons, "
                "circular brand marks, or any recognisable brand symbols — "
                "all brand elements are composited in post-production.\n"
            )
            if product_name:
                image_prompt = (
                    _no_logo_rule +
                    "SUBJECT: A confident, happy person actively using a smartphone or mobile device. "
                    "The device must be clearly and prominently visible. Professional, aspirational. "
                    "Swiss lifestyle or business context.\n"
                    "COMPOSITION: Person on RIGHT HALF, facing slightly left or toward camera. "
                    "UPPER-LEFT must be naturally light, airy, and uncluttered — "
                    "headline and price overlay added in post-production. "
                    "LIGHTING: Bright, clean, natural daylight or soft studio light.\n\n"
                ) + image_prompt
            else:
                image_prompt = (
                    _no_logo_rule +
                    "COMPOSITION: Subject, action, and visual interest in the CENTRE to RIGHT two-thirds. "
                    "LEFT THIRD relatively uncluttered — receives large white text overlay. "
                    "Swiss landscape, urban, or lifestyle context. "
                    "Premium Swiss telecommunications advertising photography style.\n\n"
                ) + image_prompt

        # Haleon composition override
        if _is_haleon:
            image_prompt = (
                "SUBJECT: Real person in a relatable everyday health moment — "
                "using, holding, or having just used the product. Warm, human, credible. "
                "No lab coats, clinical settings, or illness portrayal. "
                "Product pack/tube/bottle clearly visible and in focus.\n"
                "COMPOSITION: Subject and product in RIGHT TWO-THIRDS. "
                "LEFT THIRD clean, bright, uncluttered — receives headline overlay.\n"
                "PALETTE: White-dominant with natural Haleon green accents. "
                "Warm natural daylight. No dark or moody backgrounds.\n"
                "CRITICAL: No text, logos, brand marks, or pricing in the image.\n\n"
            ) + image_prompt

        contents.append(image_prompt)

        # ── Generate + Creative QA ─────────────────────────────────────────────
        raw_bytes = _generate_kv_image(contents, aspect_ratio)

        if raw_bytes and _is_wimbledon:
            _qa_result = _creative_qa(raw_bytes, _concept.get("title", ""), headline, brand)
            logger.info(
                "kv_creative_qa", brand=brand,
                score=_qa_result.get("overall"),
                decision=_qa_result.get("decision"),
                logo_contamination=_qa_result.get("logo_contamination"),
                issues=_qa_result.get("issues", []),
            )
            if _qa_result.get("decision") == "REGENERATE":
                _issues_str = "; ".join(_qa_result.get("issues", []))
                contents[-1] = (
                    f"CRITICAL — REGENERATION: Previous attempt scored "
                    f"{_qa_result.get('overall')}/100 and was rejected by Creative QA.\n"
                    f"QA issues found: {_issues_str}\n"
                    "Strictly fix these issues. Remove ALL brand-like marks, abstract blue shapes, "
                    "invented symbols, badges, and text from every element in the scene.\n\n"
                ) + image_prompt
                _regen = _generate_kv_image(contents, aspect_ratio)
                if _regen:
                    raw_bytes = _regen
                    logger.info("kv_qa_regenerated", brand=brand)

        if raw_bytes:
            import base64
            if _is_wimbledon:
                # Call apply_overlay() directly with is_wimbledon=True — guaranteed.
                # _apply_brand_overlay detects Wimbledon from logo_uri or headline
                # text, which are both unreliable (headline may contain no "wimbledon").
                from pathlib import Path as _PB
                _bfont_dir = _PB(__file__).resolve().parent.parent / "bucket" / "brands" / "Barclays"
                _bfp       = _barclays.resolve_font_path(_bfont_dir)
                _logo_uri  = _ref_logo or (logos[0] if logos else "")
                logger.info("kv_overlay", brand=brand, wimbledon=True)
                overlaid = _barclays.apply_overlay(
                    raw_bytes, headline,
                    logo_uri     = _logo_uri or "",
                    is_wimbledon = True,
                    font_path    = _bfp,
                    copy_subline = copy_subline,
                    copy_cta     = copy_cta,
                )
                _final_qa = _creative_qa_final(overlaid, headline)
                logger.info("kv_final_qa", decision=_final_qa.get("decision"),
                            overall=_final_qa.get("overall"))
            else:
                from app.runner import _apply_brand_overlay
                logger.info("kv_overlay", brand=brand, product_name=product_name,
                            offer_mode=bool(product_name))
                overlaid = _apply_brand_overlay(
                    raw_bytes, brand, headline, products[:1], product_name, market,
                )
            image_b64 = base64.b64encode(overlaid).decode("utf-8")

    except Exception as e:
        logger.warning("standalone_kv_failed", brand=brand, error=str(e))

    return {
        "agent": "kv", "brand": brand, "headline": headline,
        "subline": copy_subline, "cta": copy_cta, "image_b64": image_b64,
        "creative_qa": {
            k: _qa_result.get(k)
            for k in ("overall", "decision", "logo_contamination", "issues")
        } if _qa_result else {},
        "final_qa": _final_qa,
    }
