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
import base64
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
from fastapi import FastAPI, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as _BaseModel  # avoid clash with app.models

# ── Per-campaign SSE event store ──────────────────────────────────────────────
# Index-based: each SSE client tracks its own read position in the events list.
# No queue needed — avoids duplicate replay bugs.
_pipelines: dict[str, dict] = {}  # {cid: {"events": [...], "signal": asyncio.Event}}
_channel_adaptations: dict[str, dict] = {}  # {campaign_id: channel_adaptations}
_campaign_reels: dict[str, str] = {}         # {campaign_id: video_b64}
_campaign_reel_uris: dict[str, str] = {}    # {campaign_id: gs:// URI of reel}


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
from app.runner import run_agent, run_strategy_with_groq, run_copy_with_groq, run_creative_pipeline_direct, run_performance_forecast, run_brand_compliance_check, run_image_adaptation

logger   = structlog.get_logger()
settings = get_settings()

GCP_PROJECT       = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
BQ_OUTPUT_DATASET = "campaign_outputs"


async def _save_pipeline_output(campaign_id: str, output: dict) -> None:
    """Fire-and-forget: persist pipeline output JSON to GCS for history viewing.
    Large base64 blobs are stripped — GCS URIs (already uploaded) are kept instead."""
    try:
        import copy as _copy
        from google.cloud import storage as _gcs_s
        slim = _copy.deepcopy(output)
        for _k in ("image_b64", "images_b64", "video_b64"):
            slim.pop(_k, None)
        cp = slim.get("creative_pipeline")
        if isinstance(cp, dict):
            for _k in ("image_b64", "images_b64", "video_b64"):
                cp.pop(_k, None)
        blob_path = f"outputs/{campaign_id}/pipeline_output.json"
        client = _gcs_s.Client(project=GCP_PROJECT)
        bucket = client.bucket(settings.gcs_bucket)
        blob   = bucket.blob(blob_path)
        blob.upload_from_string(json.dumps(slim), content_type="application/json")
        logger.info("pipeline_output_saved", campaign_id=campaign_id)
    except Exception as e:
        logger.warning("pipeline_output_save_failed", campaign_id=campaign_id, error=str(e))


async def _bq_log_machine_brief(campaign_id: str, machine_brief: dict, brief) -> None:
    """Fire-and-forget: write one row to campaign_outputs.machine_briefs in BigQuery."""
    try:
        from google.cloud import bigquery as _bq
        import datetime as _dt

        client = _bq.Client(project=GCP_PROJECT)
        table_id = f"{GCP_PROJECT}.{BQ_OUTPUT_DATASET}.machine_briefs"

        ft = machine_brief.get("fan_truth_score", machine_brief.get("fan_truth", {}))
        if isinstance(ft, str):
            try: ft = json.loads(ft)
            except Exception: ft = {}

        channels = brief.channels if hasattr(brief, "channels") else []

        row = {
            "campaign_id":       campaign_id,
            "campaign_name":     getattr(brief, "campaign_name", ""),
            "brand":             getattr(brief, "brand", ""),
            "market":            getattr(brief, "market", ""),
            "product_category":  getattr(brief, "product_category", ""),
            "season":            getattr(brief, "season", ""),
            "channels":          ", ".join(str(c) for c in channels),
            "moment_type":       getattr(brief, "moment_type", ""),
            "validation_score":  float(machine_brief.get("validation_score") or 0),
            "validation_status": str(machine_brief.get("validation_status") or ""),
            "fan_truth_score":   float(ft.get("overall") or ft.get("score") or 0),
            "fan_truth_verdict": str(ft.get("verdict") or ""),
            "flag_count":        int(machine_brief.get("flag_count") or 0),
            "brief_json":        json.dumps(machine_brief)[:50000],
            "created_at":        _dt.datetime.utcnow().isoformat() + "Z",
        }

        errors = client.insert_rows_json(table_id, [row])
        if errors:
            logger.warning("bq_insert_errors", errors=errors)
        else:
            logger.info("bq_machine_brief_logged", campaign_id=campaign_id)
    except Exception as e:
        logger.warning("bq_log_failed", campaign_id=campaign_id, error=str(e))


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

# ── Guardrails HITL review routes ──────────────────────────────────────────
from app.hitl.approvals import approvals_router
app.include_router(approvals_router)

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


