"""
CampaignOS — Centralised Configuration
All env vars loaded once here, imported everywhere else.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── GCP ────────────────────────────────────────────────────
GCP_PROJECT     = os.environ["GOOGLE_CLOUD_PROJECT"]
GCP_LOCATION    = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GCS_BUCKET      = os.environ["GCS_BUCKET"]
BQ_DATASET      = os.getenv("BIGQUERY_DATASET", "campaignos")
BQ_PROJECT      = os.getenv("BIGQUERY_PROJECT", GCP_PROJECT)
FIRESTORE_DB    = os.getenv("FIRESTORE_DATABASE", "(default)")

# ── Analytics & Ads ────────────────────────────────────────
GA4_PROPERTY_ID          = os.getenv("GA4_PROPERTY_ID", "")
GOOGLE_ADS_DEV_TOKEN     = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_CLIENT_ID     = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
GOOGLE_ADS_CUSTOMER_ID   = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")

# ── Meta ───────────────────────────────────────────────────
META_ACCESS_TOKEN   = os.getenv("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT_ID  = os.getenv("META_AD_ACCOUNT_ID", "")
META_PAGE_ID        = os.getenv("META_PAGE_ID", "")

# ── App ────────────────────────────────────────────────────
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
DEBUG           = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO")

# ── ADK Models ─────────────────────────────────────────────
# Defaults are for Google AI (Gemini Developer API).
# If using Vertex AI, set versioned IDs in .env:
#   MODEL_FAST=gemini-2.0-flash-001
#   MODEL_SMART=gemini-2.5-pro-preview-05-06
MODEL_FAST   = os.getenv("MODEL_FAST",  "gemini-2.0-flash")
MODEL_SMART  = os.getenv("MODEL_SMART", "gemini-2.5-pro")
MODEL_IMAGE  = os.getenv("MODEL_IMAGE", "imagen-3.0-generate-001")

# ── GCS paths ──────────────────────────────────────────────
GCS_BRAND_GUIDELINES = "brand/brand_guidelines.md"
GCS_BRIEFS_PREFIX    = "briefs"
GCS_ASSETS_PREFIX    = "assets"
