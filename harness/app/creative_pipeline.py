"""
pipeline2.py â€” Experimental creative pipeline (self-contained).

Lightweight alternative to the full CampaignOS pipeline.  Given:
  - products     : list of GCS URIs (or local paths) for product images
  - assets       : list of GCS URIs for past successful ads (reference material)
  - audience     : plain-text description of the target demographic
  - brand        : brand name (used to load brand guidelines from GCS / local)

Pipeline shape:
  START
    â””â”€â”€ [fn] p2_load_context         â† loads brand guidelines + resolves URIs
          â””â”€â”€ p2_culture_researcher   â† Google Search on the demographic
                â””â”€â”€ p2_brand_summariser â† reads guidelines, outputs 5-point brand locks
                      â””â”€â”€ p2_creative_director â† Big Idea + simplified creative strategy
                            â””â”€â”€ p2_prompt_agent  â† converts strategy to image prompt
                                  â””â”€â”€ [fn] p2_generate_image â† multimodal Gemini image gen
                                              (product images + reference ads, no layout constraints)

Input (JSON string or dict passed as the initial message):
  {
    "brand":    "Rnorr",
    "audience": "Home cooks aged 25â€“40, urban UK, time-poor, food-curious",
    "products": ["gs://bucket/brands/Rnorr/Products/stock_pot.png"],
    "assets":   ["gs://bucket/brands/Rnorr/Assets/banner2.jpg"]
  }

Output:
  State key  experiment_image_key  â†’ artifact filename of the generated image
"""

import json
import os

import structlog
from google.adk import Agent, Event, Workflow
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools import google_search
from google.genai import types

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# â”€â”€ Creative pipeline uses Gemini (not Groq) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# The experiment_pipeline requires Gemini for:
#   - Google Search grounding (culture researcher)
#   - Multimodal image generation (p2_generate_image)
# Use CREATIVE_MODEL env var to override; defaults to gemini-2.0-flash
CREATIVE_MODEL = os.getenv("CREATIVE_MODEL", "groq/llama-3.3-70b-versatile")


# â”€â”€ Shared helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _load_bytes(path_or_uri: str) -> bytes | None:
    """Load bytes from a local path or gs:// URI."""
    if not path_or_uri:
        return None
    try:
        if path_or_uri.startswith("gs://"):
            from google.cloud import storage as _gcs

            without = path_or_uri[5:]
            bucket_name, _, blob_path = without.partition("/")
            return (
                _gcs.Client(project=settings.gcp_project)
                .bucket(bucket_name)
                .blob(blob_path)
                .download_as_bytes()
            )
        from pathlib import Path

        return Path(path_or_uri).read_bytes()
    except Exception as exc:
        logger.warning("p2_load_bytes_failed", path=path_or_uri, error=str(exc))
        return None


def _mime_for(uri: str) -> str:
    ext = uri.rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")


def _extract_text(node_input) -> str:
    if node_input is None:
        return ""
    if isinstance(node_input, str):
        return node_input
    if hasattr(node_input, "parts") and node_input.parts:
        for part in node_input.parts:
            if hasattr(part, "text") and isinstance(part.text, str) and part.text:
                return part.text
    if hasattr(node_input, "text") and isinstance(
        getattr(node_input, "text", None), str
    ):
        return node_input.text
    return ""


