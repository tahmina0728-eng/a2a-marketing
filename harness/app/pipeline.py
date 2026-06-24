"""
pipeline.py — ADK 2.0 Workflow DAG for CampaignOS.

Defines the root_agent (a Workflow) that orchestrates the full campaign
pipeline as a directed acyclic graph.

DAG shape:
  START
    └── [fn] load_brand_context
          └── briefing_agent
                └── [fn] persist_brief          ← saves MachineBrief to state + artifact
                      └── culture_analyst       ← Google Search grounding (multi-turn)
                            └── culture_formatter   ← structures research into CultureAnalysis
                                  └── [fn] persist_culture    ← saves CultureAnalysis to state + artifact
                                        └── creative_director   ← Big Idea + CreativeStrategy
                                              └── [fn] persist_strategy   ← saves CreativeStrategy to state + artifact
                                                    └── copy_agent   ← short/medium/long copy variants
                                                          └── [fn] persist_copy   ← saves CampaignCopy to state + artifact
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
  persist_brief         — writes MachineBrief to state + saves JSON artifact
  persist_culture       — writes CultureAnalysis to state + saves JSON artifact
  persist_strategy      — writes CreativeStrategy to state + saves JSON artifact
  persist_copy          — writes CampaignCopy to state + saves JSON artifact
  aggregate_kv_concepts — fan-in: merges both enriched concepts into kv_concepts_all

HITL gates (hitl_brief_approval removed for development):
  hitl_kv_selection    — waits for human selection of a KV concept (1 of 2)
"""

import warnings

from google.adk import Workflow
from google.adk.workflow import JoinNode
from google.adk.agents import LoopAgent

from app.agents import (
    briefing_agent,
    fan_truth_gate,
    culture_analyst,
    culture_formatter,
    creative_director,
    copy_agent,
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
from app.nodes import aggregate_kv_concepts, load_brand_context, persist_brief, persist_culture, persist_strategy, persist_copy

# Fan-in join node: waits for both KV image agents before aggregation
kv_join_node = JoinNode(name="kv_join_node")

# Retry loop: briefing_agent runs → fan_truth_gate checks the score.
# If PASS (overall ≥ 70): fan_truth_gate escalates → loop exits → pipeline continues.
# If FAIL: fan_truth_gate writes feedback to state → loop restarts → briefing_agent
#          reruns with {brief_retry_feedback} visible in its instructions.
# LoopAgent is deprecated in ADK 2.0 but remains functional. The recommended
# replacement (Workflow-based loop) is not yet ergonomic for this pattern.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    briefing_loop = LoopAgent(
        name           = "briefing_loop",
        sub_agents     = [briefing_agent, fan_truth_gate],
        max_iterations = 3,
    )

briefing_pipeline = Workflow(
    name  = "campaignos_briefing",
    edges = [
        ("START", load_brand_context, briefing_loop, persist_brief),
    ],
)

root_agent = Workflow(
    name  = "campaignos_pipeline",
    edges = [
        # ── Entry: load brand data → brief (with auto-retry) → persist → cultural intelligence → creative strategy → copy → persist ──
        ("START", load_brand_context,
         briefing_loop,   persist_brief,
         culture_analyst,  culture_formatter, persist_culture,
         creative_director, persist_strategy,
         copy_agent,       persist_copy),

        # ── KV fan-out: persist_copy → 2 parallel art directors ────────────────────
        (persist_copy, kv_generator_1),
        (persist_copy, kv_generator_2),

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
