"""
nodes.py — Deterministic graph function nodes for the CampaignOS Workflow DAG.

These are plain Python functions that execute as graph nodes with zero LLM
overhead — the Workflow engine calls them directly without any AI reasoning.

Node list:
  load_brand_context    — loads all brand/search data sources before briefing_agent
  aggregate_kv_concepts — fan-in aggregator: collects kv_concept_1..2 from state
                          into a single kv_concepts_all state entry for kv_ranker
                          (kv_concept_N is enriched with image_artifact_key by
                           kv_image_agent_N before arriving here)

ADK 2.0 mechanics used here:
  - Function nodes receive the previous node's output as `node_input`
  - Returning a Pydantic model passes it to the next Agent via input_schema
  - Parameter names matching session state keys (e.g. kv_concept_1: str = "")
    are automatically injected from state by the Workflow engine
  - Event(state={...}) persists values into session state for downstream
    instruction template substitution ({kv_concepts_all})
"""

import json
import re
from typing import AsyncGenerator

import structlog
import yaml

from google.adk import Event
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import EventActions
from google.genai import types

from app.brand_assets import get_asset_loader
from app.config import get_settings
from app.data_loader import log_brief_to_bigquery
from app.haleon_catalog import enrich_brief as haleon_enrich_brief
from app.models import (
    BrandLocks,
    BriefingContext,
    CampaignCopy,
    CreativeStrategy,
    CultureAnalysis,
    MachineBrief,
)
from app.search_client import get_search_client

logger   = structlog.get_logger()
settings = get_settings()


# ── BRIEFING STAGE FUNCTION NODE ─────────────────────────────────────────