# â”€â”€ Shared helpers (continued) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _pcm_to_wav(
    pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits: int = 16
) -> bytes:
    """Wrap raw PCM bytes in a minimal WAV container so browsers can play it."""
    import io
    import struct

    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(pcm_data)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))
    buf.write(struct.pack("<H", 1))  # PCM
    buf.write(struct.pack("<H", channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * channels * bits // 8))
    buf.write(struct.pack("<H", channels * bits // 8))
    buf.write(struct.pack("<H", bits))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(pcm_data)))
    buf.write(pcm_data)
    return buf.getvalue()


# â”€â”€ Function nodes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def p2_load_context(node_input) -> Event:
    """
    Parse the input JSON, load brand guidelines, and emit everything to state
    so downstream agents can reference it via {brand_guidelines}, {audience},
    {product_uris}, {asset_uris}.
    """
    raw = _extract_text(node_input)
    try:
        data: dict = json.loads(raw)
    except Exception:
        data = {}

    brand = data.get("brand", "")
    audience = data.get("audience", "")
    products: list[str] = data.get("products", [])
    assets: list[str] = data.get("assets", [])
    logo: str = data.get("logo", "")

    # Load brand guidelines using the same loader as the main pipeline
    brand_guidelines = ""
    if brand:
        try:
            from app.brand_assets import get_asset_loader
            brand_guidelines = get_asset_loader().load_guidelines(brand)
        except Exception as e:
            logger.warning("p2_load_guidelines_failed", brand=brand, error=str(e))

    logger.info(
        "p2_load_context",
        brand=brand,
        audience_len=len(audience),
        n_products=len(products),
        n_assets=len(assets),
        has_logo=bool(logo),
        has_brand_guidelines=bool(brand_guidelines),
    )

    return Event(
        output=raw,  # pass original message through to culture_researcher
        state={
            "p2_brand": brand,
            "p2_audience": audience,
            "p2_product_uris": json.dumps(products),
            "p2_asset_uris": json.dumps(assets),
            "p2_logo_uri": logo,
            "p2_brand_guidelines": brand_guidelines,
        },
    )


async def p2_generate_image(
    ctx: InvocationContext,
    p2_image_prompt: str = "",
    p2_product_uris: str = "",
    p2_asset_uris: str = "",
    p2_logo_uri: str = "",
) -> Event:
    """
    Multimodal image generation â€” no layout constraints, fully creative.

    Sends to Gemini:
      [reference ad images...]  â† style and mood reference
      [product images...]       â† subject to feature
      [prompt]                  â† creative direction from p2_prompt_agent
    """
    from google import genai as _genai

    if not p2_image_prompt:
        logger.warning("p2_generate_image_no_prompt")
        return Event(state={"p2_error": "p2_image_prompt is empty"})

    products: list[str] = json.loads(p2_product_uris) if p2_product_uris else []
    assets: list[str] = json.loads(p2_asset_uris) if p2_asset_uris else []

    contents: list = []

    # Text prompt first â€” Gemini image models need the instruction at the top
    contents.append(p2_image_prompt)

    # Logo â€” place first so the model treats it as a hard brand constraint
    if p2_logo_uri:
        logo_data = _load_bytes(p2_logo_uri)
        if logo_data:
            contents.append(
                "Brand logo below â€” reproduce this logo exactly as shown, "
                "placed in a natural position within the composition. "
                "Do not alter, distort, or reinterpret the logo in any way."
            )
            contents.append(
                types.Part.from_bytes(data=logo_data, mime_type=_mime_for(p2_logo_uri))
            )

    # Reference ads â€” style and mood reference
    for uri in assets:
        data = _load_bytes(uri)
        if data:
            contents.append(
                "Reference ad below â€” a past successful campaign for this brand. "
                "Use it for tonal and visual inspiration only; generate an original image."
            )
            contents.append(types.Part.from_bytes(data=data, mime_type=_mime_for(uri)))

    # Product images â€” the subject to feature
    for uri in products:
        data = _load_bytes(uri)
        if data:
            contents.append(
                "Product image below â€” feature this product prominently in the ad."
            )
            contents.append(types.Part.from_bytes(data=data, mime_type=_mime_for(uri)))

    if not contents:
        logger.warning("p2_generate_image_no_content")
        return Event(state={"p2_error": "No image content could be loaded"})

    try:
        client = _genai.Client()
        resp = client.models.generate_content(
            model=settings.gemini_model_image,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )

        img_data, mime_type = None, "image/png"
        for candidate in resp.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data is not None:
                    img_data = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/png"
                    break
            if img_data:
                break

        if img_data is None:
            raise ValueError("Gemini returned no image data")

        artifact_key = "experiment_image.png"
        await ctx.save_artifact(
            filename=artifact_key,
            artifact=types.Part.from_bytes(data=img_data, mime_type=mime_type),
        )
        logger.info("p2_image_saved", artifact_key=artifact_key)
        return Event(state={"experiment_image_key": artifact_key})

    except Exception as exc:
        logger.warning("p2_generate_image_failed", error=str(exc))
        return Event(state={"p2_error": str(exc)})


# â”€â”€ LLM Agents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

p2_culture_researcher = Agent(
    name="p2_culture_researcher",
    model=CREATIVE_MODEL,
    description="Researches the target demographic using Google Search to surface cultural tensions, media habits, and motivations.",
    instruction="""\
You are a cultural intelligence researcher.

You have been given a target audience and a brand context. Your job is to surface
what's culturally TRUE and INTERESTING about this demographic right now â€” not
what's generically expected of them.

From state:
  Audience:  {p2_audience}
  Brand:     {p2_brand}

Run 3â€“5 Google searches to find:
1. Current cultural tensions or mood in this demographic (news, social trends)
2. Their relationship with food and cooking specifically
3. Any media / creator / platform patterns that reveal how they think and communicate

Write a concise cultural intelligence brief (max 400 words):
- What is this audience FEELING right now?
- What is their relationship to home cooking and food convenience?
- What cultural insight could a brand like {p2_brand} genuinely tap into?
- One sharp "tension" sentence (the creative brief will be built on this).

Be specific. Avoid generic demographic boilerplate.
""",
    # google_search removed — Groq/LiteLLM doesn't support Gemini-native Search tool
    # Culture researcher uses Groq's training knowledge instead of live search
    output_key="p2_culture_research",
    mode="single_turn",
)


p2_brand_summariser = Agent(
    name="p2_brand_summariser",
    model=CREATIVE_MODEL,
    description="Reads the brand guidelines and outputs the 5 most important brand constraints for creative work.",
    instruction="""\
You are a brand strategist. Read the brand guidelines below and distil them into
exactly 5 brand lock points that a creative director MUST respect.

Focus on: colour, typography, tone of voice, logo rules, and the one visual DO NOT
that most commonly gets violated. Be sharp and actionable â€” one sentence each.

Brand guidelines:
{p2_brand_guidelines}

Output format (plain numbered list, no headers):
1. [colour rule]
2. [typography rule]
3. [tone / voice rule]
4. [logo / Pillow rule]
5. [visual DO NOT]
""",
    mode="single_turn",
    output_key="p2_brand_summary",
)


p2_creative_director = Agent(
    name="p2_creative_director",
    model=CREATIVE_MODEL,
    description="Synthesises cultural research and brand locks into a structured Big Idea creative brief.",
    instruction="""\
You are a world-class Creative Director. Your job is to define the BIG IDEA for this campaign â€”
the single, sharp creative concept that will drive every channel adaptation downstream.

Context from state:
  Cultural research: {p2_culture_research}
  Audience:          {p2_audience}
  Brand:             {p2_brand}
  Brand locks (5 points from the brand summariser, in the conversation above).

Default product is spaghetti bolognese. The product is always the hero.

Output a structured creative brief using EXACTLY these four labelled fields:

BIG IDEA: One punchy sentence â€” the concept that makes this campaign memorable.
CULTURAL TENSION: The specific insight from the research this idea exploits.
VISUAL CONCEPT: Two or three sentences describing what the viewer SEEs â€” composition,
  colour logic, graphic treatment, how the product sits in the frame. Be art-director precise.
MOOD: Three adjectives that define the emotional register of the image.

Do not write an image prompt. Do not add any other sections or commentary.
""",
    output_key="p2_big_idea",
    mode="single_turn",
)


p2_prompt_agent = Agent(
    name="p2_prompt_agent",
    model=CREATIVE_MODEL,
    description="Converts the Big Idea creative brief into a precise image generation prompt.",
    instruction="""\
You are a technical prompt engineer for AI image generation. You receive a creative brief
from the Creative Director and translate it into a precise, effective image generation prompt.

Creative brief:
{p2_big_idea}

Brand locks:
{p2_brand_summary}

The prompt will be sent to an image model together with:
  - The product photo (reference image 1)
  - A past successful brand ad (reference image 2)

Your prompt MUST:

1. Open with this exact sentence (do not paraphrase):
   "Using the product image provided, incorporate the product rendered faithfully and
   positioned as the visual anchor of the composition."

2. Include this exact sentence (do not paraphrase):
   "Using the reference ad image provided, draw directly on its colour energy, graphic
   confidence, and compositional logic as the stylistic foundation for this image."

3. Translate the VISUAL CONCEPT from the brief into concrete image-model directions:
   graphic composition, colour fields, negative space, typography treatment.

4. Honour brand colours: green #008641 and yellow #FFDE00 as flat colour panels, not gradients.

5. End with one NEGATIVE sentence: everything the image must not contain.

Keep the prompt under 400 words. Output ONLY the prompt â€” no headers, no explanation.
""",
    output_key="p2_image_prompt",
    mode="single_turn",
)


# â”€â”€ Channel routing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def p2_channel_router(node_input) -> Event:
    """
    Fan out to one or more channel adaptation nodes.
    Route values must match the callable names of the downstream function nodes.
    Hard-coded for now; in future, read from state["p2_channels"].
    """
    routes = [
        "p2_adapt_instagram",
        "p2_adapt_web",
        "p2_adapt_mobile",
        "p2_email_campaign",
        "p2_podcast_ad",
        "p2_reels_video",
    ]
    return Event(
        route=routes,
        state={"p2_channels": json.dumps(routes)},
    )


async def p2_adapt_instagram(
    ctx: InvocationContext,
    p2_image_prompt: str = "",
    p2_big_idea: str = "",
    p2_logo_uri: str = "",
) -> Event:
    """
    Image-to-image adaptation for Instagram square (1:1).
    Loads the key visual artifact and re-renders it via Nano Banana 2
    with square-format composition constraints.
    """
    from google import genai as _genai

    artifact = await ctx.load_artifact("experiment_image.png")
    if (
        artifact is None
        or not hasattr(artifact, "inline_data")
        or artifact.inline_data is None
    ):
        logger.warning("p2_adapt_instagram_no_artifact")
        return Event(state={"p2_error": "experiment_image.png artifact not found"})

    img_bytes = artifact.inline_data.data
    mime_type = artifact.inline_data.mime_type or "image/png"

    channel_instruction = (
        "Using the provided image as your creative reference, adapt it into a "
        "square format (1:1 aspect ratio) social media post. "
        "Recompose the elements into a tight, centred layout where the product dominates the frame. "
        "Remove any landscape negative space; fill the square with bold graphic energy. "
        "Keep text areas minimal. "
        "Preserve the brand colour palette (green #008641, yellow #FFDE00) and the "
        "overall visual identity from the reference image. "
        "Generate the adapted image."
    )

    big_idea_context = f"\n\nCampaign Big Idea:\n{p2_big_idea}" if p2_big_idea else ""
    original_context = (
        f"\n\nKey visual prompt:\n{p2_image_prompt}" if p2_image_prompt else ""
    )

    contents = [channel_instruction + big_idea_context + original_context]

    # Logo first â€” hard brand constraint
    if p2_logo_uri:
        logo_data = _load_bytes(p2_logo_uri)
        if logo_data:
            contents.append(
                "Brand logo below â€” reproduce this logo exactly as shown in the adapted image."
            )
            contents.append(
                types.Part.from_bytes(data=logo_data, mime_type=_mime_for(p2_logo_uri))
            )

    contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))

    try:
        client = _genai.Client()
        resp = client.models.generate_content(
            model=settings.gemini_model_image_adapter,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )

        out_data, out_mime = None, "image/png"
        text_response = ""
        for candidate in resp.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data is not None:
                    out_data = part.inline_data.data
                    out_mime = part.inline_data.mime_type or "image/png"
                    break
                if hasattr(part, "text") and part.text:
                    text_response += part.text
            if out_data:
                break

        if out_data is None:
            logger.warning(
                "p2_adapt_instagram_text_only", model_text=text_response[:500]
            )
            raise ValueError("Nano Banana 2 returned no image data for Instagram")

        artifact_key = "instagram_adapted.png"
        await ctx.save_artifact(
            filename=artifact_key,
            artifact=types.Part.from_bytes(data=out_data, mime_type=out_mime),
        )
        logger.info("p2_instagram_saved", artifact_key=artifact_key)
        return Event(state={"p2_instagram_image_key": artifact_key})

    except Exception as exc:
        logger.warning("p2_adapt_instagram_failed", error=str(exc))
        return Event(state={"p2_error": str(exc)})


