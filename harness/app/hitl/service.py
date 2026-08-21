"""
hitl/service.py — Human-in-the-Loop service.

When a guardrail returns Action.HITL, this service:
  1. Logs the review request with full context
  2. (Optional) sends a notification (Slack/email stub)
  3. Returns a pending token — the pipeline pauses until approved

In production, wire up approvals.py to your review UI.
"""
from __future__ import annotations

import json
import uuid
import structlog
from datetime import datetime

logger = structlog.get_logger()

# In-memory store (replace with DB/Firestore in production)
_PENDING: dict[str, dict] = {}


def submit_for_review(
    agent:    str,
    brand:    str,
    payload:  dict,
    flags:    list[dict],
    context:  dict,
) -> str:
    """Submit output for human review. Returns a review token."""
    token = str(uuid.uuid4())
    record = {
        "token":      token,
        "agent":      agent,
        "brand":      brand,
        "payload":    payload,
        "flags":      flags,
        "context":    context,
        "status":     "pending",
        "submitted":  datetime.utcnow().isoformat(),
        "reviewed":   None,
        "reviewer":   None,
        "decision":   None,
        "notes":      "",
    }
    _PENDING[token] = record
    logger.warning(
        "hitl_review_submitted",
        token  = token,
        agent  = agent,
        brand  = brand,
        flags  = [f.get("rule") for f in flags],
    )
    _notify(record)
    return token


def get_review(token: str) -> dict | None:
    return _PENDING.get(token)


def list_pending(brand: str | None = None) -> list[dict]:
    reviews = [r for r in _PENDING.values() if r["status"] == "pending"]
    if brand:
        reviews = [r for r in reviews if r["brand"] == brand]
    return reviews


def approve(token: str, reviewer: str, notes: str = "") -> bool:
    if token not in _PENDING:
        return False
    _PENDING[token].update({
        "status":   "approved",
        "reviewer": reviewer,
        "decision": "approved",
        "notes":    notes,
        "reviewed": datetime.utcnow().isoformat(),
    })
    logger.info("hitl_approved", token=token, reviewer=reviewer)
    return True


def reject(token: str, reviewer: str, notes: str = "") -> bool:
    if token not in _PENDING:
        return False
    _PENDING[token].update({
        "status":   "rejected",
        "reviewer": reviewer,
        "decision": "rejected",
        "notes":    notes,
        "reviewed": datetime.utcnow().isoformat(),
    })
    logger.info("hitl_rejected", token=token, reviewer=reviewer)
    return True


def _notify(record: dict) -> None:
    """Stub — replace with Slack/email notification in production."""
    logger.info(
        "hitl_notify",
        agent = record["agent"],
        brand = record["brand"],
        token = record["token"],
        note  = "Review required — connect to Slack/email webhook here",
    )
