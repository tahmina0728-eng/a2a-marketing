"""
email_converter/agent.py — Google ADK Agent definition for the Email Converter.

Module-level constant following the same pattern as _pipeline_agents.py.

The agent:
  1. Receives structured document content as a JSON user message
  2. Composes polished email copy (subject, headline, bullets, CTA, template)
  3. Calls build_email_html tool → renders complete HTML
  4. Calls validate_email_html tool → brand / HTML / compliance checks
  5. Returns result under output_key "email_result"

Images are NOT passed through the LLM — they are stored in ADK session
state under "email_images" before the agent is invoked, and the
build_email_html tool retrieves them via ToolContext.

Pipeline integration:
  from app.email_converter.agent import email_converter_agent
  # wire into a Workflow or invoke via Runner

Standalone integration:
  from app.agents.email_converter_runner import run_email_converter
  # called by agent_standalone.py _RUNNERS["email_converter"]
"""

from google.adk import Agent

from app.config import get_settings
from app.email_converter.instructions import EMAIL_CONVERTER_AGENT_INSTRUCTIONS
from app.email_converter.tools import build_email_html, validate_email_html

settings = get_settings()

email_converter_agent = Agent(
    name        = "email_converter_agent",
    model       = settings.reasoning_model,
    description = (
        "Converts uploaded documents (PDF, DOCX, XLSX, images, etc.) into a "
        "polished, on-brand HTML email. Composes subject, headline, bullets and "
        "CTA using LLM reasoning, selects the best layout template, builds "
        "email-client-safe HTML, and validates for brand compliance and "
        "CAN-SPAM / GDPR / CASL requirements."
    ),
    instruction = EMAIL_CONVERTER_AGENT_INSTRUCTIONS,
    tools       = [build_email_html, validate_email_html],
    output_key  = "email_result",
    mode        = "single_turn",
)
