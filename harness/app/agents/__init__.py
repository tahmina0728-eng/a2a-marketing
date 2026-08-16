# Standalone agent runners (used by agent_standalone.py)
from app.agents.briefing        import run_briefing
from app.agents.strategy        import run_strategy
from app.agents.copy            import run_copy
from app.agents.culture         import run_culture
from app.agents.channel         import run_channel, get_standalone_page
from app.agents.kv              import run_kv
from app.agents.tvc             import run_tvc
from app.agents.reel            import run_reel
from app.agents.email_templates        import run_email_templates
from app.agents.email_converter_runner import run_email_converter

# ADK pipeline agent instances (used by pipeline.py)
# Re-exported here because the agents/ package shadows the old agents.py module.
from app._pipeline_agents import (
    briefing_agent,
    fan_truth_gate,
    hitl_brief_approval,
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

from app.email_converter.agent import email_converter_agent

__all__ = [
    # Standalone runners
    "run_briefing", "run_strategy", "run_copy", "run_culture",
    "run_channel", "run_kv", "run_tvc", "run_reel",
    "run_email_templates", "run_email_converter",
    "get_standalone_page",
    # ADK pipeline agents
    "briefing_agent", "fan_truth_gate", "hitl_brief_approval",
    "culture_analyst", "culture_formatter", "creative_director", "copy_agent",
    "kv_generator_1", "kv_generator_2", "kv_image_agent_1", "kv_image_agent_2",
    "kv_ranker", "hitl_kv_selection", "channel_router",
    "content_agent", "execution_agent", "aggregation_agent", "performance_agent",
    "email_converter_agent",
]
