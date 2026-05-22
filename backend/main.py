"""
CampaignOS — FastAPI Application
Exposes the pipeline as HTTP endpoints + SSE stream.
Run: uvicorn main:app --reload --port 8000
"""
import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
import events as ev
from pipeline import run_pipeline, run_performance_check


# ── Active pipelines: campaign_id → asyncio.Queue ──────────
_pipelines: dict[str, asyncio.Queue] = {}


# ── App lifecycle ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 CampaignOS backend starting...")
    yield
    print("🛑 CampaignOS backend shutting down.")

app = FastAPI(
    title="CampaignOS API",
    description="McDonald's AI Campaign Production System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ───────────────────────────────

class CampaignBriefRequest(BaseModel):
    goal: str
    product: str
    fan_truth: str
    kpis: list[str]
    channels: list[str]
    budget: float
    audience: str
    timing: dict | None = None
    additional_notes: str | None = None


class ApprovalRequest(BaseModel):
    gate: str           # 'approve_brief' | 'approve_strategy' | 'select_kv' | 'approve_content'
    decision: str       # 'approve' | 'revise' | 'reject' | 'select_A' | 'select_B' | 'select_C'
    notes: str | None = None
    selected_index: int | None = None  # For KV concept selection


# ── Endpoints ───────────────────────────────────────────────

@app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "CampaignOS API",
        "version": "1.0.0",
        "active_pipelines": len(_pipelines),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/campaign/start")
async def start_campaign(
    brief: CampaignBriefRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a new campaign pipeline.
    Returns a campaign_id — use this to connect to the SSE stream.
    """
    campaign_id = str(uuid.uuid4())[:8].upper()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _pipelines[campaign_id] = queue

    brief_dict = brief.model_dump()
    brief_dict["campaign_id"] = campaign_id

    # Run pipeline in background — events stream via SSE
    background_tasks.add_task(run_pipeline, brief_dict, queue)

    return {
        "campaign_id": campaign_id,
        "stream_url": f"/campaign/{campaign_id}/stream",
        "approve_url": f"/campaign/{campaign_id}/approve",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/campaign/{campaign_id}/stream")
async def stream_events(campaign_id: str):
    """
    SSE endpoint — stream all pipeline events to the React frontend.
    Connect with: new EventSource('/campaign/{id}/stream')
    
    Event types:
    - pipeline_start    → campaign kicked off
    - agent_start       → an agent began working
    - token             → live thinking token (high frequency)
    - thinking          → complete thought/step
    - asset_generating  → asset creation started (show skeleton)
    - asset_ready       → asset complete (render it)
    - human_gate        → pipeline paused, waiting for approval
    - gate_resumed      → human decided, pipeline continuing
    - agent_done        → agent finished
    - error             → something went wrong
    - done              → pipeline complete, campaign is live
    """
    if campaign_id not in _pipelines:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    queue = _pipelines[campaign_id]

    async def generate() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    # Wait up to 30s for next event (keeps connection alive)
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"

                    # Close stream when pipeline ends
                    if event["type"] in ("done", "error") and not event.get("recoverable", True):
                        break

                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent proxy timeout
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            pass  # Client disconnected — clean exit

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@app.post("/campaign/{campaign_id}/approve")
async def approve_gate(campaign_id: str, approval: ApprovalRequest):
    """
    Submit a human approval decision at a pipeline gate.
    The pipeline is polling Firestore for this — it will resume within 5s.
    """
    from google.cloud import firestore
    db = firestore.AsyncClient(
        project=config.GCP_PROJECT,
        database=config.FIRESTORE_DB,
    )
    doc_ref = db.collection("approvals").document(f"{campaign_id}_{approval.gate}")
    await doc_ref.set({
        "campaign_id": campaign_id,
        "gate": approval.gate,
        "decision": approval.decision,
        "notes": approval.notes,
        "selected_index": approval.selected_index,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "ok": True,
        "campaign_id": campaign_id,
        "gate": approval.gate,
        "decision": approval.decision,
        "message": f"Decision '{approval.decision}' recorded. Pipeline will resume shortly.",
    }


@app.get("/campaign/{campaign_id}/status")
async def get_campaign_status(campaign_id: str):
    """Get the current status of a campaign pipeline."""
    if campaign_id not in _pipelines:
        raise HTTPException(status_code=404, detail="Campaign not found")
    queue = _pipelines[campaign_id]
    return {
        "campaign_id": campaign_id,
        "active": True,
        "queue_depth": queue.qsize(),
    }


@app.get("/campaigns")
async def list_campaigns():
    """List all active pipeline sessions."""
    return {
        "active_campaigns": list(_pipelines.keys()),
        "count": len(_pipelines),
    }


@app.post("/performance/run")
async def trigger_performance_check(
    campaign_id: str | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Trigger the Performance Agent manually (or via Cloud Scheduler).
    If campaign_id is provided, checks only that campaign.
    Otherwise checks all live campaigns.
    """
    background_tasks.add_task(run_performance_check, campaign_id)
    return {
        "ok": True,
        "message": f"Performance check triggered for {'all campaigns' if not campaign_id else campaign_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.delete("/campaign/{campaign_id}")
async def cleanup_campaign(campaign_id: str):
    """Remove a campaign pipeline from active memory (cleanup after done)."""
    if campaign_id in _pipelines:
        del _pipelines[campaign_id]
    return {"ok": True, "campaign_id": campaign_id}
