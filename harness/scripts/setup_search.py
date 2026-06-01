"""
setup_search.py - Create the Vertex AI Search app and GCS datastore.

Run once:
  cd d:/campaignos/harness
  uv run python scripts/setup_search.py

What it creates:
  1. A Vertex AI Search datastore (GCS unstructured) indexing brand guidelines
  2. A Search Engine (app) that queries the datastore
  3. Prints the engine ID to paste into harness/.env as SEARCH_ENGINE_ID
"""

import sys
import time
from google.cloud import discoveryengine_v1 as de
from google.api_core.exceptions import AlreadyExists

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT    = "dauntless-karma-497108-b0"
LOCATION   = "global"
GCS_URI    = "gs://dauntless-karma-497108-b0-campaignos/brands/*/Guidelines/*.md"
DS_ID      = "campaignos-brand-guidelines"
ENGINE_ID  = "campaignos-briefing-search"


def create_datastore():
    client = de.DataStoreServiceClient()
    parent = f"projects/{PROJECT}/locations/{LOCATION}/collections/default_collection"

    datastore = de.DataStore(
        display_name      = "CampaignOS Brand Guidelines",
        industry_vertical = de.IndustryVertical.GENERIC,
        content_config    = de.DataStore.ContentConfig.CONTENT_REQUIRED,
        solution_types    = [de.SolutionType.SOLUTION_TYPE_SEARCH],
    )

    try:
        op = client.create_data_store(
            parent        = parent,
            data_store    = datastore,
            data_store_id = DS_ID,
        )
        print(f"Creating datastore '{DS_ID}'...")
        result = op.result(timeout=120)
        print(f"[OK] Datastore created: {result.name}")
    except AlreadyExists:
        print(f"[OK] Datastore '{DS_ID}' already exists.")


def import_gcs_documents():
    client = de.DocumentServiceClient()
    parent = (
        f"projects/{PROJECT}/locations/{LOCATION}"
        f"/collections/default_collection/dataStores/{DS_ID}/branches/default_branch"
    )

    gcs_source = de.GcsSource(
        input_uris   = [GCS_URI],
        data_schema  = "content",
    )

    request = de.ImportDocumentsRequest(
        parent              = parent,
        gcs_source          = gcs_source,
        reconciliation_mode = de.ImportDocumentsRequest.ReconciliationMode.FULL,
    )

    print(f"Importing from {GCS_URI} ...")
    op     = client.import_documents(request=request)
    result = op.result(timeout=300)
    print(f"[OK] Import complete: {result}")


def create_engine():
    client = de.EngineServiceClient()
    parent = f"projects/{PROJECT}/locations/{LOCATION}/collections/default_collection"

    engine = de.Engine(
        display_name         = "CampaignOS Briefing Search",
        solution_type        = de.SolutionType.SOLUTION_TYPE_SEARCH,
        data_store_ids       = [DS_ID],
        search_engine_config = de.Engine.SearchEngineConfig(
            search_tier = de.SearchTier.SEARCH_TIER_STANDARD,
        ),
    )

    try:
        op = client.create_engine(
            parent    = parent,
            engine    = engine,
            engine_id = ENGINE_ID,
        )
        print(f"Creating search engine '{ENGINE_ID}'...")
        result = op.result(timeout=120)
        print(f"[OK] Engine created: {result.name}")
    except AlreadyExists:
        print(f"[OK] Engine '{ENGINE_ID}' already exists.")


if __name__ == "__main__":
    print("=== Setting up Vertex AI Search for CampaignOS ===\n")
    create_datastore()
    print("Waiting 10s for datastore to be ready...")
    time.sleep(10)
    import_gcs_documents()
    print("Waiting 10s for engine setup...")
    time.sleep(10)
    create_engine()
    print(f"""
=== Done ===
Add this to harness/.env:
  SEARCH_ENGINE_ID={ENGINE_ID}
  SEARCH_MODE=live

Note: Indexing takes 10-30 minutes. Run a test search after that.
""")
