"""
bq_vector_client.py — semantic search over campaign data via BigQuery VECTOR_SEARCH.

Drop-in replacement for pgvector_client.py.
Set SEARCH_MODE=bigquery in settings to activate.

Requires:
  - BigQuery tables with `embedding ARRAY<FLOAT64>` columns (run setup_bq_vectors.py)
  - GOOGLE_API_KEY for Gemini text-embedding-004
  - GOOGLE_CLOUD_PROJECT / GCP_PROJECT

Tables used (all in dataset configured by settings.bq_dataset):
  fan_truth_library     — fan truths with embeddings
  historical_campaigns  — campaign benchmarks with embeddings
  channel_benchmarks    — per-channel benchmarks with embeddings
  customer_segments     — synthetic audience profiles with embeddings
  brand_guidelines_chunks — chunked brand guidelines with embeddings
"""

from __future__ import annotations

import os
import structlog
from google.cloud import bigquery
from app.config import get_settings

logger   = structlog.get_logger()
settings = get_settings()

GEMINI_EMBEDDING_DIM   = 768
GEMINI_EMBEDDING_MODEL = settings.gemini_embedding_model or "text-embedding-004"

_bq_client: bigquery.Client | None = None


def _bq() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=settings.gcp_project)
    return _bq_client


def _embed(text: str) -> list[float]:
    """Generate a Gemini text-embedding-004 embedding (768 dims)."""
    try:
        import google.genai as genai
        api_key = os.getenv("GOOGLE_API_KEY", "")
        client  = genai.Client(api_key=api_key if api_key else None, vertexai=False)
        result  = client.models.embed_content(
            model    = GEMINI_EMBEDDING_MODEL,
            contents = text,
            config   = {"task_type": "RETRIEVAL_QUERY", "output_dimensionality": 768},
        )
        return list(result.embeddings[0].values)
    except Exception as e:
        logger.warning("bq_embed_failed", error=str(e), fallback="zero_vector")
        return [0.0] * GEMINI_EMBEDDING_DIM


def _vec_literal(embedding: list[float]) -> str:
    """Render an embedding list as a BigQuery ARRAY<FLOAT64> literal."""
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


def _project_dataset() -> str:
    return f"`{settings.gcp_project}.{settings.bq_dataset}`"


def search_brand_guidelines(brand: str, query: str, top_k: int = 5) -> str:
    """Semantic search over chunked brand guidelines (RAG)."""
    emb = _embed(f"{brand} brand guidelines {query}")
    vec = _vec_literal(emb)
    pd  = _project_dataset()

    sql = f"""
        SELECT base.brand, base.content, base.source_file, distance
        FROM VECTOR_SEARCH(
          (SELECT * FROM {pd}.brand_guidelines_chunks
           WHERE brand = @brand OR brand = 'All'),
          'embedding',
          (SELECT {vec} AS embedding),
          top_k => {top_k},
          distance_type => 'COSINE'
        )
        ORDER BY distance
    """
    try:
        rows = list(_bq().query(
            sql,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("brand", "STRING", brand),
            ]),
        ).result())
    except Exception as e:
        logger.warning("bq_search_brand_guidelines_failed", error=str(e))
        return ""

    if not rows:
        return ""
    chunks = "\n\n---\n\n".join(r["content"] for r in rows)
    return f"Brand guidelines (RAG — {len(rows)} most relevant sections):\n\n{chunks}"


def search_fan_truths(brand: str, product_category: str, fan_truth: str, top_k: int = 3) -> str:
    """Find the most relevant Fan Truth examples for this brief."""
    query_text = f"{brand} fan truth {fan_truth} {product_category}"
    emb = _embed(query_text)
    vec = _vec_literal(emb)
    pd  = _project_dataset()
    tbl = settings.bq_fan_truths_table  # fan_truth_library

    sql = f"""
        SELECT base.statement, base.verdict, base.specific, base.shared,
               base.special, base.overall, distance
        FROM VECTOR_SEARCH(
          (SELECT * FROM {pd}.{tbl}
           WHERE brand = @brand OR brand IS NULL),
          'embedding',
          (SELECT {vec} AS embedding),
          top_k => {top_k},
          distance_type => 'COSINE'
        )
        ORDER BY distance
    """
    try:
        rows = list(_bq().query(
            sql,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("brand", "STRING", brand),
            ]),
        ).result())
    except Exception as e:
        logger.warning("bq_search_fan_truths_failed", error=str(e))
        return "No Fan Truth examples found in database."

    if not rows:
        return "No Fan Truth examples found in database."

    lines = ["Fan Truth examples and scoring benchmarks:\n"]
    for r in rows:
        lines.append(
            f"  • \"{r['statement']}\"\n"
            f"    Verdict: {r['verdict']} | "
            f"Specific: {r['specific']}/100 | Shared: {r['shared']}/100 | "
            f"Special: {r['special']}/100 | Overall: {r['overall']}/100\n"
        )
    return "\n".join(lines)


