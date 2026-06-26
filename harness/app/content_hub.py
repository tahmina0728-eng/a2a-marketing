"""
content_hub.py — Persistent library for saved key visuals and reels.

Storage layout in the existing GCS bucket:
  gs://{bucket}/content-hub/items/{item_id}.json   ← metadata record
  gs://{bucket}/content-hub/assets/{item_id}.{ext}  ← the actual image/video bytes

Saving copies whatever the frontend already has in hand (the base64 it just
generated/displayed) into its own namespace — independent of the campaign
pipeline's own output paths, so deleting a hub item never touches campaign data.
"""

from __future__ import annotations

import base64
import json
import time
import uuid

import structlog

from app.config import get_settings

logger   = structlog.get_logger()
settings = get_settings()

_ITEMS_PREFIX  = "content-hub/items/"
_ASSETS_PREFIX = "content-hub/assets/"

_CONTENT_TYPE_EXT = {
    "image/jpeg": "jpg",
    "image/png":  "png",
    "video/mp4":  "mp4",
}


def _bucket():
    from google.cloud import storage as _gcs
    return _gcs.Client(project=settings.gcp_project).bucket(settings.gcs_bucket)


def save_item(
    *,
    kind: str,             # "kv" | "reel"
    brand: str,
    campaign_name: str,
    campaign_id: str,
    headline: str,
    asset_b64: str,
    content_type: str,
) -> dict:
    """Decode the given base64 asset, persist it + metadata to GCS, return the new item."""
    ext = _CONTENT_TYPE_EXT.get(content_type, "bin")
    item_id = uuid.uuid4().hex[:12]
    data = base64.b64decode(asset_b64)

    bucket = _bucket()
    asset_blob = bucket.blob(f"{_ASSETS_PREFIX}{item_id}.{ext}")
    asset_blob.upload_from_string(data, content_type=content_type)

    item = {
        "id":            item_id,
        "kind":          kind,
        "brand":         brand,
        "campaign_name": campaign_name,
        "campaign_id":   campaign_id,
        "headline":      headline,
        "content_type":  content_type,
        "created_at":    time.time(),
    }
    meta_blob = bucket.blob(f"{_ITEMS_PREFIX}{item_id}.json")
    meta_blob.upload_from_string(json.dumps(item), content_type="application/json")

    logger.info("content_hub_saved", item_id=item_id, kind=kind, brand=brand)
    return item


def list_items() -> list[dict]:
    """Return all saved items, newest first."""
    bucket = _bucket()
    items: list[dict] = []
    for blob in bucket.list_blobs(prefix=_ITEMS_PREFIX):
        if not blob.name.endswith(".json"):
            continue
        try:
            items.append(json.loads(blob.download_as_text()))
        except Exception as e:
            logger.warning("content_hub_item_unreadable", blob=blob.name, error=str(e))
    items.sort(key=lambda it: it.get("created_at", 0), reverse=True)
    return items


def get_asset(item_id: str) -> tuple[bytes, str] | None:
    """Return (bytes, content_type) for the given item's asset, or None if missing."""
    bucket = _bucket()
    meta_blob = bucket.blob(f"{_ITEMS_PREFIX}{item_id}.json")
    if not meta_blob.exists():
        return None
    item = json.loads(meta_blob.download_as_text())
    ext = _CONTENT_TYPE_EXT.get(item["content_type"], "bin")
    asset_blob = bucket.blob(f"{_ASSETS_PREFIX}{item_id}.{ext}")
    if not asset_blob.exists():
        return None
    return asset_blob.download_as_bytes(), item["content_type"]


def delete_item(item_id: str) -> bool:
    """Delete the metadata record and its asset. Returns True if the item existed."""
    bucket = _bucket()
    meta_blob = bucket.blob(f"{_ITEMS_PREFIX}{item_id}.json")
    if not meta_blob.exists():
        return False
    try:
        item = json.loads(meta_blob.download_as_text())
        ext = _CONTENT_TYPE_EXT.get(item.get("content_type", ""), "bin")
        bucket.blob(f"{_ASSETS_PREFIX}{item_id}.{ext}").delete()
    except Exception as e:
        logger.warning("content_hub_asset_delete_failed", item_id=item_id, error=str(e))
    meta_blob.delete()
    logger.info("content_hub_deleted", item_id=item_id)
    return True
