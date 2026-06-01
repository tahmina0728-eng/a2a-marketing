"""
index_bigquery.py — RAG indexer for BigQuery campaign/benchmark data.

Queries BigQuery tables and embeds each row into pgvector for semantic
retrieval by the briefing agent.

Tables indexed:
  briefing_agent.fan_truth_library      → fan_truths table
  briefing_agent.channel_benchmarks     → channel_benchmarks table
  briefing_agent.historical_campaigns   → campaign_benchmarks table

Run:
  cd d:\\campaignos\\harness
  uv run python scripts/index_bigquery.py

Requires:
  - GOOGLE_CLOUD_PROJECT in .env
  - BigQuery tables to exist (see harness/README.md for schema)
  - pgvector running on port 5433
"""

import os
import psycopg2
from psycopg2.extras import execute_values

GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
BQ_DATASET  = os.getenv("BQ_DATASET", "briefing_agent")
PG_HOST     = os.getenv("PGVECTOR_HOST", "127.0.0.1")
PG_PORT     = int(os.getenv("PGVECTOR_PORT", "5433"))
PG_USER     = os.getenv("PGVECTOR_USER", "campaignos")
PG_PASS     = os.getenv("PGVECTOR_PASSWORD", "campaignos")
PG_DB       = os.getenv("PGVECTOR_DB", "marketing")

_model = None
def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def index_fan_truths(bq_client, pg_cur):
    """Query BigQuery fan_truth_library and upsert into pgvector."""
    from google.cloud import bigquery
    model  = get_model()
    table  = f"{GCP_PROJECT}.{BQ_DATASET}.fan_truth_library"

    try:
        query  = f"SELECT * FROM `{table}` LIMIT 500"
        rows   = list(bq_client.query(query).result())
        print(f"  Found {len(rows)} rows in fan_truth_library")
    except Exception as e:
        print(f"  Skipping fan_truth_library: {e}")
        return 0

    batch = []
    for row in rows:
        statement = row.get("statement", "") or row.get("fan_truth", "") or str(dict(row))
        brand     = row.get("brand", "All") or "All"
        verdict   = row.get("verdict", "PASS") or "PASS"
        overall   = int(row.get("overall_score", 75) or 75)
        text      = f"{brand} fan truth: {statement}"
        emb       = model.encode(text).tolist()
        batch.append((brand, statement, row.get("category", ""), verdict,
                      row.get("specific", 70), row.get("shared", 70),
                      row.get("special", 70), overall, emb))

    if batch:
        # Clear BQ-sourced rows first
        pg_cur.execute("DELETE FROM fan_truths WHERE brand != 'Rnorr' AND brand != 'McDonalds'")
        execute_values(pg_cur,
            """INSERT INTO fan_truths
               (brand, statement, category, verdict, specific, shared, special, overall, embedding)
               VALUES %s ON CONFLICT DO NOTHING""",
            batch,
        )
    return len(batch)


def index_channel_benchmarks(bq_client, pg_cur):
    """Query BigQuery channel_benchmarks and upsert into pgvector."""
    model = get_model()
    table = f"{GCP_PROJECT}.{BQ_DATASET}.channel_benchmarks"

    try:
        rows = list(bq_client.query(f"SELECT * FROM `{table}` LIMIT 200").result())
        print(f"  Found {len(rows)} rows in channel_benchmarks")
    except Exception as e:
        print(f"  Skipping channel_benchmarks: {e}")
        return 0

    batch = []
    for row in rows:
        channel  = str(row.get("channel", ""))
        market   = str(row.get("market", "UK"))
        audience = str(row.get("audience_segment", "All"))
        notes    = str(row.get("notes", ""))
        text     = f"{channel} {market} {audience} performance {notes}"
        emb      = model.encode(text).tolist()
        batch.append((
            channel, market, audience,
            row.get("ctr_pct"), row.get("cpm_gbp"),
            row.get("engagement_pct"), row.get("completion_pct"),
            row.get("avg_dwell_sec"), notes, emb,
        ))

    if batch:
        execute_values(pg_cur,
            """INSERT INTO channel_benchmarks
               (channel, market, audience_segment, ctr_pct, cpm_gbp,
                engagement_pct, completion_pct, avg_dwell_sec, notes, embedding)
               VALUES %s ON CONFLICT DO NOTHING""",
            batch,
        )
    return len(batch)


def index_historical_campaigns(bq_client, pg_cur):
    """Query BigQuery historical_campaigns and upsert into pgvector."""
    model = get_model()
    table = f"{GCP_PROJECT}.{BQ_DATASET}.historical_campaigns"

    try:
        rows = list(bq_client.query(f"SELECT * FROM `{table}` LIMIT 500").result())
        print(f"  Found {len(rows)} rows in historical_campaigns")
    except Exception as e:
        print(f"  Skipping historical_campaigns: {e}")
        return 0

    # Create a BQ campaigns table in pgvector if it doesn't exist
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS bq_campaigns (
            id          SERIAL PRIMARY KEY,
            brand       TEXT,
            campaign_name TEXT,
            product_category TEXT,
            market      TEXT,
            season      TEXT,
            channels    TEXT[],
            reach       BIGINT,
            ctr_pct     NUMERIC(5,2),
            roas        NUMERIC(5,2),
            budget_gbp  NUMERIC(12,2),
            fan_truth   TEXT,
            result      TEXT,
            notes       TEXT,
            embedding   vector(384)
        );
        CREATE INDEX IF NOT EXISTS bqc_emb_idx
            ON bq_campaigns USING hnsw (embedding vector_cosine_ops);
    """)

    batch = []
    for row in rows:
        brand    = str(row.get("brand", ""))
        cat      = str(row.get("product_category", ""))
        market   = str(row.get("market", "UK"))
        season   = str(row.get("season", ""))
        ft       = str(row.get("fan_truth", ""))
        result   = str(row.get("result", ""))
        text     = f"{brand} {cat} {market} {season} campaign {ft} {result}"
        emb      = model.encode(text).tolist()
        batch.append((
            brand, str(row.get("campaign_name", "")), cat, market, season,
            row.get("channels", []),
            row.get("reach"), row.get("ctr_pct"), row.get("roas"),
            row.get("budget_gbp"), ft, result, str(row.get("notes", "")), emb,
        ))

    if batch:
        pg_cur.execute("DELETE FROM bq_campaigns")
        execute_values(pg_cur,
            """INSERT INTO bq_campaigns
               (brand, campaign_name, product_category, market, season, channels,
                reach, ctr_pct, roas, budget_gbp, fan_truth, result, notes, embedding)
               VALUES %s""",
            batch,
        )
    return len(batch)


if __name__ == "__main__":
    from google.cloud import bigquery
    print(f"=== Indexing BigQuery → pgvector RAG (project: {GCP_PROJECT}) ===\n")

    bq = bigquery.Client(project=GCP_PROJECT)
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=PG_DB
    )
    cur = conn.cursor()

    print("1. Fan Truth Library...")
    n1 = index_fan_truths(bq, cur)
    conn.commit()

    print("2. Channel Benchmarks...")
    n2 = index_channel_benchmarks(bq, cur)
    conn.commit()

    print("3. Historical Campaigns...")
    n3 = index_historical_campaigns(bq, cur)
    conn.commit()

    cur.close()
    conn.close()

    print(f"""
=== Done ===
  Fan truths indexed:           {n1}
  Channel benchmarks indexed:   {n2}
  Historical campaigns indexed: {n3}

Real BigQuery data is now in pgvector.
The briefing agent uses this for Fan Truth scoring and KPI validation.
""")