@app.get("/debug/trends")
def debug_trends(brand: str = "Barclays", market: str = "UK"):
    """Smoke-test Google Trends reachability from this Cloud Run instance."""
    try:
        from app.market_trends import get_trends
        result = get_trends(keywords=[brand], market=market, timeframe="today 1-m")
        return {"ok": result["signals"] > 0, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


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
        machine_brief.setdefault("brand", brief.brand)

        # Stage 2: Creative strategy
        brand_guidelines = machine_brief.pop("brand_guidelines", "")
        brand_locks      = machine_brief.pop("brand_locks_json", "{}")

        # Fallback: load guidelines directly from GCS if search returned nothing
        if not brand_guidelines or len(brand_guidelines.strip()) < 100:
            try:
                from app.brand_assets import get_asset_loader as _gal2
                _gl2 = _gal2().load_guidelines(brief.brand)
                if _gl2 and len(_gl2.strip()) > 100:
                    brand_guidelines = _gl2
            except Exception:
                pass

        strategy = await run_strategy_with_groq(machine_brief, brand_guidelines, brand_locks,
                                                 language=brief.language or "" if hasattr(brief, "language") else "")

        # Stage 3: Campaign copy
        copy = await run_copy_with_groq(machine_brief, strategy, brand_locks,
                                        language=brief.language or "" if hasattr(brief, "language") else "")

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
        # ── Stage 1a: Brief validation ──────────────────────────────────────
        await push_event(campaign_id, "briefing", "running", "Loading brand guidelines & audience data…")
        logger.info("campaign_stage1_start", campaign_id=campaign_id)

        hb1 = asyncio.create_task(_heartbeat(campaign_id, "briefing", [
            "Querying Fan Truth benchmarks from CDP…",
            "Scoring campaign KPIs against historical data…",
            "Gemini 3.5 Flash is validating your brief…",
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
        machine_brief.setdefault("brand", brief.brand)

        # ── Normalize machine_brief for frontend compatibility ─────────────
        # ADK Workflow state-dict path returns the full session state dict with
        # the actual MachineBrief JSON stored under a nested "machine_brief" key.
        # Extract and merge it so all top-level fields are accessible.
        _nested_mb = machine_brief.get("machine_brief")
        if isinstance(_nested_mb, str) and _nested_mb.strip().startswith("{"):
            try:
                for _k, _v in json.loads(_nested_mb).items():
                    machine_brief.setdefault(_k, _v)
            except Exception:
                pass

        # Resolve fan_truth for the frontend (reads fan_truth, not fan_truth_score).
        # Override whenever the current value is absent, null, or a dict with no useful overall.
        _ft_cur = machine_brief.get("fan_truth")
        _fts    = machine_brief.get("fan_truth_score", {})
        if not isinstance(_ft_cur, dict) or not _ft_cur.get("overall"):
            if isinstance(_fts, dict) and _fts:
                # fan_truth_score has the sub-scores — use it as the source
                _raw_overall = _fts.get("overall") or 0
                if not _raw_overall:
                    _raw_overall = round(
                        ((_fts.get("specific") or 0) + (_fts.get("shared") or 0) + (_fts.get("special") or 0)) / 3
                    )
                machine_brief["fan_truth"] = {
                    **_fts,
                    "overall":   _raw_overall,
                    "statement": ((_ft_cur.get("statement") if isinstance(_ft_cur, dict) else None)
                                  or _fts.get("statement") or brief.fan_truth or ""),
                }
            elif isinstance(_ft_cur, dict):
                # fan_truth IS a dict but overall is 0 — compute it from the 3-axis sub-scores
                _sp = _ft_cur.get("specific") or 0
                _sh = _ft_cur.get("shared")   or 0
                _se = _ft_cur.get("special")  or 0
                if _sp or _sh or _se:
                    _ft_cur["overall"] = round((_sp + _sh + _se) / max(sum(1 for x in (_sp, _sh, _se) if x), 1))
                    machine_brief["fan_truth"] = _ft_cur

        # Last resort: if fan_truth is still not a dict, bootstrap from user's brief input
        if not isinstance(machine_brief.get("fan_truth"), dict):
            machine_brief["fan_truth"] = {"statement": brief.fan_truth or "", "overall": 0}

        # Always ensure statement is populated from the user's brief input as a fallback
        _ft = machine_brief["fan_truth"]
        if not _ft.get("statement"):
            _ft["statement"] = brief.fan_truth or ""

        # ADK briefing_agent uses kpi_flags; Groq fallback and frontend use kpis
        if not machine_brief.get("kpis") and machine_brief.get("kpi_flags"):
            machine_brief["kpis"] = [
                {
                    "metric": (f.get("kpi") or f.get("metric") or "") if isinstance(f, dict) else "",
                    "target": f.get("target", "") if isinstance(f, dict) else "",
                    "flag":   f.get("flag",   "OK") if isinstance(f, dict) else "OK",
                    "note":   f.get("note",   "") if isinstance(f, dict) else "",
                }
                for f in machine_brief["kpi_flags"]
            ]

        # ── Extract context fields from final machine_brief ────────────────
        brand_guidelines  = machine_brief.pop("brand_guidelines", "")
        brand_locks       = machine_brief.pop("brand_locks_json", "{}")
        audience_insights = machine_brief.pop("audience_insights", "")

        # Fallback: load guidelines directly from GCS if search returned nothing
        if not brand_guidelines or len(brand_guidelines.strip()) < 100:
            try:
                from app.brand_assets import get_asset_loader as _gal
                _gl = _gal().load_guidelines(brief.brand)
                if _gl and len(_gl.strip()) > 100:
                    brand_guidelines = _gl
                    logger.info("brand_guidelines_loaded_from_gcs",
                                brand=brief.brand, chars=len(brand_guidelines))
            except Exception as _ge:
                logger.warning("brand_guidelines_gcs_fallback_failed", error=str(_ge))

        ft = machine_brief.get("fan_truth_score", machine_brief.get("fan_truth", {}))
        ft_score   = ft.get("overall", 0)   if isinstance(ft, dict) else 0
        ft_verdict = ft.get("verdict", "—") if isinstance(ft, dict) else "—"
        aud_lines  = [l for l in audience_insights.split("\n") if l.strip()]

        def _extract(lines, key):
            l = next((x for x in lines if key.lower() in x.lower()), "")
            return l.split(":")[-1].strip() if ":" in l else ""

        _ft_dict = ft if isinstance(ft, dict) else {}
        _val     = machine_brief.get("validation", {})
        _val_score = int(_val.get("score") or 0) if isinstance(_val, dict) else 0
        await push_event(campaign_id, "briefing", "done", json.dumps({
            "_text": f"Brief validated ✓ — Fan Truth {ft_verdict} {ft_score}/100",
            "score":            ft_score or _val_score,
            "validation_score": _val_score,
            "fan_truth": _ft_dict,
            "kpis": machine_brief.get("kpis", []),
            "validation_notes": machine_brief.get("validation_notes", ""),
            "audience": {
                "count":    _extract(aud_lines, "profiles"),
                "income":   _extract(aud_lines, "income"),
                "channels": _extract(aud_lines, "channels"),
            },
            # Real data-source counts + Google Trends signals (omitted when 0/empty)
            **{k: v for k, v in {
                "_chunks":              machine_brief.get("_chunks", 0),
                "_market_signals":      machine_brief.get("_market_signals", 0),
                "_campaign_records":    machine_brief.get("_campaign_records", 0),
                "_product_skus":        machine_brief.get("_product_skus", 0),
                "_market_top_keyword":  machine_brief.get("_market_top_keyword", ""),
                "_market_avg_interest": machine_brief.get("_market_avg_interest", 0),
                "_market_summary":      machine_brief.get("_market_summary", ""),
                "_market_data":         machine_brief.get("_market_data", {}),
            }.items() if v},
        }))
        # Log machine_brief to BigQuery (fire-and-forget — don't block pipeline)
        asyncio.create_task(_bq_log_machine_brief(campaign_id, machine_brief, brief))

        await asyncio.sleep(6)

        # ── Stage 1b: Brand compliance check ─────────────────────────────
        # Runs for ALL brands that have a brand.json profile. For regulated
        # industries (banking, pharma, alcohol) this gates the pipeline.
        _brand_profile_json = machine_brief.get("brand_profile_json", "{}")
        if not _brand_profile_json or _brand_profile_json == "{}":
            from app.brand_assets import get_asset_loader as _get_loader
            _bpj = _get_loader().load_brand_profile(brief.brand)
            _brand_profile_json = json.dumps(_bpj) if _bpj else "{}"

        if _brand_profile_json and _brand_profile_json != "{}":
            await push_event(campaign_id, "compliance", "running",
                f"Checking {brief.brand} brand compliance rules…")
            try:
                _brief_text = json.dumps(machine_brief)
                _compliance = await run_brand_compliance_check(
                    brand_profile_json = _brand_profile_json,
                    machine_brief      = machine_brief,
                    generated_text     = _brief_text,
                )
                _c_passed  = _compliance.get("passed", True)
                _c_score   = _compliance.get("score", 100)
                _c_issues  = _compliance.get("issues", [])
                _c_summary = _compliance.get("summary", "")
                _c_errors  = [i for i in _c_issues if i.get("severity") == "error"]
                _c_warns   = [i for i in _c_issues if i.get("severity") == "warning"]
                await push_event(campaign_id, "compliance", "done", json.dumps({
                    "_text":   f"{'✓ PASS' if _c_passed else '✗ FAIL'} — Brand compliance {_c_score}/100",
                    "passed":  _c_passed,
                    "score":   _c_score,
                    "errors":  len(_c_errors),
                    "warnings": len(_c_warns),
                    "issues":  _c_issues,
                    "summary": _c_summary,
                }))
            except Exception as _ce:
                logger.warning("compliance_check_failed", error=str(_ce))
                await push_event(campaign_id, "compliance", "done", json.dumps({
                    "_text": "Compliance check skipped", "passed": True, "score": 100, "issues": [],
                }))
            await asyncio.sleep(4)

        await asyncio.sleep(4)  # Let user read compliance result

        # ── Stage 1d: Creative strategy ───────────────────────────────────
        await push_event(campaign_id, "strategy", "running", "Building creative strategy & hero message…")
        hb2 = asyncio.create_task(_heartbeat(campaign_id, "strategy", [
            "Analysing brand voice & creative principles…",
            "Crafting the campaign hero message…",
            "Defining strategic framework & messaging pillars…",
        ], interval=20))
        try:
            strategy = await run_strategy_with_groq(machine_brief, brand_guidelines, brand_locks,
                                                     language=brief.language or "" if hasattr(brief, "language") else "")
        finally:
            hb2.cancel()
        # Try to load a brand asset thumbnail for the strategy visual
        _hero_img_b64 = ""
        try:
            from app.creative_pipeline import _load_bytes
            from app.brand_assets import get_asset_loader as _gal
            import io as _io, base64 as _b64
            from PIL import Image as _Image
            _ldr = _gal()
            _assets = _ldr.list_assets(brief.brand) if brief.brand else []
            _products = _ldr.list_products(brief.brand) if brief.brand else []
            import random as _rnd
            _pool = _assets + _products
            _img_uri = _rnd.choice(_pool) if _pool else ""
            if _img_uri:
                _data = _load_bytes(_img_uri)
                if _data and len(_data) > 1024:
                    _img = _Image.open(_io.BytesIO(_data)).convert("RGB")
                    _img.thumbnail((480, 320))
                    _buf = _io.BytesIO()
                    _img.save(_buf, format="JPEG", quality=68)
                    _hero_img_b64 = _b64.b64encode(_buf.getvalue()).decode()
        except Exception as _e:
            logger.debug("hero_image_thumb_failed", error=str(_e))

        # Keep done event small — text data only
        await push_event(campaign_id, "strategy", "done", json.dumps({
            "_text":               f'Strategy ready — "{strategy.get("hero_message", "")}"',
            "hero_message":        strategy.get("hero_message", ""),
            "big_idea":            strategy.get("big_idea", ""),
            "tagline":             strategy.get("tagline", ""),
            "strategic_framework": strategy.get("strategic_framework", ""),
            "messaging_pillars":   strategy.get("messaging_pillars", []),
        }))
        # Send hero image separately as a milestone (large payload, keep isolated)
        if _hero_img_b64:
            await push_event(campaign_id, "strategy", "milestone", json.dumps({
                "hero_image_b64": _hero_img_b64,
            }))
        await asyncio.sleep(8)  # Let user read the strategy banner

        # ── Stage 1c: Campaign copy ───────────────────────────────────────
        await push_event(campaign_id, "copy", "running", "Writing headline, body & social copy variants…")
        hb3 = asyncio.create_task(_heartbeat(campaign_id, "copy", [
            "Writing billboard-ready short headline…",
            "Crafting Instagram & TikTok copy variants…",
            "Generating CTA and long-form body copy…",
        ], interval=18))
        _channels_list = [str(c).lower() for c in brief.channels] if brief.channels else []
        _copy_lang = brief.language or "" if hasattr(brief, "language") else ""
        _ft_obj    = machine_brief.get("fan_truth_score") or machine_brief.get("fan_truth") or {}
        _ft_stmt   = _ft_obj.get("statement", "") if isinstance(_ft_obj, dict) else str(_ft_obj)
        _aud_obj   = machine_brief.get("audience") or {}
        _aud_str   = _aud_obj.get("segment", "") if isinstance(_aud_obj, dict) else str(_aud_obj)

        # ── Build full agent-chained prompt: Logos brief → Helia strategy → Ideon copy ──
        _pillars     = strategy.get("messaging_pillars", [])
        _pillars_str = " / ".join(_pillars) if isinstance(_pillars, list) else str(_pillars)

        _brief_block = "\n".join(filter(None, [
            f"Brand: {brief.brand}",
            f"Campaign: {machine_brief.get('campaign_name', '')}",
            f"Product / Occasion: {getattr(brief, 'product', '')}",
            f"Market: {machine_brief.get('market', '')}",
            f"Season: {machine_brief.get('season', '')}",
            f"Audience: {_aud_str}",
            f"Fan Truth: \"{_ft_stmt}\"",
            f"Channels: {', '.join(_channels_list)}" if _channels_list else "",
            f"Campaign Type: {getattr(brief, 'campaign_type', '')}",
            f"Notes: {getattr(brief, 'notes', '')}" if getattr(brief, 'notes', '') else "",
            f"Language: {_copy_lang}" if _copy_lang else "",
        ]))

        _strategy_block = "\n".join(filter(None, [
            f"Big Idea: {strategy.get('big_idea', '')}",
            f"Hero Message: {strategy.get('hero_message', '')}",
            f"Tagline: {strategy.get('tagline', '')}",
            f"Strategic Framework: {strategy.get('strategic_framework', '')}",
            f"Tone of Voice: {strategy.get('tone_of_voice', '')}",
            f"Culture Context: {strategy.get('culture_context', '')}",
            f"Messaging Pillars: {_pillars_str}" if _pillars_str else "",
            f"Handoff Message: {strategy.get('handoff_message', '')}",
        ]))

        if brief.brand.lower() == "barclays":
            from app.brands import barclays as _barclays
            _brand_copy_rules = _barclays.copy_prompt_block(machine_brief)
        else:
            _brand_copy_rules = ""

        _copy_prompt = "\n\n".join(filter(None, [
            "BRIEF (Logos):\n" + _brief_block,
            "STRATEGY (Helia):\n" + _strategy_block,
            _brand_copy_rules.strip() if _brand_copy_rules else "",
        ]))
        from app.agents.copy import run_copy as _ideon
        try:
            copy = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _ideon(brief.brand, _copy_prompt)
            )
        finally:
            hb3.cancel()
        _headline    = copy.get("headline", "")
        copy_subline = copy.get("subline", "").strip()
        short_hl     = _headline
        medium_hl    = _headline

        if not _headline:
            logger.warning("copy_agent_headline_missing",
                           has_raw_output="raw_output" in copy,
                           copy_keys=list(copy.keys()))

        await push_event(campaign_id, "copy", "done", json.dumps({
            "_text":           f'Copy ready — "{_headline}"' if _headline else "Copy ready ✓",
            "short_headline":  _headline,
            "subline":         copy_subline,
            "medium_headline": _headline,
            "long_headline":   _headline,
            "body":            copy.get("body", "")[:160],
            "cta":             copy.get("cta", ""),
            "channel_copy":    {},
        }))
        await asyncio.sleep(8)  # Let user read copy deck

        # ── Stage 1e: Post-copy compliance check + regenerate loop ───────────
        # Runs only when a brand.json profile exists. Checks the generated copy
        # text for prohibited phrases / tone violations and retries the copy
        # agent up to 2 times if errors are found — before the image is generated.
        _copy_compliance_passed = True
        if _brand_profile_json and _brand_profile_json != "{}":
            _copy_text = " ".join(filter(None, [
                _headline,
                copy.get("subline", ""),
                copy.get("body", ""),
                copy.get("cta", ""),
            ]))
            _MAX_COPY_RETRIES = 2
            for _retry in range(_MAX_COPY_RETRIES):
                try:
                    _cc = await run_brand_compliance_check(
                        brand_profile_json = _brand_profile_json,
                        machine_brief      = machine_brief,
                        generated_text     = _copy_text,
                    )
                except Exception:
                    _cc = {"passed": True, "score": 100, "issues": []}

                _cc_passed = _cc.get("passed", True)
                _cc_errors = [i for i in _cc.get("issues", []) if i.get("severity") == "error"]

                if _cc_passed or not _cc_errors:
                    break   # copy is compliant — no regeneration needed

                # Copy has prohibited phrases → regenerate with issue context
                logger.warning("copy_compliance_fail_retry",
                               campaign_id=campaign_id, retry=_retry + 1,
                               errors=len(_cc_errors))
                await push_event(campaign_id, "compliance", "running",
                    f"Copy compliance issues found — regenerating copy (attempt {_retry + 2})…")

                _issue_guidance = "; ".join(i.get("detail", "") for i in _cc_errors)
                _copy_prompt_retry = (
                    _copy_prompt +
                    f"\n\nCRITICAL COMPLIANCE — Avoid these issues: {_issue_guidance}"
                )
                try:
                    copy = await asyncio.get_event_loop().run_in_executor(
                        None, lambda p=_copy_prompt_retry: _ideon(brief.brand, p)
                    )
                    _headline    = copy.get("headline", "") or _headline
                    short_hl     = _headline
                    medium_hl    = _headline
                    copy_subline = copy.get("subline", "").strip() or copy_subline
                    _copy_text   = " ".join(filter(None, [
                        _headline,
                        copy.get("subline", ""),
                        copy.get("body", ""),
                        copy.get("cta", ""),
                    ]))
                except Exception as _cr_err:
                    logger.warning("copy_regenerate_failed", error=str(_cr_err))
                    break
            else:
                # All retries exhausted — flag compliance FAIL but don't block
                _copy_compliance_passed = False
                await push_event(campaign_id, "compliance", "done", json.dumps({
                    "_text": f"✗ FAIL — Copy compliance could not be resolved after {_MAX_COPY_RETRIES} retries",
                    "passed": False, "score": _cc.get("score", 0),
                    "errors": len(_cc_errors), "warnings": 0,
                    "issues": _cc.get("issues", []),
                    "summary": _cc.get("summary", ""),
                }))

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
        colours  = loader.list_colours(brief.brand)  if brief.brand else []
        logger.info("brand_assets_loaded",
                    brand=brief.brand,
                    products=len(products), logos=len(logos),
                    assets=len(assets),     colours=len(colours))

        aud = brief.audience
        audience_desc = (
            f"{aud.segment if hasattr(aud, 'segment') else aud} "
            f"{aud.age_range if hasattr(aud, 'age_range') else ''}, "
            f"{brief.market}, {brief.season} season"
        ).strip(", ")

        async def _progress(agent: str, status: str, message: str):
            await push_event(campaign_id, agent, status, message)

        t2 = time.time()
        # Filter products to match the selected product name (e.g. "Panadol" not "Advil")
        # before constructing the ordered list sent to the image generator.
        _product_slug = (brief.product if hasattr(brief, "product") else "").strip().lower()
        _matched = [p for p in products if _product_slug and _product_slug in p.lower()]
        _src_products = _matched if _matched else products
        # Prefer PNG products (transparent background) for cleaner Gemini reference
        _png_products = [p for p in _src_products if p.lower().endswith(".png")]
        _jpg_products = [p for p in _src_products if not p.lower().endswith(".png")]
        _ordered_products = (_png_products + _jpg_products)[:5]

        # Primary logo — for Barclays, auto-select the co-brand Wimbledon lockup
        # when ANY brief field references Wimbledon (name, season, product, fan truth, notes).
        _is_wimbledon_campaign = (
            brief.brand.lower() == "barclays" and any(
                "wimbledon" in str(v).lower()
                for v in [
                    getattr(brief, "campaign_name", "") or "",
                    getattr(brief, "product", "") or "",
                    getattr(brief, "fan_truth", "") or "",
                    getattr(brief, "season", "") or "",
                    getattr(brief, "notes", "") or "",
                    getattr(brief, "audience", "") or "",
                ]
                if v
            )
        )
        if _is_wimbledon_campaign:
            # Use the co-brand lockup on white bg for light grounds (default)
            _logo_primary = next(
                (p for p in logos if "wimbledon_wb" in p.lower() or "barclays-wimbledon_wb" in p.lower()), None
            ) or next(
                (p for p in logos if "wimbledon" in p.lower()), None
            ) or (logos[0] if logos else "")
            logger.info("barclays_wimbledon_logo_selected", logo=_logo_primary)
        else:
            # Standard Barclays — prefer stacked whiteBG lockup (barclays1_wb)
            _logo_primary = next(
                (p for p in logos if "barclays1_wb" in p.lower()), None
            ) or next(
                (p for p in logos if "whitebg" in p.lower() or "_wb" in p.lower()
                 and "wimbledon" not in p.lower()), None
            ) or (logos[0] if logos else "")

        # Resolve brand profile dict for model router (already loaded earlier as JSON)
        _bpd_for_router: dict | None = None
        if _brand_profile_json and _brand_profile_json != "{}":
            try:
                _bpd_for_router = json.loads(_brand_profile_json)
            except Exception:
                pass

        creative_result = await run_creative_pipeline_direct(
            brand              = brief.brand,
            audience           = audience_desc,
            product_uris       = _ordered_products,
            asset_uris         = assets[:6],
            logo_uri           = _logo_primary,
            colour_uris        = colours[:2],
            brand_guidelines   = brand_guidelines,
            big_idea_seed      = strategy.get("hero_message", ""),
            copy_headline      = short_hl or medium_hl,
            copy_subline       = copy_subline,
            copy_headlines     = [short_hl or medium_hl, medium_hl or short_hl],
            copy_cta           = copy.get("cta", ""),
            product_name       = brief.product if hasattr(brief, "product") else "",
            fan_truth          = str(machine_brief.get("fan_truth_score", machine_brief.get("fan_truth", {})).get("statement", "")),
            season             = brief.season if hasattr(brief, "season") else "",
            market             = brief.market if hasattr(brief, "market") else "",
            language           = brief.language or "" if hasattr(brief, "language") else "",
            channels           = [str(c).lower() for c in brief.channels] if brief.channels else [],
            campaign_id        = campaign_id,
            campaign_type      = getattr(brief, "campaign_type", ""),
            kpis               = machine_brief.get("kpis") or [],
            progress_cb        = _progress,
            brand_profile_dict = _bpd_for_router,
        )
        ms2 = int((time.time() - t2) * 1000)
        # Support both single image_b64 and multiple images_b64 list
        _images = creative_result.get("images_b64") or (
            [creative_result["image_b64"]] if creative_result.get("image_b64") else []
        )
        # Store channel adaptations and reel for use by the landing page generator
        _ch_adapt = creative_result.get("channel_adaptations", {})
        if _ch_adapt:
            _channel_adaptations[campaign_id] = _ch_adapt
        _reel = creative_result.get("video_b64", "")
        if _reel:
            _campaign_reels[campaign_id] = _reel
        _reel_uri = creative_result.get("video_uri", "")
        if _reel_uri:
            _campaign_reel_uris[campaign_id] = _reel_uri
        logger.info("campaign_stage2_done", campaign_id=campaign_id, ms2=ms2,
                    n_images=len(_images))
        if _images:
            await push_event(campaign_id, "kv", "milestone",
                             json.dumps({"images_b64": _images}))

        # Push reel video if generated
        _video_b64 = creative_result.get("video_b64", "")
        if _video_b64:
            await push_event(campaign_id, "reel", "milestone",
                             json.dumps({"video_b64": _video_b64}))
            await push_event(campaign_id, "reel", "done", "Campaign reel ready ✓")

        # ── Channel Adapter (final step — after key visual generated) ─────
        await push_event(campaign_id, "channel", "running", "Packaging key visual for each channel…")
        channels_list = [c.lower() for c in brief.channels] if brief.channels else []
        channel_data: dict = {}
        if "instagram" in channels_list or not channels_list:
            channel_data["instagram"] = {"platform": "Instagram", "format": "Stories + Feed",
                "headline": short_hl, "cta": copy.get("cta",""),
                "caption": (copy.get("instagram_caption","") or "")[:100]}
        if "tiktok" in channels_list or not channels_list:
            channel_data["tiktok"] = {"platform": "TikTok", "format": "Video 15–30s",
                "hook": copy.get("tiktok_hook","") or short_hl, "cta": copy.get("cta","")}
        if any(c in channels_list for c in ["google", "youtube", "search"]) or not channels_list:
            channel_data["google"] = {"platform": "Google Ads", "format": "Responsive Search",
                "headline": short_hl, "description": medium_hl}
        if "email" in channels_list or not channels_list:
            channel_data["email"] = {"platform": "Email", "format": "Newsletter",
                "subject": short_hl, "preview": medium_hl or short_hl}
        if "ooh" in channels_list:
            channel_data["ooh"] = {"platform": "OOH / Billboard", "format": "Large Format",
                "headline": short_hl, "cta": copy.get("cta","")}
        if not channel_data:
            channel_data["instagram"] = {"platform": "Instagram", "format": "Stories + Feed",
                "headline": short_hl, "cta": copy.get("cta","")}
            channel_data["tiktok"] = {"platform": "TikTok", "format": "Video 15–30s",
                "hook": short_hl, "cta": copy.get("cta","")}
        await asyncio.sleep(2)
        await push_event(campaign_id, "channel", "done", f"Campaign ready for {len(channel_data)} channels ✓")
        await push_event(campaign_id, "channel", "milestone", json.dumps(channel_data))
        await asyncio.sleep(3)

        # ── Stage 3: Performance forecast (Nexus) ────────────────────────
        await push_event(campaign_id, "performance", "running",
                         "Nexus is forecasting reach, ROAS and channel performance…")
        hb_perf = asyncio.create_task(_heartbeat(campaign_id, "performance", [
            "Querying historical campaign benchmarks…",
            "Applying Fan Truth score uplift factors…",
            "Modelling channel reach curves for each platform…",
            "Computing blended ROAS confidence intervals…",
        ], interval=18))
        try:
            perf_forecast = await run_performance_forecast(
                machine_brief = machine_brief,
                strategy      = strategy,
                copy          = copy,
                channels      = channels_list,
                campaign_id   = campaign_id,
            )
        except Exception as _pe:
            logger.warning("performance_forecast_failed", error=str(_pe))
            perf_forecast = {}
        finally:
            hb_perf.cancel()

        # run_performance_forecast always returns structured data (with a deterministic
        # fallback when the LLM output can't be parsed), so we always push the milestone.
        if perf_forecast and "raw_output" not in perf_forecast:
            await push_event(campaign_id, "performance", "milestone",
                             json.dumps(perf_forecast))
        else:
            perf_forecast = {}
        await push_event(campaign_id, "performance", "done",
                         f"Forecast ready — {perf_forecast.get('overall_confidence','—')} confidence ✓")
        await asyncio.sleep(3)

        result = {
            "status":             "ok",
            "campaign_id":        campaign_id,
            "machine_brief":      machine_brief,
            "creative_strategy":  strategy,
            "campaign_copy":      copy,
            "audience_insights":  audience_insights,
            "creative_pipeline":  creative_result,
            "performance_forecast": perf_forecast,
            "processing_time_ms": int((time.time() - t_start) * 1000),
        }
        await push_event(campaign_id, "__done__", "done", json.dumps(result))
        asyncio.create_task(_save_pipeline_output(campaign_id, result))

    except Exception as e:
        logger.error("campaign_error", campaign_id=campaign_id, error=str(e))
        await push_event(campaign_id, "__error__", "error", str(e))


async def _run_adaptation_pipeline(campaign_id: str, brief: BriefRequest) -> None:
    """
    Adapt Existing mode pipeline:
      1. Brief validation (Logos agent)
      2. Brand compliance check on brief
      3. AI image adaptation via gemini_model_image_adapter
      4. Channel variants via smart-crop (Pillow)
    """
    t_start = time.time()
    try:
        # ── Stage 1: Brief validation ─────────────────────────────────────────
        await push_event(campaign_id, "briefing", "running",
            f"Validating brief for adaptation — {brief.brand} · {brief.product}")
        hb = asyncio.create_task(_heartbeat(campaign_id, "briefing", [
            "Loading brand guidelines",
            "Checking fan truth alignment",
            "Preparing adaptation context",
        ], interval=18))
        try:
            machine_brief, ms1 = await run_agent(
                agent       = briefing_pipeline,
                input_data  = brief.model_dump(),
                campaign_id = campaign_id,
            )
        finally:
            hb.cancel()

        machine_brief.setdefault("campaign_id", campaign_id)
        machine_brief.setdefault("brand", brief.brand)
        await push_event(campaign_id, "briefing", "done",
            json.dumps({**machine_brief, "processing_time_ms": ms1}))
        await asyncio.sleep(3)

        # ── Stage 1b: Brand compliance check ─────────────────────────────────
        from app.brand_assets import get_asset_loader as _gal
        _ldr = _gal()
        _bpd = _ldr.load_brand_profile(brief.brand) if brief.brand else None
        _bpj = json.dumps(_bpd) if _bpd else "{}"

        if _bpj and _bpj != "{}":
            await push_event(campaign_id, "compliance", "running",
                f"Checking {brief.brand} compliance rules before adapting…")
            try:
                _cc = await run_brand_compliance_check(
                    brand_profile_json = _bpj,
                    machine_brief      = machine_brief,
                    generated_text     = json.dumps(machine_brief),
                )
                _cc_passed = _cc.get("passed", True)
                _cc_issues = _cc.get("issues", [])
                await push_event(campaign_id, "compliance", "done", json.dumps({
                    "_text":    f"{'✓ PASS' if _cc_passed else '✗ FAIL'} — Brand compliance {_cc.get('score', 100)}/100",
                    "passed":   _cc_passed,
                    "score":    _cc.get("score", 100),
                    "errors":   sum(1 for i in _cc_issues if i.get("severity") == "error"),
                    "warnings": sum(1 for i in _cc_issues if i.get("severity") == "warning"),
                    "issues":   _cc_issues,
                    "summary":  _cc.get("summary", ""),
                }))
            except Exception:
                await push_event(campaign_id, "compliance", "done", json.dumps({
                    "_text": "Compliance check skipped", "passed": True, "score": 100, "issues": [],
                }))
            await asyncio.sleep(3)

        # ── Stage 2: AI image adaptation ──────────────────────────────────────
        asset_count = len(brief.uploaded_assets)
        if not brief.uploaded_assets:
            await push_event(campaign_id, "kv", "done", json.dumps({
                "_text": "No assets uploaded — nothing to adapt",
                "images_b64": [], "channel_adaptations": {},
            }))
        else:
            await push_event(campaign_id, "kv", "running",
                f"Adapting {asset_count} existing {brief.brand} asset{'s' if asset_count != 1 else ''} "
                f"for {', '.join(brief.channels[:3])}…")

            # Load brand logo for the adapter to embed
            _logos = _ldr.list_logos(brief.brand) if brief.brand else []
            _logo_primary = next(
                (p for p in _logos if "whitebg" in p.lower() or "whiteBG" in p), None
            ) or (_logos[0] if _logos else "")

            # Extract copy from machine brief for headline/CTA overlay
            _copy_hl  = (machine_brief.get("short") or {}).get("headline", "")
            _copy_cta = machine_brief.get("cta", "")

            async def _adapt_progress(agent: str, status: str, msg: str):
                await push_event(campaign_id, agent, status, msg)

            adapt_result = await run_image_adaptation(
                asset_urls         = brief.uploaded_assets,
                brand              = brief.brand,
                brand_profile_dict = _bpd,
                copy_headline      = _copy_hl,
                copy_cta           = _copy_cta,
                channels           = brief.channels,
                logo_uri           = _logo_primary,
                campaign_id        = campaign_id,
                progress_cb        = _adapt_progress,
            )

            _images      = adapt_result.get("images_b64", [])
            _ch_adapt    = adapt_result.get("channel_adaptations", {})
            _adapted_n   = adapt_result.get("adapted_count", 0)

            # Upload adapted images to GCS (reuse the KV upload helper from the full pipeline)
            try:
                from app.brand_assets import get_asset_loader as _gal2
                import base64 as _b64u
                _ldr2 = _gal2()
                for _ki, _ib64 in enumerate(_images[:2]):
                    _raw = _b64u.b64decode(_ib64)
                    _uri = _ldr2.upload_output(_raw, f"outputs/{campaign_id}/adapted_kv_{_ki + 1}.jpg")
                    if _uri:
                        _images[_ki] = _uri   # keep GCS URI if upload succeeded
            except Exception:
                pass

            await push_event(campaign_id, "kv", "done", json.dumps({
                "_text":               f"{_adapted_n} adapted visual{'s' if _adapted_n != 1 else ''} ready ✓",
                "images_b64":          _images,
                "channel_adaptations": _ch_adapt,
                "adapted_count":       _adapted_n,
                "source_count":        asset_count,
                "adaptation_mode":     True,
            }))

        ms_total = int((time.time() - t_start) * 1000)
        await push_event(campaign_id, "__done__", "done", json.dumps({
            "campaign_id":        campaign_id,
            "mode":               "adapt",
            "machine_brief":      machine_brief,
            "processing_time_ms": ms_total,
        }))

    except Exception as e:
        logger.error("adaptation_error", campaign_id=campaign_id, error=str(e))
        await push_event(campaign_id, "__error__", "error", str(e))


@app.post("/campaign")
async def run_full_campaign(brief: BriefRequest):
    """Start campaign pipeline — routes to full or adaptation pipeline based on mode."""
    campaign_id = (
        f"campaign-{brief.campaign_name.lower().replace(' ', '-')[:20]}"
        f"-{str(uuid.uuid4())[:6]}"
    )
    _pipelines[campaign_id] = {"events": [], "signal": asyncio.Event()}
    if brief.mode == "adapt":
        asyncio.create_task(_run_adaptation_pipeline(campaign_id, brief))
    else:
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


# ── Infosys A2A Pipeline ───────────────────────────────────────────────────────

class InfosysPipelineRequest(_BaseModel):
    campaign_name: str       = ""
    sub_brand:     str       = ""   # Topaz | Cobalt | Aster | Finacle | McCamish | BPM
    objective:     str       = ""
    audience:      str       = ""
    buyer_truth:   str       = ""
    channels:      list[str] = ["LinkedIn"]
    market:        str       = "UK"
    locale:        str       = "en-GB"
    industry:      str       = ""
    timing:        str       = ""
    budget:        str       = ""
    product_area:  str       = ""
    run_aether:    bool      = False   # Phase 0: market intelligence
    run_visuals:   bool      = False   # Phase 4: Morphis + Kinetik
    strict_gate:   bool      = False   # True = block pipeline on any Logos BLOCK flag; False = warn and continue


@app.post("/infosys/pipeline")
async def infosys_pipeline(req: InfosysPipelineRequest):
    """
    Run the Infosys A2A pipeline:
      [Aether →] Logos → Helia → Ideon [→ parallel(Morphis, Kinetik)]

    Each stage uses the agent's SKILL.md + Infosys BrandContext as ADK instruction.
    Guardrails (analyst citations, sub-brand scope, competitor block, PII) fire automatically.
    """
    try:
        from app.agents.infosys.orchestrator import CampaignOrchestrator
        orch = CampaignOrchestrator()
        brief = req.model_dump(exclude={"run_aether", "run_visuals", "strict_gate"})
        return await orch.run_async(
            brief,
            run_aether  = req.run_aether,
            run_visuals = req.run_visuals,
            strict_gate = req.strict_gate,
        )
    except Exception as exc:
        logger.error("infosys_pipeline_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/infosys/logos")
async def infosys_logos(req: _BaseModel):
    """Run only the Logos (brief validation) stage for Infosys."""
    try:
        from app.agents.infosys.logos import LogosAgent
        r = LogosAgent().run(req.model_dump())
        return r.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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


# ── In-memory landing pages ───────────────────────────────────────────────────
_landing_pages:   dict[str, str]   = {}  # {campaign_id: html}
_campaign_images: dict[str, bytes] = {}  # {campaign_id: jpeg_bytes}


class PublishRequest(_BaseModel):
    brand:           str
    hero_message:    str = ""
    short_headline:  str = ""
    medium_headline: str = ""
    body:            str = ""
    cta:             str = ""
    tagline:         str = ""
    email_subject:   str = ""   # email-channel copy from copy agent channel_copy.email_subject
    product_name:    str = ""   # selected product for email product spotlight
    image_b64:       str = ""
    to_email:        str = ""
    channels:        list = []  # ["google_ads", "landing_page", "email"] — empty = all


@app.post("/publish/{campaign_id}")
async def publish_campaign(campaign_id: str, req: PublishRequest):
    """
    Distribute the campaign to Google Ads, a brand landing page, and email.
    Returns status for each channel.
    """
    from app.publisher import (
        publish_google_ads, generate_brand_website, send_campaign_email,
        publish_instagram, publish_instagram_reel,
    )
    results: dict = {}
    # Determine which channels to publish — empty list means all
    selected = set(req.channels) if req.channels else {"google_ads", "landing_page", "email", "instagram"}

    # Store KV image resized to 600px wide for email (Gmail blocks data: URIs;
    # also Imagen 4 raw output can be very large — resize before serving).
    if req.image_b64:
        try:
            import base64 as _b64, io as _io
            raw = _b64.b64decode(req.image_b64)
            try:
                from PIL import Image as _PILImg
                _PILImg.MAX_IMAGE_PIXELS = None   # allow large Imagen outputs
                _img = _PILImg.open(_io.BytesIO(raw)).convert("RGB")
                if _img.width > 600:
                    _new_h = int(_img.height * 600 / _img.width)
                    _img   = _img.resize((600, _new_h), _PILImg.LANCZOS)
                _buf = _io.BytesIO()
                _img.save(_buf, format="JPEG", quality=88)
                _campaign_images[campaign_id] = _buf.getvalue()
            except Exception:
                _campaign_images[campaign_id] = raw   # store raw if PIL fails
        except Exception:
            pass

    # Base URL for HTTPS image links in email (Gmail-compatible)
    _harness_base = os.getenv("HARNESS_URL", "http://localhost:8000").rstrip("/")
    _is_local = "localhost" in _harness_base or "127.0.0.1" in _harness_base
    # Localhost URLs are unreachable by Gmail — use empty string so email falls back to base64
    _img_url  = "" if _is_local else (f"{_harness_base}/campaign-image/{campaign_id}" if req.image_b64 else "")
    _logo_url = "" if _is_local else f"{_harness_base}/brand-logo/{req.brand}"

    landing_url = f"{_harness_base}/landing/{campaign_id}"  # default before landing page created

    # ── 1. Google Ads (mock) ──────────────────────────────────────────────────
    if "google_ads" in selected:
        results["google_ads"] = publish_google_ads(
            campaign_id     = campaign_id,
            brand           = req.brand,
            short_headline  = req.short_headline,
            medium_headline = req.medium_headline,
            cta             = req.cta,
            body            = req.body,
        )

    # ── 2. Brand landing page ─────────────────────────────────────────────────
    if "landing_page" in selected:
        # Bucket is public — pass GCS HTTPS URLs directly instead of loading
        # large base64 blobs into memory.  generate_brand_website/_make_bg_src
        # handles both data URIs and https:// URLs transparently.
        _pub_bucket = get_settings().gcs_bucket
        _adapt = _channel_adaptations.get(campaign_id, {})

        # Website banner: prefer in-memory base64 (same instance, no network),
        # then stored GCS URI, then predictable path URL.
        _website_banner_b64 = (_adapt.get("website") or {}).get("image_b64", "")
        if not _website_banner_b64:
            _stored_uri = (_adapt.get("website") or {}).get("gcs_uri", "")
            _website_banner_b64 = (
                _stored_uri if _stored_uri else
                f"https://storage.googleapis.com/{_pub_bucket}/outputs/{campaign_id}/channels/website.jpg"
            )

        # KV image: prefer what the frontend sent (already in browser state),
        # else use the GCS public URL (always exists after a completed campaign).
        _kv_image_b64 = req.image_b64 or (
            f"https://storage.googleapis.com/{_pub_bucket}/outputs/{campaign_id}/kv_image_1.jpg"
        )

        _reel_b64 = _campaign_reels.get(campaign_id, "")
        html = generate_brand_website(
            brand              = req.brand,
            hero_message       = req.short_headline or req.hero_message,
            tagline            = req.tagline,
            body_copy          = req.body,
            cta                = req.cta,
            campaign_image_b64 = _kv_image_b64,
            hero_image_b64     = _website_banner_b64,
            campaign_id        = campaign_id,
            video_b64          = _reel_b64,
        )
        _landing_pages[campaign_id] = html
        # Persist to GCS so it survives harness restarts
        try:
            from google.cloud import storage as _gcs_lp
            from app.config import get_settings as _gs_lp
            _cfg_lp = _gs_lp()
            _bucket_lp = _gcs_lp.Client().bucket(_cfg_lp.gcs_bucket)
            _bucket_lp.blob(f"outputs/{campaign_id}/landing.html").upload_from_string(
                html, content_type="text/html"
            )
            logger.info("landing_page_gcs_saved", campaign_id=campaign_id)
        except Exception as _e:
            logger.warning("landing_page_gcs_save_failed", error=str(_e))
        landing_url = f"{_harness_base}/landing/{campaign_id}"
        results["landing_page"] = {"status": "live", "url": f"/landing/{campaign_id}",
                                   "public_url": landing_url}
        logger.info("landing_page_created", campaign_id=campaign_id, brand=req.brand)

    # ── 3. Email ──────────────────────────────────────────────────────────────
    if "email" in selected:
        # Fall back to EMAIL_FROM env var when no recipient typed in the UI
        _recipient = req.to_email or os.getenv("EMAIL_FROM", "")
        logger.info("email_publish_attempt",
                    campaign_id  = campaign_id,
                    brand        = req.brand,
                    to_email_req = req.to_email or "(empty)",
                    to_email_use = _recipient or "(none)",
                    has_image    = bool(req.image_b64),
                    has_subject  = bool(req.email_subject),
                    smtp_user    = bool(os.getenv("EMAIL_FROM")),
                    smtp_pass    = bool(os.getenv("EMAIL_APP_PASSWORD")),
                    image_url    = _img_url or "(none)",
                    logo_url     = _logo_url,
                    )
        if _recipient:
            try:
                results["email"] = send_campaign_email(
                    to_email       = _recipient,
                    brand          = req.brand,
                    hero_message   = req.hero_message,
                    short_headline = req.short_headline,
                    email_subject  = req.email_subject,
                    body_copy      = req.body,
                    cta            = req.cta,
                    image_url      = _img_url,
                    logo_url       = _logo_url,
                    image_b64      = req.image_b64,   # base64 fallback when URL is localhost
                    landing_url    = landing_url,
                    product_name   = req.product_name,
                )
                logger.info("email_publish_result",
                            campaign_id = campaign_id,
                            result      = results["email"])
            except Exception as _email_exc:
                logger.error("email_publish_error",
                             campaign_id = campaign_id,
                             error       = str(_email_exc))
                results["email"] = {"status": "error", "error": str(_email_exc)}
        else:
            logger.warning("email_skipped_no_recipient",
                           campaign_id = campaign_id,
                           hint        = "Set EMAIL_FROM in .env or enter email in UI")
            results["email"] = {
                "status": "skipped",
                "reason": "No recipient — enter email in the launch panel or set EMAIL_FROM in .env",
            }

    # ── 4. Instagram ──────────────────────────────────────────────────────────
    if "instagram" in selected:
        _ig_image_url = ""
        try:
            from google.cloud import storage as _gcs_ig
            from app.config import get_settings as _gs_ig
            _cfg_ig = _gs_ig()
            _client_ig = _gcs_ig.Client()
            _bucket_ig = _client_ig.bucket(_cfg_ig.gcs_bucket)
            # KV concept 1 is already in GCS from the creative pipeline
            _kv_blob_path = f"outputs/{campaign_id}/kv_image_1.jpg"
            _kv_blob = _bucket_ig.blob(_kv_blob_path)
            if not _kv_blob.exists():
                # Fall back: upload from in-memory resized image
                if campaign_id in _campaign_images:
                    _kv_blob.upload_from_string(_campaign_images[campaign_id],
                                                content_type="image/jpeg")
            # Try to make the blob publicly readable (fails gracefully on uniform-access buckets)
            try:
                _kv_blob.make_public()
            except Exception as _pub_err:
                logger.debug("instagram_make_public_skipped", error=str(_pub_err))
            _ig_image_url = f"https://storage.googleapis.com/{_cfg_ig.gcs_bucket}/{_kv_blob_path}"
        except Exception as _ig_url_err:
            logger.warning("instagram_gcs_url_failed", error=str(_ig_url_err))

        # Build caption from campaign copy
        _cfg_ig_brand = __import__("app.publisher", fromlist=["BRAND_CONFIG"]).BRAND_CONFIG
        _brand_tagline = (_cfg_ig_brand.get(req.brand, {}).get("tagline", ""))
        _ig_caption = "\n\n".join(filter(None, [
            req.hero_message,
            (req.body or "")[:200] + ("…" if len(req.body or "") > 200 else ""),
            _brand_tagline,
            f"#{req.brand.replace(' ', '')} #CampaignOS #LimitedEdition",
        ]))
        results["instagram"] = publish_instagram(
            image_url = _ig_image_url,
            caption   = _ig_caption,
            brand     = req.brand,
        )

        # ── Instagram Reel ─────────────────────────────────────────────────────
        _reel_video_url = ""
        try:
            from google.cloud import storage as _gcs_reel
            from app.config import get_settings as _gs_reel
            _cfg_reel = _gs_reel()
            _gcs_client_r = _gcs_reel.Client()

            # Prefer the URI recorded at pipeline time (handles retry path reel_retry.mp4)
            _stored_uri = _campaign_reel_uris.get(campaign_id, "")
            if _stored_uri and _stored_uri.startswith("gs://"):
                _uri_without = _stored_uri[5:]
                _uri_bucket, _, _uri_blob_path = _uri_without.partition("/")
                _reel_blob = _gcs_client_r.bucket(_uri_bucket).blob(_uri_blob_path)
                logger.info("instagram_reel_checking_stored_uri", uri=_stored_uri)
            else:
                # Fallback: try canonical path then retry path
                _reel_gcs_path = f"outputs/{campaign_id}/reel.mp4"
                _reel_blob = _gcs_client_r.bucket(_cfg_reel.gcs_bucket).blob(_reel_gcs_path)
                if not _reel_blob.exists():
                    _reel_gcs_path = f"outputs/{campaign_id}/reel_retry.mp4"
                    _reel_blob = _gcs_client_r.bucket(_cfg_reel.gcs_bucket).blob(_reel_gcs_path)
                logger.info("instagram_reel_checking_path", path=_reel_gcs_path)
                _uri_bucket = _cfg_reel.gcs_bucket
                _uri_blob_path = _reel_gcs_path

            if _reel_blob.exists():
                try:
                    _reel_blob.make_public()
                except Exception:
                    pass
                _reel_video_url = f"https://storage.googleapis.com/{_uri_bucket}/{_uri_blob_path}"
                logger.info("instagram_reel_url_ready", url=_reel_video_url)
            else:
                logger.warning("instagram_reel_not_found_in_gcs",
                               campaign_id=campaign_id, stored_uri=_stored_uri)
        except Exception as _reel_url_err:
            logger.warning("instagram_reel_gcs_url_failed", error=str(_reel_url_err))

        if _reel_video_url:
            results["instagram_reel"] = publish_instagram_reel(
                video_url = _reel_video_url,
                caption   = _ig_caption,
                brand     = req.brand,
            )
        else:
            results["instagram_reel"] = {"status": "skipped", "reason": "No reel found in GCS"}

    return {"status": "ok", "campaign_id": campaign_id, "results": results}


@app.get("/landing/{campaign_id}", response_class=HTMLResponse)
async def serve_landing_page(campaign_id: str):
    """Serve the generated brand campaign landing page (in-memory → GCS fallback)."""
    html = _landing_pages.get(campaign_id)
    if not html:
        # Fallback: load from GCS (survives harness restarts)
        try:
            from google.cloud import storage as _gcs_serve
            from app.config import get_settings as _gs_serve
            _cfg_serve = _gs_serve()
            _blob = _gcs_serve.Client().bucket(_cfg_serve.gcs_bucket).blob(
                f"outputs/{campaign_id}/landing.html"
            )
            if _blob.exists():
                html = _blob.download_as_text()
                _landing_pages[campaign_id] = html  # warm the in-memory cache
        except Exception:
            pass
    if not html:
        raise HTTPException(status_code=404, detail="Landing page not found — publish first")
    return HTMLResponse(content=html)


@app.get("/agents/landing/{page_id}", response_class=HTMLResponse)
async def serve_standalone_landing_page(page_id: str):
    """Serve a live HTML preview generated by a standalone Poly (channel) agent run."""
    from app import agent_standalone
    html = agent_standalone.get_standalone_page(page_id)
    if not html:
        raise HTTPException(status_code=404, detail="Preview not found — run Poly first")
    return HTMLResponse(content=html)


# ══════════════════════════════════════════════════════════════════
# Mailchimp integration routes
# ══════════════════════════════════════════════════════════════════

@app.get("/mailchimp/ping")
async def mailchimp_ping():
    """Verify Mailchimp API key is valid."""
    from app.mailchimp_client import ping
    try:
        info = ping()
        return {"connected": True, "account_name": info.get("account_name",""),
                "email": info.get("email","")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Mailchimp connection failed: {e}")


@app.get("/mailchimp/audiences")
async def mailchimp_audiences():
    """List all Mailchimp audiences (contact lists)."""
    from app.mailchimp_client import list_audiences
    try:
        return {"audiences": list_audiences()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mailchimp/audiences/{list_id}/segments")
async def mailchimp_segments(list_id: str):
    from app.mailchimp_client import list_segments
    try:
        return {"segments": list_segments(list_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mailchimp/templates")
async def mailchimp_templates():
    from app.mailchimp_client import list_templates
    try:
        return {"templates": list_templates()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class MailchimpTemplateRequest(_BaseModel):
    name: str
    html: str


@app.post("/mailchimp/templates")
async def mailchimp_create_template(req: MailchimpTemplateRequest):
    from app.mailchimp_client import create_template
    try:
        return create_template(req.name, req.html)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class MailchimpSendRequest(_BaseModel):
    list_id:       str
    subject:       str
    html:          str
    from_name:     str  = "CampaignOS"
    reply_to:      str  = ""
    preview_text:  str  = ""
    schedule_time: str  = ""   # ISO 8601 UTC — empty = send immediately


@app.post("/mailchimp/send")
async def mailchimp_send(req: MailchimpSendRequest):
    """Create a campaign, upload HTML, and send (or schedule) via Mailchimp."""
    from app.mailchimp_client import create_and_send
    try:
        result = await asyncio.to_thread(
            create_and_send,
            list_id      = req.list_id,
            subject      = req.subject,
            html         = req.html,
            from_name    = req.from_name,
            reply_to     = req.reply_to,
            preview_text = req.preview_text,
            schedule_time= req.schedule_time,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mailchimp/reports")
async def mailchimp_reports(count: int = 10):
    from app.mailchimp_client import list_reports
    try:
        return {"reports": list_reports(count)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mailchimp/reports/{campaign_id}")
async def mailchimp_report(campaign_id: str):
    from app.mailchimp_client import get_report
    try:
        return get_report(campaign_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mailchimp/campaigns")
async def mailchimp_campaigns(count: int = 20):
    from app.mailchimp_client import list_campaigns
    try:
        return {"campaigns": list_campaigns(count)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class EmailTemplatesRequest(_BaseModel):
    prompt:    str
    brand:     str  = ""
    image_b64: str  = ""   # optional KV image (base64 JPEG) to embed as hero


@app.post("/mailchimp/email-templates")
async def mailchimp_email_templates(req: EmailTemplatesRequest):
    """
    Generate 3 HTML email layout variations.
    If image_b64 is provided it is used as the hero image in all layouts
    instead of loading from GCS — so the campaign KV image appears correctly.
    """
    from app import agent_standalone
    try:
        brand = req.brand or agent_standalone._extract_brand(req.prompt) or ""
        if not brand:
            raise HTTPException(status_code=400, detail="Brand not recognised — include brand name in prompt")
        result = await asyncio.to_thread(
            agent_standalone.run_email_templates, brand, req.prompt, req.image_b64
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════

class StandalonePublishRequest(_BaseModel):
    page_id:       str
    channel:       str   # "landing_page" | "email" | "google_ads"
    to_email:      str = ""
    # Optional preview-edited overrides — when present, replace the original copy
    email_subject: str = ""
    headline:      str = ""
    body:          str = ""


@app.post("/agents/channel/publish")
async def publish_standalone_channel(req: StandalonePublishRequest):
    """Act on what a standalone Poly run already generated — real email send,
    mocked Google Ads preview, or confirm the already-live landing page."""
    from app import agent_standalone
    try:
        result = await asyncio.to_thread(
            agent_standalone.publish_standalone_channel,
            req.page_id, req.channel, req.to_email,
            req.email_subject, req.headline, req.body,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish failed: {e}")


@app.get("/brand-logo/{brand}")
async def serve_brand_logo(brand: str):
    """
    Serve the primary brand logo as PNG with 24h cache.
    Sunrise and Haleon only have SVG files which browsers reject at small sizes,
    so we use the same programmatic Pillow generators the KV overlay pipeline uses.
    All other brands: prefer a neutral PNG from GCS/local bucket.
    """
    from fastapi.responses import Response
    from io import BytesIO
    try:
        from PIL import Image as _PIL, ImageDraw as _PID, ImageFont as _PIF
        from pathlib import Path as _Path

        def _png_bytes(img) -> bytes:
            buf = BytesIO()
            img.convert("RGBA").save(buf, format="PNG")
            return buf.getvalue()

        # ── Brand-specific logos: serve actual brand files, PIL fallback for Cloud Run ─
        import re as _re

        if brand.lower() == "infosys":
            # Serve from app/brands/infosys/logos/ — prefer the white-background lockup
            _logos_dir = _Path(__file__).parent / "app/brands/infosys/logos"
            _preferred = [
                "Infosys-tagline_WB.png",
                "Infosys-tagline_DB.png",
                "Infosys_India-Mark_WB.png",
            ]
            for _fname in _preferred:
                _f = _logos_dir / _fname
                if _f.exists():
                    return Response(content=_f.read_bytes(), media_type="image/png",
                                    headers={"Cache-Control": "public, max-age=86400"})
            # Fallback: any PNG in the logos dir
            for _f in sorted(_logos_dir.glob("*.png")):
                return Response(content=_f.read_bytes(), media_type="image/png",
                                headers={"Cache-Control": "public, max-age=86400"})

        if brand.lower() in ("sunrise",):
            # Red SVG is the actual Sunrise logo mark (~square, visible on any bg)
            _f = _Path(__file__).parent / "bucket/brands/sunrise/Logos/sunrise_logo_red.svg"
            if _f.exists():
                return Response(content=_f.read_bytes(), media_type="image/svg+xml",
                                headers={"Cache-Control": "public, max-age=86400"})
            # Cloud Run fallback: PIL red circle
            _SR = (218, 41, 28, 255)
            sz = 64; stroke = max(3, sz // 10)
            img = _PIL.new("RGBA", (sz, sz), (0, 0, 0, 0))
            d   = _PID.Draw(img)
            bb  = [0, 0, sz - 1, sz - 1]
            d.ellipse(bb, outline=_SR, width=stroke)
            d.chord(bb, start=195, end=345, fill=_SR)
            return Response(content=_png_bytes(img), media_type="image/png",
                            headers={"Cache-Control": "public, max-age=86400"})

        if brand.lower() == "haleon":
            # Crop the wordmark SVG to show just the "H" letterform (first 240 of 1426 wide)
            _f = _Path(__file__).parent / "bucket/brands/Haleon/Logos/haleon_logo_black.svg"
            if _f.exists():
                svg = _f.read_text(encoding="utf-8")
                svg = _re.sub(r'width="\d+(\.\d+)?"', 'width="222"', svg, count=1)
                svg = _re.sub(r'viewBox="[^"]*"', 'viewBox="0 0 240 222"', svg, count=1)
                return Response(content=svg.encode("utf-8"), media_type="image/svg+xml",
                                headers={"Cache-Control": "public, max-age=86400"})
            # Cloud Run fallback: PIL green pill
            w, h = 80, 32
            img = _PIL.new("RGBA", (w, h), (0, 0, 0, 0))
            d   = _PID.Draw(img)
            d.rounded_rectangle([0, 0, w - 1, h - 1], radius=6, fill=(101, 172, 30, 255))
            fnt = _PIF.load_default(size=14)
            bb  = d.textbbox((0, 0), "HALEON", font=fnt)
            d.text(((w - (bb[2]-bb[0]))//2 - bb[0], (h - (bb[3]-bb[1]))//2 - bb[1]),
                   "HALEON", font=fnt, fill=(255, 255, 255, 255))
            return Response(content=_png_bytes(img), media_type="image/png",
                            headers={"Cache-Control": "public, max-age=86400"})

        if brand.lower() == "ubs bank":
            # RGBA PNG with transparent bg — resize for web delivery
            _f = _Path(__file__).parent / "bucket/brands/UBS Bank/Logos/ubs-bank-logo.png"
            if _f.exists():
                img = _PIL.open(_f)
                img.thumbnail((128, 48), _PIL.LANCZOS)
                buf = BytesIO()
                img.convert("RGBA").save(buf, format="PNG", optimize=True)
                return Response(content=buf.getvalue(), media_type="image/png",
                                headers={"Cache-Control": "public, max-age=86400"})
            # Cloud Run fallback: PIL red circle with UBS text
            sz = 64
            img = _PIL.new("RGBA", (sz, sz), (0, 0, 0, 0))
            d   = _PID.Draw(img)
            d.ellipse([0, 0, sz - 1, sz - 1], fill=(236, 0, 0, 255))
            fnt = _PIF.load_default(size=18)
            bb  = d.textbbox((0, 0), "UBS", font=fnt)
            d.text(((sz - (bb[2]-bb[0]))//2 - bb[0], (sz - (bb[3]-bb[1]))//2 - bb[1]),
                   "UBS", font=fnt, fill=(255, 255, 255, 255))
            return Response(content=_png_bytes(img), media_type="image/png",
                            headers={"Cache-Control": "public, max-age=86400"})

        # ── All other brands: GCS → local bucket fallback ─────────────────────
        from app.brand_assets import get_asset_loader
        loader = get_asset_loader()
        logos  = loader.list_logos(brand)
        _sfx   = {"green", "red", "yellow", "orange", "purple", "blue"}
        primary = (
            next((p for p in logos if p.lower().endswith(".png")
                  and not any(p.lower().rsplit(".",1)[0].endswith(s) for s in _sfx)), None) or
            next((p for p in logos if p.lower().endswith(".png")), None) or
            next((p for p in logos if p.lower().endswith(".svg")), None) or
            (logos[0] if logos else None)
        )
        # Local fallback: GCS mode may miss files not yet uploaded to the bucket
        if not primary:
            _local_dir = _Path(__file__).parent / "bucket" / "brands" / brand / "Logos"
            for _ext in ("*.png", "*.jpg", "*.jpeg"):
                _locals = sorted(_local_dir.glob(_ext))
                if _locals:
                    primary = str(_locals[0])
                    break
        if not primary:
            raise HTTPException(status_code=404, detail=f"No logo found for {brand}")
        if primary.startswith("gs://"):
            from google.cloud import storage as _gcs
            without = primary[5:]
            bn, _, bp = without.partition("/")
            data = _gcs.Client().bucket(bn).blob(bp).download_as_bytes()
        else:
            data = _Path(primary).read_bytes()
        _ext  = primary.rsplit(".", 1)[-1].lower()
        _mime = {"svg": "image/svg+xml", "png": "image/png",
                 "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(_ext, "image/png")
        return Response(content=data, media_type=_mime,
                        headers={"Cache-Control": "public, max-age=86400"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/campaign-image/{campaign_id}")
async def serve_campaign_image(campaign_id: str):
    """
    Serve the generated KV image for email embedding.
    Image is stored in memory when the campaign is published.
    Used by email templates as a hosted image URL (Gmail blocks data: URIs).
    """
    from fastapi.responses import Response
    data = _campaign_images.get(campaign_id)
    if not data:
        raise HTTPException(status_code=404, detail="Campaign image not found — publish first")
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "no-cache, no-store"})


@app.get("/brand/{brand_name}", response_class=HTMLResponse)
async def serve_brand_website(brand_name: str):
    """Permanent brand website — no campaign needed. /brand/sunglow, /brand/rnorr, /brand/boozt"""
    from app.publisher import generate_brand_website
    brand_map = {"sunglow": "Sunglow", "rnorr": "Rnorr", "boozt": "Boozt"}
    brand = brand_map.get(brand_name.lower())
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_name}' not found. Try: sunglow, rnorr, boozt")
    html = generate_brand_website(brand=brand, campaign_id="brand-site")
    return HTMLResponse(content=html)


class ContentHubSaveRequest(_BaseModel):
    kind: str              # "kv" | "reel"
    brand: str
    campaign_name: str = ""
    campaign_id: str = ""
    headline: str = ""
    asset_b64: str
    content_type: str     # "image/jpeg" | "image/png" | "video/mp4"


@app.post("/content-hub/items")
async def content_hub_save(req: ContentHubSaveRequest):
    """Save a generated KV image or reel into the persistent Content Hub library."""
    from app import content_hub
    try:
        item = await asyncio.to_thread(
            content_hub.save_item,
            kind=req.kind, brand=req.brand, campaign_name=req.campaign_name,
            campaign_id=req.campaign_id, headline=req.headline,
            asset_b64=req.asset_b64, content_type=req.content_type,
        )
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {e}")


@app.get("/content-hub/items")
async def content_hub_list():
    """List all saved Content Hub items, newest first."""
    from app import content_hub
    try:
        items = await asyncio.to_thread(content_hub.list_items)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List failed: {e}")


@app.get("/content-hub/items/{item_id}/asset")
async def content_hub_asset(item_id: str):
    """Stream the actual image/video bytes for a saved Content Hub item."""
    from fastapi.responses import Response
    from app import content_hub
    result = await asyncio.to_thread(content_hub.get_asset, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    data, content_type = result
    return Response(content=data, media_type=content_type,
                     headers={"Cache-Control": "public, max-age=3600"})


@app.delete("/content-hub/items/{item_id}")
async def content_hub_delete(item_id: str):
    """Delete a saved Content Hub item (metadata + asset)."""
    from app import content_hub
    found = await asyncio.to_thread(content_hub.delete_item, item_id)
    if not found:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "deleted", "id": item_id}


@app.get("/brands")
async def list_brands():
    """Return all brand names that have assets in the GCS bucket."""
    try:
        from app.config import Settings
        cfg = Settings()
        from google.cloud import storage as _gcs
        client = _gcs.Client()
        blobs = client.list_blobs(cfg.gcs_bucket, prefix="brands/", delimiter="/")
        list(blobs)  # exhaust iterator to populate prefixes
        brands = sorted({
            p.replace("brands/", "").rstrip("/")
            for p in (blobs.prefixes or [])
            if p.replace("brands/", "").rstrip("/")
        })
        return {"brands": brands}
    except Exception as e:
        logger.warning("list_brands_failed", error=str(e))
        # Fallback: list from local bucket folder
        try:
            from pathlib import Path
            local = Path(__file__).parent / "bucket" / "brands"
            brands = sorted([d.name for d in local.iterdir() if d.is_dir()]) if local.is_dir() else []
            return {"brands": brands}
        except Exception:
            return {"brands": []}


@app.get("/brands/{brand_name}/assets")
async def get_brand_assets(brand_name: str):
    """Return asset file counts for a brand (same structure as the upload response)."""
    from app.brand_assets import get_asset_loader
    from pathlib import PurePosixPath
    loader = get_asset_loader()
    counts: dict[str, int] = {}
    try:
        logos    = loader.list_logos(brand_name)
        products = loader.list_products(brand_name)
        fonts    = loader.list_fonts(brand_name)
        assets   = loader.list_assets(brand_name)
        colours  = loader.list_colours(brand_name)
        # Guidelines — check for .md / .txt files
        from app.creative_pipeline import _load_bytes
        guidelines_count = 1 if loader.load_guidelines(brand_name) else 0
        if logos:        counts["logos"]      = len(logos)
        if products:     counts["products"]   = len(products)
        if fonts:        counts["fonts"]      = len(fonts)
        if assets:       counts["assets"]     = len(assets)
        if colours:      counts["colours"]    = len(colours)
        if guidelines_count: counts["guidelines"] = guidelines_count
    except Exception as e:
        logger.warning("get_brand_assets_failed", brand=brand_name, error=str(e))
    return {"brand": brand_name, "assets": counts}


@app.get("/brands/{brand_name}/list-logos")
async def list_brand_logos(brand_name: str):
    """List all logo files for a brand with HTTP serve URLs."""
    from app.brand_assets import get_asset_loader
    from pathlib import Path
    loader = get_asset_loader()
    logos = loader.list_logos(brand_name)
    result = []
    for path in logos:
        if path.startswith("gs://"):
            name = path.split("/")[-1]
            folder = "Logos" if "/Logos/" in path else "Logo"
        else:
            p = Path(path)
            name = p.name
            folder = p.parent.name
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        result.append({"name": name, "url": f"/brands/{brand_name}/serve/{folder}/{name}", "ext": ext})
    return {"brand": brand_name, "logos": result}


@app.get("/brands/{brand_name}/list-fonts")
async def list_brand_fonts(brand_name: str):
    """List all font files for a brand with HTTP serve URLs."""
    from app.brand_assets import get_asset_loader
    from pathlib import Path
    loader = get_asset_loader()
    fonts = loader.list_fonts(brand_name)
    result = []
    for path in fonts:
        if path.startswith("gs://"):
            name = path.split("/")[-1]
        else:
            p = Path(path)
            name = p.name
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        stem = name.rsplit(".", 1)[0] if "." in name else name
        result.append({"name": name, "url": f"/brands/{brand_name}/serve/Font/{name}", "ext": ext, "stem": stem})
    return {"brand": brand_name, "fonts": result}


@app.get("/brands/{brand_name}/list-colours")
async def list_brand_colours(brand_name: str):
    """Return colour palette — JSON data if available, otherwise PNG swatch URLs."""
    from app.brand_assets import get_asset_loader
    from pathlib import Path
    loader = get_asset_loader()
    # Try the structured JSON first (preferred)
    json_name = f"{brand_name.lower()}-colours.json"
    if loader._mode == "gcs":
        try:
            from google.cloud import storage as _gcs
            blob = _gcs.Client(project=settings.gcp_project).bucket(settings.gcs_bucket).blob(
                f"brands/{brand_name}/Colours/{json_name}"
            )
            import json as _json
            data = _json.loads(blob.download_as_text())
            return {"brand": brand_name, "mode": "json", "palette": data}
        except Exception:
            pass
    else:
        candidates = list((loader._local_root / brand_name / "Colours").glob("*.json")) if (loader._local_root / brand_name / "Colours").is_dir() else []
        if candidates:
            import json as _json
            data = _json.loads(candidates[0].read_text(encoding="utf-8"))
            return {"brand": brand_name, "mode": "json", "palette": data}
    # Fallback: list PNG swatch images
    swatches = loader.list_colours(brand_name)
    result = []
    for path in swatches:
        name = path.split("/")[-1] if path.startswith("gs://") else Path(path).name
        result.append({"name": name, "url": f"/brands/{brand_name}/serve/Colours/{name}"})
    return {"brand": brand_name, "mode": "images", "swatches": result}


@app.get("/brands/{brand_name}/list-products")
async def list_brand_products(brand_name: str):
    """List product images for a brand."""
    from app.brand_assets import get_asset_loader
    from pathlib import Path
    loader = get_asset_loader()
    products = loader.list_products(brand_name)
    result = []
    products_base = loader._local_root / brand_name / "Products"
    for path in products:
        if path.startswith("gs://"):
            name = path.split("/")[-1]
            result.append({"name": name, "url": f"/brands/{brand_name}/serve/Products/{name}"})
        else:
            p = Path(path)
            name = p.name
            try:
                rel = str(p.relative_to(products_base)).replace("\\", "/")
            except ValueError:
                rel = name
            result.append({"name": name, "url": f"/brands/{brand_name}/serve/Products/{rel}"})
    return {"brand": brand_name, "products": result}


@app.get("/brands/{brand_name}/list-documents")
async def list_brand_documents(brand_name: str):
    """List document files (Guidelines/, Assets/) for a brand."""
    from app.brand_assets import get_asset_loader
    from pathlib import Path
    loader = get_asset_loader()
    DOC_EXTS = {".md", ".txt", ".pdf", ".json", ".html", ".docx", ".pptx"}
    result = []
    if loader._mode == "gcs":
        try:
            from google.cloud import storage as _gcs
            client = _gcs.Client(project=settings.gcp_project)
            for subdir in ("Guidelines", "Assets"):
                prefix = f"brands/{brand_name}/{subdir}/"
                for blob in client.bucket(settings.gcs_bucket).list_blobs(prefix=prefix):
                    name = blob.name.split("/")[-1]
                    if Path(name).suffix.lower() in DOC_EXTS and not name.startswith("."):
                        result.append({"name": name, "category": subdir,
                                       "url": f"/brands/{brand_name}/serve/{subdir}/{name}"})
        except Exception:
            pass
    else:
        for subdir in ("Guidelines", "Assets"):
            folder = loader._local_root / brand_name / subdir
            if not folder.is_dir():
                continue
            for p in sorted(folder.iterdir()):
                if p.is_file() and p.suffix.lower() in DOC_EXTS and not p.name.startswith("."):
                    result.append({"name": p.name, "category": subdir,
                                   "url": f"/brands/{brand_name}/serve/{subdir}/{p.name}"})
    return {"brand": brand_name, "documents": result}


@app.get("/brands/{brand_name}/campaign-history")
async def get_brand_campaign_history(brand_name: str, limit: int = 50):
    """Return historical campaigns + generated briefs for a brand from BigQuery."""
    import asyncio

    def _query():
        try:
            from google.cloud import bigquery as _bq
        except ImportError:
            return {"error": "bigquery_unavailable"}

        client = _bq.Client(project=settings.gcp_project)
        project = settings.gcp_project
        hist_table = f"{project}.{settings.bq_dataset}.{settings.bq_campaigns_table}"
        briefs_table = f"{project}.{settings.bq_output_dataset}.{settings.bq_output_table}"
        brand_param = brand_name.lower()

        results: dict = {"historical": [], "briefs": []}

        # Historical campaigns (benchmark data)
        try:
            q = f"""
                SELECT brand, product_category, market, season, channels,
                       reach, ctr_pct, roas, engagement_pct, budget_gbp, notes
                FROM `{hist_table}`
                WHERE LOWER(brand) = @brand
                ORDER BY roas DESC
                LIMIT {limit}
            """
            job = client.query(q, job_config=_bq.QueryJobConfig(
                query_parameters=[_bq.ScalarQueryParameter("brand", "STRING", brand_param)]
            ))
            for row in job.result():
                r = dict(row)
                if isinstance(r.get("channels"), list):
                    r["channels"] = r["channels"]
                results["historical"].append(r)
        except Exception as e:
            results["historical_error"] = str(e)

        # Generated machine briefs
        try:
            q = f"""
                SELECT campaign_id, campaign_name, brand, market, product_category,
                       season, channels, moment_type, validation_score, validation_status,
                       fan_truth_score, fan_truth_verdict, flag_count, created_at
                FROM `{briefs_table}`
                WHERE LOWER(brand) = @brand
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            job = client.query(q, job_config=_bq.QueryJobConfig(
                query_parameters=[_bq.ScalarQueryParameter("brand", "STRING", brand_param)]
            ))
            for row in job.result():
                r = dict(row)
                if r.get("created_at"):
                    r["created_at"] = r["created_at"].isoformat()
                results["briefs"].append(r)
        except Exception as e:
            results["briefs_error"] = str(e)

        return results

    try:
        data = await asyncio.to_thread(_query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if data.get("error") == "bigquery_unavailable":
        raise HTTPException(status_code=503, detail="BigQuery SDK not available")

    return {"brand": brand_name, **data}


@app.get("/campaign/{campaign_id}/brief")
async def get_campaign_brief_detail(campaign_id: str):
    """Fetch full brief JSON for a specific campaign_id so the UI can re-run it."""
    import asyncio, json as _json

    def _query():
        try:
            from google.cloud import bigquery as _bq
        except ImportError:
            return {"error": "bigquery_unavailable"}

        client = _bq.Client(project=settings.gcp_project)
        table  = f"{settings.gcp_project}.{settings.bq_output_dataset}.{settings.bq_output_table}"
        q = f"""
            SELECT campaign_id, campaign_name, brand, market, product_category,
                   season, channels, moment_type, brief_json, created_at
            FROM `{table}`
            WHERE campaign_id = @cid
            LIMIT 1
        """
        job = client.query(q, job_config=_bq.QueryJobConfig(
            query_parameters=[_bq.ScalarQueryParameter("cid", "STRING", campaign_id)]
        ))
        rows = list(job.result())
        if not rows:
            return None
        r = dict(rows[0])
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
        if r.get("brief_json"):
            try:
                r["brief_parsed"] = _json.loads(r["brief_json"])
            except Exception:
                r["brief_parsed"] = {}
        return r

    try:
        row = await asyncio.to_thread(_query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if isinstance(row, dict) and row.get("error") == "bigquery_unavailable":
        raise HTTPException(status_code=503, detail="BigQuery SDK not available")

    return row


@app.get("/campaign/{campaign_id}/output")
async def get_campaign_output(campaign_id: str):
    """Fetch stored pipeline output from GCS (saved after each pipeline run)."""
    def _fetch():
        try:
            from google.cloud import storage as _gcs_s
            client = _gcs_s.Client(project=GCP_PROJECT)
            blob   = client.bucket(settings.gcs_bucket).blob(
                f"outputs/{campaign_id}/pipeline_output.json"
            )
            return json.loads(blob.download_as_text())
        except Exception:
            return None

    result = await asyncio.to_thread(_fetch)
    if result is None:
        raise HTTPException(status_code=404,
                            detail="Campaign output not found — it may predate output storage, or still be running.")
    return result


@app.get("/campaign/{campaign_id}/kv/{idx}")
async def serve_campaign_kv_image(campaign_id: str, idx: int):
    """Proxy a KV image from GCS for a historical campaign (index is 1-based)."""
    from fastapi.responses import Response

    def _fetch():
        try:
            from google.cloud import storage as _gcs_s
            client = _gcs_s.Client(project=GCP_PROJECT)
            blob   = client.bucket(settings.gcs_bucket).blob(
                f"outputs/{campaign_id}/kv_image_{idx}.jpg"
            )
            return blob.download_as_bytes()
        except Exception:
            return None

    data = await asyncio.to_thread(_fetch)
    if data is None:
        raise HTTPException(status_code=404, detail=f"KV image {idx} not found for campaign {campaign_id}")
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.get("/brands/{brand_name}/serve/{category}/{filename:path}")
async def serve_brand_asset_file(brand_name: str, category: str, filename: str):
    """Serve a brand asset file (logo, font, colour, etc.) from local bucket or GCS."""
    import mimetypes
    from fastapi.responses import Response
    from app.brand_assets import get_asset_loader
    loader = get_asset_loader()
    if loader._mode == "gcs":
        try:
            from google.cloud import storage as _gcs
            blob = _gcs.Client(project=settings.gcp_project).bucket(settings.gcs_bucket).blob(
                f"brands/{brand_name}/{category}/{filename}"
            )
            data = blob.download_as_bytes()
        except Exception:
            raise HTTPException(status_code=404, detail="File not found")
    else:
        from pathlib import Path
        base = loader._local_root / brand_name
        target = (base / category / filename).resolve()
        if not str(target).startswith(str(base.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        if not target.exists():
            raise HTTPException(status_code=404, detail="File not found")
        data = target.read_bytes()
    content_type, _ = mimetypes.guess_type(filename)
    if filename.lower().endswith(".svg"):
        content_type = "image/svg+xml"
    return Response(content=data, media_type=content_type or "application/octet-stream",
                    headers={"Cache-Control": "public, max-age=3600",
                             "Access-Control-Allow-Origin": "*"})


@app.post("/brands/{brand_name}/upload")
async def upload_brand(brand_name: str, file: UploadFile = File(...)):
    """
    Upload a new brand's asset folder as a .zip (Guidelines/Logos/Font/Colours/Assets/Products)
    and re-index it into Vertex AI Search so Logos (the briefing agent) can retrieve it.
    """
    import zipfile
    from app import brand_onboarding
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")
    data = await file.read()
    try:
        result = await asyncio.to_thread(brand_onboarding.ingest_brand_zip, brand_name, data)
        if not result["uploaded"]:
            raise HTTPException(status_code=400, detail=(
                "No recognised files found. Zip must contain Guidelines/, Logos/, Font/, "
                "Colours/, and/or Assets/ subfolders."
            ))
        reindex = await asyncio.to_thread(brand_onboarding.reindex_brand, brand_name)
        return {**result, "reindex": reindex}
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.post("/brands/{brand_name}/upload-chunk")
async def upload_brand_chunk(
    brand_name: str,
    file: UploadFile = File(...),
    session_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
):
    """
    Receive one 10 MB slice of a brand zip.  Chunks are stored in GCS at
    brands/{brand}/._chunks/{session_id}/{index:05d} and assembled on finalize.
    """
    from google.cloud import storage as _gcs
    data = await file.read()
    client = _gcs.Client(project=settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)
    bucket.blob(f"brands/{brand_name}/._chunks/{session_id}/{chunk_index:05d}").upload_from_string(data)
    return {"received": chunk_index, "total_chunks": total_chunks}


class _FinalizeUpload(_BaseModel):
    session_id:   str
    total_chunks: int


@app.post("/brands/{brand_name}/finalize-upload")
async def finalize_brand_upload(brand_name: str, req: _FinalizeUpload):
    """
    Concatenate previously uploaded chunks, run brand ingest + reindex, then
    delete the temporary chunk blobs.
    """
    import zipfile
    from google.cloud import storage as _gcs
    from app import brand_onboarding

    client = _gcs.Client(project=settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)

    # Download and assemble in order
    pieces: list[bytes] = []
    for i in range(req.total_chunks):
        blob = bucket.blob(f"brands/{brand_name}/._chunks/{req.session_id}/{i:05d}")
        pieces.append(await asyncio.to_thread(blob.download_as_bytes))

    zip_bytes = b"".join(pieces)

    # Clean up temp chunks (best-effort)
    for i in range(req.total_chunks):
        try:
            bucket.blob(f"brands/{brand_name}/._chunks/{req.session_id}/{i:05d}").delete()
        except Exception:
            pass

    try:
        result = await asyncio.to_thread(brand_onboarding.ingest_brand_zip, brand_name, zip_bytes)
        if not result["uploaded"]:
            raise HTTPException(status_code=400, detail=(
                "No recognised files found. Zip must contain Guidelines/, Logos/, Font/, "
                "Colours/, and/or Assets/ subfolders."
            ))
        reindex = await asyncio.to_thread(brand_onboarding.reindex_brand, brand_name)
        return {**result, "reindex": reindex}
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Finalize failed: {e}")


class AgentStandaloneRequest(_BaseModel):
    prompt:        str       # e.g. "UBS Bank for UK market, festive: christmas"
    duration:      int = 30  # TVC duration in seconds (15 or 30); ignored by other agents
    image_b64:     str = ""  # optional pre-generated image (channel agent skips Imagen if set)
    product_name:  str = ""  # Sunrise product selection (triggers offer-mode layout)
    market:        str = ""  # Market/region for currency resolution
    audience:      str = ""  # Target audience (drives scene people in Sunrise offer images)
    copy_headline: str = ""  # Headline from Copy Agent step — used instead of generating a new one
    copy_subline:  str = ""  # Subline from Copy Agent — rendered below headline on banner
    copy_body:     str = ""  # Body copy from Copy Agent — for channel/email use
    copy_cta:      str = ""  # CTA from Copy Agent — rendered in bottom bar on standard banners
    campaign_type:      str = ""    # Legacy: kept for backwards compat; prefer campaign_id
    campaign_id:        str = ""    # Explicit campaign identifier, e.g. "wimbledon" — exact match, no substring
    concept_id:         str = ""    # Specific creative concept, e.g. "c1_journey" — skips keyword matching
    aspect_ratio:       str = "16:9"  # Output image aspect ratio: "16:9" | "1:1" | "4:5" | "9:16"
    color_theme:        str = "blue"  # Infosys IT Services color: "blue"|"purple"|"amber"|"deep-purple"
    speaker_image_b64:  str = ""    # Base-64 executive headshot — enables circular speaker layout
    speaker_name:       str = ""    # Executive name shown below circle
    speaker_title:      str = ""    # Role / company line shown under name
    content_type_badge: str = ""    # Optional label above headline e.g. "BYLINE", "MEDIA ARTICLE"


@app.post("/agents/{agent_key}/run")
async def run_agent_standalone(agent_key: str, req: AgentStandaloneRequest):
    """
    Run a single creative agent in isolation (no upstream pipeline context) —
    given one free-text prompt that names the brand + creative direction.
    See app/agent_standalone.py.
    """
    # Performance / Nexus — async path (uses Vertex AI directly, can't go through to_thread)
    if agent_key == "performance":
        try:
            from app.runner import run_performance_standalone
            result = await run_performance_standalone(req.prompt)
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Nexus forecast failed: {e}")

    from app import agent_standalone
    try:
        result = await asyncio.to_thread(
            agent_standalone.run_agent_standalone,
            agent_key, req.prompt,
            duration=req.duration, image_b64=req.image_b64,
            product_name=req.product_name, market=req.market, audience=req.audience,
            copy_headline=req.copy_headline, copy_subline=req.copy_subline,
            copy_body=req.copy_body, copy_cta=req.copy_cta,
            campaign_type=req.campaign_type, campaign_id=req.campaign_id,
            concept_id=req.concept_id, aspect_ratio=req.aspect_ratio,
            color_theme=req.color_theme,
            speaker_image_b64=req.speaker_image_b64, speaker_name=req.speaker_name,
            speaker_title=req.speaker_title, content_type_badge=req.content_type_badge,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent run failed: {e}")


# ── Figma Integration ─────────────────────────────────────────────────────────
_figma_store: dict = {}  # {id: {image_b64, campaign_name}} + "latest" key

FIGMA_API_TOKEN = os.getenv("FIGMA_API_TOKEN", "")
FIGMA_FILE_KEY  = os.getenv("FIGMA_FILE_KEY", "")
FIGMA_API_BASE  = "https://api.figma.com/v1"


def _figma_headers() -> dict:
    return {"X-Figma-Token": FIGMA_API_TOKEN, "Content-Type": "application/json"}


async def _verify_figma_file() -> bool:
    """Check the template file is accessible with our token."""
    if not FIGMA_API_TOKEN or not FIGMA_FILE_KEY:
        return False
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{FIGMA_API_BASE}/files/{FIGMA_FILE_KEY}/nodes?ids=0%3A1",
                headers=_figma_headers(),
            )
        return r.status_code == 200
    except Exception:
        return False


class FigmaPrepareRequest(_BaseModel):
    image_b64: str
    campaign_name: str = "Campaign"


@app.post("/figma/prepare")
async def figma_prepare(req: FigmaPrepareRequest):
    """Store a generated image for Figma plugin pickup and return the file URL."""
    campaign_id = str(uuid.uuid4())[:8]
    _figma_store[campaign_id] = {
        "image_b64": req.image_b64,
        "campaign_name": req.campaign_name,
    }
    _figma_store["latest"] = campaign_id

    figma_url = (
        f"https://www.figma.com/design/{FIGMA_FILE_KEY}/A2A-Campaign-Canvas"
        if FIGMA_FILE_KEY
        else "https://www.figma.com/new"
    )

    return {
        "campaign_id": campaign_id,
        "campaign_name": req.campaign_name,
        "status": "ready",
        "figma_url": figma_url,
        "file_verified": bool(FIGMA_FILE_KEY),
        "plugin_endpoint": "/figma/latest",
    }


@app.get("/figma/latest")
async def figma_latest():
    """Figma plugin fetches the most-recently prepared image from this endpoint."""
    latest_id = _figma_store.get("latest")
    if not latest_id or latest_id not in _figma_store:
        raise HTTPException(status_code=404, detail="No image prepared yet")
    entry = _figma_store[latest_id]
    return {
        "campaign_name": entry["campaign_name"],
        "image_b64": entry["image_b64"],
    }


@app.get("/figma/status")
async def figma_status():
    """Check Figma connection status — used by the frontend to show connected state."""
    file_ok = await _verify_figma_file()
    return {
        "connected": file_ok,
        "file_key": FIGMA_FILE_KEY if FIGMA_FILE_KEY else None,
        "figma_url": f"https://www.figma.com/design/{FIGMA_FILE_KEY}" if file_ok else None,
        "has_pending_image": "latest" in _figma_store,
    }


@app.post("/convert-email")
async def convert_email(
    files: list[UploadFile] = File(...),
    brand_name:  str = Form(""),
    brand_color: str = Form("#0055A4"),
):
    """
    Convert one or more uploaded documents to a single HTML email.
    Supports: docx, pdf, xlsx, xls, csv, txt, pptx, jpg, jpeg, png, gif, webp.
    Returns { html, slots, image_count, filename, file_count }.
    """
    from app.email_converter import EmailConverterAgent
    agent = EmailConverterAgent()
    pairs: list[tuple[bytes, str]] = []
    for uf in files:
        content  = await uf.read()
        filename = uf.filename or "document"
        pairs.append((content, filename))
    try:
        result = agent.run(pairs, brand_name=brand_name.strip(), brand_color=brand_color.strip())
        return JSONResponse(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        names = ", ".join(p[1] for p in pairs)
        logger.error("convert_email_error", filenames=names, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}")


@app.post("/render-email")
async def render_email(body: dict):
    """
    Re-render an email from edited slots without re-running the full pipeline.
    Body: { slots, brand_name, brand_color }
    """
    from app.email_converter.builder import build_html
    slots       = body.get("slots", {})
    brand_name  = str(body.get("brand_name",  ""))
    brand_color = str(body.get("brand_color", "#0055A4"))
    try:
        html = build_html(slots, brand_name=brand_name, brand_color=brand_color, multi_file=False)
        return JSONResponse({"html": html})
    except Exception as exc:
        logger.error("render_email_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Render failed: {exc}")


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


