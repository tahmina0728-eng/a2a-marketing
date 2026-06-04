"""
main.py — CampaignOS ADK — FastAPI application.

Routes:
  POST /brief          → Run load_brand_context + Briefing Agent (briefing_pipeline)
  POST /pipeline       → Run full Workflow DAG pipeline (root_agent)
  GET  /health         → Liveness probe (Cloud Run)
  GET  /readiness      → Readiness probe (Cloud Run)
  POST /refresh        → Re-init search client

Authentication: --no-allow-unauthenticated on Cloud Run.
Callers must pass: Authorization: Bearer $(gcloud auth print-identity-token)
"""

import asyncio
import json
import os
import time
import uuid
import structlog
from contextlib import asynccontextmanager

# Load .env early so GROQ_API_KEY is in os.environ before agents.py imports
from dotenv import load_dotenv
load_dotenv()
if os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# ── Per-campaign SSE event store ──────────────────────────────────────────────
# Index-based: each SSE client tracks its own read position in the events list.
# No queue needed — avoids duplicate replay bugs.
_pipelines: dict[str, dict] = {}  # {cid: {"events": [...], "signal": asyncio.Event}}


async def push_event(cid: str, agent: str, status: str, message: str) -> None:
    if cid not in _pipelines:
        return
    event = {"agent": agent, "status": status, "message": message, "t": int(time.time())}
    _pipelines[cid]["events"].append(event)
    _pipelines[cid]["signal"].set()   # wake any waiting SSE generators


async def _heartbeat(cid: str, agent: str, msgs: list, interval: int = 22) -> None:
    """Push rolling status messages while a long operation runs."""
    import itertools
    for msg in itertools.cycle(msgs):
        await asyncio.sleep(interval)
        await push_event(cid, agent, "running", msg)

from app.config import get_settings
from app.models import BriefRequest
from app.pipeline import briefing_pipeline, root_agent
from app.creative_pipeline import experiment_pipeline
from app.runner import run_agent, run_strategy_with_groq, run_copy_with_groq, run_creative_pipeline_direct

logger   = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm all agents and the Search App client on startup."""
    logger.info(
        "campaignos_adk_startup",
        environment     = settings.environment,
        model_reasoning = settings.gemini_model_reasoning,
        model_image     = settings.gemini_model_image,
        search_engine   = settings.search_engine_id,
    )
    try:
        from app.search_client import get_search_client
        get_search_client()
        logger.info("agents_and_search_client_ready")
    except Exception as e:
        logger.warning("prewarm_failed", error=str(e))
    yield
    logger.info("campaignos_adk_shutdown")


app = FastAPI(
    title       = "CampaignOS — ADK Pipeline",
    description = (
        "CampaignOS powered by Google ADK 2.0 + Vertex AI. "
        "Workflow DAG campaign production pipeline with HITL gates. "
        "KV image pipeline: Gemini text-to-image → Pillow copy overlay → "
        "Nano Banana 2 image-to-image bake."
    ),
    version     = "3.1.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            },
        )
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# ── ROUTES ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Liveness probe — returns 200 while server is running."""
    return {
        "status":          "healthy",
        "service":         settings.service_name,
        "version":         "3.1.0",
        "framework":       "Google ADK 2.0 Workflow",
        "model_reasoning": settings.gemini_model_reasoning,
        "model_image":     settings.gemini_model_image,
        "search_engine":   settings.search_engine_id,
        "environment":     settings.environment,
    }


@app.get("/readiness")
def readiness():
    """Readiness probe — checks pipeline and search client are available."""
    from app.search_client import _client as _search_client

    ready = all([
        root_agent          is not None,
        briefing_pipeline   is not None,
    ])
    return {
        "ready":              ready,
        "briefing_pipeline":  briefing_pipeline is not None,
        "pipeline":           root_agent        is not None,
        "search_client":      _search_client    is not None,
    }