async def p2_adapt_web(
    ctx: InvocationContext,
    p2_image_prompt: str = "",
    p2_big_idea: str = "",
    p2_logo_uri: str = "",
) -> Event:
    """
    Image-to-image adaptation for a landscape web banner (1200Ã—628 / 1.91:1).
    Loads the key visual artifact and re-renders it via Nano Banana 2
    with wide-format composition constraints.
    """
    from google import genai as _genai

    artifact = await ctx.load_artifact("experiment_image.png")
    if (
        artifact is None
        or not hasattr(artifact, "inline_data")
        or artifact.inline_data is None
    ):
        logger.warning("p2_adapt_web_no_artifact")
        return Event(state={"p2_error": "experiment_image.png artifact not found"})

    img_bytes = artifact.inline_data.data
    mime_type = artifact.inline_data.mime_type or "image/png"

    channel_instruction = (
        "Using the provided key visual as your creative reference, re-render it as a "
        "landscape web banner (1.91:1 ratio, equivalent to 1200Ã—628 px). "
        "Anchor the product prominently on the left third of the frame, leaving the "
        "right third as a clean, high-contrast area for headline copy. "
        "The composition must read clearly at small sizes (thumbnails ~300 px wide) â€” "
        "no fine background detail, keep it graphic and flat. "
        "Preserve the brand colour palette (green #008641, yellow #FFDE00) and the "
        "overall visual identity from the reference. "
        "Output: a single finished landscape banner image."
    )

    big_idea_context = f"\n\nCampaign Big Idea:\n{p2_big_idea}" if p2_big_idea else ""
    original_context = (
        f"\n\nKey visual prompt:\n{p2_image_prompt}" if p2_image_prompt else ""
    )

    contents = [channel_instruction + big_idea_context + original_context]

    # Logo first â€” hard brand constraint
    if p2_logo_uri:
        logo_data = _load_bytes(p2_logo_uri)
        if logo_data:
            contents.append(
                "Brand logo below â€” reproduce this logo exactly as shown in the adapted image."
            )
            contents.append(
                types.Part.from_bytes(data=logo_data, mime_type=_mime_for(p2_logo_uri))
            )

    contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))

    try:
        client = _genai.Client()
        resp = client.models.generate_content(
            model=settings.gemini_model_image_adapter,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )

        out_data, out_mime = None, "image/png"
        text_response = ""
        for candidate in resp.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data is not None:
                    out_data = part.inline_data.data
                    out_mime = part.inline_data.mime_type or "image/png"
                    break
                if hasattr(part, "text") and part.text:
                    text_response += part.text
            if out_data:
                break

        if out_data is None:
            logger.warning("p2_adapt_web_text_only", model_text=text_response[:500])
            raise ValueError("Nano Banana 2 returned no image data for Web")

        artifact_key = "web_banner_adapted.png"
        await ctx.save_artifact(
            filename=artifact_key,
            artifact=types.Part.from_bytes(data=out_data, mime_type=out_mime),
        )
        logger.info("p2_web_saved", artifact_key=artifact_key)
        return Event(state={"p2_web_image_key": artifact_key})

    except Exception as exc:
        logger.warning("p2_adapt_web_failed", error=str(exc))
        return Event(state={"p2_error": str(exc)})


