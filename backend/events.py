"""
CampaignOS — SSE Event Schema
All events emitted by the pipeline to the React frontend.
Every event is a plain dict — serialised to JSON over SSE.
"""
from datetime import datetime, timezone
from typing import Any


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Pipeline lifecycle ──────────────────────────────────────

def pipeline_start(campaign_id: str, brief: dict) -> dict:
    """First event — pipeline has started."""
    return {
        "type": "pipeline_start",
        "campaign_id": campaign_id,
        "brief": brief,
        "ts": _ts(),
    }


def agent_start(agent: str, description: str) -> dict:
    """An agent has started working."""
    return {
        "type": "agent_start",
        "agent": agent,
        "description": description,
        "ts": _ts(),
    }


def agent_done(agent: str) -> dict:
    """An agent finished successfully."""
    return {
        "type": "agent_done",
        "agent": agent,
        "ts": _ts(),
    }


# ── Live thinking stream ────────────────────────────────────

def token(agent: str, text: str) -> dict:
    """
    A streaming token from the model — shown as a live
    'thinking' feed in the UI. High frequency, small payload.
    """
    return {
        "type": "token",
        "agent": agent,
        "text": text,
        "ts": _ts(),
    }


def thinking(agent: str, thought: str) -> dict:
    """
    A complete thought/reasoning step (not a raw token).
    Shown as a bullet in the activity sidebar.
    """
    return {
        "type": "thinking",
        "agent": agent,
        "thought": thought,
        "ts": _ts(),
    }


# ── Asset events ───────────────────────────────────────────

def asset_generating(agent: str, asset_type: str, label: str) -> dict:
    """
    Asset is being generated — UI shows a loading skeleton.
    asset_type: 'image' | 'kv_concept' | 'copy' | 'script' |
                'strategy' | 'brief' | 'execution_report'
    """
    return {
        "type": "asset_generating",
        "agent": agent,
        "asset_type": asset_type,
        "label": label,
        "ts": _ts(),
    }


def asset_ready(
    agent: str,
    asset_type: str,
    payload: Any,
    label: str = "",
    url: str = "",
) -> dict:
    """
    Asset is complete and ready to render in the UI.
    payload: the full JSON data for the asset
    url: optional GCS URL for images
    """
    return {
        "type": "asset_ready",
        "agent": agent,
        "asset_type": asset_type,
        "label": label,
        "payload": payload,
        "url": url,
        "ts": _ts(),
    }


# ── Human approval gates ───────────────────────────────────

def human_gate(gate: str, data: dict, options: list[str] | None = None) -> dict:
    """
    Pipeline paused — waiting for human decision.
    gate: 'approve_brief' | 'approve_strategy' |
          'select_kv' | 'approve_content'
    options: allowed decisions e.g. ['approve','revise','reject']
    """
    return {
        "type": "human_gate",
        "gate": gate,
        "data": data,
        "options": options or ["approve", "revise", "reject"],
        "ts": _ts(),
    }


def gate_resumed(gate: str, decision: str) -> dict:
    """Human made a decision — pipeline resuming."""
    return {
        "type": "gate_resumed",
        "gate": gate,
        "decision": decision,
        "ts": _ts(),
    }


# ── Errors ─────────────────────────────────────────────────

def error(agent: str, message: str, recoverable: bool = True) -> dict:
    """An agent encountered an error."""
    return {
        "type": "error",
        "agent": agent,
        "message": message,
        "recoverable": recoverable,
        "ts": _ts(),
    }


# ── Pipeline end ───────────────────────────────────────────

def pipeline_done(campaign_id: str, report: dict) -> dict:
    """Pipeline complete — campaign is live."""
    return {
        "type": "done",
        "campaign_id": campaign_id,
        "report": report,
        "ts": _ts(),
    }
