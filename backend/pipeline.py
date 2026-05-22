"""
CampaignOS — Pipeline Orchestrator
Sequences all 6 agents, streams events to the SSE queue,
handles human approval gates via Firestore polling.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from google.cloud import firestore

import config
import events as ev
from agents import (
    briefing_agent,
    strategy_agent,
    kv_agent,
    content_agent,
    execution_agent,
    performance_agent,
)


# ── Firestore client for approval gate persistence ──────────
_db: firestore.AsyncClient | None = None

def _firestore() -> firestore.AsyncClient:
    global _db
    if _db is None:
        _db = firestore.AsyncClient(
            project=config.GCP_PROJECT,
            database=config.FIRESTORE_DB,
        )
    return _db


# ── Run a single ADK agent, streaming tokens to SSE queue ──

async def run_agent(
    agent,
    input_data: dict,
    queue: asyncio.Queue,
    session_service: InMemorySessionService,
) -> dict:
    """
    Run an ADK agent and stream its output tokens to the SSE queue.
    Returns the final parsed JSON output.
    """
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name="campaignos",
    )
    session = await session_service.create_session(
        app_name="campaignos",
        user_id="pipeline",
    )

    full_text = ""

    async for event in runner.run_async(
        session_id=session.id,
        user_id="pipeline",
        new_message=Content(parts=[Part(text=json.dumps(input_data))]),
    ):
        # Stream thinking tokens live to the UI
        if event.content and event.content.parts:
            for part in event.content.parts:
                token_text = part.text or ""
                if token_text:
                    full_text += token_text
                    await queue.put(ev.token(agent.name, token_text))

    # Parse the final JSON output
    # ADK agents return JSON — strip any markdown fences the model might add
    clean = full_text.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.rsplit("```", 1)[0]
    clean = clean.strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # If not valid JSON, return as a text payload
        return {"raw_output": full_text, "_parse_error": True}


# ── Human approval gate ─────────────────────────────────────

async def wait_for_approval(
    campaign_id: str,
    gate: str,
    queue: asyncio.Queue,
    timeout_seconds: int = 7200,  # 2 hours default
) -> dict:
    """
    Block pipeline execution until a human makes a decision.
    Decision is written to Firestore by the FastAPI /approve endpoint.
    Returns the approval document: {decision, notes, selected_index, ...}
    """
    db = _firestore()
    doc_ref = db.collection("approvals").document(f"{campaign_id}_{gate}")

    # Poll Firestore every 5 seconds
    elapsed = 0
    poll_interval = 5
    while elapsed < timeout_seconds:
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if data.get("decision"):
                await queue.put(ev.gate_resumed(gate, data["decision"]))
                # Clear the approval doc so it doesn't interfere with replays
                await doc_ref.delete()
                return data
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    # Timeout — auto-reject
    await queue.put(ev.error("pipeline", f"Gate '{gate}' timed out after {timeout_seconds}s"))
    return {"decision": "timeout", "notes": "Approval gate timed out"}


# ── Main pipeline ───────────────────────────────────────────

async def run_pipeline(brief: dict, queue: asyncio.Queue) -> None:
    """
    The main CampaignOS pipeline. Runs all 6 agents in sequence
    with human approval gates between each major stage.

    All events are pushed to `queue` and streamed to the React UI via SSE.
    """
    campaign_id = brief.get("campaign_id") or str(uuid.uuid4())[:8]
    brief["campaign_id"] = campaign_id

    # Single session service for the whole pipeline
    session_service = InMemorySessionService()

    try:
        await queue.put(ev.pipeline_start(campaign_id, brief))

        # ── AGENT 1: BRIEFING ───────────────────────────────
        await queue.put(ev.agent_start(
            "briefing_agent",
            "Validating brief, scoring Fan Truth, checking KPIs vs benchmarks..."
        ))
        await queue.put(ev.asset_generating("briefing_agent", "brief", "machine_brief.json"))

        machine_brief = await run_agent(briefing_agent, brief, queue, session_service)
        machine_brief["campaign_id"] = campaign_id

        await queue.put(ev.agent_done("briefing_agent"))
        await queue.put(ev.asset_ready(
            "briefing_agent", "machine_brief", machine_brief,
            label="Validated brief",
        ))

        # ── GATE 1: Approve brief ───────────────────────────
        await queue.put(ev.human_gate(
            "approve_brief",
            {
                "title": "Review & approve campaign brief",
                "brief": machine_brief,
                "fan_truth_score": machine_brief.get("fan_truth", {}).get("total", 0),
                "validation_status": machine_brief.get("validation_status"),
                "revision_notes": machine_brief.get("revision_notes"),
            },
            options=["approve", "revise", "reject"],
        ))
        gate1 = await wait_for_approval(campaign_id, "approve_brief", queue)
        if gate1["decision"] in ("reject", "timeout"):
            await queue.put(ev.pipeline_done(campaign_id, {"status": "rejected_at_brief"}))
            return

        # ── AGENT 2: STRATEGY ───────────────────────────────
        await queue.put(ev.agent_start(
            "strategy_agent",
            "Building channel strategy, messaging hierarchy, budget allocation..."
        ))
        await queue.put(ev.asset_generating("strategy_agent", "strategy", "strategy_doc.json"))

        strategy = await run_agent(strategy_agent, machine_brief, queue, session_service)
        strategy["campaign_id"] = campaign_id

        await queue.put(ev.agent_done("strategy_agent"))
        await queue.put(ev.asset_ready(
            "strategy_agent", "strategy_doc", strategy,
            label="Channel strategy",
        ))

        # ── GATE 2: Approve strategy ────────────────────────
        await queue.put(ev.human_gate(
            "approve_strategy",
            {
                "title": "Review & approve channel strategy",
                "strategy": strategy,
                "channel_count": len(strategy.get("channel_priority", [])),
                "total_budget": strategy.get("total_budget"),
            },
            options=["approve", "revise", "reject"],
        ))
        gate2 = await wait_for_approval(campaign_id, "approve_strategy", queue)
        if gate2["decision"] in ("reject", "timeout"):
            await queue.put(ev.pipeline_done(campaign_id, {"status": "rejected_at_strategy"}))
            return

        # ── AGENT 3: KV CONCEPTS ────────────────────────────
        await queue.put(ev.agent_start(
            "kv_agent",
            "Generating 3 Key Visual concepts — visual direction, Reel scripts, colour palettes..."
        ))
        for label in ["KV Concept A", "KV Concept B", "KV Concept C"]:
            await queue.put(ev.asset_generating("kv_agent", "kv_concept", label))

        kv_result = await run_agent(strategy_agent, strategy, queue, session_service)
        # kv_result should be {"concepts": [...]} or a list
        kv_concepts = kv_result if isinstance(kv_result, list) else kv_result.get("concepts", [kv_result])

        await queue.put(ev.agent_done("kv_agent"))
        for i, concept in enumerate(kv_concepts):
            await queue.put(ev.asset_ready(
                "kv_agent", "kv_concept", concept,
                label=f"KV Concept {concept.get('concept_id', i+1)}: {concept.get('concept_name', '')}",
            ))

        # ── GATE 3: Select KV concept ───────────────────────
        await queue.put(ev.human_gate(
            "select_kv",
            {
                "title": "Select a Key Visual concept",
                "concepts": kv_concepts,
                "instruction": "Choose concept A, B, or C — or request revisions.",
            },
            options=["select_A", "select_B", "select_C", "revise"],
        ))
        gate3 = await wait_for_approval(campaign_id, "select_kv", queue)
        if gate3["decision"] in ("reject", "timeout"):
            await queue.put(ev.pipeline_done(campaign_id, {"status": "rejected_at_kv"}))
            return

        # Determine which concept was selected
        selected_letter = gate3["decision"].replace("select_", "").upper()  # "A", "B", or "C"
        selected_kv = next(
            (c for c in kv_concepts if c.get("concept_id") == selected_letter),
            kv_concepts[0]
        )

        # ── AGENT 4: CONTENT ────────────────────────────────
        await queue.put(ev.agent_start(
            "content_agent",
            f"Creating all channel assets from KV Concept {selected_letter}..."
        ))
        await queue.put(ev.asset_generating("content_agent", "content_package", "All channel copy"))

        content_input = {
            "campaign_id": campaign_id,
            "selected_kv": selected_kv,
            "strategy": strategy,
            "machine_brief": machine_brief,
        }
        content_package = await run_agent(content_agent, content_input, queue, session_service)
        content_package["campaign_id"] = campaign_id

        await queue.put(ev.agent_done("content_agent"))

        # Stream individual asset types as they're extracted
        for asset_type in ["reel_script", "tiktok", "instagram_caption", "email", "website_hero"]:
            if asset_type in content_package:
                await queue.put(ev.asset_ready(
                    "content_agent", "copy",
                    content_package[asset_type],
                    label=asset_type.replace("_", " ").title(),
                ))

        # ── GATE 4: Approve content → PUBLISH ───────────────
        await queue.put(ev.human_gate(
            "approve_content",
            {
                "title": "Review content package — approve to publish",
                "content": content_package,
                "channels": [ch["channel"] for ch in strategy.get("channel_priority", [])],
                "warning": "Approving this will publish the campaign live.",
            },
            options=["approve", "revise", "reject"],
        ))
        gate4 = await wait_for_approval(campaign_id, "approve_content", queue)
        if gate4["decision"] in ("reject", "timeout"):
            await queue.put(ev.pipeline_done(campaign_id, {"status": "rejected_at_content"}))
            return

        # ── AGENT 5: EXECUTION ──────────────────────────────
        await queue.put(ev.agent_start(
            "execution_agent",
            "Publishing to all platforms — Instagram, TikTok, Email, Website, YouTube, CTV..."
        ))

        exec_input = {
            "campaign_id": campaign_id,
            "content_package": content_package,
            "strategy": strategy,
        }
        execution_report = await run_agent(execution_agent, exec_input, queue, session_service)
        execution_report["campaign_id"] = campaign_id

        await queue.put(ev.agent_done("execution_agent"))
        await queue.put(ev.asset_ready(
            "execution_agent", "execution_report", execution_report,
            label="Campaign live — execution report",
        ))

        # ── SCHEDULE PERFORMANCE MONITORING ─────────────────
        # Agent 6 runs on Cloud Scheduler every 6h
        # Here we just store the campaign for monitoring
        await _register_for_monitoring(campaign_id, execution_report)

        await queue.put(ev.pipeline_done(campaign_id, {
            "status": "live",
            "campaign_id": campaign_id,
            "channels_live": [
                ch["channel"] for ch in execution_report.get("channels_published", [])
                if ch.get("status") == "success"
            ],
            "execution_report": execution_report,
        }))

    except Exception as e:
        await queue.put(ev.error("pipeline", f"Pipeline error: {str(e)}", recoverable=False))
        raise


async def _register_for_monitoring(campaign_id: str, execution_report: dict) -> None:
    """Register campaign in Firestore so Performance Agent can find it."""
    try:
        db = _firestore()
        await db.collection("live_campaigns").document(campaign_id).set({
            "campaign_id": campaign_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "live",
            "execution_report": execution_report,
            "next_check": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass  # Non-fatal — scheduler can also discover via BigQuery


# ── Performance Agent runner (called by Cloud Scheduler) ───

async def run_performance_check(campaign_id: str | None = None) -> dict:
    """
    Run the Performance Agent for one or all live campaigns.
    Called every 6h by Cloud Scheduler via POST /performance/run.
    """
    queue: asyncio.Queue = asyncio.Queue()  # throwaway queue for scheduler runs
    session_service = InMemorySessionService()

    # Get list of live campaigns
    db = _firestore()
    if campaign_id:
        docs = [await db.collection("live_campaigns").document(campaign_id).get()]
    else:
        docs = [doc async for doc in db.collection("live_campaigns")
                .where("status", "==", "live").stream()]

    results = []
    for doc in docs:
        if not doc.exists:
            continue
        data = doc.to_dict()
        cid = data["campaign_id"]

        await queue.put(ev.agent_start("performance_agent", f"Checking {cid}..."))
        report = await run_agent(performance_agent, data, queue, session_service)
        results.append(report)

        # If optimisation loop triggered, restart pipeline from KV Agent
        if report.get("optimisation_loop_triggered"):
            asyncio.create_task(
                restart_from_kv(cid, report.get("optimisation_brief", {}))
            )

    return {"checked": len(results), "results": results}


async def restart_from_kv(campaign_id: str, optimisation_brief: dict) -> None:
    """Restart the creative loop from KV Agent (the dashed optimisation loop)."""
    queue: asyncio.Queue = asyncio.Queue()
    # In production, this queue would feed a new SSE stream for the optimisation run
    # For now, we log it
    print(f"[OPTIMISATION LOOP] Restarting KV for {campaign_id}: {optimisation_brief}")