async def p2_adapt_mobile(
    ctx: InvocationContext,
    p2_image_prompt: str = "",
    p2_big_idea: str = "",
    p2_logo_uri: str = "",
) -> Event:
    """
    Image-to-image adaptation for a mobile banner (320Ã—50 / 6.4:1).
    Strips the composition down to a single bold graphic element â€” product
    centred, almost no background detail â€” readable at thumbnail scale.
    """
    from google import genai as _genai

    artifact = await ctx.load_artifact("experiment_image.png")
    if (
        artifact is None
        or not hasattr(artifact, "inline_data")
        or artifact.inline_data is None
    ):
        logger.warning("p2_adapt_mobile_no_artifact")
        return Event(state={"p2_error": "experiment_image.png artifact not found"})

    img_bytes = artifact.inline_data.data
    mime_type = artifact.inline_data.mime_type or "image/png"

    channel_instruction = (
        "Using the provided image as your creative reference, adapt it into an "
        "extremely wide, short mobile banner format (6.4:1 aspect ratio, equivalent "
        "to 320\u00d750 px â€” the standard mobile leaderboard). "
        "The composition must be brutally simple: one dominant graphic element (the product) "
        "centred or left-anchored, a single flat colour background. The logo and simple graphic design from the reference image. "
        "The image must read as a clear, recognisable graphic at 320 px wide. "
        "Preserve the brand colour palette (green #008641, yellow #FFDE00). "
        "Generate the adapted image."
    )

    big_idea_context = f"\n\nCampaign Big Idea:\n{p2_big_idea}" if p2_big_idea else ""
    original_context = (
        f"\n\nKey visual prompt:\n{p2_image_prompt}" if p2_image_prompt else ""
    )

    contents = [channel_instruction + big_idea_context + original_context]

    # Logo first â€” hard brand constraint
    if p2_logo_uri:
        logo_data = _load_bytes(p2_logo_uri)
        if logo_data:
            contents.append(
                "Brand logo below â€” reproduce this logo exactly as shown in the adapted image."
            )
            contents.append(
                types.Part.from_bytes(data=logo_data, mime_type=_mime_for(p2_logo_uri))
            )

    contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))

    try:
        client = _genai.Client()
        resp = client.models.generate_content(
            model=settings.gemini_model_image_adapter,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )

        out_data, out_mime = None, "image/png"
        text_response = ""
        for candidate in resp.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data is not None:
                    out_data = part.inline_data.data
                    out_mime = part.inline_data.mime_type or "image/png"
                    break
                if hasattr(part, "text") and part.text:
                    text_response += part.text
            if out_data:
                break

        if out_data is None:
            logger.warning("p2_adapt_mobile_text_only", model_text=text_response[:500])
            raise ValueError("Nano Banana 2 returned no image data for mobile banner")

        artifact_key = "mobile_banner_adapted.png"
        await ctx.save_artifact(
            filename=artifact_key,
            artifact=types.Part.from_bytes(data=out_data, mime_type=out_mime),
        )
        logger.info("p2_mobile_saved", artifact_key=artifact_key)
        return Event(state={"p2_mobile_image_key": artifact_key})

    except Exception as exc:
        logger.warning("p2_adapt_mobile_failed", error=str(exc))
        return Event(state={"p2_error": str(exc)})


