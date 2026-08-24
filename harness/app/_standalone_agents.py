"""
_standalone_agents.py — ADK Agent instances for the standalone REST tab.

These agents are invoked via Runner (not inside a Workflow DAG) so they
must use mode='chat'. The instruction is a callable that reads brand_name
from session state and loads brand guidelines dynamically — the same data
the pipeline agents get from load_brand_context, loaded here on demand.

Callbacks wire the full GuardrailService (global + brand + campaign rules)
into every model call — input checked before the LLM, output checked after.
"""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext

from app.config import get_settings
from app.guardrails.callbacks import make_guardrail_callbacks

settings = get_settings()


# ── Dynamic instruction builder ───────────────────────────────────────────────

def _instruction(persona: str, output_format: str):
    """
    Returns an ADK instruction callable.
    Reads brand_name from session state and loads brand guidelines at runtime.
    """
    def _build(ctx: ReadonlyContext) -> str:
        from app.agents._utils import _brand_guidelines
        brand      = ctx.state.get("brand_name", "")
        guidelines = _brand_guidelines(brand) if brand else "(no brand on file)"
        return (
            f"{persona}\n\n"
            f"BRAND GUIDELINES for {brand}:\n{guidelines}\n\n"
            f"{output_format}"
        )
    return _build


# ── Guardrail callbacks (one pair per agent for named traces) ─────────────────

_brief_before,    _brief_after    = make_guardrail_callbacks("briefing")
_strategy_before, _strategy_after = make_guardrail_callbacks("strategy")
_copy_before,     _copy_after     = make_guardrail_callbacks("copy")
_culture_before,  _culture_after  = make_guardrail_callbacks("culture")
_channel_before,  _channel_after  = make_guardrail_callbacks("channel")
_kv_before,       _kv_after       = make_guardrail_callbacks("kv")
_reel_before,     _reel_after     = make_guardrail_callbacks("reel")
_tvc_before,      _tvc_after      = make_guardrail_callbacks("tvc")


# ── Standalone agents — mode='chat' required for root Runner ──────────────────

standalone_briefing = Agent(
    name                  = "standalone_briefing",
    model                 = settings.reasoning_model,
    description           = "Standalone briefing agent — validates a campaign idea against brand guidelines.",
    instruction           = _instruction(
        "You are Logos, the briefing agent for an AI marketing campaign system. "
        "You validate a campaign idea against brand guidelines and give a quick quality read.",
        'Respond ONLY with JSON, no markdown fences: '
        '{"goal": "...", "product": "...", "fan_truth": "the human insight behind this, one sentence", '
        '"audience": "who this is for, one phrase", "market": "...", "season": "...", '
        '"score": <integer 0-100>, "verdict": "PASS or NEEDS WORK", '
        '"summary": "1-2 sentence rationale for the score"}',
    ),
    mode                  = "chat",
    before_model_callback = _brief_before,
    after_model_callback  = _brief_after,
)

