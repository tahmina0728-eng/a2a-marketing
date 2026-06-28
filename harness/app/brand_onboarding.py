"""
brand_onboarding.py — Upload a new brand's asset folder (as a .zip) and
re-index it into Vertex AI Search, so the briefing agent (Logos) can
immediately retrieve its guidelines and reference assets.

Folder layout expected inside the zip (matches BrandAssetLoader):
  Guidelines/brand_guidelines.md
  Logos/ (or Logo/)
  Font/
  Colours/
  Assets/
  Products/

BigQuery seed tables (historical_campaigns, fan_truth_library, channel_benchmarks)
are intentionally NOT touched here — a brand-new upload has no real campaign
history to extract, and fabricating it would pollute shared benchmark data
that other brands' agents rely on. Those stay manually-seeded as today.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path, PurePosixPath

import structlog

from app.config import get_settings

logger   = structlog.get_logger()
settings = get_settings()

_CATEGORY_DIRS   = {"Guidelines", "Logos", "Logo", "Font", "Colours", "Assets", "Products"}
_SEARCH_DS_ID    = "campaignos-brand-guidelines"
_SEARCH_LOCATION = "global"


def _bucket():
    from google.cloud import storage as _gcs
    return _gcs.Client(project=settings.gcp_project).bucket(settings.gcs_bucket)


def ingest_brand_zip(brand: str, zip_bytes: bytes) -> dict:
    """
    Unzip the given bytes, sort entries by their top-level (or second-level,
    if wrapped in one extra folder) category folder name, and upload each
    into gs://{bucket}/brands/{brand}/{category}/{filename}.

    Returns {"brand", "uploaded": {category: count}, "skipped": [paths]}.
    """
    bucket = _bucket()
    counts: dict[str, int] = {}
    skipped: list[str] = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            # Tolerate a single wrapping folder, e.g. "MyBrand/Guidelines/x.md"
            if len(parts) >= 2 and parts[0] not in _CATEGORY_DIRS and parts[1] in _CATEGORY_DIRS:
                parts = parts[1:]
            if len(parts) < 2:
                skipped.append(info.filename)
                continue
            category, *rest = parts
            filename = rest[-1] if rest else ""
            if category not in _CATEGORY_DIRS or not filename or filename.startswith("."):
                skipped.append(info.filename)
                continue

            data = zf.read(info)
            dest = f"brands/{brand}/{category}/{filename}"
            bucket.blob(dest).upload_from_string(data)
            counts[category] = counts.get(category, 0) + 1

    logger.info("brand_onboarding_uploaded", brand=brand, counts=counts, skipped=len(skipped))
    return {"brand": brand, "uploaded": counts, "skipped": skipped}


def _build_manifest(brand: str, blobs: list) -> str:
    """Plain-text manifest of a brand's assets with their GCS URIs (feeds Vertex AI Search)."""
    bucket_name = settings.gcs_bucket
    logos    = [b for b in blobs if "/Logos/"    in b.name and not b.name.endswith("/")]
    products = [b for b in blobs if "/Products/" in b.name and not b.name.endswith("/")]
    fonts    = [b for b in blobs if "/Font/"     in b.name and not b.name.endswith("/")]
    assets   = [b for b in blobs if "/Assets/"   in b.name and not b.name.endswith("/")]
    colours  = [b for b in blobs if "/Colours/"  in b.name and not b.name.endswith("/")]

    lines = [f"# {brand} Brand Asset Manifest", f"# Source: gs://{bucket_name}/brands/{brand}/", "", "## LOGOS"]
    for b in logos:
        lines.append(f"- {Path(b.name).name}: gs://{bucket_name}/{b.name}")
    lines += ["", "## PRODUCT IMAGES"]
    for i, b in enumerate(products, 1):
        lines.append(f"- Product{i} ({Path(b.name).name}): gs://{bucket_name}/{b.name}")
    lines += ["", "## FONTS"]
    for b in fonts:
        lines.append(f"- {Path(b.name).name}: gs://{bucket_name}/{b.name}")
    lines += ["", "## CAMPAIGN ASSETS / BANNERS"]
    for b in assets:
        lines.append(f"- {Path(b.name).name}: gs://{bucket_name}/{b.name}")
    lines += ["", "## COLOUR SWATCHES"]
    for b in colours:
        lines.append(f"- {Path(b.name).name}: gs://{bucket_name}/{b.name}")
    return "\n".join(lines)


def reindex_brand(brand: str) -> dict:
    """Rebuild the asset manifest for `brand` and trigger a Vertex AI Search re-import."""
    from google.cloud import discoveryengine_v1 as de
    bucket = _bucket()

    blobs    = list(bucket.list_blobs(prefix=f"brands/{brand}/"))
    manifest = _build_manifest(brand, blobs)
    bucket.blob(f"brands/{brand}/manifest.txt").upload_from_string(manifest, content_type="text/plain")

    client = de.DocumentServiceClient()
    parent = (
        f"projects/{settings.gcp_project}/locations/{_SEARCH_LOCATION}"
        f"/collections/default_collection/dataStores/{_SEARCH_DS_ID}/branches/default_branch"
    )
    op = client.import_documents(request=de.ImportDocumentsRequest(
        parent     = parent,
        gcs_source = de.GcsSource(
            input_uris  = [
                f"gs://{settings.gcs_bucket}/brands/*/Guidelines/*.txt",
                f"gs://{settings.gcs_bucket}/brands/*/Guidelines/*.md",
                f"gs://{settings.gcs_bucket}/brands/*/manifest.txt",
            ],
            data_schema = "content",
        ),
        reconciliation_mode = de.ImportDocumentsRequest.ReconciliationMode.FULL,
    ))
    logger.info("brand_onboarding_reindexed", brand=brand, operation=op.operation.name)
    return {"brand": brand, "operation": op.operation.name}