# â”€â”€ Content channel agents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

p2_email_campaign = Agent(
    name="p2_email_campaign",
    model=CREATIVE_MODEL,
    description="Translates the Big Idea into a campaign email.",
    instruction="""\
You are a direct-response email copywriter. Translate the campaign Big Idea into a
concise marketing email for the target audience.

Big Idea:
{p2_big_idea}

Audience: {p2_audience}
Brand:    {p2_brand}

Write a complete campaign email with:
- SUBJECT LINE: punchy, curiosity-driving, under 50 characters
- PREVIEW TEXT: one sentence that complements the subject line
- BODY: 3 short paragraphs â€” hook, product benefit, call to action
- CTA BUTTON TEXT: 4 words or fewer

Tone must match the Big Idea's MOOD. Brand voice is warm, confident, food-forward.
No filler phrases. No generic sign-offs. Output only the email, labelled with the
field names above.
""",
    output_key="p2_email_content",
    mode="single_turn",
)


async def p2_podcast_tts(
    ctx: InvocationContext,
    p2_podcast_script: str = "",
) -> Event:
    """
    Renders p2_podcast_script to audio via Gemini TTS.
    Stage directions like [PAUSE] / [BEAT] are stripped before synthesis.
    Gemini TTS returns raw PCM; we wrap it in a WAV header for browser playback.
    Saves result as podcast_ad.wav.
    """
    import re

    from google import genai as _genai

    if not p2_podcast_script:
        logger.warning("p2_podcast_tts_no_script")
        return Event(state={"p2_podcast_tts_error": "p2_podcast_script is empty"})

    # Extract spoken text â€” drop the SCRIPT: label, READ TIME: trailer,
    # and all stage directions in square brackets
    script_text = p2_podcast_script
    if "SCRIPT:" in script_text:
        script_text = script_text.split("SCRIPT:", 1)[-1]
    if "READ TIME:" in script_text:
        script_text = script_text.split("READ TIME:", 1)[0]
    script_text = re.sub(r"\[.*?\]", "", script_text).strip()

    try:
        client = _genai.Client()
        resp = client.models.generate_content(
            model=settings.gemini_model_tts,
            contents=script_text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Charon",
                        )
                    )
                ),
            ),
        )

        audio_part = None
        for candidate in resp.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data is not None:
                    audio_part = part.inline_data
                    break
            if audio_part:
                break

        if audio_part is None:
            raise ValueError("Gemini TTS returned no audio data")

        raw_data = audio_part.data
        mime_type = audio_part.mime_type or ""

        # Wrap raw PCM in a WAV container so the browser <audio> tag can play it
        if "pcm" in mime_type.lower() or "l16" in mime_type.lower():
            rate_match = re.search(r"rate=(\d+)", mime_type)
            sample_rate = int(rate_match.group(1)) if rate_match else 24000
            audio_bytes = _pcm_to_wav(raw_data, sample_rate=sample_rate)
            save_mime = "audio/wav"
        else:
            audio_bytes = raw_data
            save_mime = mime_type or "audio/wav"

        artifact_key = "podcast_ad.wav"
        await ctx.save_artifact(
            filename=artifact_key,
            artifact=types.Part.from_bytes(data=audio_bytes, mime_type=save_mime),
        )
        logger.info("p2_podcast_tts_saved", artifact_key=artifact_key, mime=save_mime)
        return Event(state={"p2_podcast_audio_key": artifact_key})

    except Exception as exc:
        logger.warning("p2_podcast_tts_failed", error=str(exc))
        return Event(state={"p2_podcast_tts_error": str(exc)})


