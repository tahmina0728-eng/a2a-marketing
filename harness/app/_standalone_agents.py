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
    name                  = "standalone_strategy",
    model                 = settings.reasoning_model,
    description           = "Standalone strategy agent — turns a creative direction into a Big Idea and framework.",
    instruction           = _instruction(
        "You are Helia, the creative strategist for an AI marketing campaign system. "
        "You turn a one-line creative direction into a campaign's Big Idea and strategic framework.",
        'Respond ONLY with JSON, no markdown fences: '
        '{"hero_message": "the Big Idea, one punchy sentence", '
        '"strategic_framework": "2-3 sentences on the strategic approach", '
        '"messaging_pillars": ["pillar 1", "pillar 2", "pillar 3"]}',
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