def load_brand_context(
    node_input,
    brief_json: str = "",  # state-injected fallback (populated by runner.py for the REST API path)
) -> BriefingContext:
    """
    Load all brand assets and research context needed by briefing_agent.

    Runs as the first graph node (START → load_brand_context → briefing_agent).
    Replaces the 7 sequential data-loading tool calls that briefing_agent
    previously had to orchestrate itself.

    node_input: ADK passes the user's initial message here. In adk web this is
    a Content object (google.genai.types.Content with .parts[].text). The helper
    _extract_text() handles str / Content / Part / None uniformly.

    brief_json: state-injected fallback — runner.py pre-populates session state
    with the brief JSON string so the REST API path works even if node_input
    doesn't carry the message text.

    Returns:
        BriefingContext containing all loaded data, passed to briefing_agent
        via input_schema so the LLM receives it as structured prompt context.
    """
    # Extract raw text from whatever ADK passes as node_input ─────────────
    raw_text = _extract_text(node_input) or brief_json

    logger.info(
        "load_brand_context_input",
        node_input_type = type(node_input).__name__,
        raw_text_length = len(raw_text),
        from_state      = bool(not _extract_text(node_input) and brief_json),
    )
    # Parse the brief ──────────────────────────────────────────────────────
    brief_dict: dict = {}
    if raw_text:
        try:
            brief_dict = json.loads(raw_text)
        except (json.JSONDecodeError, TypeError, ValueError):
            # Fallback: try plain-text "Key: Value" format (ADK web paste-in)
            brief_dict = _parse_kv_brief(raw_text)

    # Enrich Haleon briefs: extract sub_brand/product_category from free text
    brief_dict = haleon_enrich_brief(brief_dict)

    brand            = brief_dict.get("brand", "")
    product          = brief_dict.get("product", "")
    product_category = brief_dict.get("product_category", "")
    channels         = brief_dict.get("channels", [])
    market           = brief_dict.get("market", "UK")
    season           = brief_dict.get("season", "All")
    moment_type      = brief_dict.get("moment_type", "Day-to-Day")
    audience_raw     = brief_dict.get("audience", {})
    audience_segment = (
        audience_raw.get("segment", "")
        if isinstance(audience_raw, dict)
        else str(audience_raw)
    )

    # Load brand assets (always synchronous) ──────────────────────────────
    loader           = get_asset_loader()
    brand_guidelines = loader.load_guidelines(brand) if brand else ""
    product_paths    = loader.list_products(brand)   if brand else []
    logo_paths       = loader.list_logos(brand)      if brand else []

    # Load the structured brand profile (brand.json) — brand-owner approved,
    # never AI-invented. Used for compliance checking and as structured context.
    brand_profile_dict = loader.load_brand_profile(brand) if brand else None

    # For brands with a compliance config, prepend a compact profile block to
    # the guidelines so the briefing agent has explicit rules as hard constraints.
    if brand_profile_dict:
        from app.models import BrandProfile as _BPModel
        try:
            _bp = _BPModel(**brand_profile_dict)
            _profile_block = "BRAND PROFILE (AUTHORITATIVE — DO NOT OVERRIDE)\n" + _bp.to_context_str()
            brand_guidelines = (_profile_block + "\n\n---\n\n" + brand_guidelines).strip()
        except Exception as _bp_err:
            logger.warning("brand_profile_inject_failed", brand=brand, error=str(_bp_err))

    # Barclays: append the Logos agent SKILL file to brand guidelines so the
    # briefing agent follows FCA compliance rules and Barclays-specific tone.
    if brand.lower() == "barclays":
        logos_skill = loader.load_agent_skill(brand, "Logos")
        if logos_skill:
            brand_guidelines = (brand_guidelines + "\n\n---\n\n" + logos_skill).strip()

    # Haleon: reorder product_paths so the matched sub-brand image is first.
    # list_products() returns all 23 images alphabetically; pipeline only uses
    # product_uris[:1] as the Gemini reference, so the wrong image would be sent.
    if brand.lower() == "haleon" and product and product_paths:
        from pathlib import Path as _PP
        _prod_key = product.lower().replace("-", "").replace(" ", "")
        _match = next(
            (p for p in product_paths
             if _prod_key in _PP(p).stem.lower().replace("-", "").replace(" ", "")),
            None,
        )
        if _match:
            product_paths = [_match] + [p for p in product_paths if p != _match]

    # Parse brand locks from guidelines YAML blocks ───────────────────────
    brand_locks_dict = _parse_brand_locks(brand, brand_guidelines)

    # Live Google Trends market signals ──────────────────────────────────
    from app.market_trends import get_trends as _get_trends
    _trends = _get_trends(
        keywords  = [kw for kw in [brand, product, moment_type] if kw],
        market    = market,
        timeframe = "today 3-m",
    )

    # Load search / benchmark data ────────────────────────────────────────
    _stat_chunks           = 0
    _stat_market_signals   = _trends["signals"]
    _stat_campaign_records = 0

    if settings.search_mode == "live" and brand:
        sc = get_search_client()

        try:
            _r = sc.get_brand_rules(product_category=product_category, channels=channels)
            brand_rules_summary = _r.summary or brand_guidelines
            _stat_chunks = len(_r.results)
        except Exception:
            brand_rules_summary = brand_guidelines

        try:
            fan_truth_summary = sc.get_fan_truth_examples(
                product=product,
                product_category=product_category,
                audience=audience_segment,
            ).summary or _stub_fan_truth()
        except Exception:
            fan_truth_summary = _stub_fan_truth()

        try:
            _r = sc.get_campaign_benchmarks(
                product_category=product_category, market=market, season=season
            )
            campaign_benchmarks_summary = _r.summary or _stub_benchmarks()
            _stat_campaign_records = len(_r.results)
        except Exception:
            campaign_benchmarks_summary = _stub_benchmarks()

        try:
            channel_benchmarks_summary = sc.get_channel_benchmarks(
                channels=channels, market=market, audience_segment=audience_segment
            ).summary or _stub_channel_benchmarks()
        except Exception:
            channel_benchmarks_summary = _stub_channel_benchmarks()

        try:
            _r = sc.get_moment_type_rules(moment_type=moment_type)
            moment_type_rules_summary = _r.summary or _stub_moment_type(moment_type)
            _stat_market_signals = len(_r.results)
        except Exception:
            moment_type_rules_summary = _stub_moment_type(moment_type)

        # CDP audience insights — always from pgvector regardless of search mode
        try:
            from app.pgvector_client import search_audience_insights
            age_range      = audience_raw.get("age_range", "") if isinstance(audience_raw, dict) else ""
            audience_insights = search_audience_insights(brand, audience_segment, age_range, channels)
            logger.info("cdp_query_success", brand=brand, length=len(audience_insights))
        except Exception as e:
            logger.warning("cdp_query_failed", error=str(e), brand=brand,
                           pgvector_host=__import__("os").getenv("PGVECTOR_HOST", "NOT_SET"))
            audience_insights = ""

    elif settings.search_mode == "pgvector" and brand:
        # pgvector mode — semantic search from PostgreSQL + pgvector
        from app.pgvector_client import (
            search_brand_guidelines,
            search_fan_truths,
            search_campaign_benchmarks,
            search_channel_benchmarks,
            search_audience_insights,
        )
        fan_truth_text = brief_dict.get("fan_truth", "")
        age_range      = audience_raw.get("age_range", "") if isinstance(audience_raw, dict) else ""
        # RAG: semantic search over chunked GCS brand guidelines
        rag_guidelines  = search_brand_guidelines(brand, f"{product_category} {' '.join(channels)}")
        brand_rules_summary         = rag_guidelines or ""
        fan_truth_summary           = search_fan_truths(brand, product_category, fan_truth_text)
        campaign_benchmarks_summary = search_campaign_benchmarks(brand, product_category, market, season)
        channel_benchmarks_summary  = search_channel_benchmarks(channels, market, audience_segment)
        audience_insights           = search_audience_insights(brand, audience_segment, age_range, channels)
        moment_type_rules_summary   = _stub_moment_type(moment_type)

    else:
        # gcs_files / local mode — brand_guidelines is the source of truth;
        # brand_rules_summary is left empty to avoid duplicating it in state.
        brand_rules_summary          = ""
        fan_truth_summary            = _stub_fan_truth()
        campaign_benchmarks_summary  = _stub_benchmarks()
        channel_benchmarks_summary   = _stub_channel_benchmarks()
        audience_insights            = ""
        moment_type_rules_summary    = _stub_moment_type(moment_type)

    # Build Product1 / Product2 … name → GCS URI map ─────────────────────
    product_image_map = {
        f"Product{i + 1}": path
        for i, path in enumerate(product_paths)
    }

    # Build Product1 / Product2 … name → human-readable description map ──
    # Uses the brief's product field for the primary product (first image);
    # falls back to the filename stem for additional images.
    product_description_map: dict[str, str] = {}
    for i, path in enumerate(product_paths):
        key = f"Product{i + 1}"
        if i == 0 and product:
            label = product
            if product_category:
                label = f"{product} ({product_category})"
            product_description_map[key] = label
        else:
            # Derive a readable name from the file path stem
            stem  = (path.rstrip("/").rsplit("/", 1)[-1]).rsplit(".", 1)[0]
            label = stem.replace("_", " ").replace("-", " ").title()
            product_description_map[key] = label

    # Extract compact visual/colour rules for KV agents ───────────────────
    brand_visual_rules = _extract_brand_visual_rules(brand_guidelines)

    logger.info(
        "load_brand_context",
        brand                    = brand,
        has_guidelines           = bool(brand_guidelines),
        has_visual_rules         = bool(brand_visual_rules),
        brand_locks_keys         = list(brand_locks_dict.keys()),
        primary_colour           = brand_locks_dict.get("primary_colour"),
        accent_colour            = brand_locks_dict.get("accent_colour"),
        font                     = brand_locks_dict.get("font"),
        search_mode              = settings.search_mode,
        channels                 = channels,
        brief_keys               = list(brief_dict.keys()),
        product_image_map        = product_image_map,
        product_description_map  = product_description_map,
    )

    briefing_context = BriefingContext(
        brief_request               = brief_dict,
        brand_guidelines            = brand_guidelines,
        brand_rules_summary         = brand_rules_summary,
        fan_truth_summary           = fan_truth_summary,
        campaign_benchmarks_summary = campaign_benchmarks_summary,
        channel_benchmarks_summary  = channel_benchmarks_summary,
        audience_insights           = audience_insights,
        moment_type_rules_summary   = moment_type_rules_summary,
        brand_locks                 = brand_locks_dict,
        product_paths               = product_paths,
        logo_paths                  = logo_paths,
        product_image_map           = product_image_map,
    )

    # Emit key brand fields to session state so ALL downstream agents
    # (KV generators, ranker, content agent …) can reference them via
    # {brand_guidelines}, {brand_name}, {product_image_map} in instructions.
    # Only include brand_rules_summary in state when it differs from brand_guidelines
    # (i.e. live mode returned a summarised search result). In local/gcs mode it
    # would be a duplicate — brand_guidelines already covers it.
    state_dict = {
        "brand_guidelines":            brand_guidelines,
        "brand_visual_rules":          brand_visual_rules,
        "brand_name":                  brand,
        "brand_locks_json":            json.dumps(brand_locks_dict),
        "brand_profile_json":          json.dumps(brand_profile_dict) if brand_profile_dict else "{}",
        "product_image_map":           json.dumps(product_image_map),
        "product_description_map":     json.dumps(product_description_map),
        "product_name":                product,
        "brief_request_json":          json.dumps(brief_dict),
        "fan_truth_summary":           fan_truth_summary,
        "campaign_benchmarks_summary": campaign_benchmarks_summary,
        "channel_benchmarks_summary":  channel_benchmarks_summary,
        "audience_insights":           audience_insights,
        "moment_type_rules_summary":   moment_type_rules_summary,
        "market_trends_summary":       _trends["summary"],
        "_source_stats": json.dumps({
            k: v for k, v in {
                "_chunks":              _stat_chunks,
                "_market_signals":      _stat_market_signals,
                "_campaign_records":    _stat_campaign_records,
                "_product_skus":        len(product_paths),
                "_market_top_keyword":  _trends["top_keyword"],
                "_market_avg_interest": _trends["avg_interest"],
                "_market_summary":      _trends["summary"],
            }.items() if v  # omit zeros/empty — lets frontend ?? fallbacks stay active
        }),
    }
    if brand_rules_summary:
        state_dict["brand_rules_summary"] = brand_rules_summary

    return Event(output=briefing_context, state=state_dict)


