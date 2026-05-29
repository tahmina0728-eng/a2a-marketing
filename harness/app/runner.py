"""
runner.py — ADK Runner helper.

Wraps the ADK Runner and InMemorySessionService to provide a simple
async run_agent() function used by the FastAPI routes in main.py.

For production with Agent Engine, swap InMemorySessionService for
VertexAiSessionService to get persistent session state.
"""

import json
import time
import uuid
import structlog
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk import Agent, Workflow
from google.genai.types import Content, Part

logger = structlog.get_logger()

# Session service — in-memory for stateless Cloud Run
# Replace with VertexAiSessionService for Agent Engine deployment
session_service = InMemorySessionService()


def _parse_agent_response(raw: str) -> dict:
    """
    Parse the agent's text response as JSON.
    Handles accidental markdown code fences if present.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned.strip())


async def run_agent(
    agent:       Agent | Workflow,
    input_data:  dict,
    campaign_id: str | None = None,
) -> tuple[dict, int]:
    """
    Run an ADK agent or pipeline with input_data as the user message.

    Args:
        agent:       ADK Agent or Workflow to run
        input_data:  Dict to pass as the input message (serialised to JSON)
        campaign_id: Optional campaign ID — generated if not provided

    Returns:
        tuple of (result_dict, processing_time_ms)
    """
    start = time.time()
    cid   = campaign_id or f"run-{str(uuid.uuid4())[:8]}"

    log = logger.bind(
        agent_name  = agent.name,
        campaign_id = cid,
    )
    log.info("adk_run_start")

    # Create session
    session = session_service.create_session(
        app_name   = agent.name,
        user_id    = "campaignos",
        session_id = cid,
    )

    # Pre-populate brief in session state so load_brand_context can read it
    # via state-injected parameter (brief_json: str = "") as a fallback in
    # case node_input doesn't carry the message text directly.
    session.state["brief_json"] = json.dumps({"campaign_id": cid, **input_data})

    # Create runner
    runner = Runner(
        agent           = agent,
        app_name        = agent.name,
        session_service = session_service,
    )

    # Build input as ADK Content message
    input_content = Content(
        role  = "user",
        parts = [Part(text=json.dumps({
            "campaign_id": cid,
            **input_data,
        }))]
    )

    # Run agent — ADK handles all tool calls internally
    final_response = None
    async for event in runner.run_async(
        user_id     = "campaignos",
        session_id  = cid,
        new_message = input_content,
    ):
        if event.is_final_response():
            final_response = event.content.parts[0].text
            break

    if not final_response:
        raise ValueError(f"Agent {agent.name} returned no response")

    # Parse response
    result = _parse_agent_response(final_response)
    result.setdefault("campaign_id", cid)

    processing_ms = int((time.time() - start) * 1000)

    log.info(
        "adk_run_complete",
        processing_ms      = processing_ms,
        validation_score   = result.get("validation", {}).get("score"),
        validation_status  = result.get("validation", {}).get("status"),
    )

    return result, processing_ms
