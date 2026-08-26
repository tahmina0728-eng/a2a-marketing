from __future__ import annotations
import uuid

import structlog

from app.config import get_settings
from app.brand_assets import get_asset_loader
from app.agents._utils import _generate, _genai_client

logger   = structlog.get_logger()
settings = get_settings()


def _build_branded_start_frame(brand: str):
    """
    Build a real 16:9 starting frame with the brand's logo actually stamped on it
    (same white-pill, top-right treatment _apply_brand_overlay uses for KV images),
    for Veo's image-to-video mode. Returns a google.genai.types.Image, or None if
    there's no usable background asset or logo for this brand.
    """
    try:
        from io import BytesIO
        from PIL import Image as PILImage, ImageDraw
        from google.genai import types as gtypes
        from app.creative_pipeline import _load_bytes

        loader = get_asset_loader()

        # ── Background: first campaign asset, resized to 1280×720 ────────────
        assets = loader.list_assets(brand)
        if not assets:
            assets = loader.list_products(brand)
        if not assets:
            return None

        asset_bytes = _load_bytes(assets[0])
        if not asset_bytes:
            return None

        target_w, target_h = 1280, 720
        bg = PILImage.open(BytesIO(asset_bytes)).convert("RGB")
        bg = bg.resize((target_w, target_h), PILImage.LANCZOS)

        # ── Logo: white pill overlay, top-right (matches _apply_brand_overlay) ─
        logos = loader.list_logos(brand)
        if logos:
            import os as _os_reel
            _bslug = brand.split()[0].lower()
            if _bslug == "infosys":
                # All Infosys logos share the same brand directory, so path-substring
                # matching on "infosys" hits every file (Aster_DB, Cobalt_DB, …).
                # Match by filename stem to pin the master-brand tagline logo.
                logo_uri = (
                    next((p for p in logos if "infosys-tagline_db" in _os_reel.path.basename(p).lower()), None) or
                    next((p for p in logos if "infosys-tagline" in _os_reel.path.basename(p).lower()), None) or
                    next((p for p in logos if _os_reel.path.basename(p).lower().startswith("infosys")), None) or
                    logos[0]
                )
            else:
                logo_uri = (
                    next((p for p in logos if _bslug in p.lower() and "_dark" in p.lower()), None) or
                    next((p for p in logos if _bslug in p.lower()), None) or
                    logos[0]
                )
            logo_bytes = _load_bytes(logo_uri)
            if logo_bytes:
                logo = PILImage.open(BytesIO(logo_bytes)).convert("RGBA")
                max_lw = int(target_w * 0.20)
                max_lh = int(target_h * 0.12)
                sc = min(max_lw / max(1, logo.width), max_lh / max(1, logo.height), 1.0)
                lw, lh = max(16, int(logo.width * sc)), max(16, int(logo.height * sc))
                logo = logo.resize((lw, lh), PILImage.LANCZOS)

                pad = 12
                pill_w, pill_h = lw + pad * 2, lh + pad * 2
                margin = 24
                pill_x = target_w - pill_w - margin
                pill_y = margin

                pill = PILImage.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(pill)
                draw.rounded_rectangle([0, 0, pill_w - 1, pill_h - 1], radius=pill_h // 2,
                                       fill=(255, 255, 255, 230))
                pill.alpha_composite(logo, (pad, pad))

                bg_rgba = bg.convert("RGBA")
                bg_rgba.alpha_composite(pill, (pill_x, pill_y))
                bg = bg_rgba.convert("RGB")

        buf = BytesIO()
        bg.save(buf, format="JPEG", quality=88)
        return gtypes.Image(image_bytes=buf.getvalue(), mime_type="image/jpeg")
    except Exception as e:
        logger.warning("standalone_reel_start_frame_failed", brand=brand, error=str(e))
        return None


