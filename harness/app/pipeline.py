"""
pipeline.py — ADK 2.0 Workflow DAG for CampaignOS.

Defines the root_agent (a Workflow) that orchestrates the full campaign
pipeline as a directed acyclic graph.

DAG shape:
  START
    └── [fn] load_brand_context        ← loads all brand data (zero LLM calls)
          └── briefing_agent            ← pure reasoning; 1 tool only: save_brief_output
                └── hitl_brief_approval
                      └── strategy_agent
                            ├── kv_generator_1 → kv_image_agent_1 → copy_renderer_1 → kv_swap_1 ─┐
                            ├── kv_generator_2 → kv_image_agent_2 → copy_renderer_2 → kv_swap_2  ├── [fn] aggregate_kv_concepts
                            ├── kv_generator_3 → kv_image_agent_3 → copy_renderer_3 → kv_swap_3  │         └── kv_ranker
                            └── kv_generator_4 → kv_image_agent_4 → copy_renderer_4 → kv_swap_4 ─┘               └── hitl_kv_selection
                                                                                                                          └── channel_router
                                                                                                                                └── content_agent
                                                                                                                                      └── execution_agent
                                                                                                                                            └── aggregation_agent
                                                                                                                                                  └── performance_agent

KV image pipeline per branch (3 stages):
  Stage 1 — kv_image_agent_N  : Gemini text-to-image with product photos as
                                  multi-modal inputs → kv_image_{N}.png
  Stage 2 — copy_renderer_N   : Pillow flat text overlay (headline, brand name,
                                  tagline) → positional stencil kv_ref_{N}.png
  Stage 3 — kv_swap_agent_N   : Nano Banana 2 image-to-image; re-renders the
                                  flat Pillow text into the scene with correct
                                  lighting, shadows, material integration
                                  → finished key visual kv_final_{N}.png

Function nodes (deterministic, zero LLM cost):
  load_brand_context    — loads brand guidelines, product map, benchmark data
  aggregate_kv_concepts — fan-in: merges all 4 enriched concepts into kv_concepts_all

HITL gates:
  hitl_brief_approval  — waits for human approval of the validated brief
  hitl_kv_selection    — waits for human selection of a KV concept
"""

from google.adk import Workflow
from google.adk.workflow import JoinNode

from app.agents import (
    briefing_agent,
    hitl_brief_approval,
    strategy_agent,
    kv_generator_1,
    kv_generator_2,
    kv_generator_3,
    kv_generator_4,
    kv_image_agent_1,
    kv_image_agent_2,
    kv_image_agent_3,
    kv_image_agent_4,
    copy_renderer_agent_1,
    copy_renderer_agent_2,
    copy_renderer_agent_3,
    copy_renderer_agent_4,
    kv_swap_agent_1,
    kv_swap_agent_2,
    kv_swap_agent_3,
    kv_swap_agent_4,
    kv_ranker,
    hitl_kv_selection,
    channel_router,
    content_agent,
    execution_agent,
    aggregation_agent,
    performance_agent,
)
from app.nodes import aggregate_kv_concepts, load_brand_context

# Fan-in join node: waits for all 4 KV generators before aggregation
kv_join_node = JoinNode(name="kv_join_node")

root_agent = Workflow(
    name  = "campaignos_pipeline",
    edges = [
        # ── Entry: load all brand data, then reason, then HITL, then strategy ──
        ("START", load_brand_context, briefing_agent, hitl_brief_approval, strategy_agent),

        # ── KV fan-out: strategy → 4 parallel generators ───────────────────────
        (strategy_agent,  kv_generator_1),
        (strategy_agent,  kv_generator_2),
        (strategy_agent,  kv_generator_3),
        (strategy_agent,  kv_generator_4),

        # ── Image pipeline: generator → background gen → Pillow overlay → swap bake ────────
        # Stage 1: kv_image_agent_N  — Gemini text-to-image (product photos as multimodal
        #                               inputs) → raw background kv_image_{N}.png
        # Stage 2: copy_renderer_N   — Pillow flat overlay (headline, brand, tagline)
        #                               → reference stencil kv_ref_{N}.png
        # Stage 3: kv_swap_agent_N   — Nano Banana 2 image-to-image bake (scene-aware
        #                               text integration) → kv_final_{N}.png
        (kv_generator_1, kv_image_agent_1, copy_renderer_agent_1, kv_swap_agent_1),
        (kv_generator_2, kv_image_agent_2, copy_renderer_agent_2, kv_swap_agent_2),
        (kv_generator_3, kv_image_agent_3, copy_renderer_agent_3, kv_swap_agent_3),
        (kv_generator_4, kv_image_agent_4, copy_renderer_agent_4, kv_swap_agent_4),

        # ── KV fan-in via JoinNode: all 4 swap agents must complete ───────────────────
        (kv_swap_agent_1, kv_join_node),
        (kv_swap_agent_2, kv_join_node),
        (kv_swap_agent_3, kv_join_node),
        (kv_swap_agent_4, kv_join_node),

        # ── Aggregate fn → ranker → HITL → content production pipeline ──────────
        (kv_join_node, aggregate_kv_concepts, kv_ranker, hitl_kv_selection, channel_router,
         content_agent, execution_agent, aggregation_agent, performance_agent),
    ],
)