# ── KV FAN-IN FUNCTION NODE ───────────────────────────────────────────────

def aggregate_kv_concepts(
    node_input=None,  # JoinNode passes a list of all upstream outputs — not used; we read from state
    kv_concept_1:   str = "",
    kv_concept_2:   str = "",
    kv_image_key_1: str = "",
    kv_image_key_2: str = "",
) -> Event:
    """
    Fan-in aggregator: collect both KV concept outputs into one batch.

    Runs after kv_image_agent_1 and kv_image_agent_2 complete (via JoinNode).
    Each concept JSON has been enriched with image_artifact_key by the image agent.

    Returns an Event that:
      - Passes the aggregated JSON string as output to kv_ranker
      - Persists kv_concepts_all to session state for {kv_concepts_all} in instructions
    """
    image_uris = {
        1: kv_image_key_1,
        2: kv_image_key_2,
    }
    concepts = []
    missing  = []
    for i, raw in enumerate([kv_concept_1, kv_concept_2], start=1):
        if raw:
            try:
                clean = raw.strip() if isinstance(raw, str) else raw
                if isinstance(clean, str) and clean.startswith("```"):
                    clean = clean.split("\n", 1)[1] if "\n" in clean else clean
                    clean = clean.rsplit("```", 1)[0].strip()
                concept = json.loads(clean) if isinstance(clean, str) else clean
                if image_uris.get(i) and not concept.get("image_artifact_key"):
                    concept["image_artifact_key"] = image_uris[i]
                concepts.append(concept)
            except Exception:
                entry = {"raw": str(raw), "generator_id": i}
                if image_uris.get(i):
                    entry["image_artifact_key"] = image_uris[i]
                concepts.append(entry)
        else:
            missing.append(i)

    batch = {"concepts": concepts, "count": len(concepts), "missing": missing}
    batch_json = json.dumps(batch)

    logger.info("aggregate_kv_concepts", count=len(concepts), missing=missing)

    return Event(
        output = batch_json,
        state  = {"kv_concepts_all": batch_json},
    )


