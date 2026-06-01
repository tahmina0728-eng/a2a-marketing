"""
setup_bigquery.py — Create BigQuery dataset + tables and seed from pgvector data.

Creates:
  briefing_agent.fan_truth_library
  briefing_agent.channel_benchmarks
  briefing_agent.historical_campaigns

Then copies the data already in pgvector into BigQuery so both systems are in sync.

Run:
  cd d:\\campaignos\\harness
  uv run python scripts/setup_bigquery.py
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from google.cloud import bigquery
from google.api_core.exceptions import Conflict

GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
BQ_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
BQ_DATASET  = os.getenv("BQ_DATASET", "briefing_agent")

PG_HOST = os.getenv("PGVECTOR_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PGVECTOR_PORT", "5433"))
PG_USER = os.getenv("PGVECTOR_USER", "campaignos")
PG_PASS = os.getenv("PGVECTOR_PASSWORD", "campaignos")
PG_DB   = os.getenv("PGVECTOR_DB", "marketing")


def create_dataset(client: bigquery.Client):
    dataset_id = f"{GCP_PROJECT}.{BQ_DATASET}"
    dataset    = bigquery.Dataset(dataset_id)
    dataset.location = BQ_LOCATION
    try:
        client.create_dataset(dataset, exists_ok=True)
        print(f"  Dataset {dataset_id} ready (location: {BQ_LOCATION})")
    except Conflict:
        print(f"  Dataset {dataset_id} already exists")


def create_fan_truth_table(client: bigquery.Client):
    schema = [
        bigquery.SchemaField("brand",     "STRING"),
        bigquery.SchemaField("statement", "STRING"),
        bigquery.SchemaField("category",  "STRING"),
        bigquery.SchemaField("verdict",   "STRING"),
        bigquery.SchemaField("specific",  "INTEGER"),
        bigquery.SchemaField("shared",    "INTEGER"),
        bigquery.SchemaField("special",   "INTEGER"),
        bigquery.SchemaField("overall",   "INTEGER"),
    ]
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.fan_truth_library"
    table    = bigquery.Table(table_id, schema=schema)
    client.create_table(table, exists_ok=True)
    print(f"  Table {table_id} ready")
    return table_id


def create_channel_benchmarks_table(client: bigquery.Client):
    schema = [
        bigquery.SchemaField("channel",          "STRING"),
        bigquery.SchemaField("market",           "STRING"),
        bigquery.SchemaField("audience_segment", "STRING"),
        bigquery.SchemaField("ctr_pct",          "FLOAT64"),
        bigquery.SchemaField("cpm_gbp",          "FLOAT64"),
        bigquery.SchemaField("engagement_pct",   "FLOAT64"),
        bigquery.SchemaField("completion_pct",   "FLOAT64"),
        bigquery.SchemaField("avg_dwell_sec",    "FLOAT64"),
        bigquery.SchemaField("notes",            "STRING"),
    ]
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.channel_benchmarks"
    table    = bigquery.Table(table_id, schema=schema)
    client.create_table(table, exists_ok=True)
    print(f"  Table {table_id} ready")
    return table_id


def create_historical_campaigns_table(client: bigquery.Client):
    schema = [
        bigquery.SchemaField("brand",            "STRING"),
        bigquery.SchemaField("product_category", "STRING"),
        bigquery.SchemaField("market",           "STRING"),
        bigquery.SchemaField("season",           "STRING"),
        bigquery.SchemaField("channels",         "STRING", mode="REPEATED"),
        bigquery.SchemaField("reach",            "INTEGER"),
        bigquery.SchemaField("ctr_pct",          "FLOAT64"),
        bigquery.SchemaField("roas",             "FLOAT64"),
        bigquery.SchemaField("engagement_pct",   "FLOAT64"),
        bigquery.SchemaField("budget_gbp",       "FLOAT64"),
        bigquery.SchemaField("notes",            "STRING"),
    ]
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.historical_campaigns"
    table    = bigquery.Table(table_id, schema=schema)
    client.create_table(table, exists_ok=True)
    print(f"  Table {table_id} ready")
    return table_id


def _bq_safe(v):
    """Convert psycopg2 types to BigQuery-compatible JSON types."""
    from decimal import Decimal
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, list):
        return [_bq_safe(i) for i in v]
    return v


def _clean_row(row: dict) -> dict:
    return {k: _bq_safe(v) for k, v in row.items() if v is not None}


def seed_from_pgvector(client: bigquery.Client):
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER,
        password=PG_PASS, dbname=PG_DB,
        cursor_factory=RealDictCursor,
    )
    cur = conn.cursor()

    # Fan truths
    cur.execute("SELECT brand, statement, category, verdict, specific, shared, special, overall FROM fan_truths")
    ft_rows = [dict(r) for r in cur.fetchall()]
    if ft_rows:
        client.insert_rows_json(f"{GCP_PROJECT}.{BQ_DATASET}.fan_truth_library", ft_rows)
        print(f"  Inserted {len(ft_rows)} fan truths into BigQuery")

    # Channel benchmarks
    cur.execute("""
        SELECT channel, market, audience_segment, ctr_pct, cpm_gbp,
               engagement_pct, completion_pct, avg_dwell_sec, notes
        FROM channel_benchmarks
    """)
    ch_rows = [_clean_row(dict(r)) for r in cur.fetchall()]
    if ch_rows:
        client.insert_rows_json(f"{GCP_PROJECT}.{BQ_DATASET}.channel_benchmarks", ch_rows)
        print(f"  Inserted {len(ch_rows)} channel benchmarks into BigQuery")

    # Campaign benchmarks
    cur.execute("""
        SELECT brand, product_category, market, season, channels,
               reach, ctr_pct, roas, engagement_pct, budget_gbp, notes
        FROM campaign_benchmarks
    """)
    camp_rows = []
    for r in cur.fetchall():
        row = _clean_row(dict(r))
        row["channels"] = row.get("channels") or []
        camp_rows.append(row)
    if camp_rows:
        client.insert_rows_json(f"{GCP_PROJECT}.{BQ_DATASET}.historical_campaigns", camp_rows)
        print(f"  Inserted {len(camp_rows)} campaign benchmarks into BigQuery")

    cur.close()
    conn.close()


if __name__ == "__main__":
    print(f"=== Setting up BigQuery dataset in {BQ_LOCATION} ===\n")
    client = bigquery.Client(project=GCP_PROJECT)

    print("1. Creating dataset...")
    create_dataset(client)

    print("\n2. Creating tables...")
    create_fan_truth_table(client)
    create_channel_benchmarks_table(client)
    create_historical_campaigns_table(client)

    print("\n3. Seeding from pgvector...")
    seed_from_pgvector(client)

    print(f"""
=== Done ===
BigQuery dataset: {GCP_PROJECT}.{BQ_DATASET}
Location: {BQ_LOCATION}

Tables created and seeded with pgvector data.
Now run: uv run python scripts/index_bigquery.py
to pull the data back into pgvector embeddings.
""")