p2_podcast_ad = Agent(
    name="p2_podcast_ad",
    model=CREATIVE_MODEL,
    description="Translates the Big Idea into a 30-second podcast ad script.",
    instruction="""\
You are an audio copywriter specialising in podcast advertising. Translate the
campaign Big Idea into a 30-second host-read podcast ad script (~75 words spoken).

Big Idea:
{p2_big_idea}

Audience: {p2_audience}
Brand:    {p2_brand}

The script must:
- Open with a relatable hook that reflects the CULTURAL TENSION from the Big Idea
- Naturally introduce the product as the solution (not a hard sell)
- End with one clear verbal CTA
- Sound conversational â€” written for the ear, not the eye
- Include a [PAUSE] or [BEAT] note where the host should breathe for emphasis

Label the output: SCRIPT: followed by the script text.
Below that, add READ TIME: estimated seconds at natural speaking pace.
""",
    output_key="p2_podcast_script",
    mode="single_turn",
)


p2_reels_video = Agent(
    name="p2_reels_video",
    model=CREATIVE_MODEL,
    description="Translates the Big Idea into an 8-second reels/short-form video storyboard.",
    instruction="""\
You are a short-form video director. Translate the campaign Big Idea into a
storyboard and script for an 8-second social video (Reels / Shorts format, 9:16).

Big Idea:
{p2_big_idea}

Audience: {p2_audience}
Brand:    {p2_brand}

Structure the output as exactly 3 beats, each timed to fit within 8 seconds total:

BEAT 1 (0â€“3s): VISUAL â€” what the viewer sees. AUDIO â€” music/SFX/VO line if any.
BEAT 2 (3â€“6s): VISUAL â€” the product moment. AUDIO â€” key message or sound design.
BEAT 3 (6â€“8s): VISUAL â€” brand lock-up / CTA. AUDIO â€” sign-off or music sting.

Then add:
OVERALL MOOD: one sentence
ON-SCREEN TEXT: any supers or captions, listed per beat

Be concrete and directable â€” a production team should be able to shoot from this.
""",
    output_key="p2_reels_storyboard",
    mode="single_turn",
)