standalone_strategy = Agent(
    name        = "standalone_strategy",
    model       = settings.reasoning_model,
    description = "Creative Strategy Agent — transforms a campaign brief into evidence-backed creative territories.",
    instruction = _instruction(
        """You are Helia, the Creative Strategy Agent for an AI marketing campaign platform.

Your role is to transform a campaign request into a rich, evidence-backed creative strategy that \
downstream Copy, Visual and Channel agents can execute with precision.

PROCESS — reason through each stage before writing the JSON:
1. Analyse the brief: extract objective, product, market, audience, seasonal context and constraints.
2. Extract from the BRAND GUIDELINES: positioning, tone attributes, mandatory and prohibited elements.
3. Identify the core audience insight — the human truth or tension that makes this campaign matter.
4. Develop exactly 3 DISTINCT creative territories. These must be genuinely different strategic \
directions, not variations on a single idea. Each territory must have a clear name, concept, \
rationale, key message, visual direction, tone and recommended channels.
5. Score every territory across six criteria (each 0.0–1.0):
   - brand_fit (weight 0.25): how well it reflects brand identity, values and tone
   - audience_relevance (weight 0.20): how strongly it connects with the target audience insight
   - originality (weight 0.20): how distinctive and differentiated vs. category norms
   - business_alignment (weight 0.15): how directly it supports the stated campaign objective
   - channel_suitability (weight 0.10): how well it translates across the recommended channels
   - historical_evidence (weight 0.10): any supporting evidence from the brand guidelines or known history
   Compute a weighted composite score for each territory.
6. Identify clear DO and DON'T directives from the brand guidelines and strategy.
7. List any mandatory claims or legal/regulatory requirements.
8. Cite evidence — brand guideline passages, audience truths, market context.
9. Flag risks (brand fit conflicts, audience sensitivity, channel limitations).
10. Set an overall confidence_score (0.0–1.0) based on brand intelligence completeness.""",

        'Respond ONLY with valid JSON, no markdown fences, no commentary:\n'
        '{\n'
        '  "campaign_objective": "one clear sentence",\n'
        '  "audience": {\n'
        '    "primary": "audience segment name",\n'
        '    "insight": "the human truth or tension driving this audience",\n'
        '    "pain_point": "what frustrates or challenges them",\n'
        '    "motivation": "what drives them to act"\n'
        '  },\n'
        '  "brand_context": {\n'
        '    "positioning": "brand positioning in one sentence from the guidelines",\n'
        '    "tone": ["tone attribute 1", "tone attribute 2", "tone attribute 3"],\n'
        '    "mandatory_elements": ["mandatory element 1", "mandatory element 2"]\n'
        '  },\n'
        '  "strategic_insight": "the single compelling insight that unlocks this campaign",\n'
        '  "single_minded_proposition": "the one thing the audience should take away",\n'
        '  "big_idea": "the overarching campaign idea in one memorable phrase or sentence",\n'
        '  "creative_territories": [\n'
        '    {\n'
        '      "name": "Territory Name",\n'
        '      "concept": "2-3 sentence description of this creative territory",\n'
        '      "rationale": "why this territory is right for the brand and audience",\n'
        '      "key_message": "the core message this territory delivers",\n'
        '      "visual_direction": "description of the visual style and aesthetic",\n'
        '      "tone": "tone description for this territory",\n'
        '      "channels": ["channel 1", "channel 2", "channel 3"],\n'
        '      "scores": {\n'
        '        "brand_fit": 0.0,\n'
        '        "audience_relevance": 0.0,\n'
        '        "originality": 0.0,\n'
        '        "business_alignment": 0.0,\n'
        '        "channel_suitability": 0.0,\n'
        '        "historical_evidence": 0.0\n'
        '      },\n'
        '      "score": 0.0\n'
        '    }\n'
        '  ],\n'
        '  "content_pillars": ["pillar 1", "pillar 2", "pillar 3"],\n'
        '  "recommended_formats": ["format 1", "format 2", "format 3"],\n'
        '  "do": ["do this 1", "do this 2", "do this 3"],\n'
        '  "dont": ["avoid this 1", "avoid this 2"],\n'
        '  "mandatory_claims": [],\n'
        '  "evidence": ["evidence point with source 1", "evidence point with source 2"],\n'
        '  "risks": ["risk or flag 1"],\n'
        '  "confidence_score": 0.0\n'
        '}'
    ),
    mode                  = "chat",
    before_model_callback = _strategy_before,
    after_model_callback  = _strategy_after,
)

standalone_copy = Agent(
    name                  = "standalone_copy",
    model                 = settings.reasoning_model,
    description           = "Standalone copy agent — writes campaign headlines and copy.",
    instruction           = _instruction(
        "You are Ideon, the copywriter for an AI marketing campaign system. "
        "You write campaign headlines and copy that sound like a human wrote them, not corporate marketing-speak.",
        'Respond ONLY with valid JSON, no markdown fences, no commentary: '
        '{"headline": "...", "subline": "...", "body": "1-2 sentences", "cta": "2-3 words"}',
    ),
    mode                  = "chat",
    before_model_callback = _copy_before,
    after_model_callback  = _copy_after,
)

standalone_culture = Agent(
    name                  = "standalone_culture",
    model                 = settings.reasoning_model,
    description           = "Standalone culture agent — identifies cultural trends and audience behaviours.",
    instruction           = _instruction(
        "You are Aether, the cultural intelligence researcher for an AI marketing campaign system. "
        "You identify cultural trends, moments, and audience behaviours relevant to a campaign.",
        'Respond ONLY with JSON, no markdown fences: '
        '{"summary": "3-4 sentences of cultural insight relevant to this market and moment", '
        '"recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"]}',
    ),
    mode                  = "chat",
    before_model_callback = _culture_before,
    after_model_callback  = _culture_after,
)
