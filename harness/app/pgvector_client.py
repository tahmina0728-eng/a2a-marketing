"""
pgvector_client.py — semantic search over campaign benchmark data.

Used when SEARCH_MODE=pgvector in .env.
Replaces the stub benchmark data in load_brand_context with real
vector-searched results from PostgreSQL + pgvector.
"""

import os
import structlog
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import get_settings

logger   = structlog.get_logger()
settings = get_settings()

# ── Embedding configuration ───────────────────────────────────────────────────
# Set USE_GEMINI_EMBEDDINGS=true in .env to use Gemini Embedding 2
# Model: text-embedding-004 (768 dims) — stable, free tier via Google AI
# Requires GOOGLE_API_KEY or GOOGLE_GENAI_USE_VERTEXAI=TRUE + ADC
USE_GEMINI_EMBEDDINGS = os.getenv("USE_GEMINI_EMBEDDINGS", "false").lower() == "true"
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
GEMINI_EMBEDDING_DIM = 768   # gemini-embedding-2 with output_dimensionality=768 (under HNSW 2000 limit)

# ── Option A: Gemini Embedding 2 (text-embedding-004) ────────────────────────
def _embed_gemini(text: str) -> list[float]:
    """
    Call gemini-embedding-2 via Google AI (generativelanguage.googleapis.com).
    Uses GOOGLE_API_KEY with vertexai=False to bypass GOOGLE_GENAI_USE_VERTEXAI —
    gemini-embedding-2 is not available on Vertex AI (404).
    """
    try:
        import google.genai as genai

        api_key = os.getenv("GOOGLE_API_KEY", "")
        client = genai.Client(api_key=api_key if api_key else None, vertexai=False)

        result = client.models.embed_content(
            model   = GEMINI_EMBEDDING_MODEL,
            contents= text,
            config  = {"task_type": "RETRIEVAL_QUERY", "output_dimensionality": 768},
        )
        embedding = result.embeddings[0].values
        logger.debug("gemini_embedding_ok", model=GEMINI_EMBEDDING_MODEL, dim=len(embedding))
        return list(embedding)

    except Exception as e:
        logger.warning("gemini_embedding_failed", error=str(e),
                       fallback="zero_vector")
        return [0.0] * GEMINI_EMBEDDING_DIM


# ── Option B: sentence-transformers (all-MiniLM-L6-v2) — 384 dims ────────────
# Commented out but preserved for reference / local fallback
#
# _embedding_model = None
#
# def _get_model():
#     global _embedding_model
#     if _embedding_model is None:
#         try:
#             from sentence_transformers import SentenceTransformer
#             _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
#         except ImportError:
#             _embedding_model = None
#     return _embedding_model
#
# def _embed_st(text: str) -> list[float]:
#     model = _get_model()
#     if model is None:
#         return [0.0] * 384
#     return model.encode(text).tolist()


# ── Active embedding function ─────────────────────────────────────────────────
def _embed(text: str) -> list[float]:
    """
    Route to the configured embedding backend.
    USE_GEMINI_EMBEDDINGS=true  → Gemini text-embedding-004 (768 dims)
    USE_GEMINI_EMBEDDINGS=false → zero vector fallback (384 dims)

    NOTE: If you switch USE_GEMINI_EMBEDDINGS, you MUST rebuild all pgvector
    tables because the vector dimensions change (384 → 768).
    Run: uv run python scripts/setup_pgvector.py (drops + recreates tables)
    Then re-seed all data: seed_kaggle_cdp.py, seed_sephora_cdp.py
    """
    if USE_GEMINI_EMBEDDINGS:
        return _embed_gemini(text)
    # Fallback: zero vector (sentence-transformers not installed in prod image)
    return [0.0] * 384


def _clean(val: str) -> str:
    """Strip BOM, newlines and non-printable chars."""
    import re
    val = val.encode("utf-8").decode("utf-8-sig")
    return re.sub(r"[^\x20-\x7E]", "", val).strip()


