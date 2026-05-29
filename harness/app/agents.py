"""
agents.py — ADK 2.0 module-level agent instances for CampaignOS.

All agents are defined as module-level constants (not factory functions).
The Workflow DAG in pipeline.py references these instances directly.

Agent roster:
  briefing_agent        — validates and enriches the campaign brief
  hitl_brief_approval   — HITL gate: human sign-off on the brief
  strategy_agent        — builds campaign strategy from approved brief
  kv_generator_1..4     — parallel KV concept generators (fan-out)
  kv_image_agent_1..4   — parallel image generation; each calls generate_and_save_kv_image
                          tool → ADK artifact service (InMemory dev / GCS prod)
  kv_ranker             — ranks the 4 KV concepts (fan-in)
  hitl_kv_selection     — HITL gate: human selects KV concept
  channel_router        — maps channels to execution tasks
  content_agent         — generates content for all channels
  execution_agent       — stub activation layer
  aggregation_agent     — consolidates all pipeline outputs
  performance_agent     — generates performance tracking framework
"""

from google.adk import Agent

from app.config import get_settings
from app.models import BriefingContext
from app.instructions import (
    BRIEFING_AGENT_INSTRUCTIONS,
    HITL_BRIEF_APPROVAL_INSTRUCTIONS,
    STRATEGY_AGENT_INSTRUCTIONS,
    KV_GENERATOR_INSTRUCTIONS,
    KV_IMAGE_AGENT_INSTRUCTIONS,
    COPY_RENDERER_INSTRUCTIONS,
    KV_SWAP_AGENT_INSTRUCTIONS,
    KV_RANKER_INSTRUCTIONS,
    HITL_KV_SELECTION_INSTRUCTIONS,
    CHANNEL_ROUTER_INSTRUCTIONS,
    CONTENT_AGENT_INSTRUCTIONS,
    EXECUTION_AGENT_INSTRUCTIONS,
    AGGREGATION_AGENT_INSTRUCTIONS,
    PERFORMANCE_AGENT_INSTRUCTIONS,
)
from app.tools import save_brief_output, generate_and_save_kv_image, render_copy_overlay, refine_kv_image

settings = get_settings()

# ── BRIEFING STAGE ────────────────────────────────────────────────────────

briefing_agent = Agent(
    name         = "briefing_agent",
    model        = settings.gemini_model_reasoning,
    description  = "Validates and enriches the incoming campaign brief, scores the Fan Truth, flags KPIs, and produces a MachineBrief.",
    instruction  = BRIEFING_AGENT_INSTRUCTIONS,
    input_schema = BriefingContext,
    tools        = [save_brief_output],
    output_key   = "machine_brief",   # always captures LLM output to state
    mode         = "single_turn",
)

hitl_brief_approval = Agent(
    name        = "hitl_brief_approval",
    model       = settings.gemini_model_reasoning,
    description = "HITL gate: presents the validated brief to the marketing team for approval before strategy begins.",
    instruction = HITL_BRIEF_APPROVAL_INSTRUCTIONS,
)

# ── STRATEGY STAGE ────────────────────────────────────────────────────────

strategy_agent = Agent(
    name        = "strategy_agent",
    model       = settings.gemini_model_reasoning,
    description = "Builds the full campaign strategy (framework, hero message, channel priorities, messaging pillars) from the approved brief.",
    instruction = STRATEGY_AGENT_INSTRUCTIONS,
    mode        = "single_turn",
)

# ── KV GENERATION STAGE (fan-out) ─────────────────────────────────────────

_KV_ANGLES = [
    ("emotional connection",
     "Focus on genuine, small moments of joy that fans feel with this brand and product. "
     "Not aspirational — real, everyday warmth."),
    ("product hero",
     "Put the product front and centre. Lead with sensory appeal — texture, colour, smell, taste. "
     "The product is the hero; everything else is set dressing."),
    ("cultural moment",
     "Tap into a shared cultural tension, trend, or conversation the target audience cares about. "
     "The brand earns its place in that conversation through the product."),
    ("audience truth",
     "Start from a specific, true observation about what the target audience does, believes, or feels. "
     "The brand and product are the reward for that truth."),
]

kv_generator_1 = Agent(
    name        = "kv_generator_1",
    model       = settings.gemini_model_image,
    description = "Generates a KV concept from the emotional connection angle.",
    instruction = KV_GENERATOR_INSTRUCTIONS(1, _KV_ANGLES[0][0], _KV_ANGLES[0][1]),
    output_key  = "kv_concept_1",
    mode        = "single_turn",
)

