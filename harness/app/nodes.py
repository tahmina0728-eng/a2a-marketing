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

import structlog
import yaml

from google.adk import Event

from app.brand_assets import get_asset_loader
from app.config import get_settings
from app.models import BrandLocks, BriefingContext
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

    # Parse brand locks from guidelines YAML blocks ───────────────────────
    brand_locks_dict = _parse_brand_locks(brand, brand_guidelines)

    # Load search / benchmark data ────────────────────────────────────────
    if settings.search_mode == "live" and brand:
        sc = get_search_client()

        try:
            brand_rules_summary = sc.get_brand_rules(
                product_category=product_category, channels=channels
            ).summary or brand_guidelines
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
            campaign_benchmarks_summary = sc.get_campaign_benchmarks(
                product_category=product_category, market=market, season=season
            ).summary or _stub_benchmarks()
        except Exception:
            campaign_benchmarks_summary = _stub_benchmarks()

        try:
            channel_benchmarks_summary = sc.get_channel_benchmarks(
                channels=channels, market=market, audience_segment=audience_segment
            ).summary or _stub_channel_benchmarks()
        except Exception:
            channel_benchmarks_summary = _stub_channel_benchmarks()

        try:
            moment_type_rules_summary = sc.get_moment_type_rules(
                moment_type=moment_type
            ).summary or _stub_moment_type(moment_type)
        except Exception:
            moment_type_rules_summary = _stub_moment_type(moment_type)

    else:
        # gcs_files / local mode — brand guidelines IS the brand rules reference
        brand_rules_summary          = brand_guidelines
        fan_truth_summary            = _stub_fan_truth()
        campaign_benchmarks_summary  = _stub_benchmarks()
        channel_benchmarks_summary   = _stub_channel_benchmarks()
        moment_type_rules_summary    = _stub_moment_type(moment_type)

    # Build Product1 / Product2 … name → GCS URI map ─────────────────────
    product_image_map = {
        f"Product{i + 1}": path
        for i, path in enumerate(product_paths)
    }

    logger.info(
        "load_brand_context",
        brand              = brand,
        has_guidelines     = bool(brand_guidelines),
        search_mode        = settings.search_mode,
        channels           = channels,
        brief_keys         = list(brief_dict.keys()),
        product_image_map  = product_image_map,
    )

    briefing_context = BriefingContext(
        brief_request               = brief_dict,
        brand_guidelines            = brand_guidelines,
        brand_rules_summary         = brand_rules_summary,
        fan_truth_summary           = fan_truth_summary,
        campaign_benchmarks_summary = campaign_benchmarks_summary,
        channel_benchmarks_summary  = channel_benchmarks_summary,
        moment_type_rules_summary   = moment_type_rules_summary,
        brand_locks                 = brand_locks_dict,
        product_paths               = product_paths,
        logo_paths                  = logo_paths,
        product_image_map           = product_image_map,
    )

    # Emit key brand fields to session state so ALL downstream agents
    # (KV generators, ranker, content agent …) can reference them via
    # {brand_guidelines}, {brand_name}, {product_image_map} in instructions.
    return Event(
        output = briefing_context,
        state  = {
            "brand_guidelines":            brand_guidelines,
            "brand_name":                  brand,
            "brand_locks_json":            json.dumps(brand_locks_dict),
            "product_image_map":           json.dumps(product_image_map),
            "brief_request_json":          json.dumps(brief_dict),
            "brand_rules_summary":         brand_rules_summary,
            "fan_truth_summary":           fan_truth_summary,
            "campaign_benchmarks_summary": campaign_benchmarks_summary,
            "channel_benchmarks_summary":  channel_benchmarks_summary,
            "moment_type_rules_summary":   moment_type_rules_summary,
        },
    )


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


# ── Private helpers ───────────────────────────────────────────────────────

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
    """Parse brand lock values from YAML fenced blocks in guidelines markdown.
    Falls back to BrandLocks() defaults if no structured locks found."""
    if guidelines_text:
        try:
            for block in re.findall(
                r"```(?:yaml|YAML)\n(.*?)```", guidelines_text, re.DOTALL
            ):
                data = yaml.safe_load(block)
                if isinstance(data, dict) and any(
                    k in data for k in ("font", "primary_colour", "logo", "voice")
                ):
                    logger.info("brand_locks_parsed", brand=brand)
                    return {**BrandLocks().model_dump(), **data}
        except Exception as exc:
            logger.warning("brand_locks_parse_failed", brand=brand, error=str(exc))

    logger.info("brand_locks_default", brand=brand)
    return BrandLocks().model_dump()


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
