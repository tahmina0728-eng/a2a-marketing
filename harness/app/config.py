"""
config.py — centralised settings for CampaignOS ADK pipeline.

All values loaded from environment variables.
Copy .env.example to .env for local development.
In Cloud Run / Agent Engine these are set via deployment config.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices
from functools import lru_cache


class Settings(BaseSettings):

    # ── GCP project ───────────────────────────────────────────────────────
    # Reads GCP_PROJECT or the standard GOOGLE_CLOUD_PROJECT — whichever is set.
    gcp_project: str = Field(
        default="campaignos-prod",
        validation_alias=AliasChoices("gcp_project", "google_cloud_project"),
    )
    gcp_region: str = Field(
        default="us-central1",
        validation_alias=AliasChoices("gcp_region", "google_cloud_location"),
    )

    # ── Cloud Storage ─────────────────────────────────────────────────────
    # gs://{gcs_bucket}/brands/{brand}/Guidelines/brand_guidelines.md  ← brand rules
    # gs://{gcs_bucket}/outputs/{campaign_id}/machine_brief.json        ← agent outputs
    gcs_bucket:   str = "campaignos-assets"
    outputs_path: str = "outputs"

    # ── BigQuery ──────────────────────────────────────────────────────────
    # Source data (read via Vertex AI Search — not queried directly by agent)
    bq_dataset:          str = "briefing_agent"
    bq_campaigns_table:  str = "historical_campaigns"
    bq_fan_truths_table: str = "fan_truth_library"
    bq_channels_table:   str = "channel_benchmarks"
    # Output audit log (written directly by save tool)
    bq_output_dataset:   str = "campaign_outputs"
    bq_output_table:     str = "machine_briefs"
    # Set BQ_LOGGING_ENABLED=false to skip BigQuery writes (dev / before table exists)
    bq_logging_enabled:  bool = True

    # ── Vertex AI Search ──────────────────────────────────────────────────
    # One Search App with two datastores:
    #   Datastore 1 (GCS):      brands/{brand}/Guidelines/brand_guidelines.md
    #   Datastore 2 (BigQuery): historical_campaigns, fan_truth_library,
    #                           channel_benchmarks
    search_engine_id:            str = "campaignos-briefing-search"
    search_location:             str = "global"
    search_max_results:          int = 10
    search_summary_result_count: int = 5
    # search_mode: "live"      → Vertex AI Search (requires datastore setup)
    #              "gcs_files" → read guidelines from bucket; stub benchmark data
    search_mode:                 str = "live"

    # ── Models ────────────────────────────────────────────────────────────
    # Supports Vertex AI (gemini-2.0-flash-001) or Groq via LiteLLM (groq/llama-3.3-70b-versatile)
    gemini_model_reasoning:       str = "gemini-3.5-flash"
    gemini_model_image:           str = "gemini-3-pro-image"
    gemini_model_image_adapter:   str = "gemini-3-pro-image"
    groq_api_key:                 str = ""

    @property
    def reasoning_model(self):
        if self.gemini_model_reasoning.startswith("groq/"):
            import os
            if self.groq_api_key:
                # Strip BOM, newlines and non-ASCII characters from API key
                clean_key = self.groq_api_key.encode("utf-8").decode("utf-8-sig").strip()
                clean_key = "".join(c for c in clean_key if c.isascii())
                os.environ["GROQ_API_KEY"] = clean_key
            from google.adk.models.lite_llm import LiteLlm
            return LiteLlm(model=self.gemini_model_reasoning)
        return self.gemini_model_reasoning

    # ── Brand assets ──────────────────────────────────────────────────────
    # mode: "local"  → reads from brand_assets_local_path/brands/{brand}/
    #        "gcs"   → reads from gs://{gcs_bucket}/brands/{brand}/
    brand_assets_mode:       str = "local"
    # Relative path from the project root to the local brand bucket folder.
    # Resolves to rebuild/bucket when running from the rebuild/ directory.
    brand_assets_local_path: str = "bucket"

    # ── Service ───────────────────────────────────────────────────────────
    service_name: str = "campaignos-adk"
    log_level:    str = "INFO"
    environment:  str = "production"

    class Config:
        env_file          = ".env"
        env_file_encoding = "utf-8"
        extra             = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