kv_generator_2 = Agent(
    name        = "kv_generator_2",
    model       = settings.gemini_model_image,
    description = "Generates a KV concept from the product hero angle.",
    instruction = KV_GENERATOR_INSTRUCTIONS(2, _KV_ANGLES[1][0], _KV_ANGLES[1][1]),
    output_key  = "kv_concept_2",
    mode        = "single_turn",
)

kv_generator_3 = Agent(
    name        = "kv_generator_3",
    model       = settings.gemini_model_image,
    description = "Generates a KV concept from the cultural moment angle.",
    instruction = KV_GENERATOR_INSTRUCTIONS(3, _KV_ANGLES[2][0], _KV_ANGLES[2][1]),
    output_key  = "kv_concept_3",
    mode        = "single_turn",
)

kv_generator_4 = Agent(
    name        = "kv_generator_4",
    model       = settings.gemini_model_image,
    description = "Generates a KV concept from the audience truth angle.",
    instruction = KV_GENERATOR_INSTRUCTIONS(4, _KV_ANGLES[3][0], _KV_ANGLES[3][1]),
    output_key  = "kv_concept_4",
    mode        = "single_turn",
)

# ── KV IMAGE GENERATION STAGE (parallel, one per generator) ─────────────

kv_image_agent_1 = Agent(
    name        = "kv_image_agent_1",
    model       = settings.gemini_model_reasoning,
    description = "Generates and saves the hero image for KV concept 1 via the ADK artifact service.",
    instruction = KV_IMAGE_AGENT_INSTRUCTIONS(1),
    tools       = [generate_and_save_kv_image],
    output_key  = "kv_concept_1",   # overwrites state with enriched concept JSON
    mode        = "single_turn",
)

kv_image_agent_2 = Agent(
    name        = "kv_image_agent_2",
    model       = settings.gemini_model_reasoning,
    description = "Generates and saves the hero image for KV concept 2 via the ADK artifact service.",
    instruction = KV_IMAGE_AGENT_INSTRUCTIONS(2),
    tools       = [generate_and_save_kv_image],
    output_key  = "kv_concept_2",
    mode        = "single_turn",
)

kv_image_agent_3 = Agent(
    name        = "kv_image_agent_3",
    model       = settings.gemini_model_reasoning,
    description = "Generates and saves the hero image for KV concept 3 via the ADK artifact service.",
    instruction = KV_IMAGE_AGENT_INSTRUCTIONS(3),
    tools       = [generate_and_save_kv_image],
    output_key  = "kv_concept_3",
    mode        = "single_turn",
)

kv_image_agent_4 = Agent(
    name        = "kv_image_agent_4",
    model       = settings.gemini_model_reasoning,
    description = "Generates and saves the hero image for KV concept 4 via the ADK artifact service.",
    instruction = KV_IMAGE_AGENT_INSTRUCTIONS(4),
    tools       = [generate_and_save_kv_image],
    output_key  = "kv_concept_4",
    mode        = "single_turn",
)


# ── COPY RENDERER STAGE (Pillow text reference overlay) ──────────────────
# Each copy_renderer_agent_N loads kv_image_{N}.png, overlays typographic
# copy (headline, brand name, tagline) as a flat Pillow reference layer,
# and saves kv_ref_{N}.png. The result is a pixel-precise stencil for the
# subsequent swap agent — showing exact text position and scale.

copy_renderer_agent_1 = Agent(
    name        = "copy_renderer_agent_1",
    model       = settings.gemini_model_reasoning,
    description = "Overlays typographic reference copy onto KV 1 background using Pillow.",
    instruction = COPY_RENDERER_INSTRUCTIONS(1),
    tools       = [render_copy_overlay],
    mode        = "single_turn",
)

copy_renderer_agent_2 = Agent(
    name        = "copy_renderer_agent_2",
    model       = settings.gemini_model_reasoning,
    description = "Overlays typographic reference copy onto KV 2 background using Pillow.",
    instruction = COPY_RENDERER_INSTRUCTIONS(2),
    tools       = [render_copy_overlay],
    mode        = "single_turn",
)

copy_renderer_agent_3 = Agent(
    name        = "copy_renderer_agent_3",
    model       = settings.gemini_model_reasoning,
    description = "Overlays typographic reference copy onto KV 3 background using Pillow.",
    instruction = COPY_RENDERER_INSTRUCTIONS(3),
    tools       = [render_copy_overlay],
    mode        = "single_turn",
)

copy_renderer_agent_4 = Agent(
    name        = "copy_renderer_agent_4",
    model       = settings.gemini_model_reasoning,
    description = "Overlays typographic reference copy onto KV 4 background using Pillow.",
    instruction = COPY_RENDERER_INSTRUCTIONS(4),
    tools       = [render_copy_overlay],
    mode        = "single_turn",
)


