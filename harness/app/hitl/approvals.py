"""
hitl/approvals.py — FastAPI routes for the HITL review UI.
Mount these on the main app: app.include_router(approvals_router).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .service import get_review, list_pending, approve, reject

approvals_router = APIRouter(prefix="/hitl", tags=["hitl"])


class DecisionBody(BaseModel):
    token:    str
    reviewer: str
    notes:    str = ""


@approvals_router.get("/pending")
def get_pending(brand: str | None = None):
    return {"reviews": list_pending(brand=brand)}


@approvals_router.get("/review/{token}")
def get_one(token: str):
    r = get_review(token)
    if not r:
        raise HTTPException(404, "Review not found")
    return r


@approvals_router.post("/approve")
def do_approve(body: DecisionBody):
    ok = approve(body.token, body.reviewer, body.notes)
    if not ok:
        raise HTTPException(404, "Review token not found")
    return {"status": "approved", "token": body.token}


@approvals_router.post("/reject")
def do_reject(body: DecisionBody):
    ok = reject(body.token, body.reviewer, body.notes)
    if not ok:
        raise HTTPException(404, "Review token not found")
    return {"status": "rejected", "token": body.token}