def _connect():
    host     = _clean(os.getenv("PGVECTOR_HOST",     "127.0.0.1"))
    user     = _clean(os.getenv("PGVECTOR_USER",     "campaignos"))
    password = _clean(os.getenv("PGVECTOR_PASSWORD", "campaignos"))
    dbname   = _clean(os.getenv("PGVECTOR_DB",       "marketing"))

    # Unix socket path (Cloud SQL Auth Proxy) — no port needed
    if host.startswith("/"):
        return psycopg2.connect(
            host=host, user=user, password=password,
            dbname=dbname, cursor_factory=RealDictCursor,
        )
    return psycopg2.connect(
        host=host, port=int(os.getenv("PGVECTOR_PORT", "5433")),
        user=user, password=password,
        dbname=dbname, cursor_factory=RealDictCursor,
    )


def search_brand_guidelines(brand: str, query: str, top_k: int = 5) -> str:
    """Semantic search over chunked brand guidelines indexed from GCS."""
    emb = _embed(f"{brand} brand guidelines {query}")

    conn = _connect()
    cur  = conn.cursor()

    # Check if RAG index exists
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='brand_guidelines_chunks'")
    if cur.fetchone()["count"] == 0:
        cur.close(); conn.close()
        return ""

    cur.execute("""
        SELECT brand, content, source_file
        FROM brand_guidelines_chunks
        WHERE brand = %s OR brand = 'All'
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (brand, emb, top_k))

    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        return ""

    chunks = "\n\n---\n\n".join(r["content"] for r in rows)
    return f"Brand guidelines (RAG — {len(rows)} most relevant sections):\n\n{chunks}"


def search_fan_truths(brand: str, product_category: str, fan_truth: str, top_k: int = 3) -> str:
    """Find the most relevant Fan Truth examples for this brief."""
    query_text = f"{brand} fan truth {fan_truth} {product_category}"
    emb = _embed(query_text)

    conn = _connect()
    cur  = conn.cursor()
    cur.execute("""
        SELECT statement, verdict, specific, shared, special, overall
        FROM fan_truths
        WHERE brand = %s OR brand IS NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (brand, emb, top_k))

    rows = cur.fetchall()
    cur.close(); conn.close()

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