# ── KV SWAP STAGE (Nano Banana 2 image-to-image bake) ────────────────────
# Each kv_swap_agent_N loads kv_ref_{N}.png, composes a scene-aware
# refinement prompt from the KVConcept's visual_direction and
# typography_guidance, and calls refine_kv_image to "bake" the flat
# Pillow text into the scene with correct lighting/shadows/materials.
# The finished key visual is saved as kv_final_{N}.png.

kv_swap_agent_1 = Agent(
    name        = "kv_swap_agent_1",
    model       = settings.gemini_model_reasoning,
    description = "Bakes typographic copy into KV 1 scene via Nano Banana 2 image-to-image.",
    instruction = KV_SWAP_AGENT_INSTRUCTIONS(1),
    tools       = [refine_kv_image],
    output_key  = "kv_concept_1",   # enriches concept with final image_artifact_key
    mode        = "single_turn",
)

kv_swap_agent_2 = Agent(
    name        = "kv_swap_agent_2",
    model       = settings.gemini_model_reasoning,
    description = "Bakes typographic copy into KV 2 scene via Nano Banana 2 image-to-image.",
    instruction = KV_SWAP_AGENT_INSTRUCTIONS(2),
    tools       = [refine_kv_image],
    output_key  = "kv_concept_2",
    mode        = "single_turn",
)

kv_swap_agent_3 = Agent(
    name        = "kv_swap_agent_3",
    model       = settings.gemini_model_reasoning,
    description = "Bakes typographic copy into KV 3 scene via Nano Banana 2 image-to-image.",
    instruction = KV_SWAP_AGENT_INSTRUCTIONS(3),
    tools       = [refine_kv_image],
    output_key  = "kv_concept_3",
    mode        = "single_turn",
)

kv_swap_agent_4 = Agent(
    name        = "kv_swap_agent_4",
    model       = settings.gemini_model_reasoning,
    description = "Bakes typographic copy into KV 4 scene via Nano Banana 2 image-to-image.",
    instruction = KV_SWAP_AGENT_INSTRUCTIONS(4),
    tools       = [refine_kv_image],
    output_key  = "kv_concept_4",
    mode        = "single_turn",
)


# ── KV RANKING & SELECTION (fan-in) ──────────────────────────────────────

kv_ranker = Agent(
    name        = "kv_ranker",
    model       = settings.gemini_model_reasoning,
    description = "Evaluates all four KV concepts and selects the strongest one for HITL review.",
    instruction = KV_RANKER_INSTRUCTIONS,
    mode        = "single_turn",
)

hitl_kv_selection = Agent(
    name        = "hitl_kv_selection",
    model       = settings.gemini_model_reasoning,
    description = "HITL gate: presents all four KV concepts to the marketing team for final selection.",
    instruction = HITL_KV_SELECTION_INSTRUCTIONS,
)

# ── CONTENT PRODUCTION STAGE ──────────────────────────────────────────────

channel_router = Agent(
    name        = "channel_router",
    model       = settings.gemini_model_reasoning,
    description = "Maps the approved KV concept and channel list to a ChannelPlan with per-channel format specs.",
    instruction = CHANNEL_ROUTER_INSTRUCTIONS,
    mode        = "single_turn",
)

content_agent = Agent(
    name        = "content_agent",
    model       = settings.gemini_model_reasoning,
    description = "Generates production-ready copy and image prompts for every channel in the ChannelPlan.",
    instruction = CONTENT_AGENT_INSTRUCTIONS,
    mode        = "single_turn",
)

# ── EXECUTION & REPORTING STAGE ───────────────────────────────────────────

execution_agent = Agent(
    name        = "execution_agent",
    model       = settings.gemini_model_reasoning,
    description = "Stub activation layer — produces execution notes per channel ready for platform API integration.",
    instruction = EXECUTION_AGENT_INSTRUCTIONS,
    mode        = "single_turn",
)

aggregation_agent = Agent(
    name        = "aggregation_agent",
    model       = settings.gemini_model_reasoning,
    description = "Consolidates all pipeline outputs into a single CampaignAggregation record.",
    instruction = AGGREGATION_AGENT_INSTRUCTIONS,
    mode        = "single_turn",
)

performance_agent = Agent(
    name        = "performance_agent",
    model       = settings.gemini_model_reasoning,
    description = "Generates the initial KPI tracking framework and first-48h monitoring plan.",
    instruction = PERFORMANCE_AGENT_INSTRUCTIONS,
    mode        = "single_turn",
)
