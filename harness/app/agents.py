"""
agents.py — ADK 2.0 module-level agent instances for CampaignOS.

All agents are defined as module-level constants (not factory functions).
The Workflow DAG in pipeline.py references these instances directly.

Agent roster:
  briefing_agent        — validates and enriches the campaign brief
  hitl_brief_approval   — HITL gate: human sign-off on the brief
  culture_analyst       — researches cultural landscape via Google Search
  culture_formatter     — structures raw research into CultureAnalysis JSON
  creative_director     — synthesises brief + culture into Big Idea + CreativeStrategy
  kv_generator_1..2     — parallel KV art directors (fan-out), each with a distinct
                          composition lens; produce KVConcept with Nano Banana Pro prompt
  kv_image_agent_1..2   — parallel image generation; each calls generate_and_save_kv_image
                          tool → ADK artifact service (InMemory dev / GCS prod)
  kv_ranker             — evaluates both KV concepts and selects the stronger one (fan-in)
  hitl_kv_selection     — HITL gate: human selects from 2 KV concepts
  channel_router        — maps channels to execution tasks
  content_agent         — generates content for all channels
  execution_agent       — stub activation layer
  aggregation_agent     — consolidates all pipeline outputs
  performance_agent     — generates performance tracking framework
"""

from google.adk import Agent
from google.adk.tools import google_search

from app.config import get_settings
from app.models import BriefingContext, CultureAnalysis
from app.instructions import (
    BRIEFING_AGENT_INSTRUCTIONS,
    HITL_BRIEF_APPROVAL_INSTRUCTIONS,
    CULTURE_ANALYST_INSTRUCTIONS,
    CULTURE_FORMATTER_INSTRUCTIONS,
    CREATIVE_DIRECTOR_INSTRUCTIONS,
    KV_GENERATOR_INSTRUCTIONS,
    KV_IMAGE_AGENT_INSTRUCTIONS,
    KV_RANKER_INSTRUCTIONS,
    HITL_KV_SELECTION_INSTRUCTIONS,
    CHANNEL_ROUTER_INSTRUCTIONS,
    CONTENT_AGENT_INSTRUCTIONS,
    EXECUTION_AGENT_INSTRUCTIONS,
    AGGREGATION_AGENT_INSTRUCTIONS,
    PERFORMANCE_AGENT_INSTRUCTIONS,
)
from app.tools import save_brief_output, generate_and_save_kv_image

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

# ── CULTURAL INTELLIGENCE STAGE ───────────────────────────────────────────

culture_analyst = Agent(
    name        = "culture_analyst",
    model       = settings.gemini_model_reasoning,
    description = "Researches the cultural landscape surrounding the campaign using live Google Search.",
    instruction = CULTURE_ANALYST_INSTRUCTIONS,
    tools       = [google_search],
    # NOT single_turn — needs multiple tool calls across several searches
)

culture_formatter = Agent(
    name          = "culture_formatter",
    model         = settings.gemini_model_reasoning,
    description   = "Structures raw cultural research into a CultureAnalysis object.",
    instruction   = CULTURE_FORMATTER_INSTRUCTIONS,
    output_schema = CultureAnalysis,
    output_key    = "culture_analysis",
    mode          = "single_turn",
)

creative_director = Agent(
    name        = "creative_director",
    model       = settings.gemini_model_reasoning,
    description = "Synthesises brief, cultural intelligence, and brand guidelines into a Big Idea and CreativeStrategy.",
    instruction = CREATIVE_DIRECTOR_INSTRUCTIONS,
    output_key  = "creative_strategy",
    mode        = "single_turn",
)

# ── KV GENERATION STAGE (fan-out) ─────────────────────────────────────────

_KV_COMPOSITION_LENSES = [
    (
        "product-centred composition",
        "The product is the unambiguous visual subject. It occupies a dominant, "
        "commanding position. Background, props, and lighting exist only to flatter "
        "and desire-ify the product. Think elevated editorial product photography — "
        "the product earns the viewer's full attention from the first frame.",
    ),
    (
        "scene-led composition",
        "The scene, emotion, or human moment captures the viewer first. The product "
        "is present but earns its place within the world being depicted — it is the "
        "natural, inevitable resolution of the scene rather than its imposed subject. "
        "Think lifestyle storytelling where the product is the rewarding detail.",
    ),
]

kv_generator_1 = Agent(
    name        = "kv_generator_1",
    model       = settings.gemini_model_reasoning,
    description = "KV Art Director 1: product-centred composition lens.",
    instruction = KV_GENERATOR_INSTRUCTIONS(
        1,
        _KV_COMPOSITION_LENSES[0][0],
        _KV_COMPOSITION_LENSES[0][1],
    ),
    output_key  = "kv_concept_1",
    mode        = "single_turn",
)

kv_generator_2 = Agent(
    name        = "kv_generator_2",
    model       = settings.gemini_model_reasoning,
    description = "KV Art Director 2: scene-led composition lens.",
    instruction = KV_GENERATOR_INSTRUCTIONS(
        2,
        _KV_COMPOSITION_LENSES[1][0],
        _KV_COMPOSITION_LENSES[1][1],
    ),
    output_key  = "kv_concept_2",
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


# ── KV RANKING & SELECTION (fan-in) ──────────────────────────────────────

kv_ranker = Agent(
    name        = "kv_ranker",
    model       = settings.gemini_model_reasoning,
    description = "Evaluates both KV concepts and selects the stronger composition for HITL review.",
    instruction = KV_RANKER_INSTRUCTIONS,
    mode        = "single_turn",
)

hitl_kv_selection = Agent(
    name        = "hitl_kv_selection",
    model       = settings.gemini_model_reasoning,
    description = "HITL gate: presents both KV concepts to the marketing team for final selection.",
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
