"""
upload_kaggle_to_bq.py — Upload Kaggle Customer Personality Analysis to GCS + BigQuery.

Steps:
  1. Upload marketing_campaign.csv to GCS as raw data backup
  2. Load it into BigQuery table briefing_agent.customer_personality
  3. This makes it queryable via SQL + searchable via Search app

Run:
  cd d:/campaignos/harness
  uv run python scripts/upload_kaggle_to_bq.py
"""

import os
from pathlib import Path
from google.cloud import storage, bigquery

PROJECT    = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
BUCKET     = os.getenv("GCS_BUCKET",           "dauntless-karma-497108-b0-campaignos")
BQ_DATASET = os.getenv("BQ_DATASET",           "briefing_agent")
CSV_PATH   = Path(__file__).parent / "marketing_campaign.csv"
GCS_DEST   = "data/kaggle/marketing_campaign.csv"
BQ_TABLE   = f"{PROJECT}.{BQ_DATASET}.customer_personality"


def upload_to_gcs():
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob   = bucket.blob(GCS_DEST)
    blob.upload_from_filename(str(CSV_PATH), content_type="text/csv")
    uri = f"gs://{BUCKET}/{GCS_DEST}"
    print(f"[OK] Uploaded to GCS: {uri}")
    return uri


def load_to_bigquery(gcs_uri: str):
    client = bigquery.Client(project=PROJECT)

    job_config = bigquery.LoadJobConfig(
        source_format       = bigquery.SourceFormat.CSV,
        skip_leading_rows   = 1,
        autodetect          = True,
        write_disposition   = bigquery.WriteDisposition.WRITE_TRUNCATE,
        field_delimiter     = "\t",  # Kaggle file uses tab separator
    )

    load_job = client.load_table_from_uri(
        gcs_uri,
        BQ_TABLE,
        job_config = job_config,
    )
    print(f"Loading into BigQuery table: {BQ_TABLE} ...")
    load_job.result()

    table = client.get_table(BQ_TABLE)
    print(f"[OK] Loaded {table.num_rows:,} rows into {BQ_TABLE}")
    print(f"     Schema: {[f.name for f in table.schema[:8]]}...")


if __name__ == "__main__":
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found")
        exit(1)

    print("=== Uploading Kaggle Customer Personality dataset ===\n")

    print("1. Uploading to GCS...")
    uri = upload_to_gcs()

    print("\n2. Loading into BigQuery...")
    load_to_bigquery(uri)

    print(f"""
=== Done ===
Raw data:  gs://{BUCKET}/{GCS_DEST}
BQ table:  {BQ_TABLE}

You can now query it:
  SELECT * FROM `{BQ_TABLE}` WHERE Income > 70000 LIMIT 10

The pgvector CDP embeddings (customer_insights table) were generated
from this same data — both are now in sync.
""")
