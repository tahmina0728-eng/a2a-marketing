"""
agents/infosys/base.py — BaseInfosysAgent.

Each Infosys agent (Aether, Logos, Helia, Ideon, Morphis, Kinetik) subclasses this.

ADK pattern (same as the rest of CampaignOS):
  - Constructs a google.adk.agents.Agent with a dynamic instruction callable
  - Instruction callable reads SKILL.md + loads BrandContext (inc. BQ RAG) at call time
  - Runs through ADK Runner + InMemorySessionService so guardrail callbacks fire natively
  - run() is a sync wrapper; run_async() for use inside async pipelines

Session state keys injected per run:
  brand_name  — always "Infosys"
  rag_query   — query string for BQ vector search (set per agent invocation)
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Any

import structlog
from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.config import get_settings
from app.guardrails.callbacks import make_guardrail_callbacks
from app.schemas.common import AgentResponse, AgentInfo, JobInfo, Artifact

logger   = structlog.get_logger()
settings = get_settings()

# harness/app/brands/infosys/agents/{name}/SKILL.md
_INFOSYS_AGENTS = Path(__file__).parent.parent.parent / "brands" / "infosys" / "agents"


def _parse_json(text: str) -> dict | None:
    """Extract a JSON object from model output that may contain prose or fences."""
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


class BaseInfosysAgent:
    """
    Base class for all Infosys A2A agents.

    Subclasses set:
      name           — matches the folder under brands/infosys/agents/
      artifact_type  — the Artifact.type string for this agent's output
      output_schema  — JSON schema string injected into the ADK instruction
    """

    name: str          = "base"
    artifact_type: str = "base"
    output_schema: str = "{}"   # overridden in each subclass

    def __init__(self) -> None:
        # Load SKILL.md once at init
        skill_path = _INFOSYS_AGENTS / self.name / "SKILL.md"
        self._skill: str = (
            skill_path.read_text(encoding="utf-8")
            if skill_path.exists()
            else f"# {self.name.capitalize()} — Infosys agent\n\n(No SKILL.md found.)"
        )

        # Capture values for the closure — avoids late-binding issues
        _skill        = self._skill
        _schema       = self.output_schema
        _agent_name   = self.name

        # ── Dynamic instruction callable (same pattern as _standalone_agents.py) ──
        def _instruction(ctx: ReadonlyContext) -> str:
            from app.brand_context.loader import load_infosys_brand
            rag_query = ctx.state.get("rag_query", "")
            brand_ctx = load_infosys_brand(query=rag_query)
            return (
                "<SKILL>\n"
                f"{_skill}\n"
                "</SKILL>\n\n"
                "<BRAND_CONTEXT>\n"
                f"{brand_ctx.as_prompt_block}\n"
                "</BRAND_CONTEXT>\n\n"
                "OUTPUT INSTRUCTIONS:\n"
                "Return ONLY a valid JSON object. Do not include any text, explanation, "
                "or markdown outside the JSON object itself. Follow this exact schema:\n\n"
                f"{_schema}"
            )

        # ── Guardrail callbacks (same as existing standalone agents) ─────────────
        _before, _after = make_guardrail_callbacks(f"infosys_{self.name}")

        # ── ADK Agent ─────────────────────────────────────────────────────────────
        self._adk_agent = Agent(
            name                  = f"infosys_{self.name}",
            model                 = settings.reasoning_model,
            description           = (
                f"Infosys {self.name.capitalize()} agent — produces {self.artifact_type}"
            ),
            instruction           = _instruction,
            before_model_callback = _before,
            after_model_callback  = _after,
        )

    # ── ADK Runner ────────────────────────────────────────────────────────────────

    async def _run_adk_async(
        self,
        user_message: str,
        rag_query: str = "",
    ) -> dict:
        """Run the ADK agent through the Runner (guardrails fire natively)."""
        svc     = InMemorySessionService()
        session = await svc.create_session(
            app_name   = "campaignos_infosys",
            user_id    = "infosys_pipeline",
            session_id = str(uuid.uuid4()),
            state      = {"brand_name": "Infosys", "rag_query": rag_query},
        )
        runner = Runner(
            agent           = self._adk_agent,
            app_name        = "campaignos_infosys",
            session_service = svc,
        )

        final_text = ""
        async for event in runner.run_async(
            user_id     = "infosys_pipeline",
            session_id  = session.id,
            new_message = genai_types.Content(
                role  = "user",
                parts = [genai_types.Part(text=user_message)],
            ),
        ):
            if event.content:
                for part in (event.content.parts or []):
                    if part.text:
                        final_text = part.text   # keep the last text chunk

        parsed = _parse_json(final_text)
        if parsed:
            return parsed

        logger.warning(
            "infosys_agent_json_parse_failed",
            agent       = self.name,
            raw_preview = final_text[:300],
        )
        return {"raw": final_text}

    def _run_sync(self, user_message: str, rag_query: str = "") -> dict:
        """Sync wrapper — safe to call from a thread that has no running event loop."""
        return asyncio.run(self._run_adk_async(user_message, rag_query))

    # ── Response packaging ────────────────────────────────────────────────────────

    def _make_response(
        self,
        result: dict,
        campaign_name: str = "",
    ) -> AgentResponse:
        if "error" in result or "raw" in result:
            reason = result.get("error") or "model did not return valid JSON"
            return AgentResponse(
                agent  = AgentInfo(name=self.name),
                job    = JobInfo(campaign_name=campaign_name),
                status = "failed",
                qa     = {"error": reason, **({} if "error" in result else {"raw": result["raw"][:500]})},
            )

        # Surface any BLOCKED verdict from guardrails
        if result.get("verdict") == "BLOCKED":
            return AgentResponse(
                agent  = AgentInfo(name=self.name),
                job    = JobInfo(campaign_name=campaign_name),
                status = "blocked",
                qa     = {"blocked_by": "guardrails", "summary": result.get("summary", "")},
            )

        return AgentResponse(
            agent    = AgentInfo(name=self.name),
            job      = JobInfo(campaign_name=campaign_name),
            status   = "completed",
            artifact = Artifact(type=self.artifact_type, content=result),
        )