# ── FAN TRUTH GATE ────────────────────────────────────────────────────────────
#
# Acts as the exit condition for the LoopAgent wrapping briefing_agent.
# Escalates (exits the loop) on PASS; writes retry feedback to state on FAIL.
# Max retries are enforced by LoopAgent(max_iterations=3).

class FanTruthGateAgent(BaseAgent):
    """
    Quality gate between briefing_agent iterations in the briefing_loop.

    PASS (fan_truth_score.overall >= 70):
        Escalates → LoopAgent exits → pipeline continues to culture_analyst.

    FAIL:
        Writes specific feedback to state["brief_retry_feedback"] so
        briefing_agent can see it on the next iteration, then yields normally
        → LoopAgent starts the next iteration.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        machine_brief_json = ctx.state.get("machine_brief", "")

        verdict  = "FAIL"
        overall  = 0
        note     = ""
        suggested_alternative = ""
        validation_summary    = ""

        try:
            data         = json.loads(machine_brief_json)
            ft           = data.get("fan_truth_score", {})
            verdict      = ft.get("verdict", "FAIL")
            overall      = ft.get("overall", 0)
            note         = ft.get("note", "")
            suggested_alternative = ft.get("suggested_alternative", "")
            validation_summary = data.get("validation", {}).get("summary", "")
        except Exception as exc:
            logger.warning("fan_truth_gate_parse_failed", error=str(exc))

        if verdict == "PASS":
            logger.info("fan_truth_gate_pass", overall=overall)
            yield Event(
                author  = self.name,
                content = types.Content(parts=[types.Part(
                    text=f"Fan Truth PASS ({overall}/100). Brief approved — proceeding to cultural intelligence.",
                )]),
                actions = EventActions(escalate=True),
            )
        else:
            feedback_lines = [
                f"FAN TRUTH RETRY REQUIRED — score {overall}/100 (FAIL).",
            ]
            if note:
                feedback_lines.append(f"Issue: {note}")
            if suggested_alternative:
                feedback_lines.append(
                    f"Rewrite the fan_truth field using this stronger statement:\n"
                    f'  "{suggested_alternative}"'
                )
            if validation_summary:
                feedback_lines.append(f"Validation summary: {validation_summary}")
            feedback_lines.append(
                "Regenerate the full MachineBrief. The fan_truth_score.overall MUST reach 70 or above."
            )
            feedback = "\n".join(feedback_lines)

            logger.info("fan_truth_gate_fail", overall=overall)
            yield Event(
                author  = self.name,
                content = types.Content(parts=[types.Part(text=feedback)]),
                state   = {"brief_retry_feedback": feedback},
            )


# ── PERSISTENCE FUNCTION NODES ──────────────────────────────────────────────────
#
# Each node follows the dual-write pattern:
#   1. ctx.state[key] = json_string     → available immediately in this invocation
#   2. ctx.save_artifact(...)           → durable, downloadable, auditable
#   3. return Event(state={key: ...})   → belt-and-suspenders state commit
#
# Agents generate; nodes persist. No tools on LLM agents for persistence.

async def persist_brief(ctx: InvocationContext) -> Event:
    """
    Persist briefing_agent output.
    Runs after briefing_loop (LoopAgent). Reads MachineBrief from state
    (briefing_agent writes it there via output_key="machine_brief").
    Writes machine_brief to state and saves a JSON artifact.
    Also logs to BigQuery for audit.
    """
    brief_json = ctx.state.get("machine_brief", "")
    if not brief_json:
        logger.warning("persist_brief_empty")
        return Event(state={})

    try:
        node_input = MachineBrief.model_validate_json(brief_json)
    except Exception as exc:
        logger.warning("persist_brief_parse_failed", error=str(exc))
        return Event(state={})

    # Normalise to canonical JSON (re-serialise from the validated model)
    brief_data = node_input.model_dump(mode="json")

    # Merge real data-source counts captured by load_brand_context
    _source_stats_raw = ctx.state.get("_source_stats", "")
    if _source_stats_raw:
        try:
            _stats = json.loads(_source_stats_raw) if isinstance(_source_stats_raw, str) else _source_stats_raw
            brief_data.update(_stats)
        except Exception:
            pass

    brief_json = json.dumps(brief_data)

    # State write
    ctx.state["machine_brief"] = brief_json

    # Artifact save
    try:
        await ctx.save_artifact(
            filename = f"machine_brief_{node_input.campaign_id}.json",
            artifact = types.Part.from_bytes(
                data      = brief_json.encode("utf-8"),
                mime_type = "application/json",
            ),
        )
    except Exception as e:
        logger.warning("persist_brief_artifact_failed", error=str(e))

    # BigQuery audit log (non-fatal)
    try:
        log_brief_to_bigquery(
            node_input.campaign_id,
            node_input.structured_brief.model_dump(mode="json"),
            node_input.model_dump(mode="json"),
        )
    except Exception as e:
        logger.warning("persist_brief_bq_failed", error=str(e))

    logger.info("persist_brief", campaign_id=node_input.campaign_id)
    return Event(state={"machine_brief": brief_json})


async def persist_culture(ctx: InvocationContext, node_input: CultureAnalysis) -> Event:
    """
    Persist culture_formatter output.
    Runs between culture_formatter and creative_director.
    Writes culture_analysis to state and saves a JSON artifact.
    """
    culture_json = json.dumps(node_input.model_dump(mode="json"))

    ctx.state["culture_analysis"] = culture_json

    try:
        await ctx.save_artifact(
            filename = "culture_analysis.json",
            artifact = types.Part.from_bytes(
                data      = culture_json.encode("utf-8"),
                mime_type = "application/json",
            ),
        )
    except Exception as e:
        logger.warning("persist_culture_artifact_failed", error=str(e))

    logger.info("persist_culture")
    return Event(state={"culture_analysis": culture_json})


async def persist_strategy(ctx: InvocationContext, node_input: CreativeStrategy) -> Event:
    """
    Persist creative_director output.
    Runs between creative_director and copy_agent.
    Writes creative_strategy to state and saves a JSON artifact.
    """
    strategy_json = json.dumps(node_input.model_dump(mode="json"))

    ctx.state["creative_strategy"] = strategy_json

    try:
        await ctx.save_artifact(
            filename = f"creative_strategy_{node_input.campaign_id}.json",
            artifact = types.Part.from_bytes(
                data      = strategy_json.encode("utf-8"),
                mime_type = "application/json",
            ),
        )
    except Exception as e:
        logger.warning("persist_strategy_artifact_failed", error=str(e))

    logger.info("persist_strategy", campaign_id=node_input.campaign_id)
    return Event(state={"creative_strategy": strategy_json})


async def persist_copy(ctx: InvocationContext, node_input: CampaignCopy) -> Event:
    """
    Persist copy_agent output.
    Runs between copy_agent and the KV generator fan-out.
    Writes campaign_copy to state and saves a JSON artifact.
    """
    copy_json = json.dumps(node_input.model_dump(mode="json"))

    ctx.state["campaign_copy"] = copy_json

    try:
        await ctx.save_artifact(
            filename = f"campaign_copy_{node_input.campaign_id}.json",
            artifact = types.Part.from_bytes(
                data      = copy_json.encode("utf-8"),
                mime_type = "application/json",
            ),
        )
    except Exception as e:
        logger.warning("persist_copy_artifact_failed", error=str(e))

    logger.info("persist_copy", campaign_id=node_input.campaign_id)
    return Event(state={"campaign_copy": copy_json})


# ── Private helpers ────────────────────────────────────────────────────────────────────────────

def _extract_text(node_input) -> str:
    """
    Extract plain text from the various types ADK may pass as node_input:
      - str            → returned as-is
      - Content object → .parts[0].text extracted (google.genai.types.Content)
      - Part object    → .text extracted (google.genai.types.Part)
      - None / other   → empty string
    """
    if node_input is None:
        return ""
    if isinstance(node_input, str):
        return node_input
    # google.genai.types.Content  (has .parts list)
    if hasattr(node_input, "parts") and node_input.parts:
        for part in node_input.parts:
            if hasattr(part, "text") and isinstance(part.text, str) and part.text:
                return part.text
    # google.genai.types.Part  (has .text directly)
    if hasattr(node_input, "text") and isinstance(getattr(node_input, "text", None), str):
        return node_input.text  # type: ignore[return-value]
    return ""


def _parse_kv_brief(text: str) -> dict:
    """
    Parse a plain-text "Key: Value" brief pasted into ADK web.

    Handles the format:
        Brand: Rnorr
        Campaign name: Rnorr Liquid Seasoning Summer 2026
        Channels: Instagram, TikTok, OOH
        Target audience: Home cooks aged 25-40
        ...

    Returns a dict compatible with what briefing_agent expects.
    """
    # Field name → brief_dict key mapping (case-insensitive)
    _FIELD_MAP = {
        "brand":            "brand",
        "campaign name":    "campaign_name",
        "product":          "product",
        "product category": "product_category",
        "market":           "market",
        "season":           "season",
        "channels":         "channels",
        "budget":           "budget",
        "campaign start":   "campaign_start",
        "campaign end":     "campaign_end",
        "target audience":  "_audience_raw",
        "fan truth":        "fan_truth",
        "kpi targets":      "kpis",
        "moment type":      "moment_type",
        "goal":             "goal",
        "tone":             "tone",
        "notes":            "notes",
        "legal claims":     "legal_claims",
        "guardrails":       "guardrails",
    }

    result: dict = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key_raw, _, value = line.partition(":")
        key   = key_raw.strip().lower()
        value = value.strip()
        if not value:
            continue
        mapped = _FIELD_MAP.get(key)
        if mapped:
            result[mapped] = value

    # Channels: "Instagram, TikTok, OOH" → ["Instagram", "TikTok", "OOH"]
    if "channels" in result and isinstance(result["channels"], str):
        result["channels"] = [c.strip() for c in result["channels"].split(",") if c.strip()]

    # Audience: "Home cooks aged 25-40" → {"segment": "Home cooks", "age_range": "25-40"}
    audience_raw = result.pop("_audience_raw", None)
    if audience_raw:
        age_match = re.search(r"\b(\d{2}-\d{2})\b", audience_raw)
        age_range = age_match.group(1) if age_match else ""
        segment   = re.sub(r"\s*aged\s*\d{2}-\d{2}", "", audience_raw, flags=re.IGNORECASE).strip()
        result["audience"] = {"segment": segment, "age_range": age_range}

    if result:
        logger.info("parse_kv_brief", keys=list(result.keys()))
    return result


def _parse_brand_locks(brand: str, guidelines_text: str) -> dict:
    """
    Parse brand lock values from guidelines markdown.

    Priority:
      1. YAML fenced blocks (```yaml ... ```) — structured, authoritative
      2. Markdown prose extraction — hex colour tables, font names, DO NOT rules
      3. BrandLocks() defaults — empty placeholders
    """
    base = BrandLocks().model_dump()

    if not guidelines_text:
        logger.info("brand_locks_default", brand=brand)
        return base

    # Pass 1: YAML blocks ─────────────────────────────────────────────────
    try:
        for block in re.findall(
            r"```(?:yaml|YAML)\n(.*?)```", guidelines_text, re.DOTALL
        ):
            data = yaml.safe_load(block)
            if isinstance(data, dict) and any(
                k in data for k in ("font", "primary_colour", "logo", "voice")
            ):
                logger.info("brand_locks_parsed_yaml", brand=brand)
                return {**base, **data}
    except Exception as exc:
        logger.warning("brand_locks_yaml_parse_failed", brand=brand, error=str(exc))

    # Pass 2: Markdown prose extraction ──────────────────────────────────
    # Extract colours from table rows: | **Name** | ... | **#RRGGBB** |
    extracted: dict = {}
    for name, hex_code in re.findall(
        r"\*\*([^|*]+?)\*\*[^|]*\|[^|]*\|[^|]*\|[^|]*\*\*#([A-Fa-f0-9]{6})\*\*",
        guidelines_text,
    ):
        name_lower = name.lower().strip()
        if "green" in name_lower and "primary_colour" not in extracted:
            extracted["primary_colour"] = f"#{hex_code}"
        elif "yellow" in name_lower and "accent_colour" not in extracted:
            extracted["accent_colour"] = f"#{hex_code}"

    # Extract display font name from "#### FontName — Display" heading
    font_match = re.search(r"####\s+(\w+)\s*[\u2014\u2013-]\s*Display", guidelines_text)
    if font_match:
        extracted["font"] = font_match.group(1)

    # Extract forbidden colour pairings from accessibility prose
    # Matches lines like: "**White on Rnorr Yellow** — **fails contrast.** Never use for type."
    colour_fails = re.findall(
        r"\*\*(\w[^*]+on[^*]+)\*\*\s*[\u2014\u2013-]\s*\*\*(?:fails|Never)[^*]*\*\*",
        guidelines_text,
        re.IGNORECASE,
    )
    if colour_fails:
        extra_forbidden = [f"{c.strip()} — fails contrast, never use for type" for c in colour_fails]
        extracted["forbidden"] = base.get("forbidden", []) + extra_forbidden

    if extracted:
        logger.info("brand_locks_parsed_prose", brand=brand, keys=list(extracted.keys()))
        return {**base, **extracted}

    logger.info("brand_locks_default", brand=brand)
    return base


def _extract_brand_visual_rules(guidelines_text: str) -> str:
    """
    Extract a compact visual/colour reference card from brand guidelines markdown.

    Pulls: colour DO/DO NOT section, Accessibility rules, Engagement-based
    Colour Volume table, and Green-Yellow relationship. Capped at 3 000 chars
    so it fits comfortably in a KV agent's prompt without dominating it.

    This is the short-term substitute for a Vertex AI Search retrieval that
    would let agents query specific rules on demand.
    """
    if not guidelines_text:
        return ""

    _TARGETS = {
        "colour do",
        "colour do / do not",
        "accessibility",
        "engagement-based colour",
        "green\u2013yellow relationship",
        "colour proportion",
    }

    lines        = guidelines_text.splitlines()
    sections     = []
    in_target    = False
    current: list[str] = []

    def _is_heading(line: str) -> bool:
        s = line.strip()
        return bool(re.match(r"^#{1,5}\s", s))

    for line in lines:
        stripped = line.strip()
        lower    = stripped.lower()

        if _is_heading(line):
            if in_target and current:
                sections.append("\n".join(current))
                current = []
            in_target = any(kw in lower for kw in _TARGETS)

        if in_target:
            current.append(line)

    if in_target and current:
        sections.append("\n".join(current))

    if not sections:
        return ""

    result = "\n\n---\n\n".join(sections)
    if len(result) > 3000:
        result = result[:2997] + "..."
    return result


def _stub_fan_truth() -> str:
    return (
        "Fan Truth library not available (SEARCH_MODE != live). "
        "Score and validate the brief's Fan Truth using the brand guidelines "
        "and the three criteria: Specific, Shared, Special."
    )


def _stub_benchmarks() -> str:
    return (
        "Historical campaign benchmark data not available (SEARCH_MODE != live). "
        "Use typical FMCG benchmarks: CTR 0.5-2%, ROAS 2-4x, reach 5-20% of target "
        "audience. Flag KPI targets >50% above these as AMBITIOUS."
    )


def _stub_channel_benchmarks() -> str:
    return (
        "Channel benchmark data not available (SEARCH_MODE != live). "
        "Use typical values: Instagram CTR 1-3%, TikTok engagement 5-10%, "
        "OOH dwell time 2-4s (favour brand colour ratio 70:30). "
        "Recommend channel mix based on audience segment and brief objectives."
    )


def _stub_moment_type(moment_type: str) -> str:
    return (
        f"Moment type '{moment_type}' rules: "
        "Day-to-Day (70% of campaigns) — standard brief, Fan Truth required, "
        "no special approvals. "
        "Brand Moment (15%) — major brand event, treated logo may be approved by brand team. "
        "Partnership Moment (15%) — co-brand campaign, shared-pen creative approach, "
        "partner brand guidelines must be respected."
    )
