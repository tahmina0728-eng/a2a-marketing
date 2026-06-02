"""
index_brand_assets.py — Index GCS brand asset metadata into Vertex AI Search.

Uploads a brand_assets_manifest.txt per brand to GCS, then imports it into
the Search datastore so the search app knows about logos, fonts, and products.

This lets agents search "Rnorr logo file" and get back the GCS URI.

Run:
  cd d:/campaignos/harness
  uv run python scripts/index_brand_assets.py
"""

import os
from pathlib import Path
from google.cloud import storage, discoveryengine_v1 as de

PROJECT   = os.getenv("GOOGLE_CLOUD_PROJECT", "dauntless-karma-497108-b0")
BUCKET    = os.getenv("GCS_BUCKET", "dauntless-karma-497108-b0-campaignos")
DS_ID     = "campaignos-brand-guidelines"
LOCATION  = "global"


def build_manifest(brand: str, blobs: list) -> str:
    """Build a plain-text manifest of all brand assets with their GCS URIs."""
    logos    = [b for b in blobs if "/Logos/"    in b.name and not b.name.endswith("/")]
    products = [b for b in blobs if "/Products/" in b.name and not b.name.endswith("/")]
    fonts    = [b for b in blobs if "/Font/"     in b.name and not b.name.endswith("/")]
    assets   = [b for b in blobs if "/Assets/"   in b.name and not b.name.endswith("/")]
    colours  = [b for b in blobs if "/Colours/"  in b.name and not b.name.endswith("/")]

    lines = [
        f"# {brand} Brand Asset Manifest",
        f"# Source: gs://{BUCKET}/brands/{brand}/",
        "",
        "## LOGOS",
    ]
    for b in logos:
        lines.append(f"- {Path(b.name).name}: gs://{BUCKET}/{b.name}")

    lines += ["", "## PRODUCT IMAGES"]
    for i, b in enumerate(products, 1):
        lines.append(f"- Product{i} ({Path(b.name).name}): gs://{BUCKET}/{b.name}")

    lines += ["", "## FONTS"]
    for b in fonts:
        lines.append(f"- {Path(b.name).name}: gs://{BUCKET}/{b.name}")

    lines += ["", "## CAMPAIGN ASSETS / BANNERS"]
    for b in assets:
        lines.append(f"- {Path(b.name).name}: gs://{BUCKET}/{b.name}")

    lines += ["", "## COLOUR SWATCHES"]
    for b in colours:
        lines.append(f"- {Path(b.name).name}: gs://{BUCKET}/{b.name}")

    return "\n".join(lines)


if __name__ == "__main__":
    gcs    = storage.Client()
    bucket = gcs.bucket(BUCKET)

    # Find all brands in the bucket
    brands = set()
    for blob in bucket.list_blobs(prefix="brands/"):
        parts = blob.name.split("/")
        if len(parts) > 1 and parts[1]:
            brands.add(parts[1])

    print(f"Found brands: {sorted(brands)}\n")

    for brand in sorted(brands):
        blobs    = list(bucket.list_blobs(prefix=f"brands/{brand}/"))
        manifest = build_manifest(brand, blobs)

        # Upload manifest to GCS as .txt
        dest = f"brands/{brand}/manifest.txt"
        blob = bucket.blob(dest)
        blob.upload_from_string(manifest, content_type="text/plain")
        print(f"[OK] Uploaded: gs://{BUCKET}/{dest}")
        print(f"     Contains: {len([l for l in manifest.split(chr(10)) if l.startswith('-')])} assets\n")

    # Re-import all .txt files (including new manifests) into Search datastore
    print("Triggering Search datastore re-import...")
    client = de.DocumentServiceClient()
    parent = (
        f"projects/{PROJECT}/locations/{LOCATION}"
        f"/collections/default_collection/dataStores/{DS_ID}/branches/default_branch"
    )
    op = client.import_documents(request=de.ImportDocumentsRequest(
        parent     = parent,
        gcs_source = de.GcsSource(
            input_uris  = [f"gs://{BUCKET}/brands/*/Guidelines/*.txt",
                           f"gs://{BUCKET}/brands/*/manifest.txt"],
            data_schema = "content",
        ),
        reconciliation_mode = de.ImportDocumentsRequest.ReconciliationMode.FULL,
    ))
    print(f"[OK] Import triggered: {op.operation.name}")
    print("\nDone. The Search app now knows about all brand assets.")
    print("Agents can search 'Rnorr logo file' and get back GCS URIs.")