# â”€â”€ Campaign report (join node) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def p2_campaign_report(
    ctx: InvocationContext,
    p2_brand: str = "",
    p2_big_idea: str = "",
    p2_email_content: str = "",
    p2_podcast_script: str = "",
    p2_reels_storyboard: str = "",
) -> Event:
    """
    Join node â€” waits for all six channel branches, then aggregates every
    output into a self-contained HTML report saved as an artifact.

    Images are embedded as base64 data URIs so the file works without any
    external dependencies (including with InMemoryArtifactService).
    """
    import base64

    async def _img_tag(key: str, label: str, extra_style: str = "") -> str:
        artifact = await ctx.load_artifact(key)
        if (
            artifact is None
            or not hasattr(artifact, "inline_data")
            or artifact.inline_data is None
        ):
            return f'<p class="missing">âš  {label} not available</p>'
        mime = artifact.inline_data.mime_type or "image/png"
        b64 = base64.b64encode(artifact.inline_data.data).decode()
        return (
            f"<figure>"
            f'<img src="data:{mime};base64,{b64}" alt="{label}" style="{extra_style}">'
            f"<figcaption>{label}</figcaption>"
            f"</figure>"
        )

    async def _audio_tag(key: str, label: str) -> str:
        artifact = await ctx.load_artifact(key)
        if (
            artifact is None
            or not hasattr(artifact, "inline_data")
            or artifact.inline_data is None
        ):
            return f'<p class="missing">âš  {label} not available</p>'
        mime = artifact.inline_data.mime_type or "audio/wav"
        b64 = base64.b64encode(artifact.inline_data.data).decode()
        return (
            f"<figure>"
            f"<figcaption>{label}</figcaption>"
            f'<audio controls src="data:{mime};base64,{b64}"></audio>'
            f"</figure>"
        )

    kv_tag = await _img_tag("experiment_image.png", "Key Visual", "max-height:500px;")
    instagram_tag = await _img_tag(
        "instagram_adapted.png", "Instagram (1:1)", "max-height:360px;"
    )
    web_tag = await _img_tag(
        "web_banner_adapted.png", "Web Banner (1.91:1)", "max-height:240px;"
    )
    mobile_tag = await _img_tag(
        "mobile_banner_adapted.png", "Mobile Banner (6.4:1)", "max-height:120px;"
    )
    podcast_audio_tag = await _audio_tag("podcast_ad.wav", "Podcast Ad (30s)")

    def _section(title: str, content: str, tag: str = "pre") -> str:
        safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<section><h2>{title}</h2><{tag} class="copy">{safe}</{tag}></section>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{p2_brand} Campaign Report</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f5f5f0; color: #1a1a1a; padding: 2rem; }}
  h1   {{ font-size: 2rem; margin-bottom: 0.25rem; color: #008641; }}
  h2   {{ font-size: 1.1rem; text-transform: uppercase; letter-spacing: .08em;
          color: #008641; border-bottom: 2px solid #FFDE00; padding-bottom: .25rem;
          margin-bottom: 1rem; }}
  section {{ background: #fff; border-radius: 8px; padding: 1.5rem;
             margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .images  {{ display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: flex-end; }}
  figure   {{ display: flex; flex-direction: column; align-items: center; gap: .5rem; }}
  figcaption {{ font-size: .8rem; color: #666; }}
  img      {{ border-radius: 4px; border: 1px solid #e0e0e0; }}
  audio    {{ width: 100%; margin-top: .5rem; }}
  pre.copy {{ white-space: pre-wrap; font-size: .9rem; line-height: 1.6;
              background: #fafafa; border-radius: 4px; padding: 1rem;
              border-left: 3px solid #FFDE00; }}
  .missing {{ color: #c00; font-style: italic; }}
  .meta    {{ font-size: .85rem; color: #666; margin-top: .25rem; }}
</style>
</head>
<body>
<h1>{p2_brand} Campaign Report</h1>
<p class="meta">Generated by experiment_pipeline Â· {p2_brand}</p>

{_section("Big Idea", p2_big_idea)}

<section>
  <h2>Visual Outputs</h2>
  <div class="images">
    {kv_tag}
    {instagram_tag}
    {web_tag}
    {mobile_tag}
  </div>
</section>

{_section("Email Campaign", p2_email_content)}

<section>
  <h2>Podcast Ad</h2>
  {podcast_audio_tag}
  <details style="margin-top:1rem">
    <summary style="cursor:pointer;font-size:.85rem;color:#666">Show script</summary>
    <pre class="copy">{p2_podcast_script.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</pre>
  </details>
</section>

{_section("Reels / Short-form Video Storyboard", p2_reels_storyboard)}

</body>
</html>"""

    artifact_key = "campaign_report.html"
    await ctx.save_artifact(
        filename=artifact_key,
        artifact=types.Part.from_bytes(
            data=html.encode("utf-8"),
            mime_type="text/html",
        ),
    )
    logger.info("p2_campaign_report_saved", artifact_key=artifact_key)
    return Event(state={"p2_report_key": artifact_key})


# â”€â”€ Pipeline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

experiment_pipeline = Workflow(
    name="experiment_pipeline",
    edges=[
        # Linear creative pipeline â†’ key visual â†’ channel router
        (
            "START",
            p2_load_context,
            p2_culture_researcher,
            p2_brand_summariser,
            p2_creative_director,
            p2_prompt_agent,
            p2_generate_image,
            p2_channel_router,
        ),
        # Fan-out: router routes to all channel nodes in parallel
        (p2_channel_router, p2_adapt_instagram),
        (p2_channel_router, p2_adapt_web),
        (p2_channel_router, p2_adapt_mobile),
        (p2_channel_router, p2_email_campaign),
        (p2_channel_router, p2_podcast_ad),
        (p2_channel_router, p2_reels_video),
        # Podcast branch: script â†’ TTS render
        (p2_podcast_ad, p2_podcast_tts),
        # Fan-in: all branches converge on the report node
        (p2_adapt_instagram, p2_campaign_report),
        (p2_adapt_web, p2_campaign_report),
        (p2_adapt_mobile, p2_campaign_report),
        (p2_email_campaign, p2_campaign_report),
        (p2_podcast_tts, p2_campaign_report),
        (p2_reels_video, p2_campaign_report),
    ],
)

# ADK web entry point â€” expose as root_agent so `adk web .` picks it up
# when running from a directory that has this as the active agent.py target.
root_agent = experiment_pipeline
