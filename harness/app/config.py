"""
config.py — centralised settings for CampaignOS ADK pipeline.

All values loaded from environment variables.
Copy .env.example to .env for local development.
In Cloud Run / Agent Engine these are set via deployment config.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── GCP project ───────────────────────────────────────────────────────
    # Reads GCP_PROJECT or the standard GOOGLE_CLOUD_PROJECT — whichever is set.
    gcp_project: str = Field(
        default="campaignos-prod",
        validation_alias=AliasChoices("gcp_project", "google_cloud_project"),
    )
    gcp_region: str = "europe-west2"

    # ── Gemini models ─────────────────────────────────────────────────────
    # Override via env vars: GEMINI_MODEL_REASONING / GEMINI_MODEL_IMAGE
    gemini_model_reasoning: str = "gemini-3.5-flash"
    gemini_model_image: str = "gemini-3.1-flash-image-preview"
    gemini_model_image_adapter: str = "gemini-3.1-flash-image-preview"
    gemini_model_tts: str = "gemini-3.1-flash-tts-preview"

    # ── Brand assets ──────────────────────────────────────────────────────
    # mode: "local"  → reads from brand_assets_local_path/brands/{brand}/
    #        "gcs"   → reads from gs://{gcs_bucket}/brands/{brand}/
    brand_assets_mode: str = "gcs"
    # Relative path from the project root to the local brand bucket folder.
    # Resolves to rebuild/bucket when running from the rebuild/ directory.
    brand_assets_local_path: str = "bucket"

    # ── Service ───────────────────────────────────────────────────────────
    service_name: str = "campaignos-adk"
    log_level: str = "INFO"
    environment: str = "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