def _build_branded_end_frame(brand: str):
    """
    Build a clean 16:9 logo end-card — centered logo on a plain dark backdrop, the
    classic "ad closes on the brand" card. Passed as Veo's last_frame, which the SDK
    docs say is only supported alongside an image-to-video start frame (we have one).
    Returns a google.genai.types.Image, or None if there's no logo for this brand.
    """
    try:
        from io import BytesIO
        from PIL import Image as PILImage
        from google.genai import types as gtypes
        from app.creative_pipeline import _load_bytes

        loader = get_asset_loader()
        logos  = loader.list_logos(brand)
        if not logos:
            return None
        # Prefer a whiteBG/plain variant — reads cleanly on a dark card.
        logo_uri = next((p for p in logos if "whitebg" in p.lower()), logos[0])
        logo_bytes = _load_bytes(logo_uri)
        if not logo_bytes:
            return None

        target_w, target_h = 1280, 720
        card = PILImage.new("RGBA", (target_w, target_h), (10, 10, 19, 255))  # var(--page-bg) dark

        logo = PILImage.open(BytesIO(logo_bytes)).convert("RGBA")
        max_lw, max_lh = int(target_w * 0.32), int(target_h * 0.32)
        sc = min(max_lw / max(1, logo.width), max_lh / max(1, logo.height), 1.0)
        lw, lh = max(32, int(logo.width * sc)), max(32, int(logo.height * sc))
        logo = logo.resize((lw, lh), PILImage.LANCZOS)
        card.alpha_composite(logo, ((target_w - lw) // 2, (target_h - lh) // 2))

        buf = BytesIO()
        card.convert("RGB").save(buf, format="JPEG", quality=90)
        return gtypes.Image(image_bytes=buf.getvalue(), mime_type="image/jpeg")
    except Exception as e:
        logger.warning("standalone_reel_end_frame_failed", brand=brand, error=str(e))
        return None


def run_reel(brand: str, prompt: str, campaign_type: str = "", copy_headline: str = "") -> dict:
    """
    Standalone Kinetik — now matches the full pipeline's approach exactly:
    1. One Gemini text call to extract campaign context (big_idea, product, season,
       audience, voiceover line) from the user's free-text prompt + brand guidelines.
    2. Brand-specific visual scene direction (same templates as generate_campaign_reel).
    3. A second Gemini call generates the rich 80-100 word cinematic video+audio prompt
       using the same template the full pipeline uses.
    4. Pure text-to-video Veo call — no experimental image= / last_frame parameters,
       which the full pipeline never uses and which kept causing silent empty results.
    """
    # ── Step 1: Extract rich campaign context from the user prompt ────────────
    ctx = _generate(
        "You are Kinetik, the campaign reel director for an AI marketing campaign system.",
        brand, prompt,
        'Respond ONLY with JSON, no markdown fences: '
        '{"big_idea": "one punchy campaign concept sentence", '
        '"product": "specific product/service name, or empty string for pure service brands like banks", '
        '"season": "seasonal or festive context, e.g. Christmas, Summer, or empty string", '
        '"audience": "target audience in 5-8 words", '
        '"voiceover": "warm confident voiceover line, max 12 words"}',
    )
    big_idea  = ctx.get("big_idea", "") or prompt
    product   = ctx.get("product", "")
    season    = ctx.get("season", "")
    audience  = ctx.get("audience", "general audience")
    # If the copy agent already produced a headline, use it as the voiceover/text overlay
    # so reel and KV share the same copy output (same as the pipeline path does).
    voiceover = copy_headline.strip() if copy_headline.strip() else (ctx.get("voiceover", "") or big_idea)
    _prod     = product or f"{brand} product"

    # ── Barclays / Wimbledon detection ───────────────────────────────────────
    _is_barclays  = brand.lower() == "barclays"
    _is_wimbledon = _is_barclays and "wimbledon" in (campaign_type + " " + prompt + " " + big_idea).lower()
    if _is_barclays:
        from app.brands import barclays as _barclays_brand  # noqa: PLC0415

    # ── Step 2: Brand + occasion-aware visual scene ──────────────────────────
    import random as _rnd
    _szn = season.lower() if season else ""
    _ol  = prompt.lower()

    _is_christmas  = any(x in _szn for x in ["christmas", "xmas", "festive", "advent"])
    _is_new_year   = any(x in _szn for x in ["new year", "nye"])
    _is_diwali     = any(x in _szn for x in ["diwali", "deepavali"])
    _is_valentine  = any(x in _szn for x in ["valentine", "valentines"])
    _is_easter     = "easter" in _szn
    _is_halloween  = "halloween" in _szn
    _is_summer     = any(x in _szn for x in ["summer"])
    _is_autumn     = any(x in _szn for x in ["autumn", "fall"])
    _is_winter     = "winter" in _szn and not _is_christmas
    _is_spring     = "spring" in _szn

    # Each brand has fully distinct scene descriptions per occasion.
    # random.choice() picks one of 2-3 variants so the same brief
    # never produces the same video twice.

    def _sunglow_scene(p: str) -> str:
        if _is_christmas:
            return _rnd.choice([
                f"Three diverse women (25-38) laughing and getting ready together for Christmas night, "
                f"doing each other's hair in front of a beautifully decorated Christmas tree covered in warm fairy lights. "
                f"Red and gold baubles everywhere, {p} products on the vanity, shiny hair catching the festive glow. "
                f"Magenta-pink and deep red colour palette, genuine sisterhood and festive joy.",
                f"A mother and teenage daughter doing their hair together on Christmas morning — "
                f"kitchen table covered in gift wrap, Christmas tree in background, fairy lights strung across the window. "
                f"The daughter's hair transforms in slow motion, {p} bottle centred on the table between them. "
                f"Warm golden Christmas kitchen light, red and gold palette, pure family warmth.",
            ])
        if _is_diwali:
            return _rnd.choice([
                f"Three South Asian women (20-45) in jewel-toned saris and salwars getting ready together for Diwali, "
                f"doing each other's hair surrounded by diyas and marigold garlands. "
                f"Warm golden diya light catches their hair mid-flip, {p} products gleaming on the dressing table. "
                f"Rich jewel-tone palette — deep magenta, gold and emerald — joyful and celebratory.",
                f"A South Asian grandmother, mother and daughter getting ready for Diwali puja — "
                f"three generations doing hair together, diyas flickering, rangoli visible on the floor behind them. "
                f"{p} bottle between them, hair FLYING in slow motion catching golden diya light. "
                f"Vibrant traditional outfits, warm amber and gold colour palette.",
            ])
        if _is_new_year:
            return _rnd.choice([
                f"Four women (22-35) getting glamorous together for New Year's Eve — sequined outfits, "
                f"champagne flutes on the vanity, golden confetti beginning to fall from the ceiling. "
                f"Hair FLYING in slow motion as they count down, {p} bottle centre-frame, golden and silver palette. "
                f"Pure NYE euphoria and sisterhood.",
                f"A woman doing a dramatic hair flip in a penthouse as fireworks explode outside the floor-to-ceiling windows "
                f"behind her — golden bursts of light catching every strand of her impossibly shiny hair. "
                f"{p} bottle on the window ledge, midnight skyline, Sunglow magenta-pink and gold palette.",
            ])
        if _is_valentine:
            return _rnd.choice([
                f"A woman styling her hair with {p} for a Valentine's date — roses and petals on the dressing table, "
                f"warm rose-gold candlelight catching her flowing locks. Slow-motion hair flip with soft pink bokeh "
                f"and red rose petals raining down. Intimate, romantic, Sunglow pink and rose-gold palette.",
                f"Two women (best friends) getting ready for Valentine's night out together — laughing, "
                f"doing each other's hair, {p} products and red roses on the vanity, pink champagne on the table. "
                f"Warm rose-toned lighting, pure joy and self-love energy.",
            ])
        if _is_easter:
            return (f"A woman doing a slow-motion hair flip outdoors in a spring garden full of blooming cherry blossoms — "
                    f"pastel pink petals drifting through her shiny flowing hair. {p} bottle in foreground catching sunlight. "
                    f"Fresh spring light, pastel pink and yellow palette, renewal and joy.")
        if _is_halloween:
            return (f"A woman with dramatically gorgeous styled hair at a Halloween party — "
                    f"deep purple and amber lighting, jack-o-lanterns glowing in the background, "
                    f"her hair catching the moody cinematic light beautifully. {p} bottle in foreground, "
                    f"deep magenta-purple palette, glamorous and slightly mysterious.")
        if _is_summer:
            return _rnd.choice([
                f"A woman doing a dramatic slow-motion hair flip on a sun-drenched beach, "
                f"golden hour light turning her shiny hair into a cascade of light. "
                f"Warm ocean in the background, {p} bottle half-buried in sand in the foreground. "
                f"Bright magenta-pink and sunshine yellow, pure summer energy.",
                f"Three women at an outdoor summer festival, laughing with hair flying in the warm breeze — "
                f"colourful festival lights behind them, {p} products on the picnic blanket. "
                f"Vibrant sunshine yellow and magenta palette, joyful summer sisterhood.",
            ])
        if _is_autumn:
            return (f"A woman walking through an autumn park doing a hair flip as golden and copper leaves swirl around her — "
                    f"amber afternoon light turning her shiny hair into a warm halo. {p} bottle on a wooden bench. "
                    f"Deep amber, rust and magenta palette, cosy autumn energy.")
        # Evergreen default — still pick from variants
        if any(x in p.lower() for x in ["serum", "oil", "scalp", "treat"]):
            return (f"Close-up slow-motion of a woman applying {p} drops onto her fingertips, "
                    f"running them through her hair as golden light particles trail behind. "
                    f"The {p} bottle gleams in warm studio light. Magenta-pink and sunshine yellow palette.")
        return _rnd.choice([
            f"A beautiful woman doing a slow-motion hair flip after washing with {p}, "
            f"her shiny hair cascading through golden light particles and warm bokeh. "
            f"The {p} bottle visible in foreground. Magenta-pink and sunshine yellow, dramatic rim lighting.",
            f"Two women (25-38) in a bright bathroom, one applying {p} as the other's hair transforms "
            f"into impossibly glossy flowing locks in slow motion. Warm studio light, brand palette.",
        ])

    def _rnorr_scene(p: str) -> str:
        if _is_christmas:
            return _rnd.choice([
                f"A multi-generational family of 5 (grandparents, parents, young child) gathered around "
                f"a beautifully set Christmas dinner table — the mother is serving the hero dish made with {p}, "
                f"faces glowing with joy. Decorated Christmas tree behind them, fairy lights strung overhead, "
                f"holly centrepiece, crackers and baubles on the table. {p} pack beside the serving bowl. "
                f"Deep forest green and gold palette, warm and genuinely festive.",
                f"A parent and two children (ages 5 and 8) cooking the Christmas feast together in a "
                f"festively decorated kitchen — the children standing on stools to help stir the pot with {p}. "
                f"Christmas cards on the mantle, fairy lights in the window, steam rising dramatically. "
                f"{p} box on the counter, deep green and red palette, real family magic.",
            ])
        if _is_diwali:
            return _rnd.choice([
                f"A South Asian family of 6 (multi-generational) gathered around a Diwali feast table — "
                f"diyas glowing everywhere, rangoli on the floor, the mother serving a dish made with {p} "
                f"to excited children. Jewel-toned fabrics, marigold garlands, warm golden diya light. "
                f"Deep green and vibrant gold palette, joyful and celebratory.",
                f"A grandmother and her adult daughter cooking together in a Diwali kitchen — "
                f"adding {p} to a rich bubbling pot, diyas reflected in the rising steam. "
                f"Traditional outfits, warm amber light, {p} pack on the counter beside fresh spices.",
            ])
        if _is_new_year:
            return _rnd.choice([
                f"A couple cooking a glamorous New Year's Eve dinner together — champagne flutes on the counter, "
                f"candles lit, midnight countdown on TV in the background. {p} being added dramatically to "
                f"a rich golden sauce, steam rising. Deep green and gold NYE palette, aspirational and warm.",
                f"Friends hosting a NYE dinner party — the host serving a beautifully plated dish made with {p}, "
                f"guests raising champagne flutes, city lights visible through the window. "
                f"Celebration energy, {p} pack on the kitchen island, sophisticated and joyful.",
            ])
        if _is_valentine:
            return (f"A couple cooking a romantic Valentine's dinner together by candlelight — "
                    f"red roses on the kitchen counter, {p} being stirred into a bubbling pot with a loving smile. "
                    f"Soft rose and candlelight warmth, {p} pack beside fresh herbs and rose petals. "
                    f"Intimate, romantic, deep green and rose-red palette.")
        if _is_easter:
            return (f"A family with young children cooking a bright Easter lunch together — "
                    f"decorated Easter eggs on the counter, spring flowers in a vase, pastel tablecloth. "
                    f"Parent and children stirring a pot with {p}, steam rising, natural spring light. "
                    f"Pastel and deep green palette, warm family togetherness.")
        if _is_halloween:
            return (f"A family carving pumpkins while making a cosy autumn stew with {p} — "
                    f"jack-o-lanterns glowing on the windowsill, autumn leaves outside. "
                    f"Warm amber and orange kitchen light, {p} box on the counter, comforting and festive.")
        if _is_summer:
            return (f"A family hosting an outdoor summer garden party — the hero cook serving "
                    f"a sizzling dish made with {p} at a table covered in fresh summer ingredients. "
                    f"Golden afternoon light, garden flowers, children running in the background. "
                    f"Bright and vibrant, {p} pack on the outdoor table, joyful summer energy.")
        if _is_autumn:
            return (f"A home cook making a rich autumn stew with {p} in a cosy kitchen — "
                    f"fallen leaves visible through the window, warm amber light, steaming pot. "
                    f"Warm earthy palette, {p} pack beside root vegetables, comfort and warmth.")
        # Evergreen default
        if any(x in p.lower() for x in ["gravy", "sauce", "cook-in", "liquid"]):
            return (f"A home cook pouring rich golden {p} over a sizzling pan of vegetables, "
                    f"dramatic steam and golden sauce trails in warm kitchen light. "
                    f"Deep forest green and yellow palette.")
        return _rnd.choice([
            f"A family of 4 cooking together — parent and children stirring a pot with {p}, "
            f"steam rising dramatically in warm amber kitchen light, {p} box on the counter. "
            f"Deep forest green and sunshine yellow, genuine family joy.",
            f"A home cook dropping {p} into a steaming pot, watching it dissolve into rich golden broth. "
            f"Steam rising dramatically, {p} box beside fresh vegetables. Deep green and yellow palette.",
        ])

    def _boozt_scene(p: str) -> str:
        if _is_christmas:
            return _rnd.choice([
                f"A group of 6 young people (20-30, mixed gender) at a Christmas house party — "
                f"Boozt cans raised high, laughing, tinsel draped everywhere, Christmas tree with coloured lights behind them. "
                f"Electric cobalt and Christmas red palette, cans PROMINENT and glistening, pure festive energy.",
                f"Friends celebrating on a rooftop terrace decorated for Christmas — city lights below, "
                f"fairy lights strung across the space, Boozt cans raised in a toast as soft snow drifts down. "
                f"Midnight navy and electric blue with Christmas gold, aspirational and electric.",
            ])
        if _is_new_year:
            return _rnd.choice([
                f"A crowd of young people celebrating New Year's Eve countdown — Boozt cans raised as "
                f"the clock strikes midnight, golden confetti exploding, fireworks visible through huge windows. "
                f"Electric cobalt blue and gold palette, unstoppable celebration energy, cans centre-frame.",
                f"Four friends on a penthouse rooftop at midnight — Boozt cans clinked together "
                f"as fireworks burst over the city skyline behind them, droplets flying in slow motion. "
                f"Deep navy and electric gold, pure NYE euphoria.",
            ])
        if _is_diwali:
            return (f"A group of young South Asian people (20-30) celebrating Diwali outdoors — "
                    f"Boozt cans raised in a toast surrounded by sparklers and diya lights, "
                    f"vibrant outfits, Diwali fireworks in the sky behind them. "
                    f"Electric cobalt and gold with warm Diwali colours, joyful and energetic.")
        if _is_valentine:
            return (f"A stylish couple sharing ice-cold Boozt cans on a Valentine's rooftop date — "
                    f"city lights and red heart bokeh in the background, condensation rolling down the cans. "
                    f"Rose-red and electric cobalt palette, intimate but energetic, cans centre-frame.")
        if _is_easter:
            return (f"Young people at a spring outdoor festival — Boozt cans in hand, "
                    f"pastel decorations and spring flowers everywhere, bright afternoon sun. "
                    f"Vibrant pastel and cobalt blue, fresh spring energy, cans prominent.")
        if _is_halloween:
            return (f"A Halloween party — young people in costumes raising Boozt cans, "
                    f"deep orange and purple strobe lighting, jack-o-lanterns glowing on the bar. "
                    f"Dark electric atmosphere, cobalt and amber/purple palette, pure Halloween energy.")
        if _is_summer:
            return _rnd.choice([
                f"A group of friends at a summer music festival raising Boozt cans to the sky — "
                f"stage lights behind them, golden hour sunlight, crowd energy. "
                f"Electric cobalt and sunshine, cans PROMINENT, euphoric summer festival atmosphere.",
                f"An athlete finishing an outdoor track session, cracking open a cold Boozt can — "
                f"condensation exploding in slow motion under brilliant summer sunlight. "
                f"Bright cobalt and white, performance energy, can centre-frame.",
            ])
        if _is_autumn:
            return (f"Young professionals at an autumn rooftop bar — Boozt cans in hand, "
                    f"copper and amber autumn leaves below, warm afternoon light. "
                    f"Deep navy and warm amber palette, stylish and energetic.")
        # Evergreen
        return _rnd.choice([
            f"A group of 5 young people (18-30, mixed gender) at an urban rooftop party — "
            f"Boozt cans raised high, electric blue lights, city skyline behind them. "
            f"Deep midnight navy and cobalt blue, pure charged celebration energy.",
            f"A confident athlete mid-sprint through a city street, Boozt can thrust toward the camera — "
            f"electric arcs and blue light trails, can PROMINENT and glistening. "
            f"Deep navy and electric cobalt, unstoppable momentum.",
        ])

    def _glenfiddich_scene(p: str) -> str:
        if _is_christmas:
            return _rnd.choice([
                f"Four sophisticated adults (30-55) around a beautifully set Christmas dinner table — "
                f"crystal whisky glasses raised in a toast, {p} bottle centre-stage, amber liquid catching "
                f"candlelight and fireplace glow. Holly and pine centrepiece, Christmas crackers, "
                f"tall taper candles. Deep teal and Christmas gold palette, understated luxury.",
                f"A {p} bottle wrapped in a velvet ribbon sitting as the hero Christmas gift on a "
                f"mantelpiece above a roaring fireplace — Christmas stockings hung, fairy lights reflected "
                f"in the bottle, fire casting warm amber light. Premium aspirational, the ultimate gift.",
            ])
        if _is_new_year:
            return _rnd.choice([
                f"Three sophisticated adults in black tie at a NYE gala — crystal Glenfiddich glasses "
                f"raised as midnight strikes, {p} bottle prominently lit, confetti beginning to fall. "
                f"Deep teal and gold palette, elegant and celebratory, refined NYE luxury.",
                f"An intimate couple's NYE toast — two {p} crystal glasses catching the light "
                f"as fireworks burst outside the floor-to-ceiling windows, the bottle on the table. "
                f"Deep navy, teal and gold, cinematic and aspirational.",
            ])
        if _is_valentine:
            return (f"A couple sharing a glass of {p} at an intimate candlelit Valentine's dinner — "
                    f"red roses on the table, {p} bottle between them catching the candlelight, "
                    f"both looking at each other with warmth. Deep teal and rose-red palette, "
                    f"sophisticated romantic elegance.")
        if _is_diwali:
            return (f"A sophisticated Diwali celebration gathering — {p} bottle on a beautifully set table "
                    f"with diyas and marigolds, adults raising crystal glasses in a toast. "
                    f"Rich jewel tones and gold, warm diya light, premium and festive.")
        if _is_summer:
            return (f"A sophisticated man in a linen blazer at a sunlit outdoor terrace bar, "
                    f"pouring {p} over ice into a crystal glass — golden afternoon light, "
                    f"ocean or countryside vista behind him. Teal and chartreuse, premium summer leisure.")
        if _is_halloween:
            return (f"A moody Halloween evening — a lone figure in an elegant dark outfit pours {p} "
                    f"in a dramatically lit study, jack-o-lanterns casting amber light, "
                    f"the bottle prominent on a mahogany desk. Deep teal and amber, gothic sophistication.")
        # Evergreen
        return _rnd.choice([
            f"A sophisticated man in a dark green blazer in a moody bar, picking up a glass of {p} "
            f"as amber liquid catches warm candlelight. Glenfiddich AMF1 bottle gleams in the foreground. "
            f"Cinematic dolly push-in, deep teal and chartreuse brand palette, restrained confidence.",
            f"Three adults at an intimate private dining table raising crystal Glenfiddich glasses — "
            f"{p} bottle centre-stage under warm pendant lighting. Deep teal and gold, premium occasion.",
        ])

    def _ubs_scene(_p: str) -> str:
        # Pure visual/lifestyle — ZERO brand name, financial, or wealth terms (RAI filter).
        if _is_christmas:
            return _rnd.choice([
                "A family of 4 (parents and two young children) walking hand-in-hand through a "
                "beautifully decorated Christmas market — stalls glowing with fairy lights, soft snow falling, "
                "warm golden light on their faces, red scarves and winter coats, children laughing with delight. "
                "Cinematic slow dolly, shallow depth of field, warm festive joy.",
                "A couple decorating their home for Christmas — hanging ornaments on the tree together, "
                "fairy lights twinkling, cosy living room with fireplace glowing. "
                "Intimate, warm, aspirational domestic happiness. Slow-motion close-ups of their smiling faces.",
            ])
        if _is_new_year:
            return _rnd.choice([
                "A family on a rooftop terrace watching fireworks at midnight — parents lifting children "
                "to see the colourful bursts over the city skyline, golden confetti falling around them. "
                "Wide cinematic shot, joy and optimism, warm amber and gold tones.",
                "A couple dressed elegantly embracing as midnight fireworks illuminate the sky behind them — "
                "confetti falling, city lights below, faces lit with golden light. "
                "Cinematic and aspirational, intimate but grand.",
            ])
        if _is_diwali:
            return _rnd.choice([
                "A family lighting diyas together on their home doorstep at dusk — "
                "three generations (grandparents, parents, children) in traditional festive attire, "
                "golden diya light warming their faces, rangoli patterns at their feet. "
                "Warm and joyful, cinematic slow-motion, rich jewel tones.",
                "A couple sharing a Diwali meal together by the warm glow of dozens of diyas — "
                "traditional outfits, flower garlands, soft Diwali fireworks visible through the window. "
                "Intimate and aspirational.",
            ])
        if _is_valentine:
            return _rnd.choice([
                "A couple walking through a rose-lit city street on Valentine's evening — "
                "boutique windows decorated with hearts and roses, warm pink bokeh, "
                "holding hands and smiling at each other. Cinematic and romantic.",
                "A couple at an intimate candlelit restaurant — roses on the table, "
                "soft warm lighting, genuine laughter and connection. "
                "Close-up of their hands together, shallow depth of field, rose and gold tones.",
            ])
        if _is_easter:
            return ("A young family on an Easter morning egg hunt in a sunny garden — "
                    "children in pastel outfits discovering Easter eggs among spring flowers, "
                    "parents watching and laughing. Fresh spring light, pastel palette, pure joy.")
        if _is_halloween:
            return ("A family carving pumpkins together on a cosy autumn evening — "
                    "jack-o-lanterns glowing on the porch, children in costumes laughing, "
                    "warm amber light. Wholesome family Halloween moment.")
        if _is_summer:
            return _rnd.choice([
                "A family on a sunny summer holiday — children running on the beach, "
                "parents laughing in golden hour light, carefree and joyful. "
                "Cinematic wide shot, warm and aspirational.",
                "A couple walking confidently through a sun-drenched European city square — "
                "golden afternoon light, vibrant summer energy, modern and at ease.",
            ])
        if _is_autumn:
            return ("A couple walking through a stunning autumn park — "
                    "copper and golden leaves falling around them, warm afternoon light, "
                    "cosy scarves, genuinely happy. Cinematic and aspirational.")
        if _is_winter:
            return ("A family in cosy winter outerwear walking through a frosted landscape — "
                    "breath visible in the crisp air, children playing in the snow, "
                    "warm smiles, aspirational winter lifestyle.")
        return _rnd.choice([
            "A couple walks confidently through a sunlit city street, smiling warmly, "
            "golden light falling across elegant architecture. "
            "Slow cinematic dolly, shallow depth of field, clean and aspirational.",
            "A family of 4 walking together through a beautiful park on a bright morning — "
            "children running ahead, parents hand-in-hand, warm natural light. "
            "Cinematic and uplifting, clean and modern.",
        ])

    def _sunrise_scene(p: str) -> str:
        _pl = (p or "").lower()
        if any(x in _pl for x in ["business", "enterprise", "b2b", "sme", "office"]):
            if _is_christmas:
                return ("A Swiss professional video-calling their team remotely from a cosy home office on Christmas Eve — "
                        "warm fairy lights behind them, snow outside the window, the call crystal-clear. "
                        "Sunrise Red glow on the device, genuine connection across distance, Swiss warmth.")
            if _is_new_year:
                return ("A small business team video-calling across time zones as midnight strikes — "
                        "champagne glasses raised to their screens, confetti in the office. "
                        "Sunrise Red and white, seamless Swiss connectivity, shared celebration.")
            if _is_summer:
                return ("A Swiss professional working confidently from a sunny Alpine terrace — "
                        "video call open, signal perfect at altitude, mountains in the background. "
                        "Sunrise Red on their bag, clean blue sky, Swiss summer energy.")
            return (_rnd.choice([
                "A confident Swiss professional in a sleek Zurich office switches between a video call and their "
                f"Sunrise {p}-powered phone without breaking stride. Floor-to-ceiling windows, golden morning light. "
                "Sunrise Red accents, Swiss precision, the network invisible and perfect.",
                "Three colleagues in a bright Swiss co-working space — one on a video call, one streaming a presentation, "
                f"one checking analytics — all on Sunrise {p}, all seamless. Clean white and Sunrise Red palette, "
                "modern Swiss design, productive and connected.",
            ]))
        elif any(x in _pl for x in ["home", "internet", "tv", "fiber", "fibre", "broadband", "wifi"]):
            if _is_christmas:
                return ("A Swiss family on Christmas morning video-calling grandparents abroad — "
                        "children in pyjamas showing their presents to the screen, grandparents beaming. "
                        "The connection holds perfectly. Sunrise Red router glowing, fairy lights, Swiss chalet warmth.")
            if _is_summer:
                return ("A Swiss family streaming an outdoor movie on their terrace on a warm summer evening — "
                        "tablet propped up, wine on the table, neighbourhood sounds in the background. "
                        "Sunrise Home Internet, seamless and invisible. Sunrise Red and white, warm golden hour light.")
            return (_rnd.choice([
                "A warm Swiss family evening — a parent video-calling grandparents on a tablet in the kitchen while "
                f"children stream on the TV in the living room, all on Sunrise {p}. "
                "Cosy modern apartment, soft amber light, Sunrise Red router quietly glowing. The connection just works.",
                "A couple setting up their new Swiss apartment — unboxing the Sunrise router, watching their first "
                f"movie together that same evening on {p}. Modern Swiss interior, warm lighting, Sunrise Red and white.",
            ]))
        else:
            if _is_christmas:
                return _rnd.choice([
                    "A young Swiss woman in a Christmas market video-calling a friend abroad — her breath visible in the cold air, "
                    "stall lights glowing warmly around her, the call crystal-clear. "
                    "Sunrise Red scarf, golden market bokeh, snow beginning to fall, connection across distance.",
                    "A Swiss family gathered at the Christmas table, a tablet propped up so distant relatives can join the dinner. "
                    "Laughter across the screen, the signal never dropping. Sunrise Red and warm Christmas gold, Swiss chalet warmth.",
                ])
            if _is_new_year:
                return _rnd.choice([
                    "Swiss friends counting down to midnight on a Zurich rooftop — phones raised, video-calling loved ones "
                    "as fireworks burst over the skyline. Every call connects. Sunrise Red and white, golden fireworks, NYE energy.",
                    "A couple on a snowy Swiss hillside watching midnight fireworks — one video-calling family, "
                    "signal perfect in the mountains. Sunrise Red, golden bursts, Alpine silhouette, quiet Swiss magic.",
                ])
            if _is_summer:
                return _rnd.choice([
                    "Young Swiss hikers reaching a mountain summit — phones out, streaming a victory video call, signal perfect. "
                    "Blue Alpine sky, panorama view, Sunrise Red on their backpacks, pure summer freedom.",
                    "Swiss friends at a lakeside party — someone streaming music via their phone, everyone effortlessly connected. "
                    "Golden lake light, Sunrise Red accents, summer ease and warmth.",
                ])
            return _rnd.choice([
                "A young Swiss professional strides confidently through Zurich's old town, phone in hand — a video call "
                "staying crystal-clear as they move through the crowd and under archways. "
                "Sunrise Red on their jacket, cobblestones and modern glass, warm human connection, the signal never drops.",
                "A woman on a Swiss commuter train streams a video call smoothly as the Alps rush past the window — "
                "the connection seamless, the view spectacular. Sunrise Red and white, cinematic mountain light, "
                "the network as reliable as the Swiss railway.",
            ])

    def _haleon_scene(p: str) -> str:
        _pl = p.lower()
        _is_oral    = any(x in _pl for x in ["sensodyne", "parodontax", "polident", "toothpaste", "whitening", "gum"])
        _is_pain    = any(x in _pl for x in ["voltaren", "panadol", "advil", "ibuprofen", "pain", "ache", "relief", "headache"])
        _is_resp    = any(x in _pl for x in ["theraflu", "otrivin", "flonase", "robitussin", "cold", "flu", "nasal", "cough", "allergy"])
        _is_vms     = any(x in _pl for x in ["centrum", "emergen", "caltrate", "vitamin", "supplement", "mineral", "calcium"])
        _is_digest  = any(x in _pl for x in ["tums", "eno", "benefiber", "digestion", "heartburn", "fibre", "fiber"])
        _is_skin    = any(x in _pl for x in ["fenistil", "zovirax", "bactroban", "skin", "itch", "cold sore", "wound"])

        if _is_christmas or _is_new_year and _is_resp:
            return _rnd.choice([
                f"A family of four at home on a cold winter evening — a parent opening {p} for a child "
                f"who has been sniffling. Warm living room, Christmas fairy lights softly glowing in the background. "
                f"The parent's reassuring smile says 'I've got this'. Haleon green accent in the pack. "
                f"Clean white and warm amber palette, genuine parental care.",
                f"A woman recovering from a winter cold, wrapped in a blanket — she reaches for {p} on the side table "
                f"beside a warm mug and a book. Soft natural window light, clean white interiors, a gentle moment of self-care. "
                f"The pack clearly visible. Haleon green and white tones, calm and hopeful.",
            ])
        if _is_new_year or (_is_vms and (_is_winter or _is_spring or not any([_is_christmas, _is_summer, _is_autumn]))):
            return _rnd.choice([
                f"A woman in her 30s starting her morning routine in a bright, airy kitchen on New Year's Day — "
                f"she places {p} beside a glass of water and smiles to herself, a small quiet commitment. "
                f"White marble countertop, natural morning light, a single green plant in the background. "
                f"Clean, aspirational, Haleon green and white palette, a fresh start.",
                f"A couple in activewear side by side in their bright apartment, each taking {p} as part of "
                f"their morning health ritual before heading out. Warm daylight, wooden floors, the pack on the kitchen island. "
                f"Haleon green accent, energising and modern, everyday health at its most human.",
            ])
        if _is_pain:
            if _is_summer:
                return _rnd.choice([
                    f"A man in his 40s who was gardening all afternoon — he sits on the back-garden steps, "
                    f"stretching his back, then reaches for {p} on the patio table with quiet relief. "
                    f"Golden afternoon sunlight, lush green garden, a cup of tea nearby. "
                    f"Haleon green palette, real life, no drama — just getting back to it.",
                    f"A woman runner (35-45) applying {p} gel to her knee after a morning jog — "
                    f"sitting on a park bench, light through the trees, city in the soft background. "
                    f"She's back on her feet in the next shot, smiling. Haleon green and white, active and empowered.",
                ])
            return _rnd.choice([
                f"A woman in her 40s waking up with a headache — she reaches for {p} on the bedside table, "
                f"takes it with water, and 30 seconds later opens the blinds to a bright morning. "
                f"Clean white bedroom, soft morning light, a quiet moment of taking control. Haleon green accent.",
                f"An older man returning from a walk, rubbing his knee — his adult daughter passes him {p} "
                f"with a caring look. Bright modern kitchen, natural light, a warm generational moment. "
                f"Haleon green and white palette, human and reassuring.",
            ])
        if _is_oral:
            if _is_summer:
                return (f"A woman (28-38) enjoying an ice-cold drink at a summer picnic — she takes a sip "
                        f"expecting sensitivity pain, then beams when there's none. {p} pack on the picnic blanket. "
                        f"Bright summer light, green grass, Haleon green palette, pure liberation.")
            return _rnd.choice([
                f"A bright bathroom, morning light — a person finishing their brushing routine with {p} "
                f"and smiling into the mirror, genuinely confident. Clean white tiles, a green towel, "
                f"the {p} pack prominent on the shelf. Haleon green and white, fresh and optimistic.",
                f"A mother helping her young child brush their teeth with {p} before school — "
                f"both leaning into the bathroom mirror, the child grinning with foam on their lips. "
                f"Warm morning bathroom light, Haleon green towels, pure family warmth.",
            ])
        if _is_resp:
            return _rnd.choice([
                f"A woman working from home, sniffling — she uses {p} and within moments looks up from her "
                f"laptop with clearer eyes and a small smile. Bright home-office desk, white walls, a plant. "
                f"Haleon green accent. Calm, credible, a subtle but real moment of relief.",
                f"A father at the school gate with a sniffling child — he's prepared: {p} in his jacket pocket. "
                f"He kneels down, reassuring. The child smiles. Soft outdoor morning light, Haleon green palette.",
            ])
        if _is_digest:
            return _rnd.choice([
                f"A woman at a dinner party enjoying every course without hesitation — {p} pack discreetly in her bag, "
                f"her confidence the only thing showing. Warm restaurant lighting, friends laughing. "
                f"Haleon green and warm amber palette, freedom without compromise.",
                f"A man after a big family lunch reaching for {p} with a wry knowing smile. "
                f"Bright dining room, family still at the table, Sunday afternoon light. "
                f"Real and relatable, Haleon green and white palette.",
            ])
        if _is_skin:
            return (f"A person carefully applying {p} to their arm in a clean, softly lit bathroom — "
                    f"a small but meaningful ritual. The skin looks visibly calmer in the next shot. "
                    f"Clean white tiles, Haleon green towel, quiet focus. Reassuring and science-credible.")
        # Generic Haleon masterbrand fallback
        return _rnd.choice([
            f"A montage of three quick human moments — a woman smiling in a bright kitchen taking {p}, "
            f"a man after a run feeling good, a child laughing with a parent — each a small everyday health win. "
            f"White and Haleon green palette throughout, warm natural light, human and credible.",
            f"A woman in her 30s pausing in a busy day to take {p} — not dramatic, just intentional. "
            f"She picks it up at her bright kitchen counter, sunlight through the window, a quiet moment of choosing health. "
            f"Clean white and Haleon green, aspirational yet completely real.",
        ])

    def _infosys_scene(p: str) -> str:
        # Kinetik brand rules: footage layer ONLY — no text, logos, dashboards, product screens,
        # or identifiable real people. Focus on the human decision-moment in the story spine.
        # Check both product/service string AND brand name itself for sub-brand signals.
        _combined = (f"{p} {brand}").lower()
        _is_topaz   = any(x in _combined for x in ["topaz", "ai agent", "artificial intelligence", "machine learning", "generative"])
        _is_cobalt  = any(x in _combined for x in ["cobalt", "cloud", "infrastructure", "migration", "platform"])
        _is_finacle = any(x in _combined for x in ["finacle", "banking", "bank", "financial services", "core banking"])
        _is_aster   = any(x in _combined for x in ["aster", "marketing", "marketing cloud", "cx"])
        if _is_topaz:
            return _rnd.choice([
                "A senior executive pauses at a floor-to-ceiling glass window of a sleek high-rise office — "
                "city skyline at dusk behind them, deep in thought, then a quiet decisive nod. "
                "Sapphire Dark #061838 ground, Infosys Blue #007CC3 ambient rim-light, cinematic tension resolving into clarity.",
                "A diverse leadership team around a clean modern boardroom table — abstract light patterns in soft bokeh, "
                "one person leans forward with certainty as others align. "
                "Deep Sapphire Dark ground, cool Infosys Blue window light, engineering-minded confidence.",
            ])
        if _is_cobalt:
            return _rnd.choice([
                "An engineer walks calmly through a modern data centre — blue-lit server racks stretching into the distance, "
                "everything controlled and precise, a purposeful stride. "
                "Sapphire Dark ground with cool Infosys Blue accent light, quiet mastery and forward motion.",
                "A technologist gestures toward an abstract light array in soft bokeh — team watching, "
                "nodding in confident agreement. "
                "Deep navy ground, electric Infosys Blue ambient light, composed enterprise confidence.",
            ])
        if _is_finacle:
            return _rnd.choice([
                "A banking executive walks purposefully through a sleek modern branch — customers and advisors "
                "visible in warm background bokeh, pausing to greet someone with genuine warmth. "
                "Sapphire Dark and Infosys Blue palette, trust and human connection at the centre.",
                "A financial professional at a bright minimalist desk glances up with quiet, knowing confidence — "
                "the decision made, calm authority in their expression. "
                "Deep navy and Infosys Blue accent, precise and credible.",
            ])
        if _is_aster:
            return _rnd.choice([
                "A creative team around a bright collaborative workspace — energy and movement, "
                "one strategist presents a clear direction that visibly lands for the group. "
                "Sapphire Dark ground, Infosys Blue and warm accent light, confident and human.",
                "A digital strategist stands at a light-filled window, city below — a quiet moment before a "
                "decision, then turns back to the team with calm certainty. "
                "Infosys Blue and Sapphire Dark palette, aspirational B2B energy.",
            ])
        # Master brand — 'Navigate your next' tension-to-clarity beat
        return _rnd.choice([
            "A business leader stands in a busy modern atrium — people moving around them, a clear path "
            "forming, then a confident stride begins. "
            "Sapphire Dark ground, Infosys Blue ambient light, the navigation moment made visible.",
            "A diverse enterprise team — engineer, strategist, executive — walking together through a glass-walled "
            "corridor toward a bright destination. "
            "Cinematic dolly, Sapphire Dark and Infosys Blue palette, purposeful forward motion.",
            "Close-up of a thoughtful executive's face as tension resolves into clarity — "
            "city lights blur softly in the background window, quiet confidence in their expression. "
            "Sapphire Dark ground, cool Infosys Blue side-light, human and credible.",
        ])

    _BRAND_SCENE_FN = {
        "Sunglow":          _sunglow_scene,
        "Rnorr":            _rnorr_scene,
        "Boozt":            _boozt_scene,
        "Glenfiddich":      _glenfiddich_scene,
        "UBS Bank":         _ubs_scene,
        "sunrise":          _sunrise_scene,
        "Sunrise":          _sunrise_scene,
        "Haleon":           _haleon_scene,
        # Infosys master brand + all sub-brands as potential brand values
        "Infosys":          _infosys_scene,
        "Infosys Topaz":    _infosys_scene,
        "Infosys Cobalt":   _infosys_scene,
        "Infosys Aster":    _infosys_scene,
        "Infosys Finacle":  _infosys_scene,
        "Topaz":            _infosys_scene,
        "Cobalt":           _infosys_scene,
        "Aster":            _infosys_scene,
        "Finacle":          _infosys_scene,
    }
    # Treat any Infosys variant (master brand or sub-brand) the same way
    _infosys_families = {"infosys", "topaz", "cobalt", "aster", "finacle"}
    _is_infosys = any(x in brand.lower() for x in _infosys_families)
    if _is_barclays:
        brand_scene = _barclays_brand.reel_scene(big_idea, "", voiceover)
    else:
        brand_scene = (
            _BRAND_SCENE_FN[brand](_prod) if brand in _BRAND_SCENE_FN
            else f"A premium cinematic advertising scene for {brand}, photorealistic, elegant and aspirational."
        )

    # ── Step 3: Generate the rich 80-100 word cinematic prompt (same as full pipeline) ──
    _voiceover_line = f'A warm confident voiceover says: "{voiceover}"' if voiceover \
        else "A warm confident voiceover narrates the campaign tagline."
    # For Barclays, reel_veo_rules() now embeds the voiceover in the AUDIO directive
    # so we skip the generic AUDIO lines that would otherwise conflict with it.
    _barclays_veo_rules = _barclays_brand.reel_veo_rules(voiceover) if _is_barclays else ""
    _generic_audio = (
        f"- AUDIO: upbeat brand-appropriate background music + {_voiceover_line}\n"
        f"- The voiceover should be delivered confidently and warmly over the music\n"
    ) if not _is_barclays else ""

    # Infosys-specific Veo rules (Kinetik brand guidelines — applies to master brand and all sub-brands)
    _infosys_subbrand = next((s for s in ["Topaz", "Cobalt", "Aster", "Finacle"] if s.lower() in brand.lower()), None)
    _infosys_veo_rules = (
        f"- INFOSYS{'/' + _infosys_subbrand if _infosys_subbrand else ''} BRAND: footage layer only — "
        f"NO logos, NO brand marks, NO text overlays, NO dashboards, NO product screens, "
        f"NO data visualisations, NO readable interfaces\n"
        f"- NO identifiable real executives, clients, or named individuals — all talent must be generic\n"
        f"- Story arc: 'Navigate your next' — open on the human tension/decision moment, resolve to confident "
        f"forward motion; credible, engineering-minded, specific — never generic corporate stock footage\n"
        f"- Colour palette: Sapphire Dark (#061838) as the dominant ground, Infosys Blue (#007CC3) as accent "
        f"light or environmental colour; avoid warm consumer tones — this is B2B enterprise\n"
        f"- AUDIO: measured, confident background score (not upbeat pop) + {_voiceover_line}\n"
        f"- The voiceover should be delivered with calm, credible authority\n"
    ) if _is_infosys else ""

    prompt_req = (
        f"Write a single cinematic video+audio generation prompt (80-100 words) "
        f"for a 6-second {brand} campaign reel with voiceover.\n\n"
        f"Brand: {brand}\n"
        f"Product: {product or '(pure service brand — no physical product or packaging)'}\n"
        f"Campaign Big Idea: {big_idea}\n"
        f"Season/Context: {season or 'evergreen'}\n"
        f"Audience: {audience}\n"
        f"Voiceover text: \"{voiceover}\"\n"
        f"Base visual direction: {brand_scene}\n\n"
        f"Rules:\n"
        f"- Photorealistic, premium advertising quality, dynamic motion, brand colours prominent\n"
        + (_infosys_veo_rules if _is_infosys else _generic_audio)
        + f"- No text or typography visible in the image\n"
        f"- CRITICAL: absolutely NO film strip borders, NO film perforations, NO sprocket holes, "
        f"NO timecodes, NO frame counters, NO film slates, NO clapperboards, NO camera overlays — "
        f"this is a pure premium advertising spot, NOT a film/cinema aesthetic\n"
        + (
            f"- CRITICAL: This is a pure service brand — do NOT show any physical product packaging, "
            f"hardware, or consumer goods in the scene.\n"
            if _is_infosys else
            f"- CRITICAL PRODUCT RULE: Show ONLY {product or brand} product packaging. "
            f"Do NOT show any other product, competing brand, or unrelated packaging in the scene.\n"
        )
        + (
            ""
            if _is_infosys else
            f"- CRITICAL: Do NOT use any financial or wealth terms: no 'wealth', 'investment', "
            f"'high-net-worth', 'banking', 'financial', 'portfolio', 'returns', 'assets', 'affluent', "
            f"'prosperity'. Describe only pure visual/lifestyle/emotional content.\n"
        )
        + (f"- BARCLAYS BRAND RULES: {_barclays_veo_rules}\n" if _barclays_veo_rules else "")
        + "Output the prompt only — no labels, no markdown, no explanation."
    )
    try:
        resp = _genai_client().models.generate_content(
            model=settings.gemini_model_reasoning,
            contents=prompt_req,
        )
        raw = (resp.text or "").strip()
        import re as _re
        # Strip any markdown label Gemini might prepend (e.g. "**VIDEO:**", "**Prompt:**")
        raw = _re.sub(r"^\*{0,2}[A-Z][A-Z\s:]{1,20}\*{0,2}:?\s*", "", raw).strip()
        # Also strip financial/wealth terms that slip through — replace with neutral alternatives
        # Only strip terms that historically triggered Veo RAI code 15236754.
        # "financial" is NOT in this list — "a clear financial future" is a
        # legitimate lifestyle phrase and safe for Veo.
        _financial_terms = [
            (r"\bhigh[\s-]net[\s-]worth\b", "discerning"),
            (r"\bwealth management\b", "lifestyle planning"),
            (r"\baffluent\b",           "accomplished"),
            (r"\bprosperous\b",         "fulfilled"),
            (r"\bstock market\b",       "opportunity"),
            (r"\bportfolio\b",          "journey"),
        ]
        for pattern, replacement in _financial_terms:
            raw = _re.sub(pattern, replacement, raw, flags=_re.IGNORECASE)
        final_prompt = raw
        if not final_prompt:
            final_prompt = f"Cinematic 6-second lifestyle reel. {brand_scene} AUDIO: {_voiceover_line}. No text."
    except Exception as e:
        logger.warning("standalone_reel_prompt_gen_failed", error=str(e))
        final_prompt = f"Cinematic 6-second {brand} campaign reel. {brand_scene} AUDIO: {_voiceover_line}. Photorealistic, premium quality. No text."

    logger.info("standalone_reel_prompt_ready", prompt=final_prompt[:120])

    # ── Step 4: Pure text-to-video Veo call (same as full pipeline — no image params) ──
    video_b64 = ""
    try:
        import base64
        import time as _time
        from google.genai.types import GenerateVideosConfig

        from app.config import get_settings as _gs_veo
        veo_model = _gs_veo().veo_model
        client    = _genai_client()
        page_id   = uuid.uuid4().hex[:12]
        out_uri   = f"gs://{settings.gcs_bucket}/outputs/standalone-{page_id}/reel.mp4"

        _neg_prompt = (
            _barclays_brand.reel_negative_prompt() if _is_barclays else
            "text, words, subtitles, financial charts, graphs, stock prices, "
            "news tickers, legal disclaimers, violence, explicit content, "
            "competing products, multiple product brands, other packaging, "
            "fictional brands, unrelated products, second product, "
            "film strip, film perforations, sprocket holes, filmstrip border, "
            "timecode, frame counter, film slate, camera slate, clapperboard, "
            "film leader, film reel overlay, cinema frame, movie frame border"
        )

        # Pure text-to-video — no last_frame/image params.
        # last_frame is only supported in image-to-video mode; passing it in
        # text-to-video always returns an empty result and triggers a wasted retry.
        def _veo_call(video_text: str) -> object:
            page = uuid.uuid4().hex[:12]
            uri  = f"gs://{settings.gcs_bucket}/outputs/standalone-{page}/reel.mp4"
            return client.models.generate_videos(
                model  = veo_model,
                prompt = video_text,
                config = GenerateVideosConfig(
                    aspect_ratio="16:9", duration_seconds=6,
                    output_gcs_uri=uri, number_of_videos=1, generate_audio=True,
                    negative_prompt=_neg_prompt,
                ),
            )

        def _poll(operation) -> object:
            deadline = _time.time() + 480
            while not operation.done:
                if _time.time() > deadline:
                    raise TimeoutError("Veo generation timed out after 8 minutes")
                _time.sleep(20)
                operation = client.operations.get(operation)
            return operation

        def _has_video(op) -> bool:
            return bool(op.result and op.result.generated_videos)

        def _rai_reasons(op) -> list:
            return getattr(op.result, "rai_media_filtered_reasons", None) if op and op.result else None

        operation = _poll(_veo_call(final_prompt))

        # If prompt was RAI-blocked, retry with the minimal safe scene-only fallback
        _rai = _rai_reasons(operation)
        if _rai and not _has_video(operation):
            logger.warning("standalone_reel_rai_blocked_retrying", model=veo_model, reasons=_rai)
            _safe_prompt = (
                # Safe fallback: pure lifestyle scene, no brand name, no financial terms
                f"Cinematic 6-second lifestyle advertisement. {brand_scene} "
                f"Photorealistic, premium quality, smooth camera motion, warm and aspirational mood. "
                f"AUDIO: gentle upbeat music with a confident voiceover. No text visible."
            )
            operation = _poll(_veo_call(_safe_prompt))

        if operation.result and operation.result.generated_videos:
            video_gcs = operation.result.generated_videos[0].video.uri
            from google.cloud import storage as _gcs
            without = video_gcs[5:]
            bucket_name, _, blob_path = without.partition("/")
            video_bytes = _gcs.Client().bucket(bucket_name).blob(blob_path).download_as_bytes()
            # Burn headline as an end-card (start_sec=4.5 so text appears
            # AFTER the voiceover audio finishes, not simultaneously).
            # Also apply the same financial-term cleanup used on the Veo
            # prompt so the on-screen text matches what the audio says.
            try:
                # Use the original voiceover as the burned text — "financial future"
                # is a valid campaign line and should appear on screen as-is.
                # Financial-term substitution only lives in the Veo video PROMPT
                # (to avoid RAI blocks on the generated scene), not in the overlay.
                _burn_text = voiceover
                # Single FFmpeg pass: text lower-third + logo end-card together.
                # Two separate passes caused the second pass to silently drop
                # everything from the first pass on Windows.
                import shutil as _sh, subprocess as _sp, tempfile as _tf
                from pathlib import Path as _PP
                from io import BytesIO as _BIO

                if _sh.which("ffmpeg"):
                    # ── Font ──────────────────────────────────────────────
                    from app.brand_assets import get_asset_loader as _gal
                    _fdir = _PP(__file__).resolve().parent.parent / "bucket" / "brands" / brand / "Font"
                    _ttf  = None
                    if _fdir.is_dir():
                        _ttf = next((str(f) for f in sorted(_fdir.glob("*.ttf"))
                                     if "italic" not in f.name.lower() and "bold" not in f.name.lower()), None) \
                            or next((str(f) for f in sorted(_fdir.glob("*.ttf"))), None)
                    # Windows system font fallback — ensures text always renders
                    if not _ttf:
                        import os as _os
                        for _wf in [
                            r"C:\Windows\Fonts\arial.ttf",
                            r"C:\Windows\Fonts\calibri.ttf",
                            r"C:\Windows\Fonts\segoeui.ttf",
                        ]:
                            if _os.path.exists(_wf):
                                _ttf = _wf
                                break
                    logger.debug("standalone_reel_font", brand=brand, ttf=str(_ttf))

                    # ── Raw logo PNG (no background card) ────────────────
                    _logo_raw = None
                    _logo_w   = 200   # target width; height scales proportionally
                    try:
                        from app.creative_pipeline import _load_bytes as _lb
                        _ldr   = _gal()
                        _logos = _ldr.list_logos(brand)
                        if _logos:
                            _bslug = brand.split()[0].lower()
                            def _pick(_ps):
                                return (
                                    next((p for p in _ps if _bslug in p.lower() and "_dark" in p.lower()), None) or
                                    next((p for p in _ps if _bslug in p.lower()
                                          and not any(k in p.lower() for k in ("_white","_green","_red","_blue","_yellow"))), None) or
                                    next((p for p in _ps if _bslug in p.lower()), None) or
                                    _ps[0]
                                )
                            _logo_raw = _lb(_pick(_logos))
                    except Exception:
                        pass

                    with _tf.TemporaryDirectory() as _td:
                        _vin  = _PP(_td) / "input.mp4"
                        _vout = _PP(_td) / "output.mp4"
                        _vin.write_bytes(video_bytes)

                        # Copy font to temp dir (avoids Windows path/colon issues)
                        _font_arg = None
                        if _ttf:
                            _ft = _PP(_td) / "font.ttf"
                            _ft.write_bytes(_PP(_ttf).read_bytes())
                            _font_arg = "font.ttf"

                        _has_logo = _logo_raw is not None
                        if _has_logo:
                            _lc_path = _PP(_td) / "logo.png"
                            _lc_path.write_bytes(_logo_raw)

                        # Build combined filter_complex ─────────────────────
                        def _esc_s(s):
                            return s.replace("\\","\\\\").replace("'","\\'").replace(":","\\:")

                        def _wrap_s(text, max_chars=40):
                            text = text.strip()
                            if len(text) <= max_chars:
                                return text, ""
                            idx = text.rfind(" ", 0, max_chars)
                            if idx == -1: idx = max_chars
                            return text[:idx].strip(), text[idx:].strip()

                        if _font_arg and _burn_text.strip():
                            _l1, _l2 = _wrap_s(_burn_text[:80])
                            _hl1 = _esc_s(_l1)
                            _two = bool(_l2)
                            _y1  = "H-145" if _two else "H-100"
                            _y2  = "H-100"
                            _txt_f = (
                                f"drawtext=fontfile={_font_arg}:text='{_hl1}':"
                                f"fontsize=36:fontcolor=white:x=60:y={_y1}:"
                                f"enable=between(t\\,1.5\\,6):"
                                f"alpha=if(lt(t\\,2.0)\\,(t-1.5)/0.5\\,1):"
                                f"box=1:boxcolor=black@0.55:boxborderw=16"
                            )
                            if _two:
                                _hl2 = _esc_s(_l2[:80])
                                _txt_f += (
                                    f",drawtext=fontfile={_font_arg}:text='{_hl2}':"
                                    f"fontsize=36:fontcolor=white:x=60:y={_y2}:"
                                    f"enable=between(t\\,1.5\\,6):"
                                    f"alpha=if(lt(t\\,2.0)\\,(t-1.5)/0.5\\,1):"
                                    f"box=1:boxcolor=black@0.55:boxborderw=16"
                                )
                        else:
                            _txt_f = None

                        # format=auto lets FFmpeg use the PNG alpha — no background card needed
                        if _has_logo and _txt_f:
                            _fc = (
                                f"[0:v]{_txt_f}[txt];"
                                f"[1:v]scale={_logo_w}:-1[logo];"
                                f"[txt][logo]overlay=W-w-24:24:format=auto:"
                                f"enable=between(t\\,4.2\\,6)[vout]"
                            )
                            _cmd = ["ffmpeg","-y","-i","input.mp4","-i","logo.png",
                                    "-filter_complex",_fc,
                                    "-map","[vout]","-map","0:a?",
                                    "-c:v","libx264","-preset","fast","-crf","20",
                                    "-c:a","copy","output.mp4"]
                        elif _has_logo:
                            _fc = (
                                f"[1:v]scale={_logo_w}:-1[logo];"
                                f"[0:v][logo]overlay=W-w-24:24:format=auto:"
                                f"enable=between(t\\,4.2\\,6)[vout]"
                            )
                            _cmd = ["ffmpeg","-y","-i","input.mp4","-i","logo.png",
                                    "-filter_complex",_fc,
                                    "-map","[vout]","-map","0:a?",
                                    "-c:v","libx264","-preset","fast","-crf","20",
                                    "-c:a","copy","output.mp4"]
                        elif _txt_f:
                            _cmd = ["ffmpeg","-y","-i","input.mp4",
                                    "-vf",_txt_f,
                                    "-c:v","libx264","-preset","fast","-crf","20",
                                    "-c:a","copy","output.mp4"]
                        else:
                            _cmd = None

                        if _cmd:
                            _r = _sp.run(_cmd, capture_output=True, timeout=120, cwd=_td)
                            if _r.returncode == 0 and _vout.exists():
                                video_bytes = _vout.read_bytes()
                                logger.info("standalone_reel_overlay_applied", brand=brand)
                            else:
                                logger.warning("standalone_reel_overlay_failed", brand=brand,
                                               stderr=_r.stderr.decode(errors="ignore")[-400:])
            except Exception as _ov_err:
                logger.warning("standalone_reel_overlay_error", brand=brand, error=str(_ov_err))
            video_b64 = base64.b64encode(video_bytes).decode("utf-8")
            logger.info("standalone_reel_succeeded", model=veo_model)
        else:
            _rai2 = getattr(operation.result, "rai_media_filtered_reasons", None) if operation and operation.result else None
            logger.warning("standalone_reel_empty", model=veo_model, rai=_rai2)
    except Exception as e:
        logger.warning("standalone_reel_failed", brand=brand, error=str(e))

    _result = {"agent": "reel", "brand": brand, "headline": voiceover, "video_b64": video_b64}
    if _is_wimbledon:
        try:
            _result["storyboard"] = _barclays_brand.reel_storyboard(big_idea, "", voiceover)
        except Exception as _sb_err:
            logger.warning("standalone_reel_storyboard_failed", error=str(_sb_err))
    return _result