@app.post("/brief")
async def process_brief(brief: BriefRequest):
    """
    Run the Briefing Pipeline on a campaign brief.

    Executes:
      1. load_brand_context (zero LLM) — loads brand guidelines, product map,
         benchmark data, and brand locks from GCS / local bucket
      2. briefing_agent — validates the brief, scores Fan Truth, flags KPIs,
         and produces a MachineBrief

    The MachineBrief is saved as an ADK artifact and returned in the response.
    """
    campaign_id = (
        f"{brief.campaign_name.lower().replace(' ', '-')[:25]}"
        f"-{str(uuid.uuid4())[:8]}"
    )
    try:
        result, ms = await run_agent(
            agent       = briefing_pipeline,
            input_data  = brief.model_dump(),
            campaign_id = campaign_id,
        )
        return {
            "status":             "ok",
            "campaign_id":        campaign_id,
            "machine_brief":      result,
            "processing_time_ms": ms,
        }
    except ValueError as e:
        logger.error("brief_validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        logger.error("brief_runtime_error", error=str(e))
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("brief_unexpected_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.options("/brief-full")
async def brief_full_preflight():
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })


@app.post("/brief-full")
async def run_brief_full(brief: BriefRequest):
    """
    Full Groq-powered pipeline: Brief → Strategy → Copy.
    Returns machine_brief + creative_strategy + campaign_copy in one call.
    """
    campaign_id = (
        f"{brief.campaign_name.lower().replace(' ', '-')[:25]}"
        f"-{str(uuid.uuid4())[:8]}"
    )
    try:
        # Stage 1: Brief validation
        machine_brief, ms1 = await run_agent(
            agent       = briefing_pipeline,
            input_data  = brief.model_dump(),
            campaign_id = campaign_id,
        )
        machine_brief.setdefault("campaign_id", campaign_id)

        # Stage 2: Creative strategy
        brand_guidelines = machine_brief.pop("brand_guidelines", "")
        brand_locks      = machine_brief.pop("brand_locks_json", "{}")
        strategy = await run_strategy_with_groq(machine_brief, brand_guidelines, brand_locks)

        # Stage 3: Campaign copy
        copy = await run_copy_with_groq(machine_brief, strategy, brand_locks)

        return {
            "status":            "ok",
            "campaign_id":       campaign_id,
            "machine_brief":     machine_brief,
            "creative_strategy": strategy,
            "campaign_copy":     copy,
            "processing_time_ms": ms1,
        }
    except Exception as e:
        logger.error("brief_full_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.options("/campaign")
async def campaign_preflight():
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })


