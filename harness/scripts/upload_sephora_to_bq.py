"""
upload_sephora_to_bq.py — Upload Sephora products dataset to GCS + BigQuery.

Steps:
  1. Upload product_Sephora.csv to GCS
  2. Load into BigQuery table: briefing_agent.sephora_products
  3. Print summary stats

Run:
  cd d:/campaignos/harness
  uv run python scripts/upload_sephora_to_bq.py
"""

import os
from pathlib import Path
from google.cloud import storage, bigquery

PROJECT    = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
BUCKET     = os.getenv("GCS_BUCKET",           "dauntless-karma-497108-b0-campaignos")
BQ_DATASET = os.getenv("BQ_DATASET",           "briefing_agent")
CSV_PATH   = Path(__file__).parent / "product_Sephora.csv"
GCS_DEST   = "data/sephora/product_Sephora.csv"
BQ_TABLE   = f"{PROJECT}.{BQ_DATASET}.sephora_products"


def upload_to_gcs() -> str:
    print(f"Uploading {CSV_PATH.name} ({CSV_PATH.stat().st_size / 1024 / 1024:.1f} MB) to GCS...")
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob   = bucket.blob(GCS_DEST)
    blob.upload_from_filename(str(CSV_PATH), content_type="text/csv")
    uri = f"gs://{BUCKET}/{GCS_DEST}"
    print(f"[OK] Uploaded: {uri}")
    return uri


def load_to_bigquery(gcs_uri: str):
    client = bigquery.Client(project=PROJECT)

    job_config = bigquery.LoadJobConfig(
        source_format     = bigquery.SourceFormat.CSV,
        skip_leading_rows = 1,
        autodetect        = True,
        write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE,
        field_delimiter   = ",",
        quote_character   = '"',
        allow_quoted_newlines = True,
    )

    print(f"Loading into BigQuery: {BQ_TABLE} ...")
    load_job = client.load_table_from_uri(gcs_uri, BQ_TABLE, job_config=job_config)
    load_job.result()  # Wait for completion

    table = client.get_table(BQ_TABLE)
    print(f"[OK] Loaded {table.num_rows:,} rows, {len(table.schema)} columns")
    print(f"\nSchema:")
    for field in table.schema:
        print(f"  {field.name:<30} {field.field_type}")
    return table


def print_sample(client: bigquery.Client):
    print(f"\nSample rows (hair/volume products):")
    query = f"""
        SELECT product_name, brand_name, rating, reviews, price_usd,
               primary_category, secondary_category, tertiary_category
        FROM `{BQ_TABLE}`
        WHERE LOWER(primary_category) LIKE '%hair%'
           OR LOWER(secondary_category) LIKE '%hair%'
           OR LOWER(tertiary_category) LIKE '%volume%'
           OR LOWER(tertiary_category) LIKE '%curl%'
        LIMIT 10
    """
    try:
        rows = list(client.query(query).result())
        for r in rows:
            print(f"  {r.brand_name} — {r.product_name[:40]} | ${r.price_usd} | ⭐{r.rating}")
    except Exception as e:
        print(f"  (sample query failed — table may still be indexing: {e})")


if __name__ == "__main__":
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found")
        exit(1)

    print("=== Uploading Sephora Products to GCS + BigQuery ===\n")

    gcs_uri = upload_to_gcs()

    print("\nLoading into BigQuery...")
    bq = bigquery.Client(project=PROJECT)
    table = load_to_bigquery(gcs_uri)

    print_sample(bq)

    print(f"""
=== Done ===
GCS:       gs://{BUCKET}/{GCS_DEST}
BigQuery:  {BQ_TABLE}
Rows:      {table.num_rows:,}

Next step: run seed_sephora_cdp.py to embed products into pgvector
for Sunglow (hair care) and Boozt (volume/styling) CDP intelligence.
""")
