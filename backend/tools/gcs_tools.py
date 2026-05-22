"""
CampaignOS — GCS Tools
FunctionTools for agents to read/write Google Cloud Storage.
"""
import json
from google.cloud import storage
from google.adk.tools import FunctionTool
import config


_client: storage.Client | None = None

def _gcs() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client(project=config.GCP_PROJECT)
    return _client


@FunctionTool
def load_brand_guidelines() -> str:
    """
    Load McDonald's brand guidelines from GCS.
    Returns the full markdown text of the brand guidelines document.
    Always call this before validating any campaign brief.
    """
    try:
        bucket = _gcs().bucket(config.GCS_BUCKET)
        blob = bucket.blob(config.GCS_BRAND_GUIDELINES)
        content = blob.download_as_text()
        return content
    except Exception as e:
        return f"Brand guidelines not found. Error: {e}. Proceed with standard McDonald's brand principles: golden arches, red/yellow palette, family-friendly, fan-centric voice."


@FunctionTool
def save_json_to_gcs(path: str, data: dict) -> str:
    """
    Save a JSON object to GCS.
    Args:
        path: GCS path within the campaign bucket, e.g. 'briefs/abc123/machine_brief.json'
        data: The dict to save as JSON
    Returns:
        The GCS URI of the saved file (gs://bucket/path)
    """
    bucket = _gcs().bucket(config.GCS_BUCKET)
    blob = bucket.blob(path)
    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json"
    )
    return f"gs://{config.GCS_BUCKET}/{path}"


@FunctionTool
def load_json_from_gcs(path: str) -> dict:
    """
    Load a JSON file from GCS and return it as a dict.
    Args:
        path: GCS path within the campaign bucket
    Returns:
        Parsed JSON as a dict
    """
    bucket = _gcs().bucket(config.GCS_BUCKET)
    blob = bucket.blob(path)
    content = blob.download_as_text()
    return json.loads(content)


@FunctionTool
def upload_image_to_gcs(image_bytes: bytes, path: str, content_type: str = "image/png") -> str:
    """
    Upload raw image bytes to GCS.
    Args:
        image_bytes: Raw image bytes
        path: GCS destination path e.g. 'assets/abc123/kv_concept_1.png'
        content_type: MIME type of the image
    Returns:
        Public URL of the uploaded image
    """
    bucket = _gcs().bucket(config.GCS_BUCKET)
    blob = bucket.blob(path)
    blob.upload_from_string(image_bytes, content_type=content_type)
    # Make publicly readable for frontend display
    blob.make_public()
    return blob.public_url
