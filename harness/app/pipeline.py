"""
pipeline.py — ADK 2.0 Workflow DAG for CampaignOS.

Defines the root_agent (a Workflow) that orchestrates the full campaign
pipeline as a directed acyclic graph.

DAG shape:
  START
    └── [fn] load_brand_context
          └── briefing_agent
                └── culture_analyst   ← Google Search grounding (multi-turn)
                      └── culture_formatter   ← structures research into CultureAnalysis
                            └── creative_director   ← Big Idea + CreativeStrategy
                                  ├── kv_generator_1 → kv_image_agent_1 ─┐
                                  └── kv_generator_2 → kv_image_agent_2 ─┤
                                                                           ├── [fn] aggregate_kv_concepts
                                                                           │         └── kv_ranker
                                                                           │               └── hitl_kv_selection
                                                                           │                     └── channel_router
                                                                           │                           └── content_agent
                                                                           │                                 └── execution_agent
                                                                           │                                       └── aggregation_agent
                                                                           │                                             └── performance_agent

Function nodes (deterministic, zero LLM cost):
  load_brand_context    — loads brand guidelines, product map, benchmark data
  aggregate_kv_concepts — fan-in: merges both enriched concepts into kv_concepts_all

HITL gates (hitl_brief_approval removed for development):
  hitl_kv_selection    — waits for human selection of a KV concept (1 of 2)
"""

from google.adk import Workflow
from google.adk.workflow import JoinNode

from app.agents import (
    briefing_agent,
    culture_analyst,
    culture_formatter,
    creative_director,
    kv_generator_1,
    kv_generator_2,
    kv_image_agent_1,
    kv_image_agent_2,
    kv_ranker,
    hitl_kv_selection,
    channel_router,
    content_agent,
    execution_agent,
    aggregation_agent,
    performance_agent,
)
from app.nodes import aggregate_kv_concepts, load_brand_context

# Fan-in join node: waits for both KV image agents before aggregation
kv_join_node = JoinNode(name="kv_join_node")

root_agent = Workflow(
    name  = "campaignos_pipeline",
    edges = [
        # ── Entry: load brand data → brief → cultural intelligence → creative strategy ──
        ("START", load_brand_context, briefing_agent,
         culture_analyst, culture_formatter, creative_director),

        # ── KV fan-out: creative_director → 2 parallel art directors ───────────────────────
        (creative_director, kv_generator_1),
        (creative_director, kv_generator_2),

        # ── Image generation: art director concept → Gemini image model ────────────────────
        (kv_generator_1, kv_image_agent_1),
        (kv_generator_2, kv_image_agent_2),

        # ── KV fan-in via JoinNode: both image agents must complete ─────────────────────────
        (kv_image_agent_1, kv_join_node),
        (kv_image_agent_2, kv_join_node),

        # ── Aggregate fn → ranker → HITL → content production pipeline ──────────────────────
        (kv_join_node, aggregate_kv_concepts, kv_ranker, hitl_kv_selection,
         channel_router, content_agent, execution_agent, aggregation_agent, performance_agent),
    ],
)
