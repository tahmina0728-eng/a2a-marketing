"""Shared utilities for all standalone agent modules."""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid

import structlog
from google import genai
from google.adk.agents.base_agent import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.config import get_settings
from app.brand_assets import get_asset_loader

logger   = structlog.get_logger()
settings = get_settings()

_client = None


def _genai_client():
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=settings.gcp_project, location=settings.gcp_region)
    return _client


def _brand_guidelines(brand: str) -> str:
    text = get_asset_loader().load_guidelines(brand)
    return text[:6000] if text else "(no brand guidelines on file for this brand — use general best practice)"


def _extract_brand(text: str) -> str | None:
    """Find which known (uploaded) brand is referenced in the free text, preferring the longest match —
    e.g. "UBS Bank for UK market, festive: christmas" -> "UBS Bank", not a shorter coincidental match."""
    known = get_asset_loader().list_brands()
    text_lower = text.lower()
    matches = [b for b in known if b.lower() in text_lower]
    return max(matches, key=len) if matches else None


def _parse_json_loose(text: str) -> dict | None:
    """Pull a JSON object out of a model response that may have wrapping prose/markdown fences."""
    # Strip markdown code fences first
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _extract_language(text: str) -> str:
    """Extract language tag from prompt text, e.g. 'Language: German (de-CH)' -> 'German (de-CH)'."""
    m = re.search(r"[Ll]anguage:\s*([^\.\n,]+)", text)
    return m.group(1).strip() if m else ""


# ── ADK Runner helpers ────────────────────────────────────────────────────────

async def _run_with_adk(agent: BaseAgent, brand: str, prompt: str) -> dict:
    """
    Invoke an ADK Agent through the Runner so that before_model_callback /
    after_model_callback fire natively.  Each call gets its own in-memory
    session (ephemeral, standalone — no persistence needed).
    brand_name is written to session state so callbacks can load brand policy.
    """
    svc     = InMemorySessionService()
    session = await svc.create_session(
        app_name   = "campaignos_standalone",
        user_id    = "standalone",
        session_id = str(uuid.uuid4()),
        state      = {"brand_name": brand},
    )
    runner = Runner(
        agent           = agent,
        app_name        = "campaignos_standalone",
        session_service = svc,
    )
    final_text = ""
    async for event in runner.run_async(
        user_id     = "standalone",
        session_id  = session.id,
        new_message = genai_types.Content(
            role  = "user",
            parts = [genai_types.Part(text=prompt)],
        ),
    ):
        if event.content:
            for part in (event.content.parts or []):
                if part.text:
                    final_text = part.text  # keep last text chunk

    return _parse_json_loose(final_text) or {"raw": final_text}


def _run_adk_sync(agent: BaseAgent, brand: str, prompt: str) -> dict:
    """
    Sync wrapper around _run_with_adk — safe to call from asyncio.to_thread()
    context (FastAPI runs sync routes in a thread pool without an event loop).
    """
    return asyncio.run(_run_with_adk(agent, brand, prompt))


def _generate(
    persona: str,
    brand: str,
    prompt: str,
    output_instructions: str,
    agent_name: str = "standalone",
) -> dict:
    # ── Input guardrails (runs before the model call) ──────────────────────
    try:
        from app.guardrails import GuardrailService
        from app.guardrails.models import Action as _Action
        gs = GuardrailService(brand=brand, agent=agent_name)
        input_check = gs.check_input({"prompt": prompt, "brand": brand})
        if input_check.action == _Action.BLOCK:  # HITL submits for review but passes through
            msg = input_check.flags[0].message if input_check.flags else "Input blocked by guardrails"
            return {"verdict": "BLOCKED", "summary": msg}
    except Exception as _ge:
        logger.warning("guardrail_input_error", agent=agent_name, error=str(_ge))

    guidelines  = _brand_guidelines(brand)
    full_prompt = (
        f"{persona}\n\n"
        f"BRAND GUIDELINES for {brand}:\n{guidelines}\n\n"
        f"CREATIVE DIRECTION from the user: \"{prompt}\"\n\n"
        f"{output_instructions}"
    )
    result: dict = {}
    for attempt in range(3):
        try:
            resp = _genai_client().models.generate_content(
                model=settings.gemini_model_reasoning, contents=full_prompt,
            )
            raw    = (resp.text or "").strip()
            result = _parse_json_loose(raw) or {"raw": raw}
            break
        except Exception as _e:
            err = str(_e)
            if "429" in err and attempt < 2:
                wait = 30 * (attempt + 1)
                logger.warning("standalone_generate_429_retry", brand=brand, attempt=attempt + 1, wait=wait)
                time.sleep(wait)
            else:
                logger.warning("standalone_generate_failed", brand=brand, error=err)
                return {"error": err}
    else:
        return {"error": "quota exhausted after retries"}

    # ── Output guardrails (runs after the model responds) ──────────────────
    try:
        from app.guardrails import GuardrailService
        from app.guardrails.models import Action as _Action
        gs = GuardrailService(brand=brand, agent=agent_name)
        output_check = gs.check_output(result)  # HITL is submitted for review inside check_output
        if output_check.action == _Action.BLOCK:  # HITL passes through; only BLOCK is a hard stop
            msg = output_check.flags[0].message if output_check.flags else "Output blocked by guardrails"
            return {"verdict": "BLOCKED", "summary": msg}
    except Exception as _ge:
        logger.warning("guardrail_output_error", agent=agent_name, error=str(_ge))

    return result
