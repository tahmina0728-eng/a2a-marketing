# AI Campaign Production System

Google ADK · FastAPI · React

---

## Quick Start

### 1. GCP Setup (one-time)
```bash
cd infra
# Edit PROJECT_ID in setup_gcp.sh first
chmod +x setup_gcp.sh && ./setup_gcp.sh
```

### 2. Harness
see readme in folder

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## Architecture

```
React UI (localhost:5173)
    ↕ SSE stream + REST
FastAPI (localhost:8000)
    ↕ async
ADK Agents (6 agents, Python)
    ↕
GCS · BigQuery · Vertex AI · Firestore
    ↕
GA4 · Google Ads · Meta APIs (Execution + Performance)
```


## Adding Real Platform APIs (Execution Agent)

In `backend/tools/`, create `platform_tools.py`:

```python
# Instagram (Meta Graph API)
@FunctionTool
def publish_to_instagram(content: dict, targeting: dict) -> dict:
    import requests
    # POST to https://graph.facebook.com/v19.0/{page_id}/media
    # Then POST to /media_publish
    ...

# TikTok (TikTok for Business API)
@FunctionTool  
def publish_to_tiktok(content: dict, targeting: dict) -> dict:
    # TikTok Direct Post API
    ...

# Email (via SendGrid / Mailchimp)
@FunctionTool
def publish_to_email(content: dict, audience: dict) -> dict:
    ...
```

Then add these tools to `execution_agent` in `agents/__init__.py`.

---

## Google Ads API Setup

```bash
# 1. Apply for developer token at:
#    ads.google.com/nav/selectaccount → Tools → API Centre

# 2. Create OAuth2 credentials at Google Cloud Console
#    APIs & Services → Credentials → OAuth 2.0 Client

# 3. Generate refresh token:
pip install google-ads
python -c "
from google.ads.googleads.client import GoogleAdsClient
# Run the OAuth flow to get your refresh token
"

# 4. Add to .env:
# GOOGLE_ADS_DEVELOPER_TOKEN=...
# GOOGLE_ADS_REFRESH_TOKEN=...
```

---

## GA4 Setup

```bash
# 1. Enable Google Analytics Data API in GCP:
gcloud services enable analyticsdata.googleapis.com

# 2. Add your service account as a viewer in GA4:
#    analytics.google.com → Admin → Property Access Management
#    Add: campaignos-sa@YOUR_PROJECT.iam.gserviceaccount.com
#    Role: Viewer

# 3. Get your Property ID:
#    analytics.google.com → Admin → Property Settings → Property ID
#    Format: 123456789 (just the number, not "properties/123456789")

# 4. Add to .env:
# GA4_PROPERTY_ID=properties/123456789
```

---

## Cloud Scheduler (Performance Agent)

```bash
# Deploy Performance Agent as a Cloud Run endpoint:
gcloud run deploy campaignos-performance \
  --source ./backend \
  --region us-central1

# Schedule every 6 hours:
gcloud scheduler jobs create http campaignos-performance \
  --schedule="0 */6 * * *" \
  --uri="https://YOUR_RUN_URL/performance/run" \
  --http-method=POST \
  --time-zone="Australia/Sydney"
```
