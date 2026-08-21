"""
guardrails/callbacks.py — ADK-native guardrail callbacks.

Factory that produces before_model_callback / after_model_callback pairs
wired directly into ADK's LlmAgent lifecycle. The brand is read from
session state at runtime (set by load_brand_context before any agent runs).

Callback signatures confirmed against google-adk==2.0.0b1 source:
  BeforeModelCallback(callback_context: CallbackContext, llm_request: LlmRequest) -> LlmResponse | None
  AfterModelCallback(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse | None

ADK invokes these by keyword, so the first parameter MUST be named
'callback_context' — any other name causes an unexpected keyword argument error.

Returning None  → ADK proceeds normally.
Returning an LlmResponse → ADK short-circuits (model skipped / response replaced).
"""
from __future__ import annotations

import json

import structlog
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

logger = structlog.get_logger()


# ── helpers ───────────────────────────────────────────────────────────────────

def _text_from_request(llm_request: LlmRequest) -> str:
    for content in reversed(llm_request.contents or []):
        if content.role == "user":
            return " ".join(
                p.text for p in (content.parts or []) if p.text
            )
    return ""


def _text_from_response(llm_response: LlmResponse) -> str:
    if not llm_response.content:
        return ""
    return " ".join(
        p.text for p in (llm_response.content.parts or []) if p.text
    )


def _blocked_response(message: str) -> LlmResponse:
    payload = json.dumps({"verdict": "BLOCKED", "summary": message})
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text=payload)],
        )
    )


# ── factory ───────────────────────────────────────────────────────────────────

def make_guardrail_callbacks(agent_name: str):
    """Return (before_model_callback, after_model_callback) for the named agent."""

    def before_model(callback_context: CallbackContext, llm_request: LlmRequest) -> LlmResponse | None:
        from app.guardrails import GuardrailService

        brand = callback_context.state.get("brand_name", "")
        text  = _text_from_request(llm_request)
        if not text:
            return None

        gs     = GuardrailService(brand=brand, agent=agent_name)
        result = gs.check_input({"prompt": text, "brand": brand})

        if result.blocked:
            msg = result.flags[0].message if result.flags else "Input blocked by guardrails"
            logger.warning(
                "guardrail_input_blocked",
                agent=agent_name, brand=brand,
                rule=result.flags[0].rule if result.flags else "",
                message=msg,
            )
            return _blocked_response(msg)

        for f in result.flags:
            logger.info("guardrail_input_flag", agent=agent_name, brand=brand,
                        rule=f.rule, severity=str(f.severity), message=f.message)
        return None

    def after_model(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse | None:
        from app.guardrails import GuardrailService

        brand = callback_context.state.get("brand_name", "")
        text  = _text_from_response(llm_response)
        if not text:
            return None

        gs     = GuardrailService(brand=brand, agent=agent_name)
        result = gs.check_output({"output": text})

        if result.blocked:
            msg = result.flags[0].message if result.flags else "Output blocked by guardrails"
            logger.warning(
                "guardrail_output_blocked",
                agent=agent_name, brand=brand,
                rule=result.flags[0].rule if result.flags else "",
                message=msg,
            )
            return _blocked_response(msg)

        for f in result.flags:
            logger.info("guardrail_output_flag", agent=agent_name, brand=brand,
                        rule=f.rule, severity=str(f.severity), message=f.message)
        return None

    before_model.__name__ = f"{agent_name}_before_model"
    after_model.__name__  = f"{agent_name}_after_model"

    return before_model, after_model