def search_campaign_benchmarks(brand: str, product_category: str, market: str, season: str, top_k: int = 3) -> str:
    """Find historical campaign performance benchmarks."""
    query_text = f"{brand} {product_category} {market} {season} campaign performance"
    emb = _embed(query_text)

    conn = _connect()
    cur  = conn.cursor()
    cur.execute("""
        SELECT brand, product_category, market, season, channels,
               reach, ctr_pct, roas, engagement_pct, budget_gbp, notes
        FROM campaign_benchmarks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (emb, top_k))

    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        return "No historical campaign benchmarks found."

    lines = ["Historical campaign benchmarks:\n"]
    for r in rows:
        lines.append(
            f"  • {r['brand']} — {r['product_category']} | {r['market']} | {r['season']}\n"
            f"    Channels: {', '.join(r['channels'] or [])}\n"
            f"    Reach: {r['reach']:,} | CTR: {r['ctr_pct']}% | ROAS: {r['roas']}x | "
            f"Engagement: {r['engagement_pct']}% | Budget: £{r['budget_gbp']:,.0f}\n"
            f"    Notes: {r['notes']}\n"
        )
    return "\n".join(lines)


def search_audience_insights(brand: str, segment: str, age_range: str, channels: list[str], top_k: int = 3) -> str:
    """
    Semantic search over CDP customer data.
    Uses customer_insights (real Kaggle data) if available,
    falls back to customer_segments (synthetic profiles).
    """
    query_text = f"{brand} {segment} {age_range} {' '.join(channels)} customer behaviour"
    emb = _embed(query_text)

    conn = _connect()
    cur  = conn.cursor()

    # Check if real Kaggle data is loaded
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='customer_insights'")
    has_real_data = cur.fetchone()["count"] > 0

    if has_real_data:
        cur.execute("SELECT COUNT(*) FROM customer_insights WHERE brand = %s", (brand,))
        real_count = cur.fetchone()["count"]
    else:
        real_count = 0

    if real_count > 0:
        # Query real Kaggle data
        cur.execute("""
            SELECT brand, age_range, income, mnt_wines, mnt_meat,
                   num_deals, web_visits, has_children, top_channels, crm_notes
            FROM customer_insights
            WHERE brand = %s OR brand = 'All'
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (brand, emb, top_k))
        rows = cur.fetchall()
        cur.close(); conn.close()

        if not rows:
            return "No customer data found for this brand."

        # Aggregate insights from the top matching customers
        avg_income   = sum(float(r["income"] or 0) for r in rows) / len(rows)
        avg_meat     = sum(float(r["mnt_meat"] or 0) for r in rows) / len(rows)
        avg_deals    = sum(int(r["num_deals"] or 0) for r in rows) / len(rows)
        avg_visits   = sum(int(r["web_visits"] or 0) for r in rows) / len(rows)
        has_kids     = any(r["has_children"] for r in rows)
        all_channels = [ch for r in rows for ch in (r["top_channels"] or [])]
        top_channels = sorted(set(all_channels), key=all_channels.count, reverse=True)[:3]

        lines = [
            f"Customer audience intelligence (Kaggle CDP — {real_count:,} {brand} profiles):\n",
            f"  Most relevant segment profiles found: {len(rows)} customers matched '{segment} {age_range}'",
            f"  Avg household income: £{avg_income:,.0f}/yr",
            f"  Avg annual meat/protein spend: £{avg_meat:,.0f}",
            f"  Avg deal purchases/year: {avg_deals:.1f} (higher = price-sensitive)",
            f"  Avg web visits/month: {avg_visits:.1f}",
            f"  Has children: {'Yes' if has_kids else 'No (majority)'}",
            f"  Top channels from behaviour: {', '.join(top_channels)}",
            f"\n  Representative CRM notes from top match:\n  \"{rows[0]['crm_notes'][:300]}...\"",
        ]
        return "\n".join(lines)

    else:
        # Fall back to synthetic customer_segments
        cur.execute("""
            SELECT segment_name, size_estimate, age_range, income_band,
                   top_channels, avg_weekly_spend_gbp, behavioural_notes, fan_truth_benchmark
            FROM customer_segments
            WHERE brand = %s OR brand = 'All'
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (brand, emb, top_k))
        rows = cur.fetchall()
        cur.close(); conn.close()

        if not rows:
            return "No customer segment data available."

        lines = ["Customer audience intelligence (synthetic segments — load Kaggle CSV for real data):\n"]
        for r in rows:
            lines.append(
                f"  Segment: {r['segment_name']} | Size: {r['size_estimate']:,} | "
                f"Age: {r['age_range']} | Income: {r['income_band']}\n"
                f"  Top channels: {', '.join(r['top_channels'] or [])}\n"
                f"  Avg weekly spend: £{r['avg_weekly_spend_gbp']}\n"
                f"  Behaviour: {r['behavioural_notes']}\n"
                f"  Fan Truth benchmark: {r['fan_truth_benchmark']}\n"
            )
        return "\n".join(lines)


def search_channel_benchmarks(channels: list[str], market: str, audience_segment: str, top_k: int = 6) -> str:
    """Find per-channel performance benchmarks."""
    query_text = f"{', '.join(channels)} {market} {audience_segment} channel benchmark"
    emb = _embed(query_text)

    conn = _connect()
    cur  = conn.cursor()
    cur.execute("""
        SELECT channel, market, audience_segment,
               ctr_pct, cpm_gbp, engagement_pct, completion_pct, avg_dwell_sec, notes
        FROM channel_benchmarks
        WHERE channel = ANY(%s) OR %s::text[] IS NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (channels, channels, emb, top_k))

    rows = cur.fetchall()
    cur.close(); conn.close()

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