def search_campaign_benchmarks(
    brand: str, product_category: str, market: str, season: str, top_k: int = 3
) -> str:
    """Find historical campaign performance benchmarks."""
    query_text = f"{brand} {product_category} {market} {season} campaign performance"
    emb = _embed(query_text)
    vec = _vec_literal(emb)
    pd  = _project_dataset()
    tbl = settings.bq_campaigns_table  # historical_campaigns

    sql = f"""
        SELECT base.brand, base.product_category, base.market, base.season,
               base.channels, base.reach, base.ctr_pct, base.roas,
               base.engagement_pct, base.budget_gbp, base.notes, distance
        FROM VECTOR_SEARCH(
          (SELECT * FROM {pd}.{tbl}),
          'embedding',
          (SELECT {vec} AS embedding),
          top_k => {top_k},
          distance_type => 'COSINE'
        )
        ORDER BY distance
    """
    try:
        rows = list(_bq().query(sql).result())
    except Exception as e:
        logger.warning("bq_search_campaign_benchmarks_failed", error=str(e))
        return "No historical campaign benchmarks found."

    if not rows:
        return "No historical campaign benchmarks found."

    lines = ["Historical campaign benchmarks:\n"]
    for r in rows:
        channels = r["channels"] or []
        lines.append(
            f"  • {r['brand']} — {r['product_category']} | {r['market']} | {r['season']}\n"
            f"    Channels: {', '.join(channels)}\n"
            f"    Reach: {int(r['reach'] or 0):,} | CTR: {r['ctr_pct']}% | ROAS: {r['roas']}x | "
            f"Engagement: {r['engagement_pct']}% | Budget: £{float(r['budget_gbp'] or 0):,.0f}\n"
            f"    Notes: {r['notes']}\n"
        )
    return "\n".join(lines)


def search_audience_insights(
    brand: str, segment: str, age_range: str, channels: list[str], top_k: int = 3
) -> str:
    """Semantic search over CDP customer segments."""
    query_text = f"{brand} {segment} {age_range} {' '.join(channels)} customer behaviour"
    emb = _embed(query_text)
    vec = _vec_literal(emb)
    pd  = _project_dataset()

    sql = f"""
        SELECT base.segment_name, base.size_estimate, base.age_range, base.income_band,
               base.top_channels, base.avg_weekly_spend_gbp,
               base.behavioural_notes, base.fan_truth_benchmark, distance
        FROM VECTOR_SEARCH(
          (SELECT * FROM {pd}.customer_segments
           WHERE brand = @brand OR brand = 'All'),
          'embedding',
          (SELECT {vec} AS embedding),
          top_k => {top_k},
          distance_type => 'COSINE'
        )
        ORDER BY distance
    """
    try:
        rows = list(_bq().query(
            sql,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("brand", "STRING", brand),
            ]),
        ).result())
    except Exception as e:
        logger.warning("bq_search_audience_insights_failed", error=str(e))
        return ""

    if not rows:
        return "No customer segment data available."

    lines = ["Customer audience intelligence (BigQuery segments):\n"]
    for r in rows:
        top_ch = r["top_channels"] or []
        lines.append(
            f"  Segment: {r['segment_name']} | Size: {int(r['size_estimate'] or 0):,} | "
            f"Age: {r['age_range']} | Income: {r['income_band']}\n"
            f"  Top channels: {', '.join(top_ch)}\n"
            f"  Avg weekly spend: £{r['avg_weekly_spend_gbp']}\n"
            f"  Behaviour: {r['behavioural_notes']}\n"
            f"  Fan Truth benchmark: {r['fan_truth_benchmark']}\n"
        )
    return "\n".join(lines)


def search_channel_benchmarks(
    channels: list[str], market: str, audience_segment: str, top_k: int = 6
) -> str:
    """Find per-channel performance benchmarks."""
    query_text = f"{', '.join(channels)} {market} {audience_segment} channel benchmark"
    emb = _embed(query_text)
    vec = _vec_literal(emb)
    pd  = _project_dataset()
    tbl = settings.bq_channels_table  # channel_benchmarks

    # Request more results than needed, then post-filter to requested channels.
    # Avoids UNNEST inside VECTOR_SEARCH subquery (which may not accept params).
    fetch_k = max(top_k * 3, 20)

    sql = f"""
        SELECT base.channel, base.market, base.audience_segment,
               base.ctr_pct, base.cpm_gbp, base.engagement_pct,
               base.completion_pct, base.avg_dwell_sec, base.notes, distance
        FROM VECTOR_SEARCH(
          TABLE {pd}.{tbl},
          'embedding',
          (SELECT {vec} AS embedding),
          top_k => {fetch_k},
          distance_type => 'COSINE'
        )
        ORDER BY distance
    """
    try:
        all_rows = list(_bq().query(sql).result())
        # Post-filter to requested channels if specified
        rows = (
            [r for r in all_rows if r["channel"] in channels][:top_k]
            if channels else all_rows[:top_k]
        )
    except Exception as e:
        logger.warning("bq_search_channel_benchmarks_failed", error=str(e))
        return "No channel benchmarks found."

    if not rows:
        return "No channel benchmarks found."

    lines = ["Per-channel performance benchmarks:\n"]
    for r in rows:
        metrics = []
        if r["ctr_pct"]:        metrics.append(f"CTR: {r['ctr_pct']}%")
        if r["cpm_gbp"]:        metrics.append(f"CPM: £{r['cpm_gbp']}")
        if r["engagement_pct"]: metrics.append(f"Engagement: {r['engagement_pct']}%")
        if r["completion_pct"]: metrics.append(f"Completion: {r['completion_pct']}%")
        if r["avg_dwell_sec"]:  metrics.append(f"Dwell: {r['avg_dwell_sec']}s")
        lines.append(
            f"  • {r['channel']} ({r['market']} | {r['audience_segment']})\n"
            f"    {' | '.join(metrics)}\n"
            f"    {r['notes']}\n"
        )
    return "\n".join(lines)