async def _run_campaign_background(campaign_id: str, brief: BriefRequest) -> None:
    """Background task: run the full pipeline and push SSE events at each stage."""
    t_start = time.time()
    try:
        # ── Stage 1a: Brief validation ────────────────────────────────────
        await push_event(campaign_id, "briefing", "running", "Loading brand guidelines & audience data…")
        logger.info("campaign_stage1_start", campaign_id=campaign_id)
        hb1 = asyncio.create_task(_heartbeat(campaign_id, "briefing", [
            "Querying Fan Truth benchmarks from CDP…",
            "Scoring campaign KPIs against historical data…",
            "Gemini 2.5 Flash is validating your brief…",
            "Cross-checking audience insights & channel data…",
            "Almost there — scoring Fan Truth quality…",
        ], interval=22))
        try:
            machine_brief, ms1 = await run_agent(
                agent       = briefing_pipeline,
                input_data  = brief.model_dump(),
                campaign_id = campaign_id,
            )
        finally:
            hb1.cancel()
        machine_brief.setdefault("campaign_id", campaign_id)
        brand_guidelines  = machine_brief.pop("brand_guidelines", "")
        brand_locks       = machine_brief.pop("brand_locks_json", "{}")
        audience_insights = machine_brief.pop("audience_insights", "")
        ft = machine_brief.get("fan_truth", {})
        ft_score   = ft.get("overall", 0)   if isinstance(ft, dict) else 0
        ft_verdict = ft.get("verdict", "—") if isinstance(ft, dict) else "—"
        await push_event(campaign_id, "briefing", "done",
            f"Brief validated ✓ — Fan Truth {ft_verdict} {ft_score}/100")
        # Milestone: push structured fan truth + audience data for rich UI card
        aud_lines = [l for l in audience_insights.split("\n") if l.strip()]
        def _extract(lines, key):
            l = next((x for x in lines if key.lower() in x.lower()), "")
            return l.split(":")[-1].strip() if ":" in l else ""
        await push_event(campaign_id, "briefing", "milestone", json.dumps({
            "fan_truth": ft if isinstance(ft, dict) else {},
            "kpis": machine_brief.get("kpis", []),
            "validation_notes": machine_brief.get("validation_notes", ""),
            "audience": {
                "count":    _extract(aud_lines, "profiles"),
                "income":   _extract(aud_lines, "income"),
                "channels": _extract(aud_lines, "channels"),
                "crm":      next((l for l in aud_lines if "crm" in l.lower() or '"' in l), ""),
            },
        }))
        await asyncio.sleep(4)  # Pause so UI shows Fan Truth gauge before strategy takes over

        # ── Stage 1b: Creative strategy ───────────────────────────────────
        await push_event(campaign_id, "strategy", "running", "Building creative strategy & hero message…")
        hb2 = asyncio.create_task(_heartbeat(campaign_id, "strategy", [
            "Analysing brand voice & creative principles…",
            "Crafting the campaign hero message…",
            "Defining strategic framework & messaging pillars…",
        ], interval=20))
        try:
            strategy = await run_strategy_with_groq(machine_brief, brand_guidelines, brand_locks)
        finally:
            hb2.cancel()
        await push_event(campaign_id, "strategy", "done",
            f'Strategy ready — "{strategy.get("hero_message", "")}"')
        await push_event(campaign_id, "strategy", "milestone", json.dumps({
            "hero_message":        strategy.get("hero_message", ""),
            "big_idea":            strategy.get("big_idea", ""),
            "tagline":             strategy.get("tagline", ""),
            "strategic_framework": strategy.get("strategic_framework", ""),
            "messaging_pillars":  strategy.get("messaging_pillars", []),
        }))
        await asyncio.sleep(4)  # Pause so UI shows strategy banner before copy takes over

        # ── Stage 1c: Campaign copy ───────────────────────────────────────
        await push_event(campaign_id, "copy", "running", "Writing headline, body & social copy variants…")
        hb3 = asyncio.create_task(_heartbeat(campaign_id, "copy", [
            "Writing billboard-ready short headline…",
            "Crafting Instagram & TikTok copy variants…",
            "Generating CTA and long-form body copy…",
        ], interval=18))
        try:
            copy = await run_copy_with_groq(machine_brief, strategy, brand_locks)
        finally:
            hb3.cancel()
        short_hl  = (copy.get("short")  or {}).get("headline", "")
        medium_hl = (copy.get("medium") or {}).get("headline", "")
        await push_event(campaign_id, "copy", "done",
            f'Copy ready — "{short_hl}"' if short_hl else "Copy variants ready ✓")
        await push_event(campaign_id, "copy", "milestone", json.dumps({
            "short_headline":  short_hl,
            "medium_headline": medium_hl,
            "long_headline":   (copy.get("long") or {}).get("headline", ""),
            "body":            (copy.get("long") or {}).get("body", "")[:160] if copy.get("long") else "",
            "cta":             copy.get("cta", ""),
            "instagram":       copy.get("instagram_caption", "")[:120] if copy.get("instagram_caption") else "",
            "tiktok_hook":     copy.get("tiktok_hook", ""),
        }))
        await asyncio.sleep(4)  # Pause so UI shows copy deck before culture takes over

        if audience_insights:
            machine_brief["audience_insights"] = audience_insights
        logger.info("campaign_stage1_done", campaign_id=campaign_id)

        # ── Stage 2: Creative pipeline ────────────────────────────────────
        logger.info("campaign_stage2_start", campaign_id=campaign_id)
        from app.brand_assets import get_asset_loader
        loader   = get_asset_loader()
        products = loader.list_products(brief.brand) if brief.brand else []
        logos    = loader.list_logos(brief.brand)    if brief.brand else []
        assets   = loader.list_assets(brief.brand)   if brief.brand else []

        aud = brief.audience
        audience_desc = (
            f"{aud.segment if hasattr(aud, 'segment') else aud} "
            f"{aud.age_range if hasattr(aud, 'age_range') else ''}, "
            f"{brief.market}, {brief.season} season"
        ).strip(", ")

        async def _progress(agent: str, status: str, message: str):
            await push_event(campaign_id, agent, status, message)

        t2 = time.time()
        creative_result = await run_creative_pipeline_direct(
            brand            = brief.brand,
            audience         = audience_desc,
            product_uris     = products[:3],
            asset_uris       = assets[:3],
            logo_uri         = logos[0] if logos else "",
            brand_guidelines = brand_guidelines,
            big_idea_seed    = strategy.get("hero_message", ""),
            campaign_id      = campaign_id,
            progress_cb      = _progress,
        )
        ms2 = int((time.time() - t2) * 1000)
        logger.info("campaign_stage2_done", campaign_id=campaign_id, ms2=ms2,
                    has_image=bool(creative_result.get("image_b64")))

        result = {
            "status":             "ok",
            "campaign_id":        campaign_id,
            "machine_brief":      machine_brief,
            "creative_strategy":  strategy,
            "campaign_copy":      copy,
            "creative_pipeline":  creative_result,
            "processing_time_ms": int((time.time() - t_start) * 1000),
        }
        await push_event(campaign_id, "__done__", "done", json.dumps(result))

    except Exception as e:
        logger.error("campaign_error", campaign_id=campaign_id, error=str(e))
        await push_event(campaign_id, "__error__", "error", str(e))


@app.post("/campaign")
async def run_full_campaign(brief: BriefRequest):
    """Start full campaign pipeline — returns campaign_id immediately, streams progress via /events/{id}."""
    campaign_id = (
        f"campaign-{brief.campaign_name.lower().replace(' ', '-')[:20]}"
        f"-{str(uuid.uuid4())[:6]}"
    )
    _pipelines[campaign_id] = {"events": [], "signal": asyncio.Event()}
    asyncio.create_task(_run_campaign_background(campaign_id, brief))
    return {"campaign_id": campaign_id, "status": "started"}


@app.get("/events/{campaign_id}")
async def campaign_events(campaign_id: str):
    """SSE stream of pipeline progress events for a running campaign."""
    if campaign_id not in _pipelines:
        raise HTTPException(status_code=404, detail="Campaign not found")

    async def generate():
        idx = 0
        while campaign_id in _pipelines:
            store = _pipelines[campaign_id]
            events = store["events"]
            # Yield any new events since last read
            while idx < len(events):
                ev = events[idx]
                idx += 1
                yield f"data: {json.dumps(ev)}\n\n"
                if ev.get("agent") in ("__done__", "__error__"):
                    _pipelines.pop(campaign_id, None)
                    return
            # Wait for the next push_event signal
            store["signal"].clear()
            try:
                await asyncio.wait_for(store["signal"].wait(), timeout=600)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'agent': '__error__', 'status': 'error', 'message': 'Pipeline timed out'})}\n\n"
                _pipelines.pop(campaign_id, None)
                return

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


@app.post("/pipeline")
async def run_pipeline(brief: BriefRequest):
    """
    Run the full CampaignOS Workflow DAG pipeline.

    Runs the complete ADK 2.0 Workflow:
      load_brand_context → Briefing → HITL Approval → Strategy
      → KV fan-out x4 (concept → background → Pillow overlay → swap bake)
      → KV Ranker → HITL KV Selection → Channel Router → Content
      → Execution → Aggregation → Performance

    HITL gates require VertexAiSessionService for cross-request persistence.
    InMemorySessionService is used in this build (state lost on restart).
    """
    campaign_id = (
        f"pipeline-{brief.campaign_name.lower().replace(' ', '-')[:20]}"
        f"-{str(uuid.uuid4())[:6]}"
    )
    try:
        result, ms = await run_agent(
            agent       = root_agent,
            input_data  = brief.model_dump(),
            campaign_id = campaign_id,
        )
        return {
            "status":             "ok",
            "campaign_id":        campaign_id,
            "pipeline_output":    result,
            "processing_time_ms": ms,
        }
    except Exception as e:
        logger.error("pipeline_error", campaign_id=campaign_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")


@app.post("/refresh")
async def refresh():
    """
    Re-initialise all agents and the Search App client.
    Call after updating brand guidelines, adding new CSV data,
    or changing Search App configuration.
    """
    import app.search_client as sc
    sc._client = None
    try:
        sc.get_search_client()
        return {"status": "refreshed", "search_client": "re-initialised"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Refresh failed: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": "Internal server error"},
    )


